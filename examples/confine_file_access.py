"""File adapter: open one flat filename beneath a trusted directory."""

import os


def read_owned_file(directory_fd: int, name: str) -> bytes:
    if name == "" or name in {".", ".."} or "/" in name or "\\" in name:
        raise ValueError("a single filename is required")
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory_fd)
    with os.fdopen(fd, "rb") as stream:
        return stream.read()
