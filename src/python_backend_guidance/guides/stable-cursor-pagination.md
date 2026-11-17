+++
schema_version = 1
id = "stable-cursor-pagination"
title = "Use a stable unique cursor for pagination"
description = "Page PostgreSQL rows with an exclusive composite cursor and a unique tie-breaker instead of ambiguous timestamp-only offsets."
python = ">=3.12"
runtime = "sync"
tags = ["pagination", "keyset", "cursor", "ordering"]
aliases = ["stable cursor pagination", "timestamp tie breaker"]
status = "draft"
example = "examples/stable_cursor_pagination.py"
services = ["PostgreSQL >=16"]
libraries = {psycopg = ">=3.2,<4"}
[[sources]]
url = "https://www.postgresql.org/docs/16/queries-limit.html"
checked = 2026-11-16
+++

# Use a stable unique cursor for pagination

## When to use

Use for sequential navigation through large ordered lists. Offset pagination is
often simpler for small, stable datasets or explicit random page access.

## Rules

1. Order by immutable non-null keys ending in a unique tie-breaker.
2. Carry the complete ordering tuple in an exclusive cursor.
3. Bound page size and index the filter/order pattern.
4. Bind cursor scope to the original filters and authorized tenant.

## Reference example

Requires `events(created_at timestamptz NOT NULL, id bigint PRIMARY KEY)` and
an index on `(created_at,id)`. The caller supplies a validated initial cursor.

```python
"""Persistence adapter: paginate with a unique immutable keyset cursor."""

from datetime import datetime
from typing import cast

from psycopg import Connection

type Cursor = tuple[datetime, int]


def page(
    connection: Connection[tuple[object, ...]], after: Cursor, *, size: int = 50
) -> list[Cursor]:
    if not 1 <= size <= 100:
        raise ValueError("invalid page size")
    rows = connection.execute(
        "SELECT created_at, id FROM events "
        "WHERE (created_at, id) > (%s, %s) ORDER BY created_at, id LIMIT %s",
        (*after, size),
    ).fetchall()
    return cast(list[Cursor], rows)  # timestamptz and bigint in projection order.
```

## Guarantees and assumptions

Rows with equal timestamps are not lost at page boundaries. This is traversal of
the current dataset, not a snapshot across requests. Backdated inserts and edits
to ordering keys can still affect traversal.

## Pitfalls

`WHERE created_at > last_timestamp` skips ties. LIMIT without a unique ORDER BY
is nondeterministic. Opaque or signed cursors do not replace authorization.

## Verification

Run `uv run pytest tests/integration/test_database_contracts.py --task stable-cursor-pagination`.
Place equal timestamps across a page boundary and verify every ID appears once.

## Sources

- [PostgreSQL LIMIT and deterministic ordering](https://www.postgresql.org/docs/16/queries-limit.html)
