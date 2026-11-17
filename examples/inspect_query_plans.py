"""Persistence adapter: inspect a read without executing it as a side effect."""

from typing import cast

from psycopg import Connection

type JSONValue = (
    None | bool | int | float | str | list[JSONValue] | dict[str, JSONValue]
)


def explain_lookup(
    connection: Connection[tuple[object, ...]], tenant: str, identity: int
) -> dict[str, JSONValue]:
    row = connection.execute(
        "EXPLAIN (FORMAT JSON) SELECT body FROM documents "
        "WHERE tenant = %s AND id = %s",
        (tenant, identity),
    ).fetchone()
    assert row is not None  # EXPLAIN returns one JSON document.
    # PostgreSQL FORMAT JSON returns an array of plan objects in the first column.
    return cast(list[dict[str, JSONValue]], row[0])[0]
