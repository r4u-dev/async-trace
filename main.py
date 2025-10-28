"""
Async Call Tracing

Tracks async task creation and execution paths to help debug async code.

Public API:
  - collect_async_trace() -> dict: Collect structured trace data
  - print_async_trace(trace_data): Print formatted trace
  - print_trace(): Convenience function (collect + print)

Trace data structure:
  {
    'task_chain': [list of task info dicts],
    'current_stack': [list of frame info dicts],
    'current_task': <Task object>
  }
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
                'code': frame.line
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
    t = asyncio.create_task(worker(), name="worker-task")
    await t

async def main():
    await sub_task()
    
    print("\n=== In Main ===")
    print_trace()

def collect_async_trace():
    """Collect structured async call trace data."""
    current_task = asyncio.current_task()
    
    # Build the task chain hierarchy
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
    current_stack = []
    
    # Get the task creation context
    task_info = task_parents.get(current_task, {})
    call_trace = task_info.get('call_trace', [])
    
    # If this task has a call_trace, find where it starts in the stack
    # Frames that appear BEFORE the creation point belong to parent tasks
    creation_frame_indices = set()
    if call_trace:
        for i, frame in enumerate(stack_frames):
            for trace_frame in call_trace:
                if (frame.name == trace_frame['name'] and 
                    frame.lineno == trace_frame['line']):
                    creation_frame_indices.add(i)
    
    # Collect only frames AFTER the creation point (i.e., within current task)
    max_creation_idx = max(creation_frame_indices) if creation_frame_indices else -1
    
    for i, frame in enumerate(stack_frames):
        # Only collect frames after the creation point
        if i <= max_creation_idx:
            continue
            
        # Skip internal tracing code
        if frame.filename.endswith('main.py') and frame.name not in [
            'collect_async_trace', 'print_async_trace', 'print_trace'
        ]:
            current_stack.append({
                'name': frame.name,
                'line': frame.lineno,
                'code': frame.line,
                'filename': frame.filename
            })
    
    return {
        'task_chain': task_chain,
        'current_stack': current_stack,
        'current_task': current_task
    }


def print_async_trace(trace_data):
    """Print the structured async trace data."""
    task_chain = trace_data['task_chain']
    current_stack = trace_data['current_stack']
    current_task = trace_data['current_task']
    
    # Print the unified async execution path
    print("📋 Async Execution Path:")
    
    indent_level = 0
    for task_data in task_chain:
        name = task_data['name']
        call_trace = task_data['call_trace']
        is_current = task_data['is_current']
        
        # If no call trace, this is likely the root task
        if not call_trace:
            indent = "  " * indent_level
            if is_current:
                marker = "🟢"
                status = " [current task, root]"
            else:
                marker = "⚪"
                status = " [root task]"
            print(f"{indent}{marker} {name}{status}")
            indent_level += 1
            
            # For current root task, show the current call stack inline
            if is_current and current_stack:
                for frame_data in current_stack:
                    indent = "  " * indent_level
                    frame_name = frame_data['name']
                    frame_line = frame_data['line']
                    frame_code = frame_data.get('code', '')
                    
                    print(f"{indent}→ {frame_name}() at line {frame_line}")
                    if frame_code:
                        print(f"{indent}  {frame_code.strip()[:60]}")
                    indent_level += 1
            continue
        
        # Show each frame in the call trace
        for j, trace_frame in enumerate(call_trace):
            indent = "  " * indent_level
            frame_name = trace_frame['name']
            frame_line = trace_frame['line']
            frame_code = trace_frame.get('code', '')
            
            # Last frame in the trace is where the task was created
            if j == len(call_trace) - 1:
                if is_current:
                    marker = "🟢"
                    status = " [current task]"
                else:
                    marker = "⚪"
                    status = ""
                print(f"{indent}{marker} {frame_name}() created task '{name}'{status}")
                
                # For current task, continue with the current call stack
                if is_current and current_stack:
                    indent_level += 1
                    for frame_data in current_stack:
                        indent = "  " * indent_level
                        call_name = frame_data['name']
                        call_line = frame_data['line']
                        call_code = frame_data.get('code', '')
                        
                        print(f"{indent}→ {call_name}() at line {call_line}")
                        if call_code:
                            print(f"{indent}  {call_code.strip()[:60]}")
                        indent_level += 1
            else:
                print(f"{indent}→ {frame_name}() at line {frame_line}")
            
            if frame_code and j < len(call_trace) - 1:
                print(f"{indent}  {frame_code.strip()[:75]}")
            
            indent_level += 1


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
    print(f"📊 Task chain depth: {len(trace_data['task_chain'])}")
    print(f"📊 Current stack depth: {len(trace_data['current_stack'])}")
    
    # You can now process this data however you want
    # For example, export to JSON, filter specific tasks, etc.
    
    print("\n📋 Task Chain (ancestry):")
    for task_data in trace_data['task_chain']:
        marker = "🟢" if task_data['is_current'] else "⚪"
        status = "done" if task_data['is_done'] else "running"
        print(f"  {marker} {task_data['name']} ({status})")
    
    print("\n📞 Current Call Stack:")
    for frame in trace_data['current_stack']:
        print(f"  → {frame['name']}() at line {frame['line']}")


# Run example
if __name__ == "__main__":
    asyncio.run(main())
