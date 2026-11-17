import asyncio
import threading
from contextlib import suppress
from typing import Never

import pytest

from tests.contracts import (
    Admission,
    CallBlocking,
    ContextModule,
    Drain,
    RequestScope,
    RunRelated,
    RunStoppable,
)


@pytest.mark.contract("own-child-tasks")
class TestTaskOwnership:
    async def test_sibling_failure_waits_for_cleanup(
        self, implementation: RunRelated
    ) -> None:
        entered, cleaned = asyncio.Event(), asyncio.Event()

        async def blocked() -> Never:
            entered.set()
            try:
                await asyncio.Future[Never]()
            finally:
                cleaned.set()

        async def fail() -> Never:
            await entered.wait()
            raise ValueError("child failed")

        try:
            with pytest.raises(ExceptionGroup):
                await implementation([blocked, fail])
            assert cleaned.is_set()
        finally:
            # A defective candidate must not leave the test runner with live tasks.
            for task in asyncio.all_tasks() - {asyncio.current_task()}:
                _ = task.cancel()

    async def test_related_results_preserve_input_order(
        self, implementation: RunRelated
    ) -> None:
        async def first() -> int:
            await asyncio.sleep(0)
            return 1

        async def second() -> int:
            return 2

        assert await implementation([first, second]) == [1, 2]


@pytest.mark.contract("offload-blocking-io")
class TestBlockingIO:
    async def test_loop_progresses_while_blocking_io_waits(
        self, implementation: CallBlocking
    ) -> None:
        release = threading.Event()

        def blocking() -> bool:
            return release.wait(1)

        _ = asyncio.get_running_loop().call_soon(release.set)

        assert await implementation(blocking)

    async def test_blocking_io_error_propagates(
        self, implementation: CallBlocking
    ) -> None:
        def fail() -> Never:
            raise OSError("disk")

        with pytest.raises(OSError, match="disk"):
            await implementation(fail)


@pytest.mark.contract("stop-thread-work")
class TestThreadCancellation:
    async def test_cancel_joins_cooperatively_stopped_thread(
        self, implementation: RunStoppable
    ) -> None:
        loop = asyncio.get_running_loop()
        entered = asyncio.Event()
        cleanup_started = asyncio.Event()
        allow_cleanup = threading.Event()
        stopped = threading.Event()

        def worker(stop: threading.Event) -> None:
            _ = loop.call_soon_threadsafe(entered.set)
            _ = stop.wait(1)
            _ = loop.call_soon_threadsafe(cleanup_started.set)
            _ = allow_cleanup.wait(2)
            stopped.set()

        task = asyncio.create_task(implementation(worker))
        try:
            await asyncio.wait_for(entered.wait(), 2)
            _ = task.cancel()
            await asyncio.wait_for(cleanup_started.wait(), 2)
            assert not task.done()
            allow_cleanup.set()
            with pytest.raises(asyncio.CancelledError):
                await task
            assert stopped.is_set()
        finally:
            allow_cleanup.set()
            _ = task.cancel()
            with suppress(asyncio.CancelledError):
                await task
            assert await asyncio.to_thread(stopped.wait, 2)

    async def test_thread_result_is_returned(
        self, implementation: RunStoppable
    ) -> None:
        assert await implementation(lambda stop: 42) == 42


@pytest.mark.contract("isolate-request-context")
class TestRequestContext:
    def test_context_restored_after_error(
        self, implementation: RequestScope, solution_module: ContextModule
    ) -> None:
        variable = solution_module.request_id
        with implementation("outer"):
            with pytest.raises(ValueError), implementation("inner"):
                assert variable.get() == "inner"
                raise ValueError
            assert variable.get() == "outer"
        assert variable.get() is None

    async def test_parallel_requests_have_distinct_contexts(
        self, implementation: RequestScope, solution_module: ContextModule
    ) -> None:
        async def request(identity: str) -> str | None:
            with implementation(identity):
                await asyncio.sleep(0)
                return solution_module.request_id.get()

        assert await asyncio.gather(request("a"), request("b")) == ["a", "b"]


@pytest.mark.contract("drain-on-shutdown")
class TestShutdown:
    async def test_shutdown_cancels_and_awaits_stragglers(
        self, implementation: Drain
    ) -> None:
        started, cleaned = asyncio.Event(), asyncio.Event()

        async def pending() -> Never:
            started.set()
            try:
                await asyncio.Future[Never]()
            finally:
                cleaned.set()

        task = asyncio.create_task(pending())
        await started.wait()
        try:
            await implementation([task], grace=0)
            assert cleaned.is_set()
            assert task.done()
        finally:
            _ = task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    async def test_drain_preserves_already_completed_results(
        self, implementation: Drain
    ) -> None:
        task = asyncio.create_task(asyncio.sleep(0, result=7))
        await task

        assert await implementation([task], grace=1) == [7]


@pytest.mark.contract("reject-overload")
class TestAdmission:
    async def test_saturated_admission_rejects_without_waiting(
        self, implementation: Admission
    ) -> None:
        gate = implementation(1)
        async with gate.enter():
            with pytest.raises(RuntimeError, match="overloaded"):
                async with gate.enter():
                    pytest.fail("accepted above capacity")

    async def test_failed_request_returns_admission_slot(
        self, implementation: Admission
    ) -> None:
        gate = implementation(1)
        with pytest.raises(ValueError):
            async with gate.enter():
                raise ValueError

        async with gate.enter():
            pass
