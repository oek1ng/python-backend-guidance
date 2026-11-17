"""Domain policy: decimal money has two minor digits and half-even rounding."""

from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation, localcontext


def money(value: object) -> Decimal:
    if not isinstance(value, str) or len(value) > 64:
        raise ValueError("bounded decimal string required")
    try:
        with localcontext() as context:
            context.prec = 28
            amount = Decimal(value)
            if not amount.is_finite() or abs(amount) > Decimal("1000000000"):
                raise ValueError("invalid amount")
            return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
    except InvalidOperation as error:
        raise ValueError("invalid decimal amount") from error
