"""Mutation: accept HS384 in addition to the fixed HS256 policy."""

import jwt


def verify_token(token: str | bytes, key: str | bytes) -> dict[str, object]:
    return jwt.decode(
        token,
        key,
        algorithms=["HS256", "HS384"],
        issuer="https://issuer.example",
        audience="backend",
        options={"require": ["exp", "iss", "aud", "sub"]},
    )
