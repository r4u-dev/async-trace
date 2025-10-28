import asyncio
import sys
sys.path.insert(0, '.')
import main

async def task_a_worker():
    await asyncio.sleep(0.1)
    print("\n" + "="*60)
    print("📍 Currently executing in: task_a_worker")
    print("="*60)
    
    # Get both pieces of information
    trace = main.collect_async_trace()
    tree = main.collect_task_tree()
    
    print("\n📋 ASYNC CALL TRACE (How did we get HERE?)")
    print("Shows the path that led to THIS task:")
    for i, task_data in enumerate(trace['task_chain']):
        indent = "  " * i
        marker = "🟢" if task_data['is_current'] else "⚪"
        print(f"{indent}{marker} {task_data['name']}")
    
    print("\n🌳 TASK TREE (What ELSE is running?)")
    print("Shows ALL concurrent tasks in the system:")
    all_task_names = [data['name'] for data in tree['task_data'].values()]
    for name in all_task_names:
        print(f"  • {name}")
    
    print("\n💡 KEY DIFFERENCE:")
    print("  - Async trace: Shows YOUR ancestry (vertical)")
    print("  - Task tree: Shows ALL tasks (horizontal)")

async def task_b_worker():
    await asyncio.sleep(0.2)

async def task_a():
    t = asyncio.create_task(task_a_worker(), name="task-a-worker")
    await t

async def task_b():
    t = asyncio.create_task(task_b_worker(), name="task-b-worker")
    await t

async def demo():
    # Create two parallel tasks
    ta = asyncio.create_task(task_a(), name="task-a")
    tb = asyncio.create_task(task_b(), name="task-b")
    
    await asyncio.gather(ta, tb)

if __name__ == "__main__":
    asyncio.run(demo())

