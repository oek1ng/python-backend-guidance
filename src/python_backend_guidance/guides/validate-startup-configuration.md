+++
schema_version = 1
id = "validate-startup-configuration"
title = "Validate configuration before accepting work"
description = "Parse environment strings into explicit types and reject invalid service configuration at startup."
python = ">=3.12"
runtime = "any"
tags = ["configuration", "environment", "startup-validation", "booleans"]
aliases = ["validate startup settings", "environment boolean parsing"]
status = "draft"
example = "examples/validate_startup_configuration.py"
[[sources]]
url = "https://docs.python.org/3.12/library/os.html"
checked = 2026-11-16
[[sources]]
url = "https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html"
checked = 2026-11-16
+++

# Validate configuration before accepting work

## When to use

Use for values loaded from environment, files or secret stores. Preserve the
project's existing configuration library and precedence rules.

## Rules

1. Load and validate settings once at a deliberate startup boundary.
2. Parse boolean text explicitly instead of applying truthiness.
3. Validate ranges and relationships, not just primitive conversion.
4. Report invalid field names without logging secret values.

## Reference example

```python
"""Composition root: validate configuration before accepting traffic."""

from collections.abc import Mapping
from typing import TypedDict


class Settings(TypedDict):
    port: int
    debug: bool


def read_settings(environment: Mapping[str, str]) -> Settings:
    try:
        port = int(environment["PORT"])
    except (KeyError, ValueError) as error:
        raise ValueError("PORT must be an integer") from error
    if not 1 <= port <= 65535:
        raise ValueError("PORT out of range")
    mode = environment.get("DEBUG", "false").lower()
    if mode not in {"true", "false"}:
        raise ValueError("DEBUG must be true or false")
    return {"port": port, "debug": mode == "true"}
```

## Guarantees and assumptions

The input follows environment semantics: string keys and string values.
PORT is required and DEBUG defaults to false. The example returns ordinary data;
the application should treat its validated settings as immutable.

## Pitfalls

`bool("false")` is true. Reading environment variables repeatedly inside requests
can create inconsistent configuration. Parsing at import time makes test imports
and CLI utilities perform application startup unexpectedly.

## Verification

Run `uv run pytest tests/test_backend_lifecycle.py --task validate-startup-configuration`.
Check false text and missing, malformed and out-of-range ports.

## Sources

- [Python environment mapping](https://docs.python.org/3.12/library/os.html)
- [OWASP syntax and semantic validation](https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html)
