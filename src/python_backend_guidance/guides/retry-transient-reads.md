+++
schema_version = 1
id = "retry-transient-reads"
title = "Retry transient reads within a shared budget"
description = "Retry only classified transient failures of repeatable reads, with capped jitter, bounded attempts, and a total deadline."
python = ">=3.12"
runtime = "asyncio"
tags = ["retry", "retries", "backoff", "jitter", "idempotency", "deadline"]
aliases = [
    "recover failed reads",
    "attempt count",
    "exponential backoff",
    "temporary failures",
    "non-transient errors",
    "validation errors",
]
status = "draft"
example = "examples/retry_transient_reads.py"

[[sources]]
url = "https://www.rfc-editor.org/rfc/rfc9110.html#section-9.2.2"
checked = 2026-11-16

[[sources]]
url = "https://www.rfc-editor.org/rfc/rfc9110.html#section-10.2.3"
checked = 2026-11-16

[[sources]]
url = "https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/"
checked = 2026-11-16

[[sources]]
url = "https://docs.python.org/3.12/library/asyncio-task.html#timeouts"
checked = 2026-11-16
+++

# Retry transient reads within a shared budget

## When to use

Use for an asynchronous, repeatable read whose adapter can identify a specific
transient failure. Prefer a client's existing retry policy if it already provides
the needed classification, limits, and cancellation behavior. Do not add a
second retry layer around an already retrying SDK without accounting for it.

This is deliberately not a generic mutation retry helper. A timeout does not
establish that a previous operation had no effect. An idempotency header alone
does not establish durable server-side deduplication.

## Rules

1. Establish that repeating this particular operation is safe. HTTP method
   semantics are relevant, but do not turn an arbitrary application mutation
   into a repeatable read.
2. Retry only explicitly classified transient failures. Do not blanket-catch
   `Exception`, validation errors, authentication failures, or cancellation.
3. Limit total attempts, including the initial call, and cover attempts and
   waiting with one monotonic deadline.
4. Use capped exponential backoff with full jitter. Do not begin another attempt
   if the selected backoff cannot fit in the remaining budget.
5. Coordinate retry ownership. Independent policies at multiple layers multiply
   downstream traffic; retries can worsen overload.

## Reference example

The runnable copy is `examples/retry_transient_reads.py`. The adapter must convert
only vetted transient failures into `TransientReadError`; it is not a transport
exception classifier.

```python
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
```

## Guarantees and assumptions

The first successful result is returned without another attempt. Only
`TransientReadError` permits a retry. Attempt exhaustion propagates the last such
error; an expired budget produces `TimeoutError`. Other errors and external
cancellation propagate without retrying.

The same timeout scope covers the operation and backoff. Its cancellation is
cooperative, not a hard wall-clock or remote-execution guarantee. This policy is
per invocation, not a shared retry quota or a deployment-wide rate limiter.

## Pitfalls

- This example does not parse HTTP responses or `Retry-After`. An HTTP adapter
  must honor applicable server delay instructions within the remaining budget,
  or stop retrying; do not map such a response to this marker and discard its
  instructions. Use a vetted client policy when possible.
- Do not assume every server error is transient or every connection error proves
  that a write was never applied.
- Full jitter can select a very short delay. The attempt count and total budget
  remain essential; a positive backoff alone is not a retry bound.
- Do not hold an unrelated transaction, lock, or exhausted connection while
  sleeping between attempts.
- For mutations, specify and test the actual idempotency mechanism separately.
  This guide does not provide exactly-once execution or rollback.

## Verification

Check immediate success, classified failure recovery, attempt exhaustion,
non-transient errors, capped backoff, insufficient remaining budget, deadline
expiry, and cancellation. Control randomness and the waiting boundary when
checking backoff arithmetic; use real asyncio for cancellation and timeout tests.

## Sources

Sources checked on 2026-11-16; this draft has not had independent review.

- [RFC 9110: idempotent methods](https://www.rfc-editor.org/rfc/rfc9110.html#section-9.2.2)
- [RFC 9110: Retry-After](https://www.rfc-editor.org/rfc/rfc9110.html#section-10.2.3)
- [Amazon Builders' Library: timeouts, retries, and backoff with jitter](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/)
- [Python: timeout scopes](https://docs.python.org/3.12/library/asyncio-task.html#timeouts)
