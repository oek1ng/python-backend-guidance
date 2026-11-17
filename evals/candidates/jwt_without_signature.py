"""Mutation: disable signature verification while retaining claim validation."""

import jwt


def verify_token(token: str | bytes, key: str | bytes) -> dict[str, object]:
    # PyJWT also skips algorithm admission when signature checking is disabled.
    # Preserve the fixed policy so this candidate has only the signature defect.
    if jwt.get_unverified_header(token).get("alg") != "HS256":
        raise jwt.InvalidAlgorithmError("Only HS256 is permitted")
    return jwt.decode(
        token,
        key,
        algorithms=["HS256"],
        issuer="https://issuer.example",
        audience="backend",
        options={
            "require": ["exp", "iss", "aud", "sub"],
            "verify_signature": False,
            "verify_exp": True,
            "verify_nbf": True,
            "verify_iat": True,
            "verify_aud": True,
            "verify_iss": True,
            "verify_sub": True,
            "verify_jti": True,
        },
    )
