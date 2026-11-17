+++
schema_version = 1
id = "reject-overload"
title = "Reject overload before creating a waiter backlog"
description = "Apply immediate bounded admission to a local asyncio service and release capacity on every exit."
python = ">=3.12"
runtime = "asyncio"
tags = ["overload", "admission", "load-shedding", "capacity"]
aliases = ["reject excess requests", "bounded admission"]
status = "draft"
example = "examples/reject_overload.py"
[[sources]]
url = "https://docs.python.org/3.12/library/asyncio-task.html"
checked = 2026-11-16
+++

# Reject overload before creating a waiter backlog

## When to use

Use when waiting indefinitely would exhaust memory or exceed request deadlines.
An already bounded server queue may supply the needed admission policy.

## Rules

1. Admit work before spawning tasks or allocating expensive resources.
2. Bound active work and queued waiters separately.
3. Release capacity after failure and cancellation.
4. Map overload to the transport's retryable response with a controlled retry policy.

## Reference example

```python
"""Application policy: admit work immediately without unbounded waiters."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager


class Admission:
    capacity: int
    active: int

    def __init__(self, capacity: int) -> None:
        if capacity < 1:
            raise ValueError("capacity must be positive")
        self.capacity = capacity
        self.active = 0

    @asynccontextmanager
    async def enter(self) -> AsyncGenerator[None, None]:
        if self.active >= self.capacity:
            raise RuntimeError("overloaded")
        self.active += 1
        try:
            yield
        finally:
            self.active -= 1
```

## Guarantees and assumptions

Use one instance on one event loop. No await separates checking and reserving a
slot. The limit applies to this instance, not all processes or tenants.

## Pitfalls

`Semaphore` limits holders but can accumulate unlimited waiting tasks. Admission
capacity is not requests-per-second rate limiting or tenant fairness. Instrument
rejections and size capacity against downstream resources.

## Verification

Run `uv run pytest tests/test_backend_concurrency.py --task reject-overload`.
Check immediate refusal at capacity and slot recovery after an exception.

## Sources

- [Python task scheduling and cancellation](https://docs.python.org/3.12/library/asyncio-task.html)
