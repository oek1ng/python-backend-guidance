"""Application policy: admit work immediately without unbounded waiters."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager


class Admission:
    capacity: int
    active: int

    def __init__(self, capacity: int) -> None:
        if capacity < 1:
            raise ValueError("capacity must be positive")
        self.capacity = capacity
        self.active = 0

    @asynccontextmanager
    async def enter(self) -> AsyncGenerator[None, None]:
        if self.active >= self.capacity:
            raise RuntimeError("overloaded")
        self.active += 1
        try:
            yield
        finally:
            self.active -= 1
