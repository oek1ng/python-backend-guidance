+++
schema_version = 1
id = "restrict-outbound-destinations"
title = "Restrict outbound destinations to a trusted policy"
description = "Use configured destination IDs instead of arbitrary user URLs when an API needs only a known set of outbound services."
python = ">=3.12"
runtime = "sync"
tags = ["ssrf", "egress", "destinations", "allowlist"]
aliases = ["SSRF prevention", "restrict outbound URL"]
status = "draft"
example = "examples/restrict_outbound_destinations.py"
libraries = {httpx = ">=0.28,<1"}
[[sources]]
url = "https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html"
checked = 2026-11-16
+++

# Restrict outbound destinations to a trusted policy

## When to use

Use when business needs require calls only to a finite set of operator-controlled
services. Arbitrary external webhooks/downloads require a stronger egress design.

## Rules

1. Accept a destination identifier rather than a caller-controlled full URL.
2. Keep the destination mapping in trusted validated configuration.
3. Disable redirects and constrain network egress independently.
4. Bound connection time, response size and allowed protocols.

## Reference example

```python
"""HTTP adapter: fetch only operator-configured destinations."""

from collections.abc import Callable, Mapping

import httpx


class ResponseFetcher:
    def __init__(self, client: httpx.Client) -> None:
        self.client = client

    def __call__(self, url: str) -> bytes:
        response = self.client.get(url)
        _ = response.raise_for_status()
        return response.content


def fetch_configured(
    destination: str,
    destinations: Mapping[str, str],
    fetch: Callable[[str], bytes],
) -> bytes:
    """Application policy: callers choose IDs, not arbitrary URLs."""
    # Mapping is trusted startup configuration, not request data.
    return fetch(destinations[destination])


def fetch_destination(destination: str, destinations: Mapping[str, str]) -> bytes:
    with httpx.Client(timeout=5, follow_redirects=False, trust_env=False) as client:
        return fetch_configured(destination, destinations, ResponseFetcher(client))
```

## Guarantees and assumptions

An unknown identifier fails before any request. Configuration contains reviewed
HTTPS endpoints with controlled DNS. The example fetches a small bounded-by-contract
response; use streaming limits for untrusted sizes.

## Pitfalls

`url.startswith("https://trusted.example")` accepts lookalike authorities.
Resolving and checking an address before a separate client lookup can race DNS.
This finite-destination recipe does not secure arbitrary URLs or compromised DNS;
enforce destination networks at the actual connection boundary.

## Verification

Run `uv run pytest tests/integration/test_http_contracts.py --task restrict-outbound-destinations`.
Check that arbitrary URLs produce no request and configured destinations work.

## Sources

- [OWASP SSRF application and network controls](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html)
