"""Application workflow: coalesce borrowed loads without transferring ownership."""

import asyncio
from collections.abc import Callable, Coroutine, Hashable
from functools import partial


class SingleFlight[K: Hashable, V]:
    tasks: dict[K, asyncio.Task[V]]

    def __init__(self) -> None:
        self.tasks = {}

    def _finished(self, key: K, done: asyncio.Task[V]) -> None:
        _ = self.tasks.pop(key, None)
        if not done.cancelled():
            _ = done.exception()

    async def get(self, key: K, load: Callable[[], Coroutine[object, object, V]]) -> V:
        if key not in self.tasks:
            task = asyncio.create_task(load())
            self.tasks[key] = task
            task.add_done_callback(partial(self._finished, key))
        return await asyncio.shield(self.tasks[key])

    async def close(self) -> None:
        tasks = list(self.tasks.values())
        for task in tasks:
            _ = task.cancel()
        _ = await asyncio.gather(*tasks, return_exceptions=True)
