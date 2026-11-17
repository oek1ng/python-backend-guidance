+++
schema_version = 1
id = "verify-token-claims"
title = "Verify token signatures and required claims"
description = "Pin the JWT algorithm and trust policy, require expiration and identity claims, and validate issuer and audience."
python = ">=3.12"
runtime = "any"
tags = ["jwt", "signature", "issuer", "audience", "expiration"]
aliases = ["JWT token signature verification", "validate token claims"]
status = "draft"
example = "examples/verify_token_claims.py"
libraries = {PyJWT = ">=2.10,<3"}
[[sources]]
url = "https://pyjwt.readthedocs.io/en/stable/api.html"
checked = 2026-11-16
+++

# Verify token signatures and required claims

## When to use

Use when the application is responsible for verifying JWTs. Prefer an established
identity-provider integration when it already supplies the needed validation.

## Rules

1. Select permitted algorithms and keys from trusted configuration.
2. Require claims whose absence would bypass the policy.
3. Validate signature, expiration, issuer, audience and subject shape.
4. Perform object/action authorization after authentication.

## Reference example

```python
"""Authentication adapter: verify claims against a fixed token policy."""

import jwt


def verify_token(token: str | bytes, key: str | bytes) -> dict[str, object]:
    return jwt.decode(
        token,
        key,
        algorithms=["HS256"],
        issuer="https://issuer.example",
        audience="backend",
        options={"require": ["exp", "iss", "aud", "sub"]},
    )
```

## Guarantees and assumptions

This example is a symmetric HS256 trust domain with a strong, securely provisioned
key. Replace example issuer/audience with the deployment policy. Use the provider's
asymmetric algorithm and bounded JWKS retrieval when that is its protocol.

## Pitfalls

Decoding without signature verification is parsing, not authentication. Choosing
`algorithms` from the untrusted header lets the token select its verification
policy. Checking exp only when present accepts tokens without a required expiry.

## Verification

Run `uv run pytest tests/test_backend_security.py --task verify-token-claims`.
Use genuinely signed tokens to check wrong-key signatures, unapproved algorithms,
issuer, audience, expiry, each required claim and success.

## Sources

- [PyJWT verification options and algorithm warnings](https://pyjwt.readthedocs.io/en/stable/api.html)
