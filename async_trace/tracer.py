"""
Core async tracing functionality.

This module implements the async call tracing by monkey-patching asyncio.create_task()
and loop.run_in_executor() to track parent-child relationships between async tasks
and executor calls.
"""

import asyncio
import contextvars
import functools
import threading
import traceback
from typing import Any, Dict, List, Optional

# Track parent relationships and stack traces
_task_parents: Dict[asyncio.Task, Dict[str, Any]] = {}

# Track executor calls (using thread ID as key)
_executor_contexts: Dict[int, Dict[str, Any]] = {}

# Context variable to pass executor info to threads
_executor_context: contextvars.ContextVar[Optional[Dict[str, Any]]] = (
    contextvars.ContextVar("executor_context", default=None)
)

# Store original functions
_orig_create_task = None
_orig_get_event_loop = None
_orig_new_event_loop = None
_patched_loops: Dict[int, Any] = {}  # Track which event loops we've patched
_tracing_enabled = False


def _capture_stack(skip: int = 2) -> List[str]:
    """Capture readable stack trace lines."""
    return traceback.format_list(traceback.extract_stack()[:-skip])


def _traced_create_task(coro, *args, **kwargs) -> asyncio.Task:
    """Intercept asyncio.create_task() to record parent relationships."""
    parent = asyncio.current_task()
    stack = _capture_stack()

    # Also capture the current Python call stack at creation time
    current_stack = traceback.extract_stack()
    call_trace = []
    for frame in reversed(current_stack):
        # Skip internal tracing functions
        if frame.name in ["_traced_create_task", "_capture_stack"]:
            continue
        # Only include frames from user code (not from asyncio internals)
        if not frame.filename.endswith(("asyncio/tasks.py", "asyncio/base_events.py")):
            call_trace.insert(
                0,
                {
                    "name": frame.name,
                    "line": frame.lineno,
                    "code": frame.line,
                    "filename": frame.filename,
                },
            )

    task = _orig_create_task(coro, *args, **kwargs)
    _task_parents[task] = {"parent": parent, "stack": stack, "call_trace": call_trace}
    return task


def _traced_run_in_executor(original_method):
    """Create a traced wrapper for loop.run_in_executor()."""

    @functools.wraps(original_method)
    def wrapper(executor, func, *args):
        """Intercept run_in_executor() to record parent relationships."""
        parent = asyncio.current_task()

        # Capture the current Python call stack at executor call time
        current_stack = traceback.extract_stack()
        call_trace = []
        for frame in reversed(current_stack):
            # Skip internal tracing functions
            if frame.name in ["wrapper", "_traced_run_in_executor", "_capture_stack"]:
                continue
            # Only include frames from user code
            if not frame.filename.endswith(
                ("asyncio/tasks.py", "asyncio/base_events.py", "asyncio/events.py")
            ):
                call_trace.insert(
                    0,
                    {
                        "name": frame.name,
                        "line": frame.lineno,
                        "code": frame.line,
                        "filename": frame.filename,
                    },
                )

        # Create context info to pass to the executor thread
        executor_info = {
            "parent": parent,
            "call_trace": call_trace,
            "func_name": func.__name__ if hasattr(func, "__name__") else str(func),
        }

        # Wrap the function to set up context in the executor thread
        @functools.wraps(func)
        def traced_func(*func_args):
            thread_id = threading.get_ident()
            # Store the context for this thread
            _executor_contexts[thread_id] = executor_info
            _executor_context.set(executor_info)
            try:
                return func(*func_args)
            finally:
                # Clean up after execution
                _executor_contexts.pop(thread_id, None)

        # Call the original run_in_executor with our wrapped function
        return original_method(executor, traced_func, *args)

    return wrapper


def _patch_event_loop(loop):
    """Patch a specific event loop instance to trace run_in_executor calls."""
    loop_id = id(loop)
    if loop_id not in _patched_loops:
        original = loop.run_in_executor
        loop.run_in_executor = _traced_run_in_executor(original)
        _patched_loops[loop_id] = original


def _unpatch_event_loop(loop):
    """Restore the original run_in_executor on a specific event loop."""
    loop_id = id(loop)
    if loop_id in _patched_loops:
        loop.run_in_executor = _patched_loops[loop_id]
        del _patched_loops[loop_id]


def _traced_get_event_loop():
    """Wrapper for asyncio.get_event_loop() that auto-patches returned loops."""
    loop = _orig_get_event_loop()
    if loop and _tracing_enabled:
        _patch_event_loop(loop)
    return loop


def _traced_new_event_loop():
    """Wrapper for asyncio.new_event_loop() that auto-patches created loops."""
    loop = _orig_new_event_loop()
    if loop and _tracing_enabled:
        _patch_event_loop(loop)
    return loop


def enable_tracing():
    """
    Enable async call tracing by monkey-patching asyncio.create_task() and
    loop.run_in_executor().
    """
    global _orig_create_task, _orig_get_event_loop, _orig_new_event_loop, _tracing_enabled

    if _tracing_enabled:
        return

    # Patch create_task
    _orig_create_task = asyncio.create_task
    asyncio.create_task = _traced_create_task

    # Patch event loop getters to auto-patch loops
    _orig_get_event_loop = asyncio.get_event_loop
    _orig_new_event_loop = asyncio.new_event_loop
    asyncio.get_event_loop = _traced_get_event_loop
    asyncio.new_event_loop = _traced_new_event_loop

    # Patch the current event loop if one exists
    try:
        loop = asyncio.get_running_loop()
        _patch_event_loop(loop)
    except RuntimeError:
        # No running loop yet - we'll patch it via get/new_event_loop wrappers
        pass

    _tracing_enabled = True


def disable_tracing():
    """
    Disable async call tracing by restoring the original asyncio.create_task()
    and loop.run_in_executor().
    """
    global _tracing_enabled

    if not _tracing_enabled:
        return

    # Restore create_task
    asyncio.create_task = _orig_create_task

    # Restore event loop getters
    if _orig_get_event_loop:
        asyncio.get_event_loop = _orig_get_event_loop
    if _orig_new_event_loop:
        asyncio.new_event_loop = _orig_new_event_loop

    # Restore all patched event loops
    try:
        loop = asyncio.get_running_loop()
        _unpatch_event_loop(loop)
    except RuntimeError:
        pass

    # Clear any remaining patched loops
    # Note: we can't easily restore loop objects from IDs after the loop is gone
    # The loops will be garbage collected naturally
    _patched_loops.clear()

    _tracing_enabled = False


def collect_async_trace() -> Dict[str, Any]:
    """
    Collect structured async call trace data as a flat list of frames.

    Returns:
        dict: Trace data structure with the following keys:
            - 'frames': List of frame dicts (innermost → outermost), each containing:
                - 'name': str - Function/task name
                - 'line': int | None - Line number (None for root task)
                - 'filename': str | None - Full file path (None for root task)
                - 'indent': int - 0=innermost, higher=outermost
                - 'task': Task | None - Task object if this frame creates/is a task
                - 'is_executor': bool - True if this is an executor call
            - 'current_task': Task | None - The current asyncio task (None if in executor)
            - 'in_executor': bool - True if currently running in an executor thread

    Notes:
        - Frames are ordered from innermost (current execution) to outermost (root)
        - Task boundaries are marked by frames where 'task' is not None
        - All frames have the same structure (some fields may be None)
        - Can be called from executor threads - will trace back to the calling async task
    """
    # Ensure the current loop is patched (if we're in an async context)
    try:
        loop = asyncio.get_running_loop()
        if _tracing_enabled and id(loop) not in _patched_loops:
            _patch_event_loop(loop)
    except RuntimeError:
        # Not in an async context, might be in an executor thread
        pass

    # Check if we're in an executor thread
    thread_id = threading.get_ident()
    executor_info = _executor_contexts.get(thread_id)
    in_executor = executor_info is not None

    if in_executor:
        # In executor thread - get parent task from context
        current_task = executor_info.get("parent") if executor_info else None
    else:
        # In async context - get current task
        try:
            current_task = asyncio.current_task()
        except RuntimeError:
            # No running loop (shouldn't happen if tracing is used correctly)
            current_task = None

    # Build the task chain hierarchy first
    task_chain = []
    task = current_task
    visited_tasks = set()

    while task and task not in visited_tasks:
        task_info = _task_parents.get(task, {})

        task_data = {
            "task": task,
            "name": (
                task.get_name() if hasattr(task, "get_name") else f"Task-{id(task)}"
            ),
            "is_current": task == current_task,
            "is_done": task.done() if hasattr(task, "done") else False,
            "parent": task_info.get("parent"),
            "call_trace": task_info.get("call_trace", []),
            "creation_stack": task_info.get("stack", []),
        }

        task_chain.insert(0, task_data)
        visited_tasks.add(task)
        task = task_info.get("parent")

    # Collect current call stack (frames within current context - task or executor)
    stack_frames = traceback.extract_stack()

    if in_executor:
        # When in executor, collect stack frames from the executor thread
        current_stack = []
        for frame in stack_frames:
            # Skip internal tracing functions and wrapper
            if frame.name in [
                "collect_async_trace",
                "print_async_trace",
                "print_trace",
                "traced_func",
                "wrapper",
                "_traced_run_in_executor",
            ]:
                continue
            # Only include user code frames
            if not frame.filename.endswith(
                (
                    "tracer.py",
                    "asyncio/tasks.py",
                    "asyncio/base_events.py",
                    "concurrent/futures/thread.py",
                    "threading.py",
                )
            ):
                current_stack.append(
                    {
                        "name": frame.name,
                        "line": frame.lineno,
                        "code": frame.line,
                        "filename": frame.filename,
                    }
                )
    else:
        # Normal async task context
        task_info = _task_parents.get(current_task, {})
        call_trace = task_info.get("call_trace", [])

        # Find where the current task starts in the stack
        creation_frame_indices = set()
        if call_trace:
            for i, frame in enumerate(stack_frames):
                for trace_frame in call_trace:
                    if (
                        frame.name == trace_frame["name"]
                        and frame.lineno == trace_frame["line"]
                    ):
                        creation_frame_indices.add(i)

        max_creation_idx = max(creation_frame_indices) if creation_frame_indices else -1

        current_stack = []
        for i, frame in enumerate(stack_frames):
            if i <= max_creation_idx:
                continue
            # Skip internal tracing functions
            if frame.name in [
                "collect_async_trace",
                "print_async_trace",
                "print_trace",
            ]:
                continue
            # Only include user code frames
            if not frame.filename.endswith(
                ("tracer.py", "asyncio/tasks.py", "asyncio/base_events.py")
            ):
                current_stack.append(
                    {
                        "name": frame.name,
                        "line": frame.lineno,
                        "code": frame.line,
                        "filename": frame.filename,
                    }
                )

    # Now flatten everything into a simple linear trace with unified structure
    frames = []
    indent = 0

    for task_data in task_chain:
        call_trace = task_data["call_trace"]
        is_current = task_data["is_current"]

        # If no call trace, it's a root task
        if not call_trace:
            frames.append(
                {
                    "name": task_data["name"],
                    "line": None,
                    "filename": None,
                    "indent": indent,
                    "task": task_data["task"],
                    "is_executor": False,
                }
            )
            indent += 1

            # Add executor frames if this is the current task and we're in an executor
            if is_current and in_executor:
                executor_call_trace = executor_info.get("call_trace", [])
                for trace_frame in executor_call_trace:
                    is_executor_boundary = trace_frame == executor_call_trace[-1]
                    frames.append(
                        {
                            "name": trace_frame["name"],
                            "line": trace_frame["line"],
                            "filename": trace_frame.get("filename"),
                            "indent": indent,
                            "task": None,
                            "is_executor": is_executor_boundary,
                        }
                    )
                    indent += 1

                # Add current stack frames from executor thread
                for frame_data in current_stack:
                    frames.append(
                        {
                            "name": frame_data["name"],
                            "line": frame_data["line"],
                            "filename": frame_data.get("filename"),
                            "indent": indent,
                            "task": None,
                            "is_executor": False,
                        }
                    )
                    indent += 1
            # Add current stack frames if this is the current root task (not executor)
            elif is_current:
                for frame_data in current_stack:
                    frames.append(
                        {
                            "name": frame_data["name"],
                            "line": frame_data["line"],
                            "filename": frame_data.get("filename"),
                            "indent": indent,
                            "task": None,
                            "is_executor": False,
                        }
                    )
                    indent += 1
        else:
            # Add call trace frames
            for j, trace_frame in enumerate(call_trace):
                is_last = j == len(call_trace) - 1

                if is_last:
                    # This is the task creation point - mark with task boundary
                    frames.append(
                        {
                            "name": trace_frame["name"],
                            "line": trace_frame["line"],
                            "filename": trace_frame.get("filename"),
                            "indent": indent,
                            "task": task_data["task"],
                            "is_executor": False,
                        }
                    )
                    indent += 1

                    # Add executor frames if this is the current task and we're in an executor
                    if is_current and in_executor:
                        executor_call_trace = executor_info.get("call_trace", [])
                        for trace_frame in executor_call_trace:
                            is_executor_boundary = trace_frame == executor_call_trace[-1]
                            frames.append(
                                {
                                    "name": trace_frame["name"],
                                    "line": trace_frame["line"],
                                    "filename": trace_frame.get("filename"),
                                    "indent": indent,
                                    "task": None,
                                    "is_executor": is_executor_boundary,
                                }
                            )
                            indent += 1

                        # Add current stack frames from executor thread
                        for frame_data in current_stack:
                            frames.append(
                                {
                                    "name": frame_data["name"],
                                    "line": frame_data["line"],
                                    "filename": frame_data.get("filename"),
                                    "indent": indent,
                                    "task": None,
                                    "is_executor": False,
                                }
                            )
                            indent += 1
                    # Add current stack frames if this is the current task (not executor)
                    elif is_current:
                        for frame_data in current_stack:
                            frames.append(
                                {
                                    "name": frame_data["name"],
                                    "line": frame_data["line"],
                                    "filename": frame_data.get("filename"),
                                    "indent": indent,
                                    "task": None,
                                    "is_executor": False,
                                }
                            )
                            indent += 1
                else:
                    # Regular call frame
                    frames.append(
                        {
                            "name": trace_frame["name"],
                            "line": trace_frame["line"],
                            "filename": trace_frame.get("filename"),
                            "indent": indent,
                            "task": None,
                            "is_executor": False,
                        }
                    )
                    indent += 1

    # Reverse frames to go from inner (current) to outer (root)
    frames.reverse()

    # Recalculate indents for the reversed order
    max_indent = max((f["indent"] for f in frames), default=0)
    for frame in frames:
        frame["indent"] = max_indent - frame["indent"]

    return {"frames": frames, "current_task": current_task, "in_executor": in_executor}


def print_async_trace(trace_data: Dict[str, Any]):
    """
    Print the structured async trace data (inner → outer).

    Args:
        trace_data: The trace data dict returned by collect_async_trace()
    """
    frames = trace_data["frames"]
    for frame in frames:
        indent = "  " * frame["indent"]
        name = frame["name"]
        line = frame["line"]
        filename = frame.get("filename")
        is_executor = frame.get("is_executor", False)

        # Add executor marker if this is an executor call
        executor_marker = " [EXECUTOR]" if is_executor else ""

        # Format the line info
        if line is not None:
            # Show shortened filename if available
            file_display = ""
            if filename:
                file_display = f" [{filename}]"

            print(f"{indent}↑ {name}() at line {line}{file_display}{executor_marker}")
        else:
            # Root task without line number
            print(f"{indent}↑ {name}{executor_marker}")


def print_trace():
    """Convenience function to collect and print the async call trace."""
    trace_data = collect_async_trace()
    print_async_trace(trace_data)
