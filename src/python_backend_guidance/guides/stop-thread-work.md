+++
schema_version = 1
id = "stop-thread-work"
title = "Stop and join cooperative thread work on cancellation"
description = "Signal a worker thread explicitly and join it before propagating asyncio cancellation."
python = ">=3.12"
runtime = "asyncio"
tags = ["threads", "cancellation", "stop-event", "join"]
aliases = ["cancel thread worker", "thread continues after timeout"]
status = "draft"
example = "examples/stop_thread_work.py"
[[sources]]
url = "https://docs.python.org/3.12/library/asyncio-task.html"
checked = 2026-11-16
+++

# Stop and join cooperative thread work on cancellation

## When to use

Use for a thread function you control that can regularly check a stop event.
For an uninterruptible external API, use its own timeout or a process boundary.

## Rules

1. Define a cooperative stop protocol and finite blocking waits in the worker.
2. Shield the owned thread task from the caller's cancellation.
3. On cancellation, request stop and await actual completion.
4. Preserve cancellation even if worker cleanup also fails.

## Reference example

```python
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
```

## Guarantees and assumptions

Normal results/errors propagate. Cancellation is delayed until the cooperative
worker stops; the example retrieves, but does not log, a secondary worker error.
The worker must check the event and make every blocking wait finite.

## Pitfalls

`future.cancel()` does not kill a running OS thread. A worker that ignores the
event makes this join unbounded. Do not promise a hard deadline for this helper.

## Verification

Run `uv run pytest tests/test_backend_concurrency.py --task stop-thread-work`.
Check that the thread has exited when the awaiting task reports cancellation.

## Sources

- [Python shielding, cancellation and threads](https://docs.python.org/3.12/library/asyncio-task.html)
