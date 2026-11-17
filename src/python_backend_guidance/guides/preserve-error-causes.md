+++
schema_version = 1
id = "preserve-error-causes"
title = "Preserve internal error causes behind a safe boundary"
description = "Translate expected dependency failures into stable application errors while retaining diagnostic exception chaining."
python = ">=3.12"
runtime = "any"
tags = ["exceptions", "error-boundary", "causality", "public-errors"]
aliases = ["preserve exception cause", "safe dependency error"]
status = "draft"
example = "examples/preserve_error_causes.py"
[[sources]]
url = "https://docs.python.org/3.12/reference/simple_stmts.html"
checked = 2026-11-16
+++

# Preserve internal error causes behind a safe boundary

## When to use

Use where a dependency-specific exception becomes an application-level failure.
Let exceptions propagate unchanged within a layer when translation adds no meaning.

## Rules

1. Catch only failures this boundary knows how to classify.
2. Chain the original error with `raise ... from error`.
3. Expose a stable safe message/code through the external adapter.
4. Log the failure once at the owning diagnostic boundary with suitable redaction.

## Reference example

```python
"""Application boundary: expose a fixed error while preserving its cause."""

from collections.abc import Callable


class BackendUnavailable(Exception):
    pass


def read_backend[T](operation: Callable[[], T]) -> T:
    try:
        return operation()
    except OSError as error:
        raise BackendUnavailable("backend temporarily unavailable") from error
```

## Guarantees and assumptions

Here the operation contract classifies OSError as dependency unavailability.
The original error remains accessible through `__cause__`; unrelated programming
errors propagate. No logging or transport mapping occurs in this small helper.

## Pitfalls

`except Exception: return None` hides bugs as missing data. Including raw database
or network error text in public responses can leak secrets. A chained traceback
is for controlled diagnostics, not serialization to clients.

## Verification

Run `uv run pytest tests/test_backend_observability.py --task preserve-error-causes`.
Check cause identity, public-message safety and propagation of a TypeError.

## Sources

- [Python raise and exception chaining](https://docs.python.org/3.12/reference/simple_stmts.html)
