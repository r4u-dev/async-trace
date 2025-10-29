"""
Example demonstrating async tracing with run_in_executor.

This shows how async_trace can track calls that cross the async/sync boundary
when using asyncio.run_in_executor to run blocking code in a thread pool.
"""

import asyncio
import time
from async_trace import print_trace


def blocking_work():
    """A blocking function that runs in a thread pool executor."""
    time.sleep(0.1)  # Simulate blocking I/O
    print("\n=== Inside blocking_work (running in executor thread) ===")
    print_trace()
    return "work completed"


def nested_blocking():
    """Another blocking function to show nested calls."""
    print("\n=== Inside nested_blocking (running in executor thread) ===")
    print_trace()
    return "nested work"


async def worker_with_executor():
    """Worker task that uses run_in_executor."""
    loop = asyncio.get_event_loop()
    
    # Run blocking work in executor
    result = await loop.run_in_executor(None, blocking_work)
    print(f"Result: {result}")
    
    # Run another blocking function
    result2 = await loop.run_in_executor(None, nested_blocking)
    print(f"Result2: {result2}")


async def task_manager():
    """Task that creates a worker with executor calls."""
    task = asyncio.create_task(worker_with_executor(), name="executor-worker")
    await task


async def main():
    """Main entry point."""
    await task_manager()
    
    print("\n=== Back in Main (async context) ===")
    print_trace()


if __name__ == "__main__":
    asyncio.run(main())

