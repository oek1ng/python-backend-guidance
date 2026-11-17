+++
schema_version = 1
id = "version-message-payloads"
title = "Version message envelopes explicitly"
description = "Normalize supported old and new event schemas at the boundary and reject unknown versions deliberately."
python = ">=3.12"
runtime = "any"
tags = ["schema-version", "message-compatibility", "envelopes", "evolution"]
aliases = ["version message payload", "backward compatible events"]
status = "draft"
example = "examples/version_message_payloads.py"
[[sources]]
url = "https://docs.python.org/3.12/library/json.html"
checked = 2026-11-16
+++

# Version message envelopes explicitly

## When to use

Use when old events remain queued or stored while producers and consumers evolve.
A stable single schema is simpler while no incompatible change is needed.

## Rules

1. Carry an explicit version independent of deployment or package version.
2. Decode supported versions into one internal representation.
3. Deploy compatible consumers before producers emit a new version.
4. Define unknown-field, unknown-version and replay-retention policies separately.

## Reference example

The caller already parsed a bounded JSON object. Additional fields are ignored
by this reader; changing the meaning of existing fields still needs a new version.

```python
"""Input boundary: normalize versioned envelopes into one internal shape."""

from collections.abc import Mapping
from typing import TypedDict, cast


class UserEvent(TypedDict):
    user_id: str


def decode_event(event: Mapping[str, object]) -> UserEvent:
    version = event.get("version")
    if type(version) is not int:
        raise ValueError("integer version required")
    if version == 1:
        identity = event.get("user_id")
    elif version == 2:
        subject = event.get("subject")
        identity = (
            cast(dict[object, object], subject).get("id")
            if isinstance(subject, dict)
            else None
        )
    else:
        raise ValueError("unsupported version")
    if not isinstance(identity, str) or identity == "":
        raise ValueError("invalid identity")
    return {"user_id": identity}
```

## Guarantees and assumptions

Both supported envelopes produce the same internal shape. Unknown versions fail
explicitly so the consumer can quarantine or defer them. This is a project-level
schema policy using Python JSON types, not a universal event standard.

## Pitfalls

Guessing the version from whichever field happens to exist can misinterpret mixed
payloads. Removing the old decoder immediately after deployment breaks delayed
messages and historical replays.

## Verification

Run `uv run pytest tests/test_backend_data.py --task version-message-payloads`.
Check old/new normalization, unknown versions and malformed versioned shapes.

## Sources

- [Python JSON representation and decoding](https://docs.python.org/3.12/library/json.html)
