"""Application workflow: an inventory import that eagerly schedules every record."""

import asyncio
from collections.abc import AsyncIterable, Awaitable, Callable


async def sync_inventory[T](
    records: AsyncIterable[T],
    persist: Callable[[T], Awaitable[None]],
    *,
    workers: int,
    pending: int,
) -> int:
    if workers < 1 or pending < 1:
        raise ValueError("workers and pending must be positive")
    tasks: list[asyncio.Task[None]] = []
    async for record in records:
        tasks.append(asyncio.ensure_future(persist(record)))
    _ = await asyncio.gather(*tasks)
    return len(tasks)
