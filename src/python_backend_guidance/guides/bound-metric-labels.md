+++
schema_version = 1
id = "bound-metric-labels"
title = "Keep metric label cardinality bounded"
description = "Use finite route templates and outcome classes instead of raw URLs, request IDs or user identities in metrics."
python = ">=3.12"
runtime = "any"
tags = ["metrics", "cardinality", "labels", "route-templates"]
aliases = ["high cardinality metrics", "bounded metric labels"]
status = "draft"
example = "examples/bound_metric_labels.py"
[[sources]]
url = "https://prometheus.io/docs/practices/instrumentation/"
checked = 2026-11-16
+++

# Keep metric label cardinality bounded

## When to use

Use for labelled counters, histograms and gauges in a service. Unlabelled metrics
are sufficient when no operational breakdown is needed.

## Rules

1. Define a finite label vocabulary before instrumenting a hot path.
2. Use matched route templates and bounded fallback labels.
3. Keep request IDs and user identifiers in appropriately protected logs/traces.
4. Budget the product of label dimensions, histogram buckets and replicas.

## Reference example

```python
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
```

## Guarantees and assumptions

The example has four route values and six status classes. Status is a validated
integer from the adapter. It produces labels only; the application's metrics
client owns registration and collection.

## Pitfalls

Raw `/users/<id>` paths create one series per ID. Hashing a user ID retains its
cardinality. Several individually modest dimensions can still multiply into
an expensive number of time series.

## Verification

Run `uv run pytest tests/test_backend_observability.py --task bound-metric-labels`.
Check that arbitrary paths collapse to the fallback and templates remain recognizable.

## Sources

- [Prometheus instrumentation cardinality guidance](https://prometheus.io/docs/practices/instrumentation/)
