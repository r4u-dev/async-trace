"""
Async Call Tracing

Tracks async task creation and execution paths to help debug async code.

Public API:
  - collect_async_trace() -> dict: Collect structured trace data
  - print_async_trace(trace_data): Print formatted trace
  - print_trace(): Convenience function (collect + print)

Trace data structure (flat list of frames, innermost → outermost):
  {
    'frames': [
      {
        'name': str,                    # Function/task name
        'line': int | None,             # Line number (None for root task)
        'filename': str | None,         # Full file path (None for root task)
        'indent': int,                  # 0=innermost, higher=outermost
        'task': <Task object> | None,   # Task object if this frame creates/is a task
      }
    ],
    'current_task': <Task object>
  }
  
  Notes:
  - Frames are ordered from innermost (current execution) to outermost (root)
  - Task boundaries are marked by frames where 'task' is not None
  - All frames have the same structure (some fields may be None)
"""
import asyncio, traceback

# Track parent relationships and stack traces
task_parents = {}

def capture_stack(skip=2):
    """Capture readable stack trace lines."""
    return traceback.format_list(traceback.extract_stack()[:-skip])

# Keep reference to the original function
_orig_create_task = asyncio.create_task

def traced_create_task(coro, *args, **kwargs):
    """Intercept asyncio.create_task() to record parent relationships."""
    parent = asyncio.current_task()
    stack = capture_stack()
    
    # Also capture the current Python call stack at creation time
    current_stack = traceback.extract_stack()
    call_trace = []
    for frame in reversed(current_stack):
        if frame.filename.endswith('main.py') and frame.name not in ['traced_create_task', 'capture_stack']:
            call_trace.insert(0, {
                'name': frame.name,
                'line': frame.lineno,
                'code': frame.line,
                'filename': frame.filename
            })
    
    task = _orig_create_task(coro, *args, **kwargs)
    task_parents[task] = {
        "parent": parent,
        "stack": stack,
        "call_trace": call_trace  # Store the calling path
    }
    return task

# Apply monkey patch
asyncio.create_task = traced_create_task

async def inner_task():
    print("\n=== In Inner Task ===")
    print_trace()
    await asyncio.sleep(1)

async def worker():
    await inner_task()

async def sub_task():
    t = asyncio.create_task(worker())
    await t

async def main():
    await sub_task()
    
    print("\n=== In Main ===")
    print_trace()

def collect_async_trace():
    """Collect structured async call trace data as a flat list of frames."""
    current_task = asyncio.current_task()
    
    # Build the task chain hierarchy first
    task_chain = []
    task = current_task
    visited_tasks = set()
    
    while task and task not in visited_tasks:
        task_info = task_parents.get(task, {})
        
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
    task_info = task_parents.get(current_task, {})
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
        if frame.filename.endswith('main.py') and frame.name not in [
            'collect_async_trace', 'print_async_trace', 'print_trace'
        ]:
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


def print_async_trace(trace_data):
    """Print the structured async trace data (inner → outer)."""
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
                import os
                file_display = f" [{os.path.basename(filename)}]"
            
            print(f"{indent}↑ {name}() at line {line}{file_display}")
        else:
            # Root task without line number
            print(f"{indent}↑ {name}")


def print_trace():
    """Collect and print the async call trace."""
    trace_data = collect_async_trace()
    print_async_trace(trace_data)

# Example: Using structured trace data
async def example_structured_trace():
    """Example showing how to use structured trace data."""
    await sub_task()
    
    # Collect structured data without printing
    trace_data = collect_async_trace()
    
    print("\n=== Using Structured Trace Data ===")
    print(f"📊 Current task: {trace_data['current_task'].get_name()}")
    print(f"📊 Total frames: {len(trace_data['frames'])}")
    
    # All frames have the same structure - super simple!
    
    print("\n📋 Frames (innermost → outermost):")
    for i, frame in enumerate(trace_data['frames']):
        indent = "  " * frame['indent']
        line_info = f" at line {frame['line']}" if frame['line'] else ""
        task_marker = " [TASK]" if frame['task'] else ""
        print(f"{indent}[{i}] {frame['name']}(){line_info}{task_marker}")
    
    # First frame is the innermost (current execution point)
    print("\n📍 Current Execution (first frame):")
    if trace_data['frames']:
        first = trace_data['frames'][0]
        line_info = f" at line {first['line']}" if first['line'] else ""
        print(f"  → {first['name']}(){line_info}")
    
    # Last frame is the outermost (root)
    print("\n🌳 Root Task (last frame):")
    if trace_data['frames']:
        last = trace_data['frames'][-1]
        print(f"  → {last['name']}")
    
    # Easy to filter - e.g., find all task boundaries
    print("\n🔍 Task Boundaries:")
    for frame in trace_data['frames']:
        if frame['task']:
            line_info = f" at line {frame['line']}" if frame['line'] else ""
            print(f"  - {frame['name']}(){line_info} → Task: {frame['task'].get_name()}")


# Run example
if __name__ == "__main__":
    asyncio.run(main())
