+++
schema_version = 1
id = "own-child-tasks"
title = "Own child tasks with structured concurrency"
description = "Join related asyncio tasks, cancel siblings on failure, and finish cleanup before the parent returns."
python = ">=3.12"
runtime = "asyncio"
tags = ["structured-concurrency", "taskgroup", "siblings", "cleanup"]
aliases = ["child task lifetime", "orphan background tasks", "sibling failure"]
status = "draft"
example = "examples/own_child_tasks.py"
[[sources]]
url = "https://docs.python.org/3.12/library/asyncio-task.html"
checked = 2026-11-16
+++

# Own child tasks with structured concurrency

## When to use

Use for a fixed, small set of related async operations whose lifetime belongs to
one parent. Sequential awaits are simpler when the work need not overlap.

## Rules

1. Keep related tasks in a `TaskGroup`; finish the group before returning.
2. Let cancellation propagate after `finally` cleanup.
3. Handle exception groups deliberately at the owning boundary.
4. Combine this with bounded admission for large or unbounded input.

## Reference example

```python
"""Application workflow: keep related tasks inside their parent's lifetime."""

import asyncio
from collections.abc import Callable, Coroutine, Iterable


async def run_related[T](
    operations: Iterable[Callable[[], Coroutine[object, object, T]]],
) -> list[T]:
    async with asyncio.TaskGroup() as group:
        tasks = [group.create_task(operation()) for operation in operations]
    return [task.result() for task in tasks]
```

## Guarantees and assumptions

Results preserve input order. A failing child causes cooperative sibling
cancellation; group exit waits for cleanup. Operations are zero-argument coroutine
factories. They must not suppress cancellation or block the event loop.

## Pitfalls

Bare `create_task()` followed by an early return abandons ownership. Default
`gather()` propagation does not cancel all other children after the first error.
TaskGroup does not itself limit the number of tasks.

## Verification

Run `uv run pytest tests/test_backend_concurrency.py --task own-child-tasks`.
Check ordered results and sibling cleanup before a failure escapes.

## Sources

- [Python task groups and cancellation](https://docs.python.org/3.12/library/asyncio-task.html)
