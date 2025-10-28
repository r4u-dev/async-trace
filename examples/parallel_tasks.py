"""
Example with parallel tasks.

This demonstrates async tracing with multiple concurrent tasks.
"""

import asyncio
from async_trace import print_trace


async def task_a_worker():
    """Worker for task A."""
    await asyncio.sleep(0.1)
    print("\n=== Inside task_a_worker ===")
    print_trace()


async def task_b_worker():
    """Worker for task B."""
    await asyncio.sleep(0.2)


async def task_a():
    """Task A creates a worker."""
    t = asyncio.create_task(task_a_worker(), name="task-a-worker")
    await t


async def task_b():
    """Task B creates a worker."""
    t = asyncio.create_task(task_b_worker(), name="task-b-worker")
    await t


async def main():
    """Main creates two parallel tasks."""
    # Create two tasks in parallel
    ta = asyncio.create_task(task_a(), name="task-a")
    tb = asyncio.create_task(task_b(), name="task-b")
    
    # Both run concurrently
    await asyncio.gather(ta, tb)


if __name__ == "__main__":
    asyncio.run(main())

