"""Persistence adapter: atomically reject an older writer's fencing token."""

from psycopg import Connection


def fenced_write(
    connection: Connection[tuple[object, ...]], identity: int, token: int, value: str
) -> None:
    row = connection.execute(
        "UPDATE resources SET token = %s, value = %s "
        "WHERE id = %s AND token < %s RETURNING id",
        (token, value, identity, token),
    ).fetchone()
    if row is None:
        raise ValueError("stale fencing token or missing resource")
