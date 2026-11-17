+++
schema_version = 1
id = "authorize-objects"
title = "Authorize the specific object on every access"
description = "Scope database object reads by the authenticated principal instead of treating a supplied object ID as permission."
python = ">=3.12"
runtime = "sync"
tags = ["authorization", "object-access", "ownership", "idor"]
aliases = ["object level authorization", "broken object authorization"]
status = "draft"
example = "examples/authorize_objects.py"
services = ["PostgreSQL >=16"]
libraries = {psycopg = ">=3.2,<4"}
[[sources]]
url = "https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html"
checked = 2026-11-16
+++

# Authorize the specific object on every access

## When to use

Use for object reads, updates, deletes and downloads. The simple owner model
below should be replaced with the application's existing permission model when
sharing, roles or relationship-based grants are required.

## Rules

1. Derive principal identity from verified authentication.
2. Check permission for the actual object and requested action.
3. Put simple scope predicates in the retrieval/update query when possible.
4. Apply the same policy to alternate paths, exports and background operations.

## Reference example

Requires `private_documents(id PRIMARY KEY, owner text, body text)`.

```python
"""Persistence adapter: fetch within the authenticated principal's scope."""

from typing import cast

from psycopg import Connection


def owned_document(
    connection: Connection[tuple[object, ...]], principal: str, identity: int
) -> str:
    row = connection.execute(
        "SELECT body FROM private_documents WHERE id = %s AND owner = %s",
        (identity, principal),
    ).fetchone()
    if row is None:
        raise LookupError("document not found")
    return cast(str, row[0])  # The declared body column is non-null text.
```

## Guarantees and assumptions

Unauthorized and absent rows share the same error response shape. The trusted
caller supplies principal identity; authentication and transport error mapping
are outside the helper. This query demonstrates read ownership only.

## Pitfalls

A UUID is an identifier, not a permission. Checking that a user is logged in
does not authorize an arbitrary object ID. Fetch-then-check paths risk accidental
use of unauthorized data before the check.

## Verification

Run `uv run pytest tests/integration/test_database_contracts.py --task authorize-objects`.
Check owner success and denial for a different authenticated principal.

## Sources

- [OWASP authorization on every request](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html)
