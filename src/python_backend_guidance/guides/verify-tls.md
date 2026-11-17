+++
schema_version = 1
id = "verify-tls"
title = "Verify TLS identity with an explicit trust policy"
description = "Keep certificate-chain and hostname verification enabled when configuring an internal or public HTTPS client."
python = ">=3.12"
runtime = "sync"
tags = ["tls", "certificates", "hostname", "trust-store"]
aliases = ["HTTPS certificate verification", "custom CA bundle"]
status = "draft"
example = "examples/verify_tls.py"
libraries = {httpx = ">=0.28,<1"}
[[sources]]
url = "https://www.python-httpx.org/advanced/ssl/"
checked = 2026-11-16
+++

# Verify TLS identity with an explicit trust policy

## When to use

Use for HTTPS, including private services with an internal CA. Keep the standard
client trust store when there is no specific need to customize it.

## Rules

1. Validate both the certificate chain and the requested hostname.
2. Load an operator-controlled CA bundle rather than disabling verification.
3. Treat TLS failures as configuration/security failures, not automatic retry targets.
4. Keep trust material and client credentials out of request-controlled paths.

## Reference example

```python
"""HTTP adapter: trust an explicit CA without disabling verification."""

import ssl
from os import PathLike

import httpx


def fetch_verified(url: str, *, cafile: str | PathLike[str]) -> str:
    context = ssl.create_default_context(cafile=cafile)
    with httpx.Client(verify=context, timeout=5, trust_env=False) as client:
        response = client.get(url)
        _ = response.raise_for_status()
        return response.text
```

## Guarantees and assumptions

The URL and CA path come from trusted configuration. The default client SSL
context checks chain and hostname. This minimal one-off fetch owns its client;
repeat calls should reuse one configured lifespan client.

## Pitfalls

`verify=False` hides broken trust configuration and enables interception.
Trusting a CA does not authorize arbitrary destinations; apply an outbound policy.
Certificate revocation and rotation requirements need deployment-specific handling.

## Verification

Run `uv run pytest tests/integration/test_http_contracts.py --task verify-tls`.
Use a real local TLS server and distinct trusted/untrusted test CAs.

## Sources

- [HTTPX SSL verification](https://www.python-httpx.org/advanced/ssl/)
