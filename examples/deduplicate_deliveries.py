"""Persistence adapter: commit an inbox record and local effect together."""

from psycopg import Connection


def apply_message(
    connection: Connection[tuple[object, ...]],
    message_id: str,
    account: int,
    amount: int,
) -> bool:
    with connection.transaction():
        inserted = connection.execute(
            "INSERT INTO inbox (id) VALUES (%s) ON CONFLICT DO NOTHING RETURNING id",
            (message_id,),
        ).fetchone()
        if inserted is None:
            return False
        if (
            connection.execute(
                "UPDATE accounts SET balance = balance + %s WHERE id = %s RETURNING id",
                (amount, account),
            ).fetchone()
            is None
        ):
            raise LookupError(account)
        return True
