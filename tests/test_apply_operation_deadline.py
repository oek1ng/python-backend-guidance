import asyncio
from contextlib import suppress
from typing import Never

import pytest

from tests.contracts import FetchAndStore

pytestmark = pytest.mark.contract("apply-operation-deadline")


async def test_pipeline_passes_loaded_value_and_returns_store_result(
    implementation: FetchAndStore,
) -> None:
    stored: list[dict[str, int]] = []

    async def fetch() -> dict[str, int]:
        return {"id": 7}

    async def store(value: dict[str, int]) -> str:
        stored.append(value)
        return "receipt"

    result = await implementation(
        fetch, store, deadline=asyncio.get_running_loop().time() + 60
    )

    assert result == "receipt"
    assert stored == [{"id": 7}]


async def test_expired_budget_does_not_start_work(
    implementation: FetchAndStore,
) -> None:
    async def unexpected(*args: object) -> Never:
        pytest.fail("An expired operation must not start a stage")

    with pytest.raises(TimeoutError):
        await implementation(
            unexpected, unexpected, deadline=asyncio.get_running_loop().time() - 1
        )


@pytest.mark.parametrize("blocked_stage", ["fetch", "store"])
async def test_deadline_covers_each_stage_and_waits_for_cleanup(
    implementation: FetchAndStore, blocked_stage: str
) -> None:
    cleaned_up = asyncio.Event()
    release = asyncio.Event()
    loop = asyncio.get_running_loop()
    deadline = loop.time() + 0.02
    # An unbounded implementation returns successfully instead of borrowing the
    # outer deadlock guard's TimeoutError as evidence of correct behavior.
    witness = loop.call_at(deadline + 0.5, release.set)

    async def block() -> None:
        try:
            await release.wait()
        finally:
            cleaned_up.set()

    async def fetch() -> str:
        if blocked_stage == "fetch":
            await block()
        return "payload"

    async def store(value: str) -> None:
        if blocked_stage == "store":
            await block()

    try:
        async with asyncio.timeout(5):
            with pytest.raises(TimeoutError):
                await implementation(fetch, store, deadline=deadline)
    finally:
        witness.cancel()

    assert cleaned_up.is_set()


async def test_external_cancellation_is_not_reported_as_a_deadline(
    implementation: FetchAndStore,
) -> None:
    started = asyncio.Event()
    cleaned_up = asyncio.Event()

    async def fetch() -> None:
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            cleaned_up.set()

    async def store(value: None) -> Never:
        pytest.fail("Cancelled fetch must not start store")

    task = asyncio.create_task(
        implementation(fetch, store, deadline=asyncio.get_running_loop().time() + 60)
    )
    try:
        async with asyncio.timeout(5):
            await started.wait()

            _ = task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task

        assert cleaned_up.is_set()
    finally:
        if not task.done():
            _ = task.cancel()
        with suppress(asyncio.CancelledError):
            await task


async def test_stage_error_is_not_reclassified_as_timeout(
    implementation: FetchAndStore,
) -> None:
    failure = ValueError("invalid payload")

    async def fetch() -> Never:
        raise failure

    async def store(value: object) -> Never:
        pytest.fail("Failed fetch must not start store")

    with pytest.raises(ValueError) as raised:
        await implementation(
            fetch, store, deadline=asyncio.get_running_loop().time() + 60
        )

    assert raised.value is failure


async def test_nonfinite_deadline_is_rejected(implementation: FetchAndStore) -> None:
    async def unexpected(*args: object) -> Never:
        pytest.fail("Invalid budget must not start work")

    with pytest.raises(ValueError, match="finite"):
        await implementation(unexpected, unexpected, deadline=float("nan"))
