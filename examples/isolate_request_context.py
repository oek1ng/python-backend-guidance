"""Input boundary: restore request context even when a request fails."""

from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar

request_id: ContextVar[str | None] = ContextVar("request_id", default=None)


@contextmanager
def request_scope(value: str) -> Generator[None, None, None]:
    token = request_id.set(value)
    try:
        yield
    finally:
        request_id.reset(token)
