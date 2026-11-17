"""Persistence adapter: commit an idempotency result and mutation together."""

from typing import cast

from psycopg import Connection


def require_positive_amount(amount: int) -> None:
    """Domain rule: a credit must increase the balance."""
    if amount <= 0:
        raise ValueError("amount must be positive")


def credit_once(
    connection: Connection[tuple[object, ...]], key: str, account: int, amount: int
) -> int:
    require_positive_amount(amount)
    with connection.transaction():
        row = connection.execute(
            "INSERT INTO requests (key, account, amount) VALUES (%s, %s, %s) "
            "ON CONFLICT (key) DO NOTHING RETURNING key",
            (key, account, amount),
        ).fetchone()
        if row is None:
            previous = connection.execute(
                "SELECT account, amount, result FROM requests WHERE key = %s",
                (key,),
            ).fetchone()
            assert previous is not None  # The conflicting committed request exists.
            if previous[:2] != (account, amount):
                raise ValueError("idempotency key reused with different input")
            # The declared requests.result column stores the committed integer balance.
            return cast(int, previous[2])
        result = connection.execute(
            "UPDATE accounts SET balance = balance + %s WHERE id = %s "
            "RETURNING balance",
            (amount, account),
        ).fetchone()
        if result is None:
            raise LookupError(account)
        _ = connection.execute(
            "UPDATE requests SET result = %s WHERE key = %s", (result[0], key)
        )
        return cast(int, result[0])  # accounts.balance is an integer column.
