"""Application workflow: one monotonic deadline covers both async stages."""

import asyncio
import math
from collections.abc import Awaitable, Callable


async def fetch_and_store[T, R](
    fetch: Callable[[], Awaitable[T]],
    store: Callable[[T], Awaitable[R]],
    *,
    deadline: float,
) -> R:
    if not math.isfinite(deadline):
        raise ValueError("deadline must be finite")
    if deadline <= asyncio.get_running_loop().time():
        raise TimeoutError("operation deadline already expired")

    async with asyncio.timeout_at(deadline):
        value = await fetch()
        return await store(value)


async def demo_fetch() -> str:
    return "payload"


async def demo_store(value: str) -> str:
    return f"Stored {value}"


async def main() -> None:
    deadline = asyncio.get_running_loop().time() + 2
    print(await fetch_and_store(demo_fetch, demo_store, deadline=deadline))


if __name__ == "__main__":
    asyncio.run(main())
