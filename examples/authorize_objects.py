"""Persistence adapter: fetch within the authenticated principal's scope."""

from typing import cast

from psycopg import Connection


def owned_document(
    connection: Connection[tuple[object, ...]], principal: str, identity: int
) -> str:
    row = connection.execute(
        "SELECT body FROM private_documents WHERE id = %s AND owner = %s",
        (identity, principal),
    ).fetchone()
    if row is None:
        raise LookupError("document not found")
    return cast(str, row[0])  # The declared body column is non-null text.
