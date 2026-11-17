"""Persistence adapter: reject stale edits with an atomic compare-and-swap."""

from typing import cast

from psycopg import Connection


def update_document(
    connection: Connection[tuple[object, ...]], identity: int, version: int, body: str
) -> int:
    row = connection.execute(
        "UPDATE documents SET body = %s, version = version + 1 "
        "WHERE id = %s AND version = %s RETURNING version",
        (body, identity, version),
    ).fetchone()
    if row is None:
        raise ValueError("stale version or missing document")
    return cast(int, row[0])  # RETURNING projects the integer version column.
