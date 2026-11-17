+++
schema_version = 1
id = "expire-cached-values"
title = "Define cache freshness and invalidation"
description = "Expire local cached values at a monotonic TTL boundary and explicitly invalidate known changed entries."
python = ">=3.12"
runtime = "any"
tags = ["cache-expiry", "ttl", "invalidation", "staleness"]
aliases = ["cache expiration policy", "TTL freshness boundary"]
status = "draft"
example = "examples/expire_cached_values.py"
[[sources]]
url = "https://docs.python.org/3.12/library/time.html"
checked = 2026-11-16
[[sources]]
url = "https://www.rfc-editor.org/rfc/rfc9111.html"
checked = 2026-11-16
+++

# Define cache freshness and invalidation

## When to use

Use when stale reads are acceptable for a defined interval. Read the source of
truth directly for decisions that require immediate consistency.

## Rules

1. Choose TTL from tolerated staleness, not an arbitrary performance wish.
2. Use monotonic elapsed time for local expiry.
3. Invalidate affected entries after a successful write.
4. Bound cache capacity separately from entry freshness.

## Reference example

```python
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
```

## Guarantees and assumptions

At or after expiry, get raises KeyError. This single-owner demonstration assumes
a finite key set and finite positive TTL. It has no capacity eviction, distributed
clock protocol, or synchronization for multiple threads.

## Pitfalls

TTL does not stop a racing stale loader from repopulating after invalidation.
Strict read-after-write behavior needs versioning or stronger coordination.
Do not serialize monotonic timestamps across machines or process restarts.

## Verification

Run `uv run pytest tests/test_backend_cache.py --task expire-cached-values`.
Use a controlled clock to check the exact boundary and explicit invalidation.

## Sources

- [Python monotonic time](https://docs.python.org/3.12/library/time.html)
- [HTTP freshness model](https://www.rfc-editor.org/rfc/rfc9111.html)
