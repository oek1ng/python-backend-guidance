"""Observability boundary: labels use a finite route vocabulary."""

from typing import Final, TypedDict

ROUTES: Final[frozenset[str]] = frozenset({"/orders", "/orders/{id}", "/health"})


class MetricLabels(TypedDict):
    route: str
    status_class: str


def metric_labels(route: str, status: int) -> MetricLabels:
    return {
        "route": route if route in ROUTES else "unmatched",
        "status_class": f"{status // 100}xx" if 100 <= status <= 599 else "other",
    }
