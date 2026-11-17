"""Composition root: unwind resources when a later acquisition fails."""

from collections.abc import Callable, Generator, Iterable
from contextlib import ExitStack, contextmanager
from typing import Protocol


class Closeable(Protocol):
    def close(self) -> None: ...


@contextmanager
def open_resources[T: Closeable](
    factories: Iterable[Callable[[], T]],
) -> Generator[list[T], None, None]:
    with ExitStack() as stack:
        resources: list[T] = []
        for factory in factories:
            resource = factory()
            _ = stack.callback(resource.close)
            resources.append(resource)
        yield resources
