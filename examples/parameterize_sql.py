"""Persistence adapter: bind values while keeping SQL identifiers fixed."""

from typing import cast

from psycopg import Connection


def find_user(
    connection: Connection[tuple[object, ...]], name: str
) -> list[tuple[int]]:
    rows = connection.execute(
        "SELECT id FROM users WHERE name = %s", (name,)
    ).fetchall()
    return cast(list[tuple[int]], rows)  # SELECT projects only users.id (integer).
