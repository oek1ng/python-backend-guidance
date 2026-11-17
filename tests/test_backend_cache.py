import asyncio
from typing import Never

import pytest

from tests.contracts import CacheKey, Lookup, NotFoundModule, SingleFlight, TTLCache


@pytest.mark.contract("scope-cache-keys")
class TestCacheKeys:
    def test_cache_key_separates_tenants_and_delimiters(
        self, implementation: CacheKey
    ) -> None:
        keys = {
            implementation("a:b", "c", "en"),
            implementation("a", "b:c", "en"),
            implementation("other", "c", "en"),
            implementation("a:b", "c", "fr"),
        }

        assert len(keys) == 4


@pytest.mark.contract("expire-cached-values")
class TestCacheExpiry:
    def test_expiry_boundary_is_a_miss(self, implementation: TTLCache) -> None:
        now = [10]
        cache = implementation(ttl=5, clock=lambda: now[0])
        cache.put("key", "value")
        now[0] = 15

        with pytest.raises(KeyError):
            _ = cache.get("key")

    def test_explicit_invalidation_removes_fresh_value(
        self, implementation: TTLCache
    ) -> None:
        cache = implementation(ttl=5, clock=lambda: 10)
        cache.put("key", "value")
        assert cache.get("key") == "value"

        cache.invalidate("key")
        with pytest.raises(KeyError):
            _ = cache.get("key")


@pytest.mark.contract("coalesce-cache-misses")
class TestSingleFlight:
    async def test_simultaneous_misses_share_one_load(
        self, implementation: SingleFlight
    ) -> None:
        flight = implementation()
        release = asyncio.Event()
        calls = []

        async def load() -> int:
            calls.append(1)
            await release.wait()
            return 42

        first = asyncio.create_task(flight.get("key", load))
        second = asyncio.create_task(flight.get("key", load))
        await asyncio.sleep(0)
        release.set()
        try:
            assert await asyncio.gather(first, second) == [42, 42]
            assert len(calls) == 1
        finally:
            await flight.close()

    async def test_cancelled_waiter_does_not_cancel_shared_load(
        self, implementation: SingleFlight
    ) -> None:
        flight = implementation()
        entered, release = asyncio.Event(), asyncio.Event()

        async def load() -> int:
            entered.set()
            await release.wait()
            return 42

        first = asyncio.create_task(flight.get("key", load))
        second = asyncio.create_task(flight.get("key", load))
        await entered.wait()
        _ = first.cancel()
        try:
            with pytest.raises(asyncio.CancelledError):
                await first
            release.set()
            assert await second == 42
        finally:
            await flight.close()

    async def test_failed_load_can_be_retried(
        self, implementation: SingleFlight
    ) -> None:
        flight = implementation()
        attempts = 0

        async def load() -> int:
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise OSError("temporary backend failure")
            return 42

        try:
            with pytest.raises(OSError, match="temporary backend failure"):
                _ = await flight.get("key", load)

            assert await flight.get("key", load) == 42
            assert attempts == 2
        finally:
            await flight.close()

    async def test_close_awaits_loader_cleanup(
        self, implementation: SingleFlight
    ) -> None:
        flight = implementation()
        entered, cleaning, release, cleaned = (asyncio.Event() for _ in range(4))
        finish = asyncio.Event()

        async def load() -> int:
            entered.set()
            try:
                await finish.wait()
            finally:
                cleaning.set()
                try:
                    await release.wait()
                except asyncio.CancelledError:
                    # close may cancel a load that has already begun cleanup.
                    await release.wait()
                cleaned.set()
            return 42

        waiter = asyncio.create_task(flight.get("key", load))
        closing: asyncio.Task[None] | None = None
        try:
            await asyncio.wait_for(entered.wait(), 5)

            closing = asyncio.create_task(flight.close())
            finish.set()  # A draining close is also a valid ownership strategy.
            await asyncio.wait_for(cleaning.wait(), 5)
            assert not closing.done()
            release.set()
            await asyncio.wait_for(closing, 5)

            assert cleaned.is_set()
        finally:
            finish.set()
            release.set()
            await flight.close()
            _ = await asyncio.gather(waiter, return_exceptions=True)
            if closing is not None:
                _ = await asyncio.gather(closing, return_exceptions=True)


@pytest.mark.contract("distinguish-cache-misses")
class TestNegativeCaching:
    def test_backend_failure_is_not_cached_as_absence(
        self, implementation: Lookup
    ) -> None:
        cache: dict[str, str | None] = {}

        def fail(key: str) -> Never:
            raise OSError("backend unavailable")

        with pytest.raises(OSError):
            _ = implementation(cache, "key", fail)
        assert "key" not in cache

    def test_definitive_absence_is_cached(
        self, implementation: Lookup, solution_module: NotFoundModule
    ) -> None:
        cache: dict[str, str | None] = {}
        calls: list[str] = []

        def missing(key: str) -> Never:
            calls.append(key)
            raise solution_module.NotFound

        assert implementation(cache, "key", missing) is None
        assert implementation(cache, "key", missing) is None
        assert calls == ["key"]
