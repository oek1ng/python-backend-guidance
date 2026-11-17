+++
schema_version = 1
id = "serialize-migration-runners"
title = "Coordinate concurrent migration runners"
description = "Use a shared PostgreSQL advisory transaction lock so competing instances cannot execute the same migration concurrently."
python = ">=3.12"
runtime = "sync"
tags = ["migrations", "advisory-lock", "coordination", "deployment"]
aliases = ["concurrent migration runners", "serialize schema migrations"]
status = "draft"
example = "examples/serialize_migration_runners.py"
services = ["PostgreSQL >=16"]
libraries = {psycopg = ">=3.2,<4"}
[[sources]]
url = "https://www.postgresql.org/docs/16/explicit-locking.html"
checked = 2026-11-16
+++

# Coordinate concurrent migration runners

## When to use

Use if deployment architecture permits overlapping migration runners. A single
coordinated migration job is often simpler; keep the existing migration tool's
coordination mechanism when it already works.

## Rules

1. Use one shared coordination identity for every runner of the same schema.
2. Check and record migration versions while holding coordination.
3. Release locks on success, failure and disconnect.
4. Match lock lifetime to transactional versus nontransactional DDL.

## Reference example

```python
"""Persistence adapter: serialize migrations with a PostgreSQL advisory lock."""

from collections.abc import Callable

from psycopg import Connection


def run_migration(
    connection: Connection[tuple[object, ...]],
    migration: Callable[[Connection[tuple[object, ...]]], None],
) -> None:
    with connection.transaction():
        row = connection.execute(
            "SELECT pg_try_advisory_xact_lock(%s)", (73194201,)
        ).fetchone()
        assert row is not None  # SELECT of a scalar function always returns one row.
        if row[0] is not True:
            raise RuntimeError("another migration runner holds the lock")
        migration(connection)
```

## Guarantees and assumptions

Use an idle autocommit connection. Cooperating runners in this database use the
same application-reserved lock ID. The callback owns version-ledger checks and
executes only DDL allowed in a transaction.

## Pitfalls

A process-local mutex does not coordinate replicas. Advisory locks are cooperative,
not protection from arbitrary administrative SQL. CREATE INDEX CONCURRENTLY cannot
run in this transaction scope; its coordination needs a separate lifecycle.

## Verification

Run `uv run pytest tests/integration/test_database_contracts.py --task serialize-migration-runners`.
Hold the lock on one real connection and reject another; verify rollback and
lock release after a failed migration.

## Sources

- [PostgreSQL advisory lock lifetimes](https://www.postgresql.org/docs/16/explicit-locking.html)
