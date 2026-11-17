+++
schema_version = 1
id = "deduplicate-mutations"
title = "Persist mutation idempotency with its result"
description = "Deduplicate retried writes using a unique request key, bound input, and an atomic PostgreSQL mutation/result record."
python = ">=3.12"
runtime = "sync"
tags = ["idempotency", "mutations", "request-key", "duplicate-writes"]
aliases = ["idempotent write retry", "durable idempotency key"]
status = "draft"
example = "examples/deduplicate_mutations.py"
services = ["PostgreSQL >=16"]
libraries = {psycopg = ">=3.2,<4"}
[[sources]]
url = "https://www.postgresql.org/docs/16/transaction-iso.html"
checked = 2026-11-16
[[sources]]
url = "https://www.psycopg.org/psycopg3/docs/basic/transactions.html"
checked = 2026-11-16
+++

# Persist mutation idempotency with its result

## When to use

Use when clients can repeat the same local database mutation after an ambiguous
timeout. Use a provider's own idempotency protocol for remote payments or other
external effects; this transaction cannot roll them back.

## Rules

1. Give the request key a database unique constraint and scope it to the principal.
2. Bind the key to all effect-relevant inputs; reject conflicting reuse.
3. Commit the effect and stable response together.
4. Retain keys for the supported retry window; document expiry and replay policy.

## Reference example

Requires `accounts(id PRIMARY KEY, balance NOT NULL)` and
`requests(key PRIMARY KEY, account NOT NULL, amount NOT NULL, result)`.
The trusted caller has already authorized the account and scoped the key.

```python
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
```

## Guarantees and assumptions

Use an idle autocommit connection with READ COMMITTED isolation. A conflicting
insert waits; the following statement can see the committed result. Records
must not be deleted during the retry window. The helper owns the transaction.

## Pitfalls

`if key not in cache: apply()` races and loses state on restart. An HTTP header
alone supplies no persistence. This example covers one positive integer credit,
not currency conversion, arbitrary side effects, or an exactly-once network.

## Verification

Run `uv run pytest tests/integration/test_database_contracts.py --task deduplicate-mutations`
with a disposable PostgreSQL endpoint. Check replayed results and conflicting input.

## Sources

- [PostgreSQL isolation and ON CONFLICT](https://www.postgresql.org/docs/16/transaction-iso.html)
- [Psycopg transaction ownership](https://www.psycopg.org/psycopg3/docs/basic/transactions.html)
