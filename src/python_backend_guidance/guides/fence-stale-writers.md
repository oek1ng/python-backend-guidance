+++
schema_version = 1
id = "fence-stale-writers"
title = "Fence stale lease holders at the storage boundary"
description = "Reject writes from expired lock owners using monotonic fencing tokens checked atomically by PostgreSQL."
python = ">=3.12"
runtime = "sync"
tags = ["fencing", "leases", "stale-writer", "distributed-locks"]
aliases = ["expired lock owner write", "fencing token"]
status = "draft"
example = "examples/fence_stale_writers.py"
services = ["PostgreSQL >=16"]
libraries = {psycopg = ">=3.2,<4"}
[[sources]]
url = "https://martin.kleppmann.com/2016/02/08/how-to-do-distributed-locking.html"
checked = 2026-11-16
[[sources]]
url = "https://www.postgresql.org/docs/16/transaction-iso.html"
checked = 2026-11-16
+++

# Fence stale lease holders at the storage boundary

## When to use

Use when an expiring distributed lease protects correctness-sensitive writes.
A local transaction or row lock is simpler when all work is in one database.

## Rules

1. Obtain strictly increasing tokens from the coordination system.
2. Carry the token with the write to the protected resource.
3. Enforce the ordering atomically in the storage system.
4. Ensure every writer uses the protocol; client-side expiry checks are insufficient.

## Reference example

Requires `resources(id PRIMARY KEY, token bigint NOT NULL, value text)`.
Tokens are already authenticated, monotonically allocated and initially above zero.

```python
"""Persistence adapter: atomically reject an older writer's fencing token."""

from psycopg import Connection


def fenced_write(
    connection: Connection[tuple[object, ...]], identity: int, token: int, value: str
) -> None:
    row = connection.execute(
        "UPDATE resources SET token = %s, value = %s "
        "WHERE id = %s AND token < %s RETURNING id",
        (token, value, identity, token),
    ).fetchone()
    if row is None:
        raise ValueError("stale fencing token or missing resource")
```

## Guarantees and assumptions

A newer accepted token prevents a later write with an older or equal token.
This single-write-per-token example rejects duplicate tokens; retries requiring
the original response need an additional idempotency protocol.

## Pitfalls

Checking lease validity and then writing leaves a pause/network-delay window.
A random UUID lock value is not an ordered fencing token. Tokens alone do not
prove lease freshness before a newer token reaches storage, nor generate leases.

## Verification

Run `uv run pytest tests/integration/test_database_contracts.py --task fence-stale-writers`.
Write with the newer owner, then verify the older owner cannot replace its value.

## Sources

- [Kleppmann: fencing and distributed locks](https://martin.kleppmann.com/2016/02/08/how-to-do-distributed-locking.html)
- [PostgreSQL atomic update predicates](https://www.postgresql.org/docs/16/transaction-iso.html)
