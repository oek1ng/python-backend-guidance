+++
schema_version = 1
id = "parameterize-sql"
title = "Bind SQL values instead of interpolating them"
description = "Keep untrusted values separate from SQL syntax and use explicit identifier composition when needed."
python = ">=3.12"
runtime = "sync"
tags = ["sql", "parameters", "injection", "queries"]
aliases = ["SQL injection prevention", "parameterized SQL values"]
status = "draft"
example = "examples/parameterize_sql.py"
services = ["PostgreSQL >=16"]
libraries = {psycopg = ">=3.2,<4"}
[[sources]]
url = "https://www.psycopg.org/psycopg3/docs/basic/params.html"
checked = 2026-11-16
+++

# Bind SQL values instead of interpolating them

## When to use

Use for every SQL query with variable values. Follow the chosen driver's parameter
syntax; do not change drivers merely to match this Psycopg example.

## Rules

1. Send values as the execute parameter sequence.
2. Leave parameter placeholders unquoted in the SQL text.
3. Use allowlisted identifiers and the driver's identifier composition API.
4. Bound returned rows separately; parameter binding is not resource control.

## Reference example

Requires `users(id PRIMARY KEY, name text)`.

```python
"""Persistence adapter: bind values while keeping SQL identifiers fixed."""

from typing import cast

from psycopg import Connection


def find_user(
    connection: Connection[tuple[object, ...]], name: str
) -> list[tuple[int]]:
    rows = connection.execute(
        "SELECT id FROM users WHERE name = %s", (name,)
    ).fetchall()
    return cast(list[tuple[int]], rows)  # SELECT projects only users.id (integer).
```

## Guarantees and assumptions

A name containing quotes or SQL operators remains a value. The caller owns the
connection and transaction. The example assumes a bounded users result set.

## Pitfalls

`f"WHERE name = '{name}'"` lets data become SQL syntax. Escaping by replacing
quotes is not an adequate substitute for binding. A value parameter cannot stand
in for a table name, column name, or sort direction.

## Verification

Run `uv run pytest tests/integration/test_database_contracts.py --task parameterize-sql`.
Check an ordinary match and an injection-shaped input against a real table.

## Sources

- [Psycopg query parameters](https://www.psycopg.org/psycopg3/docs/basic/params.html)
