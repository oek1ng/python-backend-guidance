+++
schema_version = 1
id = "use-aware-timestamps"
title = "Represent instants with timezone-aware timestamps"
description = "Require an explicit offset at an instant boundary and normalize to aware UTC without guessing the sender's timezone."
python = ">=3.12"
runtime = "any"
tags = ["datetime", "timezone", "utc", "instants"]
aliases = ["timezone aware timestamps", "reject naive datetime"]
status = "draft"
example = "examples/use_aware_timestamps.py"
[[sources]]
url = "https://docs.python.org/3.12/library/datetime.html"
checked = 2026-11-16
+++

# Represent instants with timezone-aware timestamps

## When to use

Use for event times, expiration instants and audit timestamps. Calendar dates and
future local-time schedules have different semantics and need their own models.

## Rules

1. Require an explicit timezone/offset for an instant.
2. Convert with `astimezone`, not by replacing the timezone label.
3. Store and compare aware instants consistently, normally in UTC.
4. Use monotonic time for elapsed deadlines, not wall-clock timestamps.

## Reference example

```python
"""Input boundary: require an offset and normalize instants to UTC."""

from datetime import UTC, datetime


def parse_instant(value: str) -> datetime:
    instant = datetime.fromisoformat(value)
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError("an explicit UTC offset is required")
    return instant.astimezone(UTC)
```

## Guarantees and assumptions

Accepted ISO-format input with an offset becomes an aware UTC datetime.
Python's parser accepts more forms than a strict RFC 3339 API may allow; use
additional syntax validation if the wire contract requires that narrower format.

## Pitfalls

`naive.replace(tzinfo=UTC)` asserts an interpretation; it does not discover one.
UTC alone cannot preserve the user's intended future local schedule through DST
changes. Preserve an IANA timezone for those schedules.

## Verification

Run `uv run pytest tests/test_backend_data.py --task use-aware-timestamps`.
Reject naive input and verify actual offset conversion.

## Sources

- [Python aware and naive datetimes](https://docs.python.org/3.12/library/datetime.html)
