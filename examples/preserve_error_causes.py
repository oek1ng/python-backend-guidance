"""Application boundary: expose a fixed error while preserving its cause."""

from collections.abc import Callable


class BackendUnavailable(Exception):
    pass


def read_backend[T](operation: Callable[[], T]) -> T:
    try:
        return operation()
    except OSError as error:
        raise BackendUnavailable("backend temporarily unavailable") from error
