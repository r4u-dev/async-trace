"""
Basic example showing async call tracing.

This example demonstrates how to use async_trace to track the execution path
of async tasks.
"""

import asyncio
from async_trace import print_trace


async def inner_task():
    """Innermost task that prints the call trace."""
    print("\n=== In Inner Task ===")
    print_trace()
    await asyncio.sleep(0.1)


async def worker():
    """Worker task that calls inner_task."""
    await inner_task()


async def sub_task():
    """Sub-task that creates and awaits a worker."""
    t = asyncio.create_task(worker())
    await t


async def main():
    """Main entry point that starts the task chain."""
    await sub_task()
    
    print("\n=== In Main ===")
    print_trace()


if __name__ == "__main__":
    asyncio.run(main())

