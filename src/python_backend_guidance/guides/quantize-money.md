+++
schema_version = 1
id = "quantize-money"
title = "Make monetary precision and rounding explicit"
description = "Parse finite bounded decimal amounts without binary floats and quantize using the currency's declared rounding policy."
python = ">=3.12"
runtime = "any"
tags = ["money", "decimal", "rounding", "precision"]
aliases = ["decimal monetary amount", "currency rounding"]
status = "draft"
example = "examples/quantize_money.py"
[[sources]]
url = "https://docs.python.org/3.12/library/decimal.html"
checked = 2026-11-16
+++

# Make monetary precision and rounding explicit

## When to use

Use when decimal amounts have accounting or contractual meaning. Integer minor
units are often simpler when no fractional intermediate calculation is needed.

## Rules

1. Parse decimal strings or integer minor units, not binary floats.
2. Reject nonfinite and out-of-policy amounts.
3. Specify currency scale and rounding point/mode explicitly.
4. Use a local decimal context so unrelated code cannot alter the policy.

## Reference example

```python
"""Domain policy: decimal money has two minor digits and half-even rounding."""

from decimal import ROUND_HALF_EVEN, Context, Decimal, InvalidOperation, localcontext


def money(value: object) -> Decimal:
    if not isinstance(value, str) or len(value) > 64:
        raise ValueError("bounded decimal string required")
    try:
        with localcontext(Context(prec=28)):
            amount = Decimal(value)
            if not amount.is_finite() or amount.copy_abs() > Decimal("1000000000"):
                raise ValueError("invalid amount")
            return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
    except InvalidOperation as error:
        raise ValueError("invalid decimal amount") from error
```

## Guarantees and assumptions

The example implements one two-decimal HALF_EVEN policy with a bounded amount.
It is not universal for all currencies or tax rules. Carry currency identity
alongside amounts and serialize without converting back through float.

## Pitfalls

`Decimal(0.1)` preserves the binary approximation. `round(float(text), 2)` can
produce a different amount at decimal boundaries. Rounding each line item and
rounding the total can differ; choose the domain's rule.

## Verification

Run `uv run pytest tests/test_backend_data.py --task quantize-money`.
Check decimal tie rounding, exact limit enforcement, context independence, and
rejection of floats, nonfinite and oversized values.

## Sources

- [Python Decimal arithmetic and quantize](https://docs.python.org/3.12/library/decimal.html)
