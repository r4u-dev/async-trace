"""
Example showing how to use structured trace data.

This demonstrates the structured API that returns trace data as a dict,
which you can process programmatically.
"""

import asyncio
from async_trace import collect_async_trace, print_async_trace


async def inner_task():
    """Innermost task."""
    await asyncio.sleep(0.1)


async def worker():
    """Worker task."""
    await inner_task()


async def sub_task():
    """Sub-task that creates a worker."""
    t = asyncio.create_task(worker())
    await t


async def main():
    """Main entry point demonstrating structured trace usage."""
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
    
    # You can also print it nicely formatted
    print("\n📝 Formatted Output:")
    print_async_trace(trace_data)


if __name__ == "__main__":
    asyncio.run(main())

