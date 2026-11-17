# Checkout invoice

Fix `solution.py` while preserving this Python 3.12+ interface:

```python
def invoice_total(lines: list[tuple[str, int]]) -> Decimal: ...
```

Each tuple is `(unit_price_text, quantity)`. Prices are decimal strings, not
floats: accept only finite amounts with absolute value no greater than
`1000000000`, including values with more than two digits after the decimal
point. Reject an amount *slightly* over the maximum before rounding it.
Reject non-string values, nonfinite numbers, malformed decimal text and
strings longer than 64 characters with `ValueError`. Quantity must be an
integer (not `bool`) from 1 to 1000; otherwise raise `ValueError`.

Round each unit price to two decimal places using HALF_EVEN, **then** multiply
by its quantity and sum the results. Return `Decimal("0.00")` for an empty
invoice. The result and validation must not depend on an ambient decimal
context or binary floating-point conversion. This example uses one declared
currency policy, not arbitrary tax or conversion rules. Python 3.12+ stdlib.
