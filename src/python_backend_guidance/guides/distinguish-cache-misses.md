+++
schema_version = 1
id = "distinguish-cache-misses"
title = "Keep backend failure distinct from cacheable absence"
description = "Negative-cache only definitive not-found results; preserve temporary backend errors without poisoning the cache."
python = ">=3.12"
runtime = "any"
tags = ["negative-cache", "not-found", "backend-errors", "absence"]
aliases = ["cache failure versus miss", "negative caching errors"]
status = "draft"
example = "examples/distinguish_cache_misses.py"
[[sources]]
url = "https://www.rfc-editor.org/rfc/rfc9111.html"
checked = 2026-11-16
+++

# Keep backend failure distinct from cacheable absence

## When to use

Use when repeated requests for absent records are expensive. Skip negative
caching if new records must become visible immediately and no invalidation exists.

## Rules

1. Distinguish cache miss, authoritative absence and backend failure.
2. Cache only an adapter's explicit definitive-not-found classification.
3. Give negative entries a suitable TTL and invalidation on creation.
4. Keep tenant and authorization scope in negative cache keys too.

## Reference example

```python
"""Application workflow: only a definitive absence is eligible for caching."""

from collections.abc import Callable, Hashable, MutableMapping


class NotFound(Exception):
    pass


def lookup[K: Hashable, V](
    cache: MutableMapping[K, V | None], key: K, load: Callable[[K], V]
) -> V | None:
    if key in cache:
        return cache[key]
    value: V | None
    try:
        value = load(key)
    except NotFound:
        value = None
    cache[key] = value
    return value
```

## Guarantees and assumptions

`None` represents definitive absence in this contract. Other loader exceptions
propagate without changing the cache. The caller supplies a bounded TTL cache;
the test dictionary isolates classification behavior, not expiration.

## Pitfalls

`except Exception: cache[key] = None` turns an outage into durable false absence.
A hidden authorization failure is not necessarily cacheable not-found across
principals. HTTP cacheability rules must still be applied by HTTP caches.

## Verification

Run `uv run pytest tests/test_backend_cache.py --task distinguish-cache-misses`.
Verify a transient error leaves no entry and definitive absence avoids another load.

## Sources

- [HTTP negative responses and cacheability](https://www.rfc-editor.org/rfc/rfc9111.html)
