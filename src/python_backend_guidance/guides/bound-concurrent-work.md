+++
schema_version = 1
id = "bound-concurrent-work"
title = "Bound concurrent work"
description = "Process a large async input stream with bounded concurrency and backpressure."
python = ">=3.12"
runtime = "asyncio"
tags = ["asyncio", "concurrency", "backpressure", "worker-pool", "cancellation"]
aliases = [
    "parallel worker pool",
    "bounded fanout",
    "task per item",
    "pending jobs",
    "concurrent workload",
    "consumer backpressure",
    "waiting tasks",
]
status = "draft"
example = "examples/bound_concurrent_work.py"

[[sources]]
url = "https://docs.python.org/3.12/library/asyncio-queue.html"
checked = 2026-11-16

[[sources]]
url = "https://docs.python.org/3.12/library/asyncio-task.html#task-groups"
checked = 2026-11-16

[[sources]]
url = "https://docs.python.org/3.12/library/asyncio-task.html#task-cancellation"
checked = 2026-11-16

[[sources]]
url = "https://docs.python.org/3.12/library/asyncio-sync.html#semaphore"
checked = 2026-11-16
+++

# Bound concurrent work

## When to use

Use this guidance for a large or unknown number of independent asynchronous I/O
operations.

For a small, explicitly bounded batch, `asyncio.gather()` with a semaphore may be
sufficient. Do not introduce a worker pool without a capacity problem to solve.
Preserve an application's existing concurrency runtime; do not introduce asyncio
into a Trio application to copy this example.

## Rules

1. **Bound active work and pending work separately.** A semaphore limits active
   operations, but does not prevent creating one waiting task per input item.
2. **Apply backpressure to the producer.** Stop consuming input when capacity is
   exhausted. A task group alone does not bound task creation.
3. **Keep child tasks within their owner's lifetime.** On failure or cancellation,
   await their termination.
4. **Propagate cancellation after cleanup.** Use resource context managers or
   `finally`; do not turn `CancelledError` into a successful return.
5. **Choose the limit's scope explicitly.** A per-request limit does not protect a
   shared dependency from many concurrent requests.

## Reference example

This complete example uses only Python 3.12+ standard-library APIs. The runnable
copy is `examples/bound_concurrent_work.py`; a test keeps it identical to this
code block.

```python
"""Application workflow: a bounded asyncio worker pool for borrowed operations."""

import asyncio
from collections.abc import AsyncIterable, AsyncIterator, Awaitable, Callable


async def _worker[T](
    queue: asyncio.Queue[tuple[T] | None],
    handle: Callable[[T], Awaitable[None]],
) -> None:
    while True:
        item = await queue.get()
        if item is None:
            return
        await handle(item[0])


async def consume_bounded[T](
    source: AsyncIterable[T],
    handle: Callable[[T], Awaitable[None]],
    *,
    concurrency: int,
    buffer_size: int,
) -> None:
    if concurrency < 1 or buffer_size < 1:
        raise ValueError("concurrency and buffer_size must be positive")

    # Wrap each payload so None remains available as an unambiguous stop marker.
    queue: asyncio.Queue[tuple[T] | None] = asyncio.Queue(maxsize=buffer_size)

    async with asyncio.TaskGroup() as group:
        for _ in range(concurrency):
            _ = group.create_task(_worker(queue, handle))

        async for item in source:
            await queue.put((item,))

        for _ in range(concurrency):
            await queue.put(None)


async def demo_source() -> AsyncIterator[int]:
    for item in range(10):
        yield item


async def demo_handle(item: int) -> None:
    await asyncio.sleep(0)  # Stand in for an asynchronous I/O operation.
    print(f"Processed {item}")


async def main() -> None:
    await consume_bounded(demo_source(), demo_handle, concurrency=3, buffer_size=6)


if __name__ == "__main__":
    asyncio.run(main())
```

## Guarantees and assumptions

- At most `concurrency` handler calls are active within this invocation.
- At most `buffer_size` entries are queued. The producer may additionally hold
  one item while awaiting insertion.
- Input is consumed incrementally, with a fixed number of workers rather than
  one task per input item.
- Successful completion means every input item was handled once by this
  invocation. Completion order is unspecified.
- An ordinary exception from the producer or a worker makes `TaskGroup` cancel
  and await the remaining workers, then report the failure in an
  `ExceptionGroup`.
- Cancelling the enclosing operation cancels and awaits its workers. Source and
  handler code must cooperate with cancellation. Independently cancelling
  individual workers is not part of this helper's contract: `TaskGroup` does not
  treat a child's cancellation as an ordinary failure.

`TaskGroup` tracks completion here; `queue.join()` and `queue.task_done()` are not
needed. The caller owns resource-bearing input streams and shared clients: close
them with their context managers, or `contextlib.aclosing()` for an owned async
generator. Handlers must not detach work that outlives the owning operation.

## Pitfalls

- **Zero means unbounded.** `asyncio.Queue(maxsize=0)` creates an unbounded queue,
  not a disabled buffer. Reject non-positive configuration values.
- **An item limit is not a byte limit.** Payload size, upstream prefetching,
  handler allocations, and accumulated results need separate consideration.
- **Concurrency is not request rate.** This helper does not enforce requests per
  second or a process-wide or deployment-wide capacity limit.
- **Cancellation is not rollback.** Completed side effects remain. Pending input
  can be discarded on failure. This is not a durable queue or an exactly-once
  delivery mechanism.
- **Cancellation is cooperative.** Blocking code or suppressed cancellation can
  prevent shutdown. Cancelling an await does not forcibly stop an already-running
  thread or undo a remote operation. Define deadlines separately.

## Verification

Check bounded active work, bounded read-ahead, successful completion, producer
and handler failures, and cancellation of the enclosing operation. Coordinate
tests with events rather than elapsed-time assertions. A generous timeout may
act as a deadlock guard, not a performance requirement.

## Sources

Sources reviewed on 2026-11-16. API availability is not a claim that every
compatible Python release has been tested; see the repository's CI matrix.

- [Python: asyncio queues](https://docs.python.org/3.12/library/asyncio-queue.html)
- [Python: task groups](https://docs.python.org/3.12/library/asyncio-task.html#task-groups)
- [Python: task cancellation](https://docs.python.org/3.12/library/asyncio-task.html#task-cancellation)
- [Python: semaphores](https://docs.python.org/3.12/library/asyncio-sync.html#semaphore)
