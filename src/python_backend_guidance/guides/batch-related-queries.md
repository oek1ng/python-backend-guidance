+++
schema_version = 1
id = "batch-related-queries"
title = "Batch related reads instead of issuing N+1 queries"
description = "Fetch children for a bounded set of parent IDs in one query while preserving empty parents and deterministic grouping."
python = ">=3.12"
runtime = "sync"
tags = ["batching", "n-plus-one", "related-rows", "query-count"]
aliases = ["N+1 database queries", "batch related records"]
status = "draft"
example = "examples/batch_related_queries.py"
services = ["PostgreSQL >=16"]
libraries = {psycopg = ">=3.2,<4"}
[[sources]]
url = "https://www.psycopg.org/psycopg3/docs/basic/params.html"
checked = 2026-11-16
[[sources]]
url = "https://www.postgresql.org/docs/16/functions-comparisons.html"
checked = 2026-11-16
+++

# Batch related reads instead of issuing N+1 queries

## When to use

Use when a list view loads children separately for each parent. An ORM's explicit
prefetch/eager-loading feature may already provide this behavior.

## Rules

1. Fetch related data once per bounded batch.
2. Deduplicate parent IDs and bind them as values.
3. Preserve parents without children in the returned shape.
4. Measure query count and returned volume; a single huge query can still be costly.

## Reference example

Requires `items(order_id bigint, sku text)`; index `order_id` for the actual workload.

```python
"""Persistence adapter: fetch related rows in one bounded batch."""

from collections.abc import Iterable
from typing import LiteralString, Protocol, cast


class ItemQuery(Protocol):
    def execute(
        self, query: LiteralString, params: tuple[list[int]], /
    ) -> Iterable[tuple[object, ...]]: ...


def bounded_ids(order_ids: Iterable[int]) -> list[int]:
    """Application policy: deduplicate without exceeding the batch budget."""
    ids = list(dict.fromkeys(order_ids))
    if len(ids) > 500:
        raise ValueError("batch too large")
    return ids


def load_items(connection: ItemQuery, order_ids: Iterable[int]) -> dict[int, list[str]]:
    ids = bounded_ids(order_ids)
    result: dict[int, list[str]] = {identity: [] for identity in ids}
    if len(ids) != 0:
        rows = connection.execute(
            "SELECT order_id, sku FROM items WHERE order_id = ANY(%s) "
            "ORDER BY order_id, sku",
            (ids,),
        )
        # The query projects (bigint order_id, text sku) from the declared schema.
        for identity, sku in cast(Iterable[tuple[int, str]], rows):
            result[identity].append(sku)
    return result
```

## Guarantees and assumptions

An empty batch performs no query; an accepted nonempty batch performs one. Input
is already finite and each parent has a bounded child count. Very large inputs
need streaming batches before calling this helper.

## Pitfalls

`for parent: SELECT children WHERE parent_id=...` scales round trips with list
size. Unbounded eager joins can multiply rows and memory. Include authorization
scope in the parent selection and child query for shared databases.

## Verification

Run `uv run pytest tests/integration/test_database_contracts.py --task batch-related-queries`.
Check actual query count, empty parents, sorted results and oversized batches.

## Sources

- [Psycopg bound values](https://www.psycopg.org/psycopg3/docs/basic/params.html)
- [PostgreSQL ANY comparisons](https://www.postgresql.org/docs/16/functions-comparisons.html)
