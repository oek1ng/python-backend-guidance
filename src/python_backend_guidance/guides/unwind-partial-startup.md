+++
schema_version = 1
id = "unwind-partial-startup"
title = "Unwind partially acquired startup resources"
description = "Register cleanup immediately after each acquisition so a later startup failure closes earlier resources in reverse order."
python = ">=3.12"
runtime = "sync"
tags = ["startup", "exitstack", "partial-failure", "resource-cleanup"]
aliases = ["partial startup cleanup", "unwind failed resource acquisition"]
status = "draft"
example = "examples/unwind_partial_startup.py"
[[sources]]
url = "https://docs.python.org/3.12/library/contextlib.html"
checked = 2026-11-16
+++

# Unwind partially acquired startup resources

## When to use

Use when startup acquires a dynamic or optional sequence of resources. Nested
`with` statements are simpler for a small fixed set of native context managers.

## Rules

1. Register each cleanup immediately after that acquisition succeeds.
2. Unwind in reverse dependency order.
3. Keep ownership in the stack for the full service lifespan.
4. Use AsyncExitStack for resources whose cleanup must be awaited.

## Reference example

```python
"""Composition root: unwind resources when a later acquisition fails."""

from collections.abc import Callable, Generator, Iterable
from contextlib import ExitStack, contextmanager
from typing import Protocol


class Closeable(Protocol):
    def close(self) -> None: ...


@contextmanager
def open_resources[T: Closeable](
    factories: Iterable[Callable[[], T]],
) -> Generator[list[T], None, None]:
    with ExitStack() as stack:
        resources: list[T] = []
        for factory in factories:
            resource = factory()
            _ = stack.callback(resource.close)
            resources.append(resource)
        yield resources
```

## Guarantees and assumptions

A later acquisition failure triggers cleanup of all earlier acquired resources.
Each factory is responsible for cleaning its own partial failure before returning.
Callbacks should be bounded; cleanup errors still need an application logging policy.

## Pitfalls

`resources = [factory() for factory in factories]` before entering cleanup loses
earlier resources when a later factory fails. Transferring callbacks out of the
stack without an explicit new owner recreates the same leak.

## Verification

Run `uv run pytest tests/test_backend_lifecycle.py --task unwind-partial-startup`.
Check failed second acquisition and reverse cleanup order after success.

## Sources

- [Python ExitStack](https://docs.python.org/3.12/library/contextlib.html)
