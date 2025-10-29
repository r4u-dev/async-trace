"""
Core async tracing functionality.

This module implements the async call tracing by monkey-patching asyncio.create_task()
to track parent-child relationships between async tasks.
"""

import asyncio
import traceback
from typing import Dict, List, Any


# Track parent relationships and stack traces
_task_parents: Dict[asyncio.Task, Dict[str, Any]] = {}

# Store original create_task function
_orig_create_task = None
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
        if frame.name in ['_traced_create_task', '_capture_stack']:
            continue
        # Only include frames from user code (not from asyncio internals)
        if not frame.filename.endswith(('asyncio/tasks.py', 'asyncio/base_events.py')):
            call_trace.insert(0, {
                'name': frame.name,
                'line': frame.lineno,
                'code': frame.line,
                'filename': frame.filename
            })
    
    task = _orig_create_task(coro, *args, **kwargs)
    _task_parents[task] = {
        "parent": parent,
        "stack": stack,
        "call_trace": call_trace
    }
    return task


def enable_tracing():
    """Enable async call tracing by monkey-patching asyncio.create_task()."""
    global _orig_create_task, _tracing_enabled
    
    if _tracing_enabled:
        return
    
    _orig_create_task = asyncio.create_task
    asyncio.create_task = _traced_create_task
    _tracing_enabled = True


def disable_tracing():
    """Disable async call tracing by restoring the original asyncio.create_task()."""
    global _tracing_enabled
    
    if not _tracing_enabled:
        return
    
    asyncio.create_task = _orig_create_task
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
            - 'current_task': Task - The current asyncio task
    
    Notes:
        - Frames are ordered from innermost (current execution) to outermost (root)
        - Task boundaries are marked by frames where 'task' is not None
        - All frames have the same structure (some fields may be None)
    """
    current_task = asyncio.current_task()
    
    # Build the task chain hierarchy first
    task_chain = []
    task = current_task
    visited_tasks = set()
    
    while task and task not in visited_tasks:
        task_info = _task_parents.get(task, {})
        
        task_data = {
            'task': task,
            'name': task.get_name() if hasattr(task, 'get_name') else f"Task-{id(task)}",
            'is_current': task == current_task,
            'is_done': task.done() if hasattr(task, 'done') else False,
            'parent': task_info.get('parent'),
            'call_trace': task_info.get('call_trace', []),
            'creation_stack': task_info.get('stack', [])
        }
        
        task_chain.insert(0, task_data)
        visited_tasks.add(task)
        task = task_info.get("parent")
    
    # Collect current call stack (only frames within the current task)
    stack_frames = traceback.extract_stack()
    task_info = _task_parents.get(current_task, {})
    call_trace = task_info.get('call_trace', [])
    
    # Find where the current task starts in the stack
    creation_frame_indices = set()
    if call_trace:
        for i, frame in enumerate(stack_frames):
            for trace_frame in call_trace:
                if (frame.name == trace_frame['name'] and 
                    frame.lineno == trace_frame['line']):
                    creation_frame_indices.add(i)
    
    max_creation_idx = max(creation_frame_indices) if creation_frame_indices else -1
    
    current_stack = []
    for i, frame in enumerate(stack_frames):
        if i <= max_creation_idx:
            continue
        # Skip internal tracing functions
        if frame.name in ['collect_async_trace', 'print_async_trace', 'print_trace']:
            continue
        # Only include user code frames
        if not frame.filename.endswith(('tracer.py', 'asyncio/tasks.py', 'asyncio/base_events.py')):
            current_stack.append({
                'name': frame.name,
                'line': frame.lineno,
                'code': frame.line,
                'filename': frame.filename
            })
    
    # Now flatten everything into a simple linear trace with unified structure
    frames = []
    indent = 0
    
    for task_data in task_chain:
        call_trace = task_data['call_trace']
        is_current = task_data['is_current']
        
        # If no call trace, it's a root task
        if not call_trace:
            frames.append({
                'name': task_data['name'],
                'line': None,
                'filename': None,
                'indent': indent,
                'task': task_data['task']
            })
            indent += 1
            
            # Add current stack frames if this is the current root task
            if is_current:
                for frame_data in current_stack:
                    frames.append({
                        'name': frame_data['name'],
                        'line': frame_data['line'],
                        'filename': frame_data.get('filename'),
                        'indent': indent,
                        'task': None
                    })
                    indent += 1
        else:
            # Add call trace frames
            for j, trace_frame in enumerate(call_trace):
                is_last = j == len(call_trace) - 1
                
                if is_last:
                    # This is the task creation point - mark with task boundary
                    frames.append({
                        'name': trace_frame['name'],
                        'line': trace_frame['line'],
                        'filename': trace_frame.get('filename'),
                        'indent': indent,
                        'task': task_data['task']
                    })
                    indent += 1
                    
                    # Add current stack frames if this is the current task
                    if is_current:
                        for frame_data in current_stack:
                            frames.append({
                                'name': frame_data['name'],
                                'line': frame_data['line'],
                                'filename': frame_data.get('filename'),
                                'indent': indent,
                                'task': None
                            })
                            indent += 1
                else:
                    # Regular call frame
                    frames.append({
                        'name': trace_frame['name'],
                        'line': trace_frame['line'],
                        'filename': trace_frame.get('filename'),
                        'indent': indent,
                        'task': None
                    })
                    indent += 1
    
    # Reverse frames to go from inner (current) to outer (root)
    frames.reverse()
    
    # Recalculate indents for the reversed order
    max_indent = max((f['indent'] for f in frames), default=0)
    for frame in frames:
        frame['indent'] = max_indent - frame['indent']
    
    return {
        'frames': frames,
        'current_task': current_task
    }


def print_async_trace(trace_data: Dict[str, Any]):
    """
    Print the structured async trace data (inner → outer).
    
    Args:
        trace_data: The trace data dict returned by collect_async_trace()
    """
    frames = trace_data['frames']
    for frame in frames:
        indent = "  " * frame['indent']
        name = frame['name']
        line = frame['line']
        filename = frame.get('filename')
        
        # Format the line info
        if line is not None:
            # Show shortened filename if available
            file_display = ""
            if filename:
                file_display = f" [{filename}]"
            
            print(f"{indent}↑ {name}() at line {line}{file_display}")
        else:
            # Root task without line number
            print(f"{indent}↑ {name}")


def print_trace():
    """Convenience function to collect and print the async call trace."""
    trace_data = collect_async_trace()
    print_async_trace(trace_data)

