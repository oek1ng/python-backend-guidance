"""Domain policy: a cache identity includes all authorization dimensions."""

import json


def cache_key(tenant: str, subject: str, locale: str) -> str:
    return json.dumps(
        ["profile-v1", tenant, subject, locale],
        ensure_ascii=True,
        separators=(",", ":"),
    )
