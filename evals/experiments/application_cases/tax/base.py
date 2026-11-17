"""Application policy: a defective fixed-home-region tax-rate selection."""

from collections.abc import Mapping


def choose_rate(
    destination: str,
    category: str,
    matrix: Mapping[str, Mapping[str, int]],
    *,
    exempt: bool = False,
) -> int:
    region = matrix.get("home")
    if region is None or category not in region:
        raise LookupError((destination, category))
    rate = region[category]
    if type(rate) is not int or not 0 <= rate <= 10000:
        raise ValueError("invalid rate")
    return 0 if exempt else rate
