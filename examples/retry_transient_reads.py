"""Application policy: bounded retries for a borrowed read-only operation."""

import asyncio
import math
import random
from collections.abc import Awaitable, Callable


class TransientReadError(Exception):
    """The adapter identified a transient failure of a repeatable read."""


async def retry_read[T](
    operation: Callable[[], Awaitable[T]],
    *,
    deadline: float,
    max_attempts: int = 3,
    base_delay: float = 0.1,
    max_delay: float = 2.0,
) -> T:
    if max_attempts < 1:
        raise ValueError("max_attempts must be positive")
    if not math.isfinite(deadline):
        raise ValueError("deadline must be finite")
    if any(not math.isfinite(delay) or delay < 0 for delay in (base_delay, max_delay)):
        raise ValueError("backoff delays must be finite and nonnegative")

    loop = asyncio.get_running_loop()
    if deadline <= loop.time():
        raise TimeoutError("retry deadline already expired")

    attempt = 1
    ceiling = min(base_delay, max_delay)
    async with asyncio.timeout_at(deadline):
        while True:
            try:
                return await operation()
            except TransientReadError:
                if attempt >= max_attempts:
                    raise

            delay = random.uniform(0, ceiling)
            if delay >= deadline - loop.time():
                raise TimeoutError("retry backoff cannot fit within the deadline")
            await asyncio.sleep(delay)
            ceiling = min(max_delay, ceiling * 2)
            attempt += 1


class DemoRead:
    def __init__(self) -> None:
        self.attempts = 0

    async def __call__(self) -> str:
        self.attempts += 1
        if self.attempts == 1:
            raise TransientReadError("temporary unavailability")
        return "recovered"


async def main() -> None:
    deadline = asyncio.get_running_loop().time() + 2
    print(await retry_read(DemoRead(), deadline=deadline))


if __name__ == "__main__":
    asyncio.run(main())
