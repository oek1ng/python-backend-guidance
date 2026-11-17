"""Mutation: roll back failed transfers but omit the commit on success."""

from psycopg import Connection


def transfer(
    connection: Connection[tuple[object, ...]], source: int, target: int, amount: int
) -> None:
    if amount <= 0 or source == target:
        raise ValueError("distinct accounts and a positive amount required")
    _ = connection.execute("BEGIN")
    try:
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
    except BaseException:
        connection.rollback()
        raise
