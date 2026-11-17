+++
schema_version = 1
id = "prevent-lost-updates"
title = "Reject stale concurrent updates"
description = "Use an atomic version predicate so a stale PostgreSQL writer cannot overwrite a newer edit."
python = ">=3.12"
runtime = "sync"
tags = ["lost-updates", "optimistic-locking", "version", "compare-and-swap"]
aliases = ["PostgreSQL lost updates", "stale concurrent edit"]
status = "draft"
example = "examples/prevent_lost_updates.py"
services = ["PostgreSQL >=16"]
libraries = {psycopg = ">=3.2,<4"}
[[sources]]
url = "https://www.postgresql.org/docs/16/transaction-iso.html"
checked = 2026-11-16
+++

# Reject stale concurrent updates

## When to use

Use for read-edit-save workflows where users must learn that their version is
stale. For counters, an atomic SQL increment is simpler; row locks suit some
multi-statement invariants.

## Rules

1. Carry the version read by the editor into the update.
2. Match identity and expected version in one atomic UPDATE.
3. Increment the version in that same statement.
4. Report conflict; do not silently overwrite or blindly retry stale input.

## Reference example

Requires `documents(id PRIMARY KEY, version integer NOT NULL, body text)`.

```python
"""Persistence adapter: reject stale edits with an atomic compare-and-swap."""

from typing import cast

from psycopg import Connection


def update_document(
    connection: Connection[tuple[object, ...]], identity: int, version: int, body: str
) -> int:
    row = connection.execute(
        "UPDATE documents SET body = %s, version = version + 1 "
        "WHERE id = %s AND version = %s RETURNING version",
        (body, identity, version),
    ).fetchone()
    if row is None:
        raise ValueError("stale version or missing document")
    return cast(int, row[0])  # RETURNING projects the integer version column.
```

## Guarantees and assumptions

All writers must honor the version discipline. PostgreSQL rechecks the predicate
after a concurrent update under READ COMMITTED. Authorization must additionally
scope this query where needed.

## Pitfalls

Checking the version in a separate SELECT still races. An outer transaction
alone does not prevent lost updates at every isolation level. Immutable cursor
IDs and edit versions solve different problems.

## Verification

Run `uv run pytest tests/integration/test_database_contracts.py --task prevent-lost-updates`.
Use separate connections carrying the same version; only the first edit may succeed.

## Sources

- [PostgreSQL concurrent update behavior](https://www.postgresql.org/docs/16/transaction-iso.html)
