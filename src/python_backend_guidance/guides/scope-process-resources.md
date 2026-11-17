+++
schema_version = 1
id = "scope-process-resources"
title = "Create runtime-bound resources inside worker lifespans"
description = "Initialize pooled async clients after worker and event-loop creation, then close them before that loop shuts down."
python = ">=3.12"
runtime = "asyncio"
tags = ["worker-lifespan", "processes", "event-loop", "client-ownership"]
aliases = ["client created before fork", "event loop bound client"]
status = "draft"
example = "examples/scope_process_resources.py"
libraries = {httpx = ">=0.28,<1"}
[[sources]]
url = "https://www.python-httpx.org/async/"
checked = 2026-11-16
[[sources]]
url = "https://www.psycopg.org/psycopg3/docs/advanced/pool.html"
checked = 2026-11-16
+++

# Create runtime-bound resources inside worker lifespans

## When to use

Use with multi-worker or pre-fork servers and event-loop-bound clients. Pure
immutable configuration can still be loaded before worker creation.

## Rules

1. Create live connections and pools in the worker's startup/lifespan hook.
2. Reuse them within that worker rather than constructing them per request.
3. Drain users before closing resources and stopping the event loop.
4. Keep imports free of connection-opening and thread-starting side effects.

## Reference example

```python
"""Composition root: initialize clients inside the worker's lifespan."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import httpx


@asynccontextmanager
async def worker_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    async with httpx.AsyncClient(timeout=5, trust_env=False) as client:
        yield client
```

## Guarantees and assumptions

Call this scope once per worker after its runtime starts and pass the borrowed
client to handlers. Each scope owns a distinct client. The example does not
configure a particular server or process creation model.

## Pitfalls

Live module-global pools may be copied across fork or reused across event loops.
Creating an AsyncClient inside a hot request loop defeats connection reuse.
An imported factory is safe; an imported open resource may not be.

## Verification

Run `uv run pytest tests/integration/test_http_contracts.py --task scope-process-resources`.
Verify isolated lifespans and closure after real HTTP use. Server-specific
fork/startup ordering requires an integration check in the adopting application.

## Sources

- [HTTPX async client lifecycle](https://www.python-httpx.org/async/)
- [Psycopg delayed pool opening](https://www.psycopg.org/psycopg3/docs/advanced/pool.html)
