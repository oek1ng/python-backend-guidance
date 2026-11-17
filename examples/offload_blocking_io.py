"""Application workflow: offload a borrowed synchronous operation."""

import asyncio
from collections.abc import Callable


async def call_blocking[R, *Args](operation: Callable[[*Args], R], *args: *Args) -> R:
    return await asyncio.to_thread(operation, *args)
