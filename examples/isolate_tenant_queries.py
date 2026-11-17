"""Persistence adapter: scope reads by the authenticated tenant."""

from typing import cast

from psycopg import Connection


def tenant_document(
    connection: Connection[tuple[object, ...]], tenant: str, identity: int
) -> str:
    row = connection.execute(
        "SELECT body FROM tenant_documents WHERE tenant = %s AND id = %s",
        (tenant, identity),
    ).fetchone()
    if row is None:
        raise LookupError("document not found")
    return cast(str, row[0])  # The declared body column is non-null text.
