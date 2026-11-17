"""Domain policy: an absent field preserves, while null clears a value."""

from collections.abc import Mapping
from typing import cast


def patch_profile(
    current: Mapping[str, str | None], patch: object
) -> dict[str, str | None]:
    if not isinstance(patch, dict):
        raise ValueError("invalid patch")
    fields = cast(dict[object, object], patch)
    if len(set(fields) - {"nickname"}) != 0:
        raise ValueError("invalid patch")
    result = dict(current)
    if "nickname" in fields:
        value = fields["nickname"]
        if value is not None and not isinstance(value, str):
            raise ValueError("nickname must be a string or null")
        result["nickname"] = value
    return result
