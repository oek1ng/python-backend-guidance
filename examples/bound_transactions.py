"""Persistence adapter: own the whole transfer transaction."""

from psycopg import Connection


def validate_transfer(source: int, target: int, amount: int) -> None:
    """Domain rule: only positive transfers between distinct accounts are valid."""
    if amount <= 0 or source == target:
        raise ValueError("distinct accounts and a positive amount required")


def transfer(
    connection: Connection[tuple[object, ...]], source: int, target: int, amount: int
) -> None:
    validate_transfer(source, target, amount)
    with connection.transaction():
        debit = connection.execute(
            "UPDATE accounts SET balance = balance - %s "
            "WHERE id = %s AND balance >= %s RETURNING id",
            (amount, source, amount),
        ).fetchone()
        if debit is None:
            raise ValueError("missing account or insufficient funds")
        credit = connection.execute(
            "UPDATE accounts SET balance = balance + %s WHERE id = %s RETURNING id",
            (amount, target),
        ).fetchone()
        if credit is None:
            raise LookupError(target)
