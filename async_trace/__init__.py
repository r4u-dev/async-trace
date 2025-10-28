"""
Async Call Tracing - Track async task creation and execution paths

This library helps debug async code by tracking task creation and execution paths.
It monkey-patches asyncio.create_task() to record parent-child relationships between tasks.

Public API:
    collect_async_trace() -> dict: Collect structured trace data
    print_async_trace(trace_data): Print formatted trace
    print_trace(): Convenience function (collect + print)
    enable_tracing(): Enable the async tracing (done automatically on import)
    disable_tracing(): Disable the async tracing

Example:
    ```python
    import asyncio
    from async_trace import print_trace
    
    async def worker():
        print_trace()  # Shows the call path that led here
        await asyncio.sleep(1)
    
    async def main():
        await asyncio.create_task(worker())
    
    asyncio.run(main())
    ```

For more information, see the documentation or examples.
"""

from .tracer import (
    collect_async_trace,
    print_async_trace,
    print_trace,
    enable_tracing,
    disable_tracing,
)

__version__ = "0.1.0"

__all__ = [
    "collect_async_trace",
    "print_async_trace",
    "print_trace",
    "enable_tracing",
    "disable_tracing",
]

# Enable tracing by default when the module is imported
enable_tracing()

