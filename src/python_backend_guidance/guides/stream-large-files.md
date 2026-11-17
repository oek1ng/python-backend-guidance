+++
schema_version = 1
id = "stream-large-files"
title = "Stream files with bounded buffers"
description = "Copy file data incrementally, enforce an accepted-byte budget, and keep stream ownership explicit."
python = ">=3.12"
runtime = "sync"
tags = ["files", "streaming-copy", "memory", "byte-budget"]
aliases = ["stream large file", "bounded file buffer"]
status = "draft"
example = "examples/stream_large_files.py"
[[sources]]
url = "https://docs.python.org/3.12/library/io.html"
checked = 2026-11-16
+++

# Stream files with bounded buffers

## When to use

Use for uploads, exports and file copies that may be larger than available memory.
Reading a small fixed-size configuration file at once is often simpler.

## Rules

1. Read finite chunks rather than the entire source.
2. Count actual bytes and reject beyond the allowed total.
3. Define who closes each stream and removes partial output.
4. Publish a completed artifact only after successful copy and validation.

## Reference example

```python
"""File adapter: copy borrowed streams with bounded reads and total bytes."""

from typing import Protocol


class BinaryReader(Protocol):
    def read(self, size: int, /) -> bytes: ...


class BinaryWriter(Protocol):
    def write(self, data: bytes, /) -> int: ...


def copy_stream(source: BinaryReader, destination: BinaryWriter, *, limit: int) -> int:
    if limit < 0:
        raise ValueError("limit must be nonnegative")
    count = 0
    while (chunk := source.read(min(65536, limit - count + 1))) != b"":
        count += len(chunk)
        if count > limit:
            raise ValueError("file too large")
        _ = destination.write(chunk)
    return count
```

## Guarantees and assumptions

Inputs are blocking binary buffered streams honoring requested read size and
complete writes. The helper reads at most one byte beyond the limit to detect
overflow. Both streams remain caller-owned; partial destination content may exist.

## Pitfalls

`destination.write(source.read())` scales memory with the file. A raw/nonblocking
writer may perform short writes and needs a different loop. Blocking file I/O
must not run directly on an async request's event loop.

## Verification

Run `uv run pytest tests/test_backend_files.py --task stream-large-files`.
Check byte preservation and that excess input is not written to the destination.

## Sources

- [Python binary buffered I/O](https://docs.python.org/3.12/library/io.html)
