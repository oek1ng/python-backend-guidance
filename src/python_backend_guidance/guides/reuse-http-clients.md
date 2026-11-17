+++
schema_version = 1
id = "reuse-http-clients"
title = "Reuse and close HTTP clients"
description = "Own a pooled HTTP client across related calls and close it at the service or batch lifespan boundary."
python = ">=3.12"
runtime = "sync"
tags = ["http", "client-lifecycle", "connection-reuse", "keepalive"]
aliases = ["HTTP connection pool lifecycle", "reuse HTTP connections"]
status = "draft"
example = "examples/reuse_http_clients.py"
libraries = {httpx = ">=0.28,<1"}
[[sources]]
url = "https://www.python-httpx.org/advanced/clients/"
checked = 2026-11-16
+++

# Reuse and close HTTP clients

## When to use

Use for repeated outbound calls. A one-off script can use a one-off request;
a long-lived service should normally own its client for its worker lifespan.

## Rules

1. Create the client at an explicit ownership boundary.
2. Reuse its connection pool across calls to the same origin.
3. Close responses and the client even on errors.
4. Configure timeouts, pool limits, and environment proxy policy deliberately.

## Reference example

```python
"""Composition root: own one HTTP client for a batch of requests."""

from collections.abc import Callable, Iterable

import httpx


class TextFetcher:
    def __init__(self, client: httpx.Client) -> None:
        self.client = client

    def __call__(self, url: str) -> str:
        response = self.client.get(url)
        _ = response.raise_for_status()
        return response.text


def fetch_with_reader(
    fetch_text: Callable[[str], str], urls: Iterable[str]
) -> list[str]:
    """Application workflow: read borrowed URLs through an injected port."""
    return [fetch_text(url) for url in urls]


def fetch_batch(urls: Iterable[str]) -> list[str]:
    with httpx.Client(timeout=5, trust_env=False) as client:
        return fetch_with_reader(TextFetcher(client), urls)
```

## Guarantees and assumptions

The client closes on exit and can reuse keep-alive connections when the server
permits. Inputs and responses are bounded by the caller. `trust_env=False` is an
explicit example choice; deployments relying on an outbound proxy must configure it.

## Pitfalls

`httpx.get()` inside a loop creates separate client lifetimes. A module-global
client created before fork can transfer invalid live state into workers.
Async handlers should use a lifespan-owned AsyncClient.

## Verification

Run `uv run pytest tests/integration/test_http_contracts.py --task reuse-http-clients`.
A real HTTP/1.1 server observes the same TCP peer for repeated requests.

## Sources

- [HTTPX clients and connection pooling](https://www.python-httpx.org/advanced/clients/)
