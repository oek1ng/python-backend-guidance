"""Composition root: allocate a pool from the deployment connection budget."""

from psycopg import Connection
from psycopg_pool import ConnectionPool


def pool_capacity(*, database_limit: int, reserved: int, processes: int) -> int:
    """Deployment policy independent of the pool implementation."""
    if processes < 1 or reserved < 0:
        raise ValueError("invalid process count or reserve")
    capacity = (database_limit - reserved) // processes
    if capacity < 1:
        raise ValueError("no connection budget")
    return capacity


def open_pool(
    dsn: str, *, database_limit: int, reserved: int, processes: int
) -> ConnectionPool[Connection[tuple[object, ...]]]:
    capacity = pool_capacity(
        database_limit=database_limit, reserved=reserved, processes=processes
    )
    return ConnectionPool[Connection[tuple[object, ...]]](
        dsn,
        connection_class=Connection[tuple[object, ...]],
        min_size=0,
        max_size=capacity,
        max_waiting=capacity,
        timeout=1,
    )
