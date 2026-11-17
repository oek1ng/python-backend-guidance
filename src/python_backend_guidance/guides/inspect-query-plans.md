+++
schema_version = 1
id = "inspect-query-plans"
title = "Inspect query plans before prescribing indexes"
description = "Use representative PostgreSQL plans and statistics to diagnose scans and estimates without accidentally executing expensive statements."
python = ">=3.12"
runtime = "sync"
tags = ["explain", "query-plans", "indexes", "statistics"]
aliases = ["inspect SQL query plan", "database index performance"]
status = "draft"
example = "examples/inspect_query_plans.py"
services = ["PostgreSQL >=16"]
libraries = {psycopg = ">=3.2,<4"}
[[sources]]
url = "https://www.postgresql.org/docs/16/using-explain.html"
checked = 2026-11-16
+++

# Inspect query plans before prescribing indexes

## When to use

Use for a measured slow query or surprising resource usage. Do not add an index
to every column without workload evidence.

## Rules

1. Inspect the real filter, join and ordering shape with representative parameters.
2. Compare row estimates with actual measurements in an appropriate environment.
3. Account for index write cost, storage and selectivity.
4. Distinguish plain EXPLAIN from EXPLAIN ANALYZE, which executes the statement.

## Reference example

Requires `documents(tenant text, id bigint, body text)`. This helper only obtains
an estimated JSON plan; interpreting and benchmarking it is a separate step.

```python
"""Persistence adapter: inspect a read without executing it as a side effect."""

from typing import cast

from psycopg import Connection

type JSONValue = (
    None | bool | int | float | str | list[JSONValue] | dict[str, JSONValue]
)


def explain_lookup(
    connection: Connection[tuple[object, ...]], tenant: str, identity: int
) -> dict[str, JSONValue]:
    row = connection.execute(
        "EXPLAIN (FORMAT JSON) SELECT body FROM documents "
        "WHERE tenant = %s AND id = %s",
        (tenant, identity),
    ).fetchone()
    assert row is not None  # EXPLAIN returns one JSON document.
    # PostgreSQL FORMAT JSON returns an array of plan objects in the first column.
    return cast(list[dict[str, JSONValue]], row[0])[0]
```

## Guarantees and assumptions

No ANALYZE execution of the read is requested. PostgreSQL still plans the query
and can acquire planning locks. The connection remains caller-owned.

## Pitfalls

An exact plan-node assertion on a tiny test table is brittle; a sequential scan
may be optimal. EXPLAIN ANALYZE on writes can cause effects, and rollback does
not undo every external or sequence effect.

## Verification

Run `uv run pytest tests/integration/test_database_contracts.py --task inspect-query-plans`.
Check structured estimated output and bound input. Production performance requires
representative data and before/after measurement.

## Sources

- [PostgreSQL EXPLAIN and ANALYZE](https://www.postgresql.org/docs/16/using-explain.html)
