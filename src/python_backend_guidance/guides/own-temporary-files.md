+++
schema_version = 1
id = "own-temporary-files"
title = "Own temporary workspaces for one operation"
description = "Create a private temporary directory atomically and clean it up on both success and failure."
python = ">=3.12"
runtime = "sync"
tags = ["temporary-files", "workspace", "cleanup", "ownership"]
aliases = ["temporary file cleanup", "secure temporary directory"]
status = "draft"
example = "examples/own_temporary_files.py"
[[sources]]
url = "https://docs.python.org/3.12/library/tempfile.html"
checked = 2026-11-16
+++

# Own temporary workspaces for one operation

## When to use

Use for staged uploads, conversion tools and intermediate export artifacts.
In-memory buffers may be simpler for small bounded data.

## Rules

1. Use secure atomic temporary-file/directory APIs.
2. Scope workspace ownership to the operation that consumes it.
3. Close open files and stop subprocess users before leaving that scope.
4. Bound disk usage and plan stale-workspace cleanup after process crashes.

## Reference example

```python
"""File adapter: own and clean the workspace for one borrowed operation."""

from collections.abc import Callable
from pathlib import Path
from tempfile import TemporaryDirectory


def with_workspace[T](operation: Callable[[Path], T]) -> T:
    with TemporaryDirectory(prefix="backend-") as directory:
        return operation(Path(directory))
```

## Guarantees and assumptions

Normal and exceptional scope exit invoke cleanup. The callback must finish all
workspace users before returning. Returned values must not depend on paths that
the scope removes.

## Pitfalls

Constructing `/tmp/<user-input>` can collide or traverse paths. Generating a name
and opening it later creates a race. Context cleanup cannot run after SIGKILL,
power loss, or a host crash.

## Verification

Run `uv run pytest tests/test_backend_files.py --task own-temporary-files`.
Check result propagation and removal after callback failure.

## Sources

- [Python temporary files and directories](https://docs.python.org/3.12/library/tempfile.html)
