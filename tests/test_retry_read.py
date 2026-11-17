import asyncio
from contextlib import suppress
from typing import Never

import pytest

from tests.contracts import RetryModule, RetryRead, RetrySettings

pytestmark = pytest.mark.contract("retry-transient-reads")


async def test_success_is_returned_without_an_extra_attempt(
    implementation: RetryRead,
) -> None:
    attempts = 0

    async def operation() -> str:
        nonlocal attempts
        attempts += 1
        return "value"

    result = await implementation(
        operation, deadline=asyncio.get_running_loop().time() + 60
    )

    assert result == "value"
    assert attempts == 1


async def test_backoff_grows_to_its_cap_and_stops_after_success(
    implementation: RetryRead, solution_module: RetryModule, retry_delays: list[float]
) -> None:
    attempts = 0
    transient = solution_module.TransientReadError

    async def operation() -> str:
        nonlocal attempts
        attempts += 1
        if attempts < 5:
            raise transient("temporary unavailability")
        return "recovered"

    result = await implementation(
        operation,
        deadline=asyncio.get_running_loop().time() + 60,
        max_attempts=5,
        base_delay=0.25,
        max_delay=0.5,
    )

    assert result == "recovered"
    assert attempts == 5
    assert retry_delays == [0.25, 0.5, 0.5, 0.5]


async def test_retry_exhaustion_preserves_the_last_error(
    implementation: RetryRead, solution_module: RetryModule
) -> None:
    failure = solution_module.TransientReadError("still unavailable")
    attempts = 0

    async def operation() -> Never:
        nonlocal attempts
        attempts += 1
        raise failure

    with pytest.raises(solution_module.TransientReadError) as raised:
        await implementation(
            operation,
            deadline=asyncio.get_running_loop().time() + 60,
            max_attempts=3,
            base_delay=0,
            max_delay=0,
        )

    assert raised.value is failure
    assert attempts == 3


async def test_nontransient_error_is_not_retried(implementation: RetryRead) -> None:
    failure = ValueError("invalid request")
    attempts = 0

    async def operation() -> Never:
        nonlocal attempts
        attempts += 1
        raise failure

    with pytest.raises(ValueError) as raised:
        await implementation(operation, deadline=asyncio.get_running_loop().time() + 60)

    assert raised.value is failure
    assert attempts == 1


async def test_backoff_that_cannot_fit_does_not_start_another_attempt(
    implementation: RetryRead, solution_module: RetryModule, retry_delays: list[float]
) -> None:
    attempts = 0

    async def operation() -> Never:
        nonlocal attempts
        attempts += 1
        raise solution_module.TransientReadError("unavailable")

    with pytest.raises(TimeoutError):
        await implementation(
            operation,
            deadline=asyncio.get_running_loop().time() + 1,
            base_delay=2,
            max_delay=2,
        )

    assert attempts == 1
    assert retry_delays == []


async def test_operation_is_covered_by_the_total_deadline(
    implementation: RetryRead,
) -> None:
    cleaned_up = asyncio.Event()
    release = asyncio.Event()
    loop = asyncio.get_running_loop()
    deadline = loop.time() + 0.02
    witness = loop.call_at(deadline + 0.5, release.set)

    async def operation() -> None:
        try:
            await release.wait()
        finally:
            cleaned_up.set()

    try:
        async with asyncio.timeout(5):
            with pytest.raises(TimeoutError):
                await implementation(operation, deadline=deadline)
    finally:
        witness.cancel()

    assert cleaned_up.is_set()


async def test_cancellation_does_not_trigger_a_retry(implementation: RetryRead) -> None:
    started = asyncio.Event()
    attempts = 0

    async def operation() -> None:
        nonlocal attempts
        attempts += 1
        started.set()
        await asyncio.Event().wait()

    task = asyncio.create_task(
        implementation(operation, deadline=asyncio.get_running_loop().time() + 60)
    )
    try:
        async with asyncio.timeout(5):
            await started.wait()
            _ = task.cancel()

            with pytest.raises(asyncio.CancelledError):
                await task

        assert attempts == 1
    finally:
        if not task.done():
            _ = task.cancel()
        with suppress(asyncio.CancelledError):
            await task


async def test_expired_deadline_does_not_attempt_the_read(
    implementation: RetryRead,
) -> None:
    async def unexpected() -> Never:
        pytest.fail("Expired retry budget must not start work")

    with pytest.raises(TimeoutError):
        await implementation(unexpected, deadline=asyncio.get_running_loop().time() - 1)


@pytest.mark.parametrize(
    "settings",
    [
        {"max_attempts": 0},
        {"base_delay": -1},
        {"max_delay": float("inf")},
    ],
    ids=["no-attempts", "negative-backoff", "nonfinite-backoff"],
)
async def test_invalid_retry_settings_are_rejected(
    implementation: RetryRead, settings: RetrySettings
) -> None:
    async def unexpected() -> Never:
        pytest.fail("Invalid settings must not start work")

    with pytest.raises(ValueError):
        await implementation(
            unexpected,
            deadline=asyncio.get_running_loop().time() + 60,
            max_attempts=settings.get("max_attempts", 3),
            base_delay=settings.get("base_delay", 0.1),
            max_delay=settings.get("max_delay", 2.0),
        )
