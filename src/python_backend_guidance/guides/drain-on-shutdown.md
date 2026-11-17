+++
schema_version = 1
id = "drain-on-shutdown"
title = "Drain owned work before shutdown"
description = "Stop admission, allow a grace period, then cancel and join outstanding asyncio tasks."
python = ">=3.12"
runtime = "asyncio"
tags = ["shutdown", "drain", "grace-period", "sigterm"]
aliases = ["graceful shutdown", "stop accepting requests"]
status = "draft"
example = "examples/drain_on_shutdown.py"
[[sources]]
url = "https://docs.python.org/3.12/library/asyncio-task.html"
checked = 2026-11-16
+++

# Drain owned work before shutdown

## When to use

Use in a service lifespan that owns a finite set of in-flight tasks. Integrate
with the server's existing shutdown hook instead of installing competing hooks.

## Rules

1. Stop admission and report not-ready before taking the task snapshot.
2. Allow a finite grace interval, then cancel remaining owned tasks.
3. Await cleanup and observe all results before closing shared clients.
4. Reserve time in the supervisor's termination budget for cleanup.

## Reference example

```python
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
```

## Guarantees and assumptions

The grace period is bounded; cancellation cleanup remains cooperative. Tasks
must implement finite cleanup. Results are returned in snapshot order, which
is unspecified for the set used here. Callers must inspect exception results.

## Pitfalls

Calling `cancel()` and immediately closing database pools races with cleanup.
Continuing to create tasks after the snapshot defeats draining. A process
supervisor supplies the ultimate hard stop for cancellation-resistant work.

## Verification

Run `uv run pytest tests/test_backend_concurrency.py --task drain-on-shutdown`.
Check completion, cancellation cleanup, and collection of already-finished tasks.

## Sources

- [Python waiting and cancellation](https://docs.python.org/3.12/library/asyncio-task.html)
