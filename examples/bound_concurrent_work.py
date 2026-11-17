"""Application workflow: a bounded asyncio worker pool for borrowed operations."""

import asyncio
from collections.abc import AsyncIterable, AsyncIterator, Awaitable, Callable


async def _worker[T](
    queue: asyncio.Queue[tuple[T] | None],
    handle: Callable[[T], Awaitable[None]],
) -> None:
    while True:
        item = await queue.get()
        if item is None:
            return
        await handle(item[0])


async def consume_bounded[T](
    source: AsyncIterable[T],
    handle: Callable[[T], Awaitable[None]],
    *,
    concurrency: int,
    buffer_size: int,
) -> None:
    if concurrency < 1 or buffer_size < 1:
        raise ValueError("concurrency and buffer_size must be positive")

    # Wrap each payload so None remains available as an unambiguous stop marker.
    queue: asyncio.Queue[tuple[T] | None] = asyncio.Queue(maxsize=buffer_size)

    async with asyncio.TaskGroup() as group:
        for _ in range(concurrency):
            _ = group.create_task(_worker(queue, handle))

        async for item in source:
            await queue.put((item,))

        for _ in range(concurrency):
            await queue.put(None)


async def demo_source() -> AsyncIterator[int]:
    for item in range(10):
        yield item


async def demo_handle(item: int) -> None:
    await asyncio.sleep(0)  # Stand in for an asynchronous I/O operation.
    print(f"Processed {item}")


async def main() -> None:
    await consume_bounded(demo_source(), demo_handle, concurrency=3, buffer_size=6)


if __name__ == "__main__":
    asyncio.run(main())
