+++
schema_version = 1
id = "budget-connection-pools"
title = "Budget connection pools across all processes"
description = "Divide a database connection budget across peak worker processes and bound pool waiters."
python = ">=3.12"
runtime = "sync"
tags = ["connection-pools", "database-capacity", "workers", "pool-sizing"]
aliases = ["database connection budget", "pool size across replicas"]
status = "draft"
example = "examples/budget_connection_pools.py"
services = ["PostgreSQL >=16"]
libraries = {psycopg = ">=3.2,<4", psycopg-pool = ">=3.2,<4"}
[[sources]]
url = "https://www.psycopg.org/psycopg3/docs/advanced/pool.html"
checked = 2026-11-16
+++

# Budget connection pools across all processes

## When to use

Use when each service worker owns a pool. Include other applications, migration
jobs and rollout overlap in the database capacity calculation.

## Rules

1. Reserve connections for operations and other workloads.
2. Divide the remaining budget by the maximum simultaneous worker count.
3. Bound both pool size and waiting requests.
4. Close the pool in the worker lifespan after borrowers drain.

## Reference example

```python
"""Composition root: allocate a pool from the deployment connection budget."""

from psycopg import Connection
from psycopg_pool import ConnectionPool


def pool_capacity(*, database_limit: int, reserved: int, processes: int) -> int:
    """Deployment policy independent of the pool implementation."""
    if processes < 1 or reserved < 0:
        raise ValueError("invalid process count or reserve")
    capacity = (database_limit - reserved) // processes
    if capacity < 1:
        raise ValueError("no connection budget")
    return capacity


def open_pool(
    dsn: str, *, database_limit: int, reserved: int, processes: int
) -> ConnectionPool[Connection[tuple[object, ...]]]:
    capacity = pool_capacity(
        database_limit=database_limit, reserved=reserved, processes=processes
    )
    return ConnectionPool[Connection[tuple[object, ...]]](
        dsn,
        connection_class=Connection[tuple[object, ...]],
        min_size=0,
        max_size=capacity,
        max_waiting=capacity,
        timeout=1,
    )
```

## Guarantees and assumptions

Caller-owned pools cap each process at the calculated allocation. Configuration
is trusted integer input and `processes` includes peak replicas times workers.
Use the returned pool as a context manager.

## Pitfalls

Setting every worker's max_size to the database's limit oversubscribes it.
PgBouncer changes the relationship between client and server connections; assess
that topology separately. Connection count alone does not ensure healthy query load.

## Verification

Run `uv run pytest tests/integration/test_database_contracts.py --task budget-connection-pools`.
Hold all allocated real connections and verify another acquisition times out.

## Sources

- [Psycopg pool lifecycle and limits](https://www.psycopg.org/psycopg3/docs/advanced/pool.html)
