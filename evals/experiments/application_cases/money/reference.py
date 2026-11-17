"""Application policy: round validated unit prices before calculating an invoice."""

from decimal import ROUND_HALF_EVEN, Context, Decimal, InvalidOperation, localcontext


def invoice_total(lines: list[tuple[str, int]]) -> Decimal:
    total = Decimal("0.00")
    with localcontext(Context(prec=28)):
        for price, quantity in lines:
            if not isinstance(price, str) or len(price) > 64:
                raise ValueError("invalid price")
            if type(quantity) is not int or not 1 <= quantity <= 1000:
                raise ValueError("invalid quantity")
            try:
                amount = Decimal(price)
                if not amount.is_finite() or amount.copy_abs() > Decimal("1000000000"):
                    raise ValueError("invalid price")
                unit = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
            except InvalidOperation as error:
                raise ValueError("invalid price") from error
            total += unit * quantity
    return total
