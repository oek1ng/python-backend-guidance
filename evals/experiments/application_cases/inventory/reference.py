"""Application workflow: own bounded persistence work for an inventory import."""

import asyncio
from collections.abc import AsyncIterable, Awaitable, Callable


async def _persist_worker[T](
    queue: asyncio.Queue[tuple[T] | None],
    persist: Callable[[T], Awaitable[None]],
    completed: list[int],
) -> None:
    while True:
        item = await queue.get()
        if item is None:
            return
        await persist(item[0])
        completed[0] += 1


async def sync_inventory[T](
    records: AsyncIterable[T],
    persist: Callable[[T], Awaitable[None]],
    *,
    workers: int,
    pending: int,
) -> int:
    if workers < 1 or pending < 1:
        raise ValueError("workers and pending must be positive")
    queue: asyncio.Queue[tuple[T] | None] = asyncio.Queue(maxsize=pending)
    completed = [0]
    async with asyncio.TaskGroup() as group:
        for _ in range(workers):
            _ = group.create_task(_persist_worker(queue, persist, completed))
        async for record in records:
            await queue.put((record,))
        for _ in range(workers):
            await queue.put(None)
    return completed[0]
