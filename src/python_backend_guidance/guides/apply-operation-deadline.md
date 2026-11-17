+++
schema_version = 1
id = "apply-operation-deadline"
title = "Apply an operation-wide deadline"
description = "Share one monotonic deadline across sequential async stages while preserving errors and cancellation."
python = ">=3.12"
runtime = "asyncio"
tags = ["timeouts", "deadline", "budget", "cancellation", "workflow"]
aliases = [
    "workflow budget",
    "time budget",
    "fetch and store",
    "monotonic timeout",
    "timeout per stage",
    "cancel workflow",
]
status = "draft"
example = "examples/apply_operation_deadline.py"

[[sources]]
url = "https://docs.python.org/3.12/library/asyncio-task.html#timeouts"
checked = 2026-11-16

[[sources]]
url = "https://docs.python.org/3.12/library/asyncio-task.html#task-cancellation"
checked = 2026-11-16

[[sources]]
url = "https://docs.python.org/3.12/library/asyncio-eventloop.html#asyncio.loop.time"
checked = 2026-11-16
+++

# Apply an operation-wide deadline

## When to use

Use when multiple async stages must share a caller's total time budget.
A timeout applied separately to each stage can multiply total waiting time.
For a single call, a well-tested client's own timeout may already suffice.
Keep an existing runtime's equivalent timeout scope rather than switching to
asyncio just to copy this example.

## Rules

1. Compute an absolute deadline with the event loop's monotonic clock. Do not
   use a wall-clock timestamp with `asyncio.timeout_at()`.
2. Cover the entire owned workflow with one timeout scope. Nested helpers must
   share the deadline rather than receiving a fresh full budget.
3. Reject an already expired budget before starting new work.
4. Preserve external cancellation and domain exceptions. Catch a timeout outside
   its context manager, not by swallowing `CancelledError` inside it.
5. Use cancellation-aware resource owners. A timeout is not a rollback or a
   guarantee that a remote side effect did not complete.

## Reference example

The runnable copy is `examples/apply_operation_deadline.py`.

```python
"""Application workflow: one monotonic deadline covers both async stages."""

import asyncio
import math
from collections.abc import Awaitable, Callable


async def fetch_and_store[T, R](
    fetch: Callable[[], Awaitable[T]],
    store: Callable[[T], Awaitable[R]],
    *,
    deadline: float,
) -> R:
    if not math.isfinite(deadline):
        raise ValueError("deadline must be finite")
    if deadline <= asyncio.get_running_loop().time():
        raise TimeoutError("operation deadline already expired")

    async with asyncio.timeout_at(deadline):
        value = await fetch()
        return await store(value)


async def demo_fetch() -> str:
    return "payload"


async def demo_store(value: str) -> str:
    return f"Stored {value}"


async def main() -> None:
    deadline = asyncio.get_running_loop().time() + 2
    print(await fetch_and_store(demo_fetch, demo_store, deadline=deadline))


if __name__ == "__main__":
    asyncio.run(main())
```

## Guarantees and assumptions

Both stages execute inside the same timeout scope, using the supplied absolute
deadline. If the budget is already expired, neither starts. Success returns the
store result; ordinary stage errors propagate unchanged.

Deadline expiry requests cancellation and normally produces `TimeoutError`
outside the scope. Caller cancellation remains `CancelledError`. Both rely on
cooperative code: blocking work, detached tasks, or suppressed cancellation can
defeat shutdown.

The stages own their resources and must release them in context managers or
`finally`. Cleanup can exceed the original budget; this is not a hard real-time
limit. Absolute loop deadlines are local to that clock: propagate a suitable
remaining budget across process boundaries, not the raw numeric deadline.

## Pitfalls

- Client connect/read timeouts and a workflow-wide deadline protect different
  things; one does not automatically replace the other.
- A stage can raise its own `TimeoutError`. That exception alone does not prove
  the outer budget expired; retain the timeout context and inspect `expired()`
  if the distinction matters.
- Do not shield the whole operation to make a timeout disappear. Shielded work
  requires explicit ownership, an independent bound, and eventual observation.
- Cancelling a wait does not terminate an already-running thread or undo a
  database commit. Do not automatically retry a mutation after a timeout.

## Verification

Check both fetch and store stalls, rejection of an expired budget, preservation
of ordinary errors, external cancellation, and resource cleanup. Tests may wait
for a timer to expire, but must not assert short elapsed-time windows or
throughput. Use a separate generous deadlock guard.

## Sources

Sources checked on 2026-11-16; this draft has not had independent review.

- [Python: timeout scopes](https://docs.python.org/3.12/library/asyncio-task.html#timeouts)
- [Python: cancellation](https://docs.python.org/3.12/library/asyncio-task.html#task-cancellation)
- [Python: event-loop clock](https://docs.python.org/3.12/library/asyncio-eventloop.html#asyncio.loop.time)
