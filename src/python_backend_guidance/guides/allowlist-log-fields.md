+++
schema_version = 1
id = "allowlist-log-fields"
title = "Allowlist log fields instead of dumping requests"
description = "Construct structured events from approved fields so headers, credentials and newly introduced secrets are excluded by default."
python = ">=3.12"
runtime = "any"
tags = ["logging", "secrets", "redaction", "privacy"]
aliases = ["secret redaction logs", "safe structured request logs"]
status = "draft"
example = "examples/allowlist_log_fields.py"
[[sources]]
url = "https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html"
checked = 2026-11-16
+++

# Allowlist log fields instead of dumping requests

## When to use

Use for HTTP, authentication and integration logs that can see sensitive input.
Start with the minimum fields needed to diagnose behavior.

## Rules

1. Build a structured event from approved bounded fields.
2. Use route templates, not raw URLs or query strings.
3. Exclude credentials, cookies, bodies and secret-bearing exception text by default.
4. Apply the same policy to traces, error reporters and debug logs.

## Reference example

```python
"""Input boundary: build a safe event from approved scalar fields."""

from collections.abc import Mapping
from typing import Literal, TypedDict


class RequestEvent(TypedDict):
    event: Literal["request"]
    method: str
    route: str
    status: int


def request_event(
    method: str, route: str, status: int, headers: Mapping[str, str]
) -> RequestEvent:
    # headers is intentionally excluded, including credentials and cookies.
    return {"event": "request", "method": method, "route": route, "status": status}
```

## Guarantees and assumptions

No header values enter the event. Method, matched route template and status are
trusted bounded metadata from the transport adapter. The logging encoder must
escape control characters in any permitted external strings.

## Pitfalls

`logger.info("%s", request.__dict__)` exposes future fields too. A denylist of
known secret names misses new credentials and nested copies. An allowlisted field
is not automatically safe if it contains an unbounded raw user value.

## Verification

Run `uv run pytest tests/test_backend_observability.py --task allowlist-log-fields`.
Check that known credentials and unknown future headers are both excluded.

## Sources

- [OWASP logging exclusions and sanitization](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html)
