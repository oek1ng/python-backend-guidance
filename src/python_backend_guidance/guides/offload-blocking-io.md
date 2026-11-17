+++
schema_version = 1
id = "offload-blocking-io"
title = "Move blocking I/O off the event loop"
description = "Keep asyncio responsive while calling a bounded synchronous I/O function in a worker thread."
python = ">=3.12"
runtime = "asyncio"
tags = ["blocking-io", "threads", "event-loop", "responsiveness"]
aliases = ["blocking sync function", "event loop stall", "to_thread"]
status = "draft"
example = "examples/offload_blocking_io.py"
[[sources]]
url = "https://docs.python.org/3.12/library/asyncio-task.html"
checked = 2026-11-16
+++

# Move blocking I/O off the event loop

## When to use

Use when an async handler must call an existing synchronous I/O API. Prefer a
native async client when it already fits the project. Ordinary sync workers
do not need this adapter.

## Rules

1. Offload the complete blocking call, not just its construction.
2. Bound submissions before the executor; a thread limit does not bound its queue.
3. Configure timeouts in the underlying synchronous API.
4. Confirm thread safety and avoid sharing a thread-affine connection.

## Reference example

```python
"""Application workflow: offload a borrowed synchronous operation."""

import asyncio
from collections.abc import Callable


async def call_blocking[R, *Args](operation: Callable[[*Args], R], *args: *Args) -> R:
    return await asyncio.to_thread(operation, *args)
```

## Guarantees and assumptions

The caller gets the function's result or exception while the loop can progress.
`to_thread` propagates context into the thread; changes there do not propagate
back. The application owns executor shutdown.

## Pitfalls

`async def handler(): return sync_client.read()` still blocks the loop.
Cancelling the await does not stop a running thread. This is not a recommendation
to parallelize pure-Python CPU work with threads.

## Verification

Run `uv run pytest tests/test_backend_concurrency.py --task offload-blocking-io`.
An event-loop callback must progress while the blocking function waits.

## Sources

- [Python running functions in threads](https://docs.python.org/3.12/library/asyncio-task.html)
