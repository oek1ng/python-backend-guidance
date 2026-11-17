"""Persistence adapter: commit a business change and outbox event together."""

import json

from psycopg import Connection


def event_payload(account: int, amount: int) -> str:
    """Application event shape independent of transaction management."""
    return json.dumps({"account": account, "amount": amount})


def change_and_enqueue(
    connection: Connection[tuple[object, ...]], account: int, amount: int, event_id: str
) -> None:
    with connection.transaction():
        row = connection.execute(
            "UPDATE accounts SET balance = balance + %s WHERE id = %s RETURNING id",
            (amount, account),
        ).fetchone()
        if row is None:
            raise LookupError(account)
        _ = connection.execute(
            "INSERT INTO outbox (id, payload) VALUES (%s, %s)",
            (event_id, event_payload(account, amount)),
        )
