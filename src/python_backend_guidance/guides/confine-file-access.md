+++
schema_version = 1
id = "confine-file-access"
title = "Confine file access beneath a trusted directory"
description = "Use a trusted POSIX directory descriptor, flat names and no-follow opening to reject traversal and symlink escapes."
python = ">=3.12"
runtime = "sync"
tags = ["path-traversal", "symlinks", "file-access", "directory-fd"]
aliases = ["safe path traversal file uploads", "symlink file escape"]
status = "draft"
example = "examples/confine_file_access.py"
services = ["POSIX filesystem with dir_fd and O_NOFOLLOW support"]
[[sources]]
url = "https://docs.python.org/3.12/library/os.html"
checked = 2026-11-16
+++

# Confine file access beneath a trusted directory

## When to use

Use for a flat, application-owned storage directory addressed by an opaque
filename. Nested paths require a component-wise secure traversal or a suitable
platform API; do not stretch this helper into that use case.

## Rules

1. Open and retain a trusted root directory descriptor.
2. Accept one filename component, rejecting separators and dot traversal.
3. Refuse symlink following atomically at open.
4. Keep untrusted users from creating device files, hard links or directories in the root.

## Reference example

```python
"""File adapter: open one flat filename beneath a trusted directory."""

import os


def read_owned_file(directory_fd: int, name: str) -> bytes:
    if name == "" or name in {".", ".."} or "/" in name or "\\" in name:
        raise ValueError("a single filename is required")
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory_fd)
    with os.fdopen(fd, "rb") as stream:
        return stream.read()
```

## Guarantees and assumptions

POSIX support is required. The directory descriptor is caller-owned; the opened
file is closed by the helper. Files are regular, bounded-size, application-created
objects; filesystem ownership and authorization are separate prerequisites.

## Pitfalls

`resolve(); check_prefix(); open()` has a check/use race in mutable directories.
String prefix checks confuse sibling paths. O_NOFOLLOW does not reject hard links
or special files; directory write permissions are part of this recipe's assumptions.

## Verification

Run `uv run pytest tests/test_backend_security.py --task confine-file-access`.
Check a real symlink escape, parent traversal and a regular local file.

## Sources

- [Python descriptor-relative opening and O_NOFOLLOW](https://docs.python.org/3.12/library/os.html)
