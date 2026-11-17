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
