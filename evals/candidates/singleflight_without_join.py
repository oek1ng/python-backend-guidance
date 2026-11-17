"""Mutation: cancel shared loaders but return before their cleanup completes."""

from collections.abc import Hashable
from typing import override

from examples.coalesce_cache_misses import SingleFlight as CorrectSingleFlight


class SingleFlight[K: Hashable, V](CorrectSingleFlight[K, V]):
    @override
    async def close(self) -> None:
        for task in list(self.tasks.values()):
            _ = task.cancel()
