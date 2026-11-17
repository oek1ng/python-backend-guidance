"""Application workflow: keep related tasks inside their parent's lifetime."""

import asyncio
from collections.abc import Callable, Coroutine, Iterable


async def run_related[T](
    operations: Iterable[Callable[[], Coroutine[object, object, T]]],
) -> list[T]:
    async with asyncio.TaskGroup() as group:
        tasks = [group.create_task(operation()) for operation in operations]
    return [task.result() for task in tasks]
