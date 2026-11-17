+++
schema_version = 1
id = "bound-transactions"
title = "Make transaction ownership and boundaries explicit"
description = "Commit related PostgreSQL changes together and roll back the entire unit when any required step fails."
python = ">=3.12"
runtime = "sync"
tags = ["transactions", "atomicity", "rollback", "commit"]
aliases = ["database transaction rollback", "atomic transfer"]
status = "draft"
example = "examples/bound_transactions.py"
services = ["PostgreSQL >=16"]
libraries = {psycopg = ">=3.2,<4"}
[[sources]]
url = "https://www.psycopg.org/psycopg3/docs/basic/transactions.html"
checked = 2026-11-16
+++

# Make transaction ownership and boundaries explicit

## When to use

Use when several local database statements implement one invariant. A single
atomic statement is simpler if it can express the entire operation.

## Rules

1. Identify the caller that owns commit/rollback; borrowers must not commit it.
2. Keep related updates within one transaction scope.
3. Validate affected-row results, not just absence of SQL errors.
4. Keep remote I/O and long computation outside locks whenever possible.

## Reference example

Requires `accounts(id PRIMARY KEY, balance integer NOT NULL)`.

```python
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
```

## Guarantees and assumptions

Use an idle autocommit Psycopg connection. Both changes commit or neither does.
Amounts are already validated integer minor units; caller authorization is separate.
Concurrent reverse transfers may deadlock and need a transaction-level retry policy.

## Pitfalls

Two autocommitted updates can leave a partial transfer. On a connection already
inside a transaction, `transaction()` may create a savepoint rather than owning
the outer commit. Catching a database error does not repair an aborted transaction.

## Verification

Run `uv run pytest tests/integration/test_database_contracts.py --task bound-transactions`.
Check a successful transfer from a separate connection to establish commit
visibility, and missing-target rollback in real PostgreSQL.

## Sources

- [Psycopg transaction contexts](https://www.psycopg.org/psycopg3/docs/basic/transactions.html)
