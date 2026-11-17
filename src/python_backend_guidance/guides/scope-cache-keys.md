+++
schema_version = 1
id = "scope-cache-keys"
title = "Include authorization scope in cache identity"
description = "Build collision-free cache keys from tenant, subject and representation parameters to avoid cross-scope data reuse."
python = ">=3.12"
runtime = "any"
tags = ["cache-keys", "tenant", "representation", "collisions"]
aliases = ["tenant scoped cache key", "cache key collision"]
status = "draft"
example = "examples/scope_cache_keys.py"
[[sources]]
url = "https://www.rfc-editor.org/rfc/rfc9111.html"
checked = 2026-11-16
[[sources]]
url = "https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html"
checked = 2026-11-16
+++

# Include authorization scope in cache identity

## When to use

Use when cached results differ by tenant, user, locale, permissions or query
options. Shared public data can use a simpler identity.

## Rules

1. Include every dimension that changes the result or its visibility.
2. Encode boundaries unambiguously rather than concatenating delimiters.
3. Version the key namespace when representation semantics change.
4. Authorize access independently of whether the cache hit.

## Reference example

```python
"""Domain policy: a cache identity includes all authorization dimensions."""

import json


def cache_key(tenant: str, subject: str, locale: str) -> str:
    return json.dumps(
        ["profile-v1", tenant, subject, locale],
        ensure_ascii=True,
        separators=(",", ":"),
    )
```

## Guarantees and assumptions

Inputs are bounded strings from authenticated scope and normalized request
parameters. JSON array encoding separates their boundaries. This application
cache design borrows the representation-identity principle from HTTP caching.

## Pitfalls

`f"{tenant}:{subject}"` can collide when components contain delimiters. A global
`profile:{id}` key may cross tenants. Hashing a key hides neither sensitive values
in the cached payload nor missing authorization dimensions.

## Verification

Run `uv run pytest tests/test_backend_cache.py --task scope-cache-keys`.
Check separator-shaped inputs, different tenants/locales and stable encoding.

## Sources

- [HTTP cache identity and variants](https://www.rfc-editor.org/rfc/rfc9111.html)
- [OWASP authorization boundaries](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html)
