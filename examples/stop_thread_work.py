"""Application workflow: cancel and join a borrowed cooperative worker."""

import asyncio
import threading
from collections.abc import Callable


async def run_stoppable[T](worker: Callable[[threading.Event], T]) -> T:
    stop = threading.Event()
    task = asyncio.create_task(asyncio.to_thread(worker, stop))
    try:
        return await asyncio.shield(task)
    except asyncio.CancelledError:
        stop.set()
        # Repeated cancellation must not abandon the owned thread.
        while not task.done():
            try:
                await asyncio.shield(task)
            except asyncio.CancelledError:
                continue
            except Exception:
                break
        # Retrieve a worker exception without replacing cancellation.
        if not task.cancelled():
            _ = task.exception()
        raise
