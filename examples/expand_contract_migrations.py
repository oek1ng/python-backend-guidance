"""Persistence adapter: expand the schema before a later contract step."""

from typing import cast

from psycopg import Connection


def expand_profile(connection: Connection[tuple[object, ...]]) -> None:
    with connection.transaction():
        _ = connection.execute("SET LOCAL lock_timeout = '1s'")
        _ = connection.execute("ALTER TABLE profiles ADD COLUMN display_name text")


def read_profile(connection: Connection[tuple[object, ...]], identity: int) -> str:
    row = connection.execute(
        "SELECT COALESCE(display_name, name) FROM profiles WHERE id = %s",
        (identity,),
    ).fetchone()
    assert row is not None  # The caller supplies an existing profile identity.
    return cast(str, row[0])  # COALESCE falls back to the non-null text name.
