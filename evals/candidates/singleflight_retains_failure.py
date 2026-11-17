"""Mutation: retain failed loads so later requests cannot retry the backend."""

import asyncio
from collections.abc import Callable, Coroutine, Hashable
from typing import override

from examples.coalesce_cache_misses import SingleFlight as CorrectSingleFlight


class SingleFlight[K: Hashable, V](CorrectSingleFlight[K, V]):
    @override
    async def get(self, key: K, load: Callable[[], Coroutine[object, object, V]]) -> V:
        if key not in self.tasks:
            task = asyncio.create_task(load())
            self.tasks[key] = task

            def finished(done: asyncio.Task[V]) -> None:
                if done.cancelled() or done.exception() is None:
                    _ = self.tasks.pop(key, None)

            task.add_done_callback(finished)
        return await asyncio.shield(self.tasks[key])
