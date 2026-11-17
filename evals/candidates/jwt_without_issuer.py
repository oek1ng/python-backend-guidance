"""Mutation: require an issuer but do not verify its trusted value."""

import jwt


def verify_token(token: str | bytes, key: str | bytes) -> dict[str, object]:
    return jwt.decode(
        token,
        key,
        algorithms=["HS256"],
        issuer="https://issuer.example",
        audience="backend",
        options={"require": ["exp", "iss", "aud", "sub"], "verify_iss": False},
    )
