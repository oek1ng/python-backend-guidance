+++
schema_version = 1
id = "distinguish-patch-null"
title = "Distinguish missing fields from explicit null"
description = "Define partial-update semantics so absent fields preserve values and explicit null clears a nullable field."
python = ">=3.12"
runtime = "any"
tags = ["patch", "null", "missing-fields", "partial-update"]
aliases = ["PATCH absent versus null", "nullable partial update"]
status = "draft"
example = "examples/distinguish_patch_null.py"
[[sources]]
url = "https://www.rfc-editor.org/rfc/rfc7396.html"
checked = 2026-11-16
+++

# Distinguish missing fields from explicit null

## When to use

Use for partial updates with nullable fields. A full replacement representation
can be simpler if clients always send the complete resource.

## Rules

1. Document absent, null and concrete-value meanings separately.
2. Check membership rather than using `get()` when absence matters.
3. Validate allowed update fields to prevent mass assignment.
4. Combine partial updates with authorization and a concurrent-edit policy.

## Reference example

```python
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
```

## Guarantees and assumptions

The function returns a new flat mapping and does not modify current. This is an
application-specific nullable-field contract. RFC 7396 JSON Merge Patch instead
uses null to remove an object member; do not advertise this as a full RFC implementation.

## Pitfalls

`if patch.get("nickname") is not None` loses explicit clearing. Dropping every
falsey value also loses empty strings, zero and false. PATCH itself does not
guarantee idempotency for arbitrary update operations.

## Verification

Run `uv run pytest tests/test_backend_data.py --task distinguish-patch-null`.
Check clearing, preserving absent fields and input immutability.

## Sources

- [RFC 7396 null and absent-member semantics](https://www.rfc-editor.org/rfc/rfc7396.html)
