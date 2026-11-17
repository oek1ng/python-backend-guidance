+++
schema_version = 1
id = "own-resource-lifetimes"
title = "Give each resource one explicit lifetime owner"
description = "Close owned resources on every scope exit while allowing borrowers to use them without taking over cleanup."
python = ">=3.12"
runtime = "sync"
tags = ["resources", "context-manager", "close", "lifetime"]
aliases = ["resource ownership cleanup", "context manager lifetime"]
status = "draft"
example = "examples/own_resource_lifetimes.py"
[[sources]]
url = "https://docs.python.org/3.12/library/contextlib.html"
checked = 2026-11-16
+++

# Give each resource one explicit lifetime owner

## When to use

Use for a closeable resource without its own suitable context manager. Prefer
the library's native `with` or `async with` interface when available.

## Rules

1. Decide which scope owns acquisition and cleanup.
2. Put close in `finally`, not after the successful operation only.
3. Let borrowers use the resource without closing someone else's ownership.
4. Finish all borrowers before the owning scope exits.

## Reference example

```python
"""Composition root: own a resource so borrowers do not close it."""

from collections.abc import Callable, Generator
from contextlib import contextmanager
from typing import Protocol


class Closeable(Protocol):
    def close(self) -> None: ...


@contextmanager
def owned_resource[T: Closeable](
    open_resource: Callable[[], T],
) -> Generator[T, None, None]:
    resource = open_resource()
    try:
        yield resource
    finally:
        resource.close()
```

## Guarantees and assumptions

If acquisition succeeds, close is invoked on every scope exit. The resource's
close method must implement the needed cleanup semantics. A close error may
replace the active exception; choose a reporting policy if that matters.

## Pitfalls

Relying on garbage collection makes release timing unpredictable. Closing a
borrowed pool/client inside a helper breaks other users. Sync close should not be
used for a resource requiring awaited shutdown.

## Verification

Run `uv run pytest tests/test_backend_lifecycle.py --task own-resource-lifetimes`.
Check usability inside the scope and release after a body exception.

## Sources

- [Python context managers and cleanup](https://docs.python.org/3.12/library/contextlib.html)
