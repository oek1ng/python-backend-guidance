"""Persistence adapter: fetch related rows in one bounded batch."""

from collections.abc import Iterable
from typing import LiteralString, Protocol, cast


class ItemQuery(Protocol):
    def execute(
        self, query: LiteralString, params: tuple[list[int]], /
    ) -> Iterable[tuple[object, ...]]: ...


def bounded_ids(order_ids: Iterable[int]) -> list[int]:
    """Application policy: deduplicate without exceeding the batch budget."""
    ids = list(dict.fromkeys(order_ids))
    if len(ids) > 500:
        raise ValueError("batch too large")
    return ids


def load_items(connection: ItemQuery, order_ids: Iterable[int]) -> dict[int, list[str]]:
    ids = bounded_ids(order_ids)
    result: dict[int, list[str]] = {identity: [] for identity in ids}
    if len(ids) != 0:
        rows = connection.execute(
            "SELECT order_id, sku FROM items WHERE order_id = ANY(%s) "
            "ORDER BY order_id, sku",
            (ids,),
        )
        # The query projects (bigint order_id, text sku) from the declared schema.
        for identity, sku in cast(Iterable[tuple[int, str]], rows):
            result[identity].append(sku)
    return result
