+++
schema_version = 1
id = "isolate-request-context"
title = "Isolate and restore request context"
description = "Use ContextVar tokens to isolate concurrent request metadata and restore nested scopes on failure."
python = ">=3.12"
runtime = "any"
tags = ["contextvars", "request-context", "isolation", "tokens"]
aliases = ["request context leakage", "reset context variable"]
status = "draft"
example = "examples/isolate_request_context.py"
[[sources]]
url = "https://docs.python.org/3.12/library/contextvars.html"
checked = 2026-11-16
+++

# Isolate and restore request context

## When to use

Use for request IDs and other cross-cutting metadata accessed below a handler.
Pass business inputs explicitly when that makes dependencies clearer.

## Rules

1. Declare the ContextVar at module scope, with an immutable default.
2. Reset with the exact token in `finally`; do not set an assumed default.
3. Treat task creation as a context-copy boundary.
4. Pass selected context explicitly across broker or process boundaries.

## Reference example

```python
"""Input boundary: restore request context even when a request fails."""

from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar

request_id: ContextVar[str | None] = ContextVar("request_id", default=None)


@contextmanager
def request_scope(value: str) -> Generator[None, None, None]:
    token = request_id.set(value)
    try:
        yield
    finally:
        request_id.reset(token)
```

## Guarantees and assumptions

Nested scopes restore the prior value; asyncio tasks have independent contexts.
Values themselves are not deep-copied. Store a string ID, not a shared mutable
request dictionary.

## Pitfalls

A process-global `current_request` leaks between concurrent handlers. Detached
tasks may retain the originating request context after that request ends.
Context metadata is not an authorization decision.

## Verification

Run `uv run pytest tests/test_backend_concurrency.py --task isolate-request-context`.
Check parallel tasks and nested restoration after an exception.

## Sources

- [Python context variables](https://docs.python.org/3.12/library/contextvars.html)
