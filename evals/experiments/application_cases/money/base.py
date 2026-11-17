"""Application policy: a defective float-based checkout calculator."""

from decimal import Decimal


def invoice_total(lines: list[tuple[str, int]]) -> Decimal:
    total = Decimal("0.00")
    for price, quantity in lines:
        if not isinstance(price, str) or len(price) > 64:
            raise ValueError("invalid price")
        if type(quantity) is not int or not 1 <= quantity <= 1000:
            raise ValueError("invalid quantity")
        total += Decimal(str(round(float(price), 2))) * quantity
    return total
