+++
schema_version = 1
id = "enforce-database-constraints"
title = "Enforce shared invariants in the database"
description = "Use unique, foreign-key, not-null and check constraints to arbitrate all database writers."
python = ">=3.12"
runtime = "sync"
tags = ["constraints", "uniqueness", "foreign-keys", "invariants"]
aliases = ["database unique constraint", "check then insert race"]
status = "draft"
example = "examples/enforce_database_constraints.py"
services = ["PostgreSQL >=16"]
libraries = {psycopg = ">=3.2,<4"}
[[sources]]
url = "https://www.postgresql.org/docs/16/ddl-constraints.html"
checked = 2026-11-16
+++

# Enforce shared invariants in the database

## When to use

Use for invariants that must survive parallel requests, scripts and background
workers. Application validation still provides earlier, clearer feedback.

## Rules

1. Express uniqueness and references with database constraints.
2. Combine CHECK with NOT NULL when null is not permitted.
3. Handle specific constraint violations at the domain boundary.
4. Plan validation and locks when adding constraints to populated tables.

## Reference example

The referenced `accounts(id PRIMARY KEY)` table must already exist.

```python
"""Persistence adapter: install constraints that arbitrate concurrent writers."""

from psycopg import Connection


def create_reservations(connection: Connection[tuple[object, ...]]) -> None:
    _ = connection.execute(
        "CREATE TABLE reservations ("
        "id bigint PRIMARY KEY, "
        "account bigint NOT NULL REFERENCES accounts(id), "
        "reference text NOT NULL UNIQUE, "
        "quantity integer NOT NULL CHECK (quantity > 0))"
    )
```

## Guarantees and assumptions

PostgreSQL rejects duplicates, missing references and nonpositive quantities.
The migration caller owns the connection and deployment coordination. The schema
is illustrative; choose tenant-scoped uniqueness when reference identity is local.

## Pitfalls

`SELECT exists(...)` followed by INSERT races. A CHECK expression evaluating to
NULL does not reject the row. Constraints enforce data integrity, not who may
read or modify a row.

## Verification

Run `uv run pytest tests/integration/test_database_contracts.py --task enforce-database-constraints`.
Insert invalid rows directly to verify enforcement independently of application validation.

## Sources

- [PostgreSQL constraints](https://www.postgresql.org/docs/16/ddl-constraints.html)
