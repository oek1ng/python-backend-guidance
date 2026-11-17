"""Exploratory application grading; not accessible during agent authoring."""

import asyncio
import importlib.util
import os
import sys
import unittest
from collections import Counter
from collections.abc import AsyncIterable, AsyncIterator, Awaitable, Callable
from pathlib import Path
from typing import Protocol, cast


class SyncInventory(Protocol):
    def __call__[T](
        self,
        records: AsyncIterable[T],
        persist: Callable[[T], Awaitable[None]],
        *,
        workers: int,
        pending: int,
    ) -> Awaitable[int]: ...


def solution() -> SyncInventory:
    path = Path(os.environ["PBG_CANDIDATE"])
    spec = importlib.util.spec_from_file_location("app_candidate", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return cast(SyncInventory, getattr(module, "sync_inventory"))


async def source[T](items: list[T]) -> AsyncIterator[T]:
    for item in items:
        yield item


class InventoryChecks(unittest.IsolatedAsyncioTestCase):
    async def test_returns_count_and_handles_none_once(self) -> None:
        persisted: list[int | None] = []

        async def persist(item: int | None) -> None:
            persisted.append(item)

        count = await asyncio.wait_for(
            solution()(source([None, 1, 2]), persist, workers=2, pending=1), 3
        )

        self.assertEqual(count, 3)
        self.assertEqual(Counter(persisted), Counter([None, 1, 2]))

    async def test_backpressure_bounds_input_and_active_handlers(self) -> None:
        release = asyncio.Event()
        ready = asyncio.Event()
        produced = active = completed = peak = peak_pending = 0

        async def records() -> AsyncIterator[int]:
            nonlocal produced, peak_pending
            for item in range(50):
                produced += 1
                peak_pending = max(peak_pending, produced - completed)
                yield item

        async def persist(item: int) -> None:
            nonlocal active, completed, peak
            active += 1
            peak = max(peak, active)
            if active == 2:
                ready.set()
            try:
                await release.wait()
                completed += 1
            finally:
                active -= 1

        task = asyncio.ensure_future(
            solution()(records(), persist, workers=2, pending=2)
        )
        try:
            await asyncio.wait_for(ready.wait(), 3)
            self.assertEqual(active, 2)
            self.assertLessEqual(produced, 5)
            release.set()
            self.assertEqual(await asyncio.wait_for(task, 3), 50)
            self.assertLessEqual(peak, 2)
            self.assertLessEqual(peak_pending, 5)
        finally:
            release.set()
            if not task.done():
                _ = task.cancel()
            _ = await asyncio.gather(task, return_exceptions=True)

    async def test_handler_error_joins_started_handlers(self) -> None:
        ready = asyncio.Event()
        fail = asyncio.Event()
        active = 0
        error = RuntimeError("storage failed")

        async def persist(item: int) -> None:
            nonlocal active
            active += 1
            if active == 2:
                ready.set()
            try:
                if item == 0:
                    await fail.wait()
                    raise error
                await asyncio.Event().wait()
            finally:
                active -= 1

        task = asyncio.ensure_future(
            solution()(source(list(range(50))), persist, workers=2, pending=1)
        )
        try:
            await asyncio.wait_for(ready.wait(), 3)
            fail.set()
            with self.assertRaises(Exception):
                _ = await asyncio.wait_for(task, 3)
            self.assertEqual(active, 0)
        finally:
            if not task.done():
                _ = task.cancel()
            _ = await asyncio.gather(task, return_exceptions=True)

    async def test_invalid_capacity_does_not_read_source(self) -> None:
        started: list[int] = []

        async def persist(item: int) -> None:
            started.append(item)

        with self.assertRaises(ValueError):
            _ = await solution()(source([1]), persist, workers=0, pending=1)
        self.assertEqual(started, [])


if __name__ == "__main__":
    _ = unittest.main(verbosity=2)
