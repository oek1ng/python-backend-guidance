+++
schema_version = 1
id = "expand-contract-migrations"
title = "Expand schemas before contracting old behavior"
description = "Keep old and new application versions compatible during a PostgreSQL rolling migration."
python = ">=3.12"
runtime = "sync"
tags = ["migrations", "schema-evolution", "rolling-deploy", "compatibility"]
aliases = ["expand contract migration", "backward compatible schema"]
status = "draft"
example = "examples/expand_contract_migrations.py"
services = ["PostgreSQL >=16"]
libraries = {psycopg = ">=3.2,<4"}
[[sources]]
url = "https://www.postgresql.org/docs/16/ddl-alter.html"
checked = 2026-11-16
+++

# Expand schemas before contracting old behavior

## When to use

Use when deployments overlap versions or rollback must remain possible. A brief
coordinated maintenance window can be simpler for small applications.

## Rules

1. Add compatible schema first; keep old readers and writers working.
2. Deploy fallback/dual-write behavior, then backfill in bounded resumable batches.
3. Verify completeness and retire old versions before enforcing or dropping fields.
4. Budget DDL lock waits and rehearse on realistic table sizes.

## Reference example

Starts with `profiles(id PRIMARY KEY, name text NOT NULL)`.
This demonstrates expansion and read fallback, not a complete migration framework.

```python
"""Persistence adapter: expand the schema before a later contract step."""

from typing import cast

from psycopg import Connection


def expand_profile(connection: Connection[tuple[object, ...]]) -> None:
    with connection.transaction():
        _ = connection.execute("SET LOCAL lock_timeout = '1s'")
        _ = connection.execute("ALTER TABLE profiles ADD COLUMN display_name text")


def read_profile(connection: Connection[tuple[object, ...]], identity: int) -> str:
    row = connection.execute(
        "SELECT COALESCE(display_name, name) FROM profiles WHERE id = %s",
        (identity,),
    ).fetchone()
    assert row is not None  # The caller supplies an existing profile identity.
    return cast(str, row[0])  # COALESCE falls back to the non-null text name.
```

## Guarantees and assumptions

Old inserts remain valid because the new field is nullable. The new reader
falls back to the old field. Use an idle autocommit connection and a coordinated
migration runner with its own version ledger.

## Pitfalls

Adding a required column without a compatible default breaks old writers.
Fallback alone does not reconcile later old-version edits after backfill; choose
and test a dual-write or reconciliation policy before contracting.

## Verification

Run `uv run pytest tests/integration/test_database_contracts.py --task expand-contract-migrations`.
Execute old inserts after expansion and read both old and backfilled rows.

## Sources

- [PostgreSQL schema alterations](https://www.postgresql.org/docs/16/ddl-alter.html)
