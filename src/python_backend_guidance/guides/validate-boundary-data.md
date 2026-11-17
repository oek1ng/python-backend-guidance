+++
schema_version = 1
id = "validate-boundary-data"
title = "Validate external data at the boundary"
description = "Check input shape, exact types and domain bounds before passing request data into business operations."
python = ">=3.12"
runtime = "any"
tags = ["validation", "input-schema", "types", "unknown-fields"]
aliases = ["validate request payload", "boolean integer validation"]
status = "draft"
example = "examples/validate_boundary_data.py"
[[sources]]
url = "https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html"
checked = 2026-11-16
+++

# Validate external data at the boundary

## When to use

Use for requests, configuration, messages and external API data. Prefer the
project's existing schema library for larger or nested schemas.

## Rules

1. Parse with a safe format parser, then validate syntax and domain meaning.
2. Make coercion and unknown-field behavior explicit.
3. Bound lengths, counts and nesting before expensive processing.
4. Keep validation separate from authorization and database invariants.

## Reference example

```python
"""Input boundary: validate an order schema before using its fields."""

from typing import TypedDict, cast


class Order(TypedDict):
    sku: str
    quantity: int


def parse_order(value: object) -> Order:
    if not isinstance(value, dict):
        raise ValueError("expected sku and quantity only")
    # isinstance establishes the container; its keys/values remain untrusted.
    fields = cast(dict[object, object], value)
    if set(fields) != {"sku", "quantity"}:
        raise ValueError("expected sku and quantity only")
    sku, quantity = fields["sku"], fields["quantity"]
    if not isinstance(sku, str) or not 1 <= len(sku) <= 64:
        raise ValueError("invalid sku")
    if type(quantity) is not int or not 1 <= quantity <= 100:
        raise ValueError("invalid quantity")
    return {"sku": sku, "quantity": quantity}
```

## Guarantees and assumptions

This contract rejects extra fields, floats, booleans and out-of-range quantities.
It validates a parsed object; transport and parser size limits occur earlier.
Other contracts may intentionally permit additive fields.

## Pitfalls

`isinstance(True, int)` is true in Python. Automatically assigning every input
field can enable mass assignment. Type annotations alone do not validate runtime
data, and valid input does not imply permission to perform the operation.

## Verification

Run `uv run pytest tests/test_backend_data.py --task validate-boundary-data`.
Check valid input, boolean quantities and this contract's unknown-field policy.

## Sources

- [OWASP input validation](https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html)
