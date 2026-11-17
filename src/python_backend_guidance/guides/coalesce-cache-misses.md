+++
schema_version = 1
id = "coalesce-cache-misses"
title = "Coalesce simultaneous cache misses"
description = "Share one in-flight asyncio load per key and isolate waiter cancellation to reduce local cache stampedes."
python = ">=3.12"
runtime = "asyncio"
tags = ["cache-stampede", "singleflight", "coalescing", "loaders"]
aliases = ["cache miss stampede", "single flight loader"]
status = "draft"
example = "examples/coalesce_cache_misses.py"
[[sources]]
url = "https://docs.python.org/3.12/library/asyncio-task.html"
checked = 2026-11-16
+++

# Coalesce simultaneous cache misses

## When to use

Use when many requests for one missing key would duplicate expensive reads.
Ordinary cache-aside loading is simpler at low concurrency.

## Rules

1. Share an in-flight operation per fully scoped cache key.
2. Prevent one cancelled waiter from cancelling work needed by others.
3. Remove completed/failed work so later requests can retry.
4. Own shared tasks in a service lifespan and bound distinct-key admission.

## Reference example

```python
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
```

## Guarantees and assumptions

One instance belongs to one event loop. Callers stop admission before close.
Loaders must have their own deadlines and must not recursively request the same
key. The helper shares work, not cached completed values.

## Pitfalls

A lock around each caller's separate load serializes duplicate work rather than
sharing its result. This local helper does not coordinate replicas. The loader
inherits the first caller's context, so scope keys correctly and avoid user-specific
side effects.

## Verification

Run `uv run pytest tests/test_backend_cache.py --task coalesce-cache-misses`.
Check one load for simultaneous requests, isolation of a cancelled waiter,
retry after loader failure, and close waiting for asynchronous loader cleanup.

## Sources

- [Python task ownership and shield](https://docs.python.org/3.12/library/asyncio-task.html)
