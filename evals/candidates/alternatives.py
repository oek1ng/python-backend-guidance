"""Valid alternative implementations of the public guide contracts."""

import asyncio
from collections.abc import AsyncIterable, Awaitable, Callable, Hashable
from typing import override

from examples.coalesce_cache_misses import SingleFlight as CorrectSingleFlight


async def consume_bounded[T](
    source: AsyncIterable[T],
    handle: Callable[[T], Awaitable[None]],
    *,
    concurrency: int,
    buffer_size: int,
) -> None:
    """Workers pull under a lock without an intermediate queue."""
    if concurrency < 1 or buffer_size < 1:
        raise ValueError("concurrency and buffer_size must be positive")
    iterator = aiter(source)
    lock = asyncio.Lock()

    async def worker() -> None:
        while True:
            async with lock:
                try:
                    item = await anext(iterator)
                except StopAsyncIteration:
                    return
            await handle(item)

    async with asyncio.TaskGroup() as group:
        for _ in range(concurrency):
            _ = group.create_task(worker())


class SingleFlight[K: Hashable, V](CorrectSingleFlight[K, V]):
    @override
    async def close(self) -> None:
        """Drain loaders with their own deadlines instead of cancelling them."""
        _ = await asyncio.gather(*list(self.tasks.values()), return_exceptions=True)
