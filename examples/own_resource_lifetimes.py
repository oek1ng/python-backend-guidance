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
