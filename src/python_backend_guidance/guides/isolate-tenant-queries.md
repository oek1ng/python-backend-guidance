+++
schema_version = 1
id = "isolate-tenant-queries"
title = "Carry tenant scope into every data access"
description = "Include authenticated tenant identity in database lookups so local object IDs cannot cross tenant boundaries."
python = ">=3.12"
runtime = "sync"
tags = ["tenant-isolation", "multitenancy", "scoped-queries", "data-access"]
aliases = ["tenant data isolation", "cross tenant query"]
status = "draft"
example = "examples/isolate_tenant_queries.py"
services = ["PostgreSQL >=16"]
libraries = {psycopg = ">=3.2,<4"}
[[sources]]
url = "https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html"
checked = 2026-11-16
+++

# Carry tenant scope into every data access

## When to use

Use in a shared-table multi-tenant application. Preserve the project's chosen
isolation architecture; separate databases or row-level security may already
provide additional boundaries.

## Rules

1. Resolve the authorized tenant from trusted authentication/membership state.
2. Scope reads, writes, joins and uniqueness to that tenant where appropriate.
3. Include tenant scope in caches, jobs and exported storage keys.
4. Test with identical local object IDs in different tenants.

## Reference example

Requires `tenant_documents(tenant text, id bigint, body text, PRIMARY KEY(tenant,id))`.

```python
"""Persistence adapter: scope reads by the authenticated tenant."""

from typing import cast

from psycopg import Connection


def tenant_document(
    connection: Connection[tuple[object, ...]], tenant: str, identity: int
) -> str:
    row = connection.execute(
        "SELECT body FROM tenant_documents WHERE tenant = %s AND id = %s",
        (tenant, identity),
    ).fetchone()
    if row is None:
        raise LookupError("document not found")
    return cast(str, row[0])  # The declared body column is non-null text.
```

## Guarantees and assumptions

The query selects only the supplied authorized tenant. It does not establish
membership or permission within that tenant. Callers and every other access path
must honor the same boundary.

## Pitfalls

Trusting a body-supplied tenant ID bypasses isolation. Adding a tenant filter to
the primary query but omitting it from a join or cache key still leaks data.
Session-scoped database tenant settings need careful pool reset.

## Verification

Run `uv run pytest tests/integration/test_database_contracts.py --task isolate-tenant-queries`.
Use colliding local IDs and verify a missing tenant cannot access another's row.

## Sources

- [OWASP access-control scope](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html)
