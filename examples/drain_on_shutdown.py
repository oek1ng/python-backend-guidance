"""Composition root: drain owned tasks and cancel stragglers on shutdown."""

import asyncio
from collections.abc import Iterable


async def drain[T](
    tasks: Iterable[asyncio.Task[T]], *, grace: float
) -> list[T | BaseException]:
    if grace < 0:
        raise ValueError("grace must be nonnegative")
    owned = set(tasks)
    if len(owned) == 0:
        return []
    _, pending = await asyncio.wait(owned, timeout=grace)
    for task in pending:
        _ = task.cancel()
    return await asyncio.gather(*owned, return_exceptions=True)
