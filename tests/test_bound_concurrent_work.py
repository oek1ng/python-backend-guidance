import asyncio
from collections import Counter
from collections.abc import AsyncIterator, Iterable
from contextlib import suppress

import pytest

from tests.contracts import ConsumeBounded

pytestmark = pytest.mark.contract("bound-concurrent-work")


def contains_failure(error: BaseException, expected: BaseException) -> bool:
    return error is expected or (
        isinstance(error, BaseExceptionGroup)
        and any(contains_failure(child, expected) for child in error.exceptions)
    )


async def source[T](items: Iterable[T]) -> AsyncIterator[T]:
    for item in items:
        yield item


async def cancel_and_wait(task: asyncio.Task[None]) -> None:
    if task.done():
        return
    _ = task.cancel()
    with suppress(asyncio.CancelledError):
        await task


@pytest.mark.parametrize("items", [[], [None, 0, 1, 2]])
async def test_success_handles_each_item_once_including_none(
    implementation: ConsumeBounded, items: list[int | None]
) -> None:
    handled: list[int | None] = []

    async def handle(item: int | None) -> None:
        handled.append(item)

    async with asyncio.timeout(5):
        await implementation(source(items), handle, concurrency=3, buffer_size=1)

    assert Counter(handled) == Counter(items)


async def test_saturated_workers_apply_backpressure_to_input(
    implementation: ConsumeBounded,
) -> None:
    concurrency, buffer_size = 3, 2
    capacity = concurrency + buffer_size + 1
    workers_ready = asyncio.Event()
    release = asyncio.Event()
    active = produced = completed = peak = peak_pending = 0

    async def input_stream() -> AsyncIterator[int]:
        nonlocal produced, peak_pending
        for item in range(100):
            produced += 1
            peak_pending = max(peak_pending, produced - completed)
            yield item

    async def handle(item: int) -> None:
        nonlocal active, completed, peak
        active += 1
        peak = max(peak, active)
        if active == concurrency:
            workers_ready.set()
        try:
            await release.wait()
            completed += 1
        finally:
            active -= 1

    task = asyncio.create_task(
        implementation(
            input_stream(),
            handle,
            concurrency=concurrency,
            buffer_size=buffer_size,
        )
    )
    try:
        async with asyncio.timeout(5):
            await workers_ready.wait()

            assert active == concurrency
            assert produced <= capacity

            release.set()
            await task
            assert peak == concurrency
            assert peak_pending <= capacity
    finally:
        release.set()
        await cancel_and_wait(task)


async def test_handler_failure_stops_other_work(implementation: ConsumeBounded) -> None:
    workers_ready = asyncio.Event()
    fail = asyncio.Event()
    active = 0
    failure = RuntimeError("handler failed")

    async def handle(item: int) -> None:
        nonlocal active
        active += 1
        if active == 2:
            workers_ready.set()
        try:
            if item == 0:
                await fail.wait()
                raise failure
            await asyncio.Event().wait()
        finally:
            active -= 1

    task = asyncio.create_task(
        implementation(source(range(100)), handle, concurrency=2, buffer_size=1)
    )
    try:
        async with asyncio.timeout(5):
            await workers_ready.wait()
            fail.set()

            with pytest.raises(Exception) as raised:
                await task

        assert contains_failure(raised.value, failure)
        assert active == 0
    finally:
        await cancel_and_wait(task)


async def test_source_failure_cancels_active_work(
    implementation: ConsumeBounded,
) -> None:
    started = asyncio.Event()
    cleaned_up = asyncio.Event()
    failure = RuntimeError("source failed")

    async def input_stream() -> AsyncIterator[int]:
        yield 0
        await started.wait()
        raise failure

    async def handle(item: int) -> None:
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            cleaned_up.set()

    async with asyncio.timeout(5):
        with pytest.raises(Exception) as raised:
            await implementation(input_stream(), handle, concurrency=2, buffer_size=1)

    assert contains_failure(raised.value, failure)
    assert cleaned_up.is_set()


async def test_parent_cancellation_waits_for_worker_cleanup(
    implementation: ConsumeBounded,
) -> None:
    workers_ready = asyncio.Event()
    cleanup_started = asyncio.Event()
    allow_cleanup = asyncio.Event()
    active = cleaning_up = cleaned_up = 0

    async def handle(item: int) -> None:
        nonlocal active, cleaning_up, cleaned_up
        active += 1
        if active == 2:
            workers_ready.set()
        try:
            await asyncio.Event().wait()
        finally:
            cleaning_up += 1
            if cleaning_up == 2:
                cleanup_started.set()
            await allow_cleanup.wait()
            active -= 1
            cleaned_up += 1

    task = asyncio.create_task(
        implementation(source(range(100)), handle, concurrency=2, buffer_size=1)
    )
    try:
        async with asyncio.timeout(5):
            await workers_ready.wait()
            assert active == 2

            _ = task.cancel()
            await cleanup_started.wait()
            assert not task.done()

            allow_cleanup.set()
            with pytest.raises(asyncio.CancelledError):
                await task

        assert active == 0
        assert cleaned_up == 2
    finally:
        allow_cleanup.set()
        await cancel_and_wait(task)


@pytest.mark.parametrize(
    ("concurrency", "buffer_size"),
    [(0, 1), (1, 0)],
    ids=["no-workers", "unbounded-queue"],
)
async def test_nonpositive_limits_are_rejected(
    implementation: ConsumeBounded, concurrency: int, buffer_size: int
) -> None:
    async def handle(item: int) -> None:
        raise AssertionError("Invalid configuration must not start work")

    with pytest.raises(ValueError, match="must be positive"):
        await implementation(
            source([0]),
            handle,
            concurrency=concurrency,
            buffer_size=buffer_size,
        )
