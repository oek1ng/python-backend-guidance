+++
schema_version = 1
id = "replace-files-atomically"
title = "Separate atomic file replacement from durability"
description = "Stage a complete file beside its destination, sync it, atomically replace the name, and sync the directory on POSIX."
python = ">=3.12"
runtime = "sync"
tags = ["atomic-files", "fsync", "durability", "replace"]
aliases = ["atomic file replacement", "durable file write"]
status = "draft"
example = "examples/replace_files_atomically.py"
services = ["POSIX local filesystem supporting directory fsync"]
[[sources]]
url = "https://docs.python.org/3.12/library/os.html"
checked = 2026-11-16
[[sources]]
url = "https://docs.python.org/3.12/library/tempfile.html"
checked = 2026-11-16
+++

# Separate atomic file replacement from durability

## When to use

Use when readers should see either the old complete file or the new complete file.
A database or object store may be more appropriate for multi-writer application state.

## Rules

1. Stage in the destination directory so replacement stays on one filesystem.
2. Flush Python buffers and sync file data before replacing the name.
3. Sync the directory when crash persistence of the name matters.
4. Clean up staging paths and define permission/ownership policy.

## Reference example

```python
"""File adapter: stage, replace, and sync a file on POSIX."""

import os
import tempfile
from os import PathLike
from pathlib import Path


def replace_file(path: str | PathLike[str], content: bytes) -> None:
    path = Path(path)
    fd, temporary = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            _ = stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
```

## Guarantees and assumptions

The directory is trusted and not concurrently renamed; content is bounded.
The new file has mkstemp's private permissions, not the old file's metadata.
POSIX/filesystem durability behavior must be verified for the actual deployment.

## Pitfalls

Opening the destination with `"wb"` truncates the old value before success.
Atomic replacement is not multi-writer conflict control. Failure of directory
fsync after replacement is an ambiguous durability outcome, not a rollback.

## Verification

Run `uv run pytest tests/test_backend_files.py --task replace-files-atomically`.
Inject pre-replacement sync failure and verify the old file and cleanup. These
tests do not simulate power loss or certify filesystem crash durability.

## Sources

- [Python replace and fsync](https://docs.python.org/3.12/library/os.html)
- [Python secure temporary creation](https://docs.python.org/3.12/library/tempfile.html)
