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
