+++
schema_version = 1
id = "retry-whole-transactions"
title = "Retry the entire transaction after a serialization conflict"
description = "Restart reads and writes in a fresh PostgreSQL transaction after classified serialization or deadlock failures."
python = ">=3.12"
runtime = "sync"
tags = ["serialization", "deadlocks", "transaction-retry", "postgresql"]
aliases = ["serialization failure retry", "retry deadlocked transaction"]
status = "draft"
example = "examples/retry_whole_transactions.py"
services = ["PostgreSQL >=16"]
libraries = {psycopg = ">=3.2,<4"}
[[sources]]
url = "https://www.postgresql.org/docs/16/transaction-iso.html"
checked = 2026-11-16
+++

# Retry the entire transaction after a serialization conflict

## When to use

Use for a repeatable database-only unit whose isolation policy can produce
serialization failures or deadlocks. Prefer an existing transaction runner that
already provides equivalent classification and limits.

## Rules

1. Retry the complete transaction, including reads that informed its writes.
2. Catch only classified retryable database errors after rollback.
3. Bound attempts and backoff; coordinate with statement and operation deadlines.
4. Keep non-idempotent external side effects outside the replayed callback.

## Reference example

```python
"""Persistence adapter: retry PostgreSQL conflicts around whole transactions."""

import random
import time
from collections.abc import Callable

from psycopg import Connection
from psycopg.errors import DeadlockDetected, SerializationFailure


def run_transaction[T](
    connection: Connection[tuple[object, ...]],
    operation: Callable[[Connection[tuple[object, ...]]], T],
    *,
    attempts: int = 3,
) -> T:
    if attempts < 1:
        raise ValueError("attempts must be positive")
    attempt = 0
    while True:
        try:
            with connection.transaction():
                _ = connection.execute("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE")
                return operation(connection)
        except (SerializationFailure, DeadlockDetected):
            if attempt == attempts - 1:
                raise
            time.sleep(random.uniform(0, min(0.05 * 2**attempt, 0.5)))
            attempt += 1
```

## Guarantees and assumptions

Use an idle autocommit connection so each iteration owns a new transaction.
The example deliberately selects SERIALIZABLE; keep the application's chosen
isolation when adapting it. Attempts are bounded, but each statement needs its own
finite timeout. Commit failures are inside the retry boundary.

## Pitfalls

Retrying only the failed UPDATE reuses stale decisions. Retrying inside an aborted
transaction fails again. Unique violations and connection loss are not universally
safe retry signals; an ambiguous commit may require idempotency.

## Verification

Run `uv run pytest tests/integration/test_database_contracts.py --task retry-whole-transactions`.
A second real connection induces a serialization conflict; verify the retry rereads
the changed balance and permanent constraint errors are attempted once.

## Sources

- [PostgreSQL isolation and transaction retries](https://www.postgresql.org/docs/16/transaction-iso.html)
