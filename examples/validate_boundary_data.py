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
