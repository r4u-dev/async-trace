# async-trace

**Call stack frames for asyncio tasks, just like Python's traceback for sync code**

When debugging synchronous Python code, you use `traceback` to see the call stack. But for asyncio code, tasks can be created from anywhere, making it hard to understand the execution flow. `async-trace` solves this by providing call stack frames that show the complete path from task creation to execution—giving you the same debugging power for async code that Python's traceback provides for sync code.

## Features

- 📚 **Stack Frames for Async**: Get call stack frames for asyncio tasks, similar to `traceback` for sync code
- 🔍 **Complete Call Path**: See the full execution path from current task back to the root
- 📊 **Structured Frame Data**: Access frames programmatically with line numbers, filenames, and task info
- 🎯 **Zero Configuration**: Just import and call `print_trace()` - that's it!
- 🪶 **Lightweight**: Minimal overhead, no external dependencies
- 🐍 **Python 3.8+**: Works with modern Python versions

## Installation

```bash
pip install async-trace
```

## Quick Start

Just like you'd use `traceback.print_stack()` for sync code, use `print_trace()` for async:

```python
import asyncio
from async_trace import print_trace

async def worker():
    print_trace()  # Shows the async call stack!
    await asyncio.sleep(1)

async def main():
    await asyncio.create_task(worker())

asyncio.run(main())
```

Output shows the complete async call stack:
```
↑ worker() at line 6 [example.py]
  ↑ main() at line 10 [example.py]
    ↑ Task-1
```

Each line is a frame showing the function name, line number, and file—just like a traceback!

## Usage

### Simple Tracing

The easiest way to use `async-trace` is with the `print_trace()` function:

```python
import asyncio
from async_trace import print_trace

async def inner_task():
    print("\n=== Current execution path ===")
    print_trace()
    await asyncio.sleep(0.1)

async def worker():
    await inner_task()

async def sub_task():
    t = asyncio.create_task(worker())
    await t

async def main():
    await sub_task()

asyncio.run(main())
```

### Structured Trace Data

For programmatic analysis, use `collect_async_trace()`:

```python
import asyncio
from async_trace import collect_async_trace

async def worker():
    trace_data = collect_async_trace()
    
    # Access structured data
    print(f"Current task: {trace_data['current_task'].get_name()}")
    print(f"Total frames: {len(trace_data['frames'])}")
    
    # Iterate through frames (innermost to outermost)
    for frame in trace_data['frames']:
        print(f"{frame['name']} at line {frame['line']}")
        if frame['task']:
            print(f"  → Creates task: {frame['task'].get_name()}")

async def main():
    await asyncio.create_task(worker())

asyncio.run(main())
```

### Trace Data Structure

The `collect_async_trace()` function returns a dict with:

```python
{
    'frames': [
        {
            'name': str,              # Function/task name
            'line': int | None,       # Line number (None for root)
            'filename': str | None,   # File path (None for root)
            'indent': int,            # Indentation level (0 = innermost)
            'task': Task | None,      # Task object if this creates a task
        },
        # ... more frames (innermost → outermost)
    ],
    'current_task': Task  # The current asyncio task
}
```

## Advanced Usage

### Enable/Disable Tracing

Tracing is automatically enabled when you import the module, but you can control it manually:

```python
from async_trace import enable_tracing, disable_tracing

# Disable tracing temporarily
disable_tracing()

# ... do some work without tracing overhead ...

# Re-enable tracing
enable_tracing()
```

### Custom Formatting

You can use the structured data to create custom output:

```python
from async_trace import collect_async_trace

async def worker():
    trace_data = collect_async_trace()
    
    # Find all task boundaries
    print("Task creation points:")
    for frame in trace_data['frames']:
        if frame['task'] and frame['line']:
            print(f"  • {frame['name']}() at line {frame['line']}")
    
    # Show just the function names
    print("\nCall path:")
    print(" → ".join(f['name'] for f in trace_data['frames']))
```

## Use Cases

### Debugging Complex Async Code

When you have multiple layers of async functions and tasks, it can be hard to understand the execution flow:

```python
import asyncio
from async_trace import print_trace

async def process_data(data):
    # Where did this task come from?
    print_trace()  # Shows the complete path!
    return data.upper()

async def worker(item):
    result = await process_data(item)
    return result

async def main():
    tasks = [asyncio.create_task(worker(f"item-{i}")) for i in range(3)]
    await asyncio.gather(*tasks)

asyncio.run(main())
```

### Understanding Task Dependencies

Track which tasks create which other tasks:

```python
from async_trace import collect_async_trace

async def leaf_task():
    trace = collect_async_trace()
    
    print("My ancestors:")
    for frame in trace['frames']:
        if frame['task']:
            print(f"  - {frame['task'].get_name()}")
```

### Performance Profiling

Find where tasks are being created in your code:

```python
from async_trace import collect_async_trace

async def monitored_task():
    trace = collect_async_trace()
    
    # Count how deep the task nesting is
    task_count = sum(1 for f in trace['frames'] if f['task'])
    if task_count > 5:
        print(f"Warning: Deep task nesting ({task_count} levels)")
```

## How It Works

Python's `traceback` module can show you the call stack for synchronous code because it's linear—one function calls another. But asyncio tasks break this chain: a task can be created in one place and executed much later, making the execution path unclear.

`async-trace` solves this by:
1. **Tracking task creation**: Monkey-patches `asyncio.create_task()` to record where each task was created
2. **Capturing call stacks**: Records the full call stack at each task creation point
3. **Reconstructing the path**: When you call `print_trace()`, it walks up the task chain to show the complete execution path

This gives you the same debugging power for async code that Python's traceback provides for sync code.

### Benefits:
- **Accurate**: Captures the actual task creation relationships
- **Lightweight**: Minimal overhead, just recording metadata at task creation time
- **Non-invasive**: No changes needed to your async code—just import and use

## Examples

See the [`examples/`](examples/) directory for more examples:

- `basic_example.py` - Simple tracing example
- `structured_trace.py` - Using structured trace data
- `parallel_tasks.py` - Tracing parallel/concurrent tasks

## API Reference

### Functions

#### `print_trace()`
Convenience function to collect and print the async call trace.

#### `collect_async_trace() -> dict`
Collect structured async call trace data.

Returns a dict with `frames` (list of frame dicts) and `current_task` (Task object).

#### `print_async_trace(trace_data: dict)`
Print formatted trace output from trace data returned by `collect_async_trace()`.

#### `enable_tracing()`
Enable async call tracing (enabled by default on import).

#### `disable_tracing()`
Disable async call tracing to avoid overhead.

## Requirements

- Python 3.8 or higher
- No external dependencies (uses only the standard library)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - see LICENSE file for details.

## Changelog

### 0.1.0 (Initial Release)
- Basic async call tracing functionality
- Structured trace data API
- Support for Python 3.8+

