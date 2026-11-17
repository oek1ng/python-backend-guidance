"""Persistence adapter: serialize migrations with a PostgreSQL advisory lock."""

from collections.abc import Callable

from psycopg import Connection


def run_migration(
    connection: Connection[tuple[object, ...]],
    migration: Callable[[Connection[tuple[object, ...]]], None],
) -> None:
    with connection.transaction():
        row = connection.execute(
            "SELECT pg_try_advisory_xact_lock(%s)", (73194201,)
        ).fetchone()
        assert row is not None  # SELECT of a scalar function always returns one row.
        if row[0] is not True:
            raise RuntimeError("another migration runner holds the lock")
        migration(connection)
