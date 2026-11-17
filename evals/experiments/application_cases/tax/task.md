# Tax-rate selection

Fix `solution.py` while preserving this Python 3.12+ interface:

```python
def choose_rate(
    destination: str,
    category: str,
    matrix: Mapping[str, Mapping[str, int]],
    *,
    exempt: bool = False,
) -> int: ...
```

The trusted `matrix` stores a region-specific tax rate in integer basis points
for every `(destination, category)` pair. Select the rate for the *exact*
pair; do not fall back to a home region or another category. Unknown pairs
raise `LookupError`. Rates must be integers other than `bool`, between 0 and
10000 inclusive; invalid configured rates raise `ValueError`. Validate the
selected pair and its rate even if `exempt=True`, then return zero for an
exempt transaction. Otherwise return the configured rate. Do not calculate
money or infer a statutory tax rate: the supplied table is the complete policy.
Python 3.12+ stdlib only.
