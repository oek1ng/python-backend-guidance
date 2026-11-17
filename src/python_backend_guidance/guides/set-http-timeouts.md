+++
schema_version = 1
id = "set-http-timeouts"
title = "Budget HTTP connection, pool, read and write waits"
description = "Configure distinct HTTP transport timeouts so an exhausted pool or stalled body cannot wait indefinitely."
python = ">=3.12"
runtime = "sync"
tags = ["http", "transport-timeouts", "pool-wait", "read-timeout"]
aliases = ["HTTP connect read write pool timeout", "stalled response body"]
status = "draft"
example = "examples/set_http_timeouts.py"
libraries = {httpx = ">=0.28,<1"}
[[sources]]
url = "https://www.python-httpx.org/advanced/timeouts/"
checked = 2026-11-16
+++

# Budget HTTP connection, pool, read and write waits

## When to use

Use for outbound calls with latency objectives. Start with the client's existing
defaults and adjust using measured workloads, rather than copying these numbers.

## Rules

1. Set connection establishment and pool-acquisition budgets.
2. Bound read and write inactivity separately.
3. Keep attempts and retries inside an operation-wide deadline.
4. Close the caller-owned client after use.

## Reference example

```python
"""Composition root: configure explicit HTTP client phase budgets."""

import httpx


def make_http_client() -> httpx.Client:
    return httpx.Client(
        timeout=httpx.Timeout(connect=1, read=0.1, write=1, pool=0.1),
        limits=httpx.Limits(max_connections=1, max_keepalive_connections=1),
        trust_env=False,
    )
```

## Guarantees and assumptions

HTTPX enforces phase-specific inactivity limits. The one-connection pool and
short read timeout are illustrative values for a small test, not production sizing.
The caller must use `with make_http_client() as client`.

## Pitfalls

`timeout=None` allows indefinite waits. A peer sending occasional bytes can
outlive a read timeout indefinitely; a read timeout is not a total deadline.
Retries multiply elapsed time unless they share a budget.

## Verification

Run `uv run pytest tests/integration/test_http_contracts.py --task set-http-timeouts`.
Exercise both a stalled real response and an exhausted connection pool.

## Sources

- [HTTPX timeout phases](https://www.python-httpx.org/advanced/timeouts/)
