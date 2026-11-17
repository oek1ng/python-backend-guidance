"""Static regression checks: Pyrefly must preserve concrete caller result types.

These functions are checked, not executed; runtime behavior has public contracts.
"""

import io
from pathlib import Path
from typing import assert_type

from psycopg import Connection

from examples.apply_operation_deadline import fetch_and_store
from examples.coalesce_cache_misses import SingleFlight
from examples.distinguish_cache_misses import lookup
from examples.expire_cached_values import TTLCache
from examples.offload_blocking_io import call_blocking
from examples.own_resource_lifetimes import owned_resource
from examples.own_temporary_files import with_workspace
from examples.retry_transient_reads import retry_read
from examples.retry_whole_transactions import run_transaction


def synchronous_results(connection: Connection[tuple[object, ...]]) -> None:
    cache = TTLCache[str, int](ttl=1)
    cache.put("key", 1)
    assert_type(cache.get("key"), int)
    negative_cache: dict[str, int | None] = {}
    assert_type(lookup(negative_cache, "key", len), int | None)
    assert_type(run_transaction(connection, lambda conn: "result"), str)
    assert_type(with_workspace(lambda path: path / "result"), Path)
    with owned_resource(io.BytesIO) as stream:
        assert_type(stream, io.BytesIO)


async def asynchronous_results() -> None:
    async def fetch() -> int:
        return 1

    async def store(value: int) -> str:
        return str(value)

    def blocking(value: int, prefix: str) -> str:
        return f"{prefix}{value}"

    assert_type(await fetch_and_store(fetch, store, deadline=1), str)
    assert_type(await retry_read(fetch, deadline=1), int)
    assert_type(await call_blocking(blocking, 1, "value="), str)
    flight = SingleFlight[str, int]()
    assert_type(await flight.get("key", fetch), int)
