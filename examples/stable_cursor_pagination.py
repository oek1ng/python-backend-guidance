"""Persistence adapter: paginate with a unique immutable keyset cursor."""

from datetime import datetime
from typing import cast

from psycopg import Connection

type Cursor = tuple[datetime, int]


def page(
    connection: Connection[tuple[object, ...]], after: Cursor, *, size: int = 50
) -> list[Cursor]:
    if not 1 <= size <= 100:
        raise ValueError("invalid page size")
    rows = connection.execute(
        "SELECT created_at, id FROM events "
        "WHERE (created_at, id) > (%s, %s) ORDER BY created_at, id LIMIT %s",
        (*after, size),
    ).fetchall()
    return cast(list[Cursor], rows)  # timestamptz and bigint in projection order.
