+++
schema_version = 1
id = "control-redirects"
title = "Make redirect policy explicit for credentialed requests"
description = "Refuse automatic redirects on sensitive outbound requests before credentials or data reach a new destination."
python = ">=3.12"
runtime = "sync"
tags = ["redirects", "credentials", "authorization-header", "http"]
aliases = ["redirect credential leak", "disable automatic redirects"]
status = "draft"
example = "examples/control_redirects.py"
libraries = {httpx = ">=0.28,<1"}
[[sources]]
url = "https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html"
checked = 2026-11-16
+++

# Make redirect policy explicit for credentialed requests

## When to use

Use for sensitive API calls with an expected endpoint. Public web navigation has
different requirements and may need a bounded, explicitly validated redirect loop.

## Rules

1. Disable implicit redirects for a fixed service endpoint.
2. Treat each redirect target as a fresh authorization and egress decision.
3. Do not forward secrets based only on an apparently related hostname.
4. If redirects are required, bound hops and reject HTTPS downgrade.

## Reference example

```python
"""HTTP adapter: refuse redirects on a credentialed request."""

import httpx


def fetch_private(client: httpx.Client, url: str, token: str) -> bytes:
    response = client.get(
        url, headers={"Authorization": f"Bearer {token}"}, follow_redirects=False
    )
    if response.is_redirect:
        raise ValueError("redirect requires a new destination policy decision")
    _ = response.raise_for_status()
    return response.content
```

## Guarantees and assumptions

No redirected request is sent. The initial URL must already be authorized, and
the caller owns the HTTPX client and bounds response size. Sensitive tokens are
never included in the error text.

## Pitfalls

Checking the initial URL and then enabling `follow_redirects=True` can bypass
that check. Library-specific credential stripping is useful but is not a complete
SSRF or application data disclosure policy.

## Verification

Run `uv run pytest tests/integration/test_http_contracts.py --task control-redirects`.
Check that the redirect target receives no request.

## Sources

- [OWASP SSRF redirect handling](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html)
