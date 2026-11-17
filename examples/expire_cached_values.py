"""Application policy: a local cache with an injected monotonic clock."""

import time
from collections.abc import Callable, Hashable


class TTLCache[K: Hashable, V]:
    ttl: float
    clock: Callable[[], float]
    entries: dict[K, tuple[float, V]]

    def __init__(
        self, *, ttl: float, clock: Callable[[], float] = time.monotonic
    ) -> None:
        if ttl <= 0:
            raise ValueError("ttl must be positive")
        self.ttl, self.clock = ttl, clock
        self.entries = {}

    def put(self, key: K, value: V) -> None:
        self.entries[key] = (self.clock() + self.ttl, value)

    def get(self, key: K) -> V:
        expiry, value = self.entries[key]
        if self.clock() >= expiry:
            del self.entries[key]
            raise KeyError(key)
        return value

    def invalidate(self, key: K) -> None:
        _ = self.entries.pop(key, None)
