+++
schema_version = 1
id = "separate-health-probes"
title = "Separate liveness from readiness"
description = "Keep dependency outages and draining out of liveness while withholding readiness when the service cannot accept useful work."
python = ">=3.12"
runtime = "any"
tags = ["health", "liveness", "readiness", "startup"]
aliases = ["liveness readiness probes", "dependency outage restart loop"]
status = "draft"
example = "examples/separate_health_probes.py"
[[sources]]
url = "https://kubernetes.io/docs/concepts/configuration/liveness-readiness-startup-probes/"
checked = 2026-11-16
+++

# Separate liveness from readiness

## When to use

Use when a supervisor restarts unhealthy processes and a load balancer routes
traffic only to ready instances. Kubernetes is one example, not a requirement.

## Rules

1. Make liveness indicate local progress or an unrecoverable local failure.
2. Use readiness for completed startup, required dependencies and admission state.
3. Set not-ready before graceful draining.
4. Keep probes cheap, bounded and resistant to synchronized dependency load.

## Reference example

```python
"""Application policy: separate process liveness from admission readiness."""

from typing import Literal, TypedDict


class Health(TypedDict):
    live: Literal[True]
    ready: bool


def health(*, started: bool, draining: bool, database_ready: bool) -> Health:
    return {
        "live": True,
        "ready": started and not draining and database_ready,
    }
```

## Guarantees and assumptions

This pure state mapping assumes the process can execute the probe, which is its
minimal liveness criterion. `database_ready` represents a required dependency's
bounded recent check; optional dependencies should not gate all traffic.

## Pitfalls

Failing liveness whenever a database is down restarts every instance during the
same outage. Checking every dependency synchronously on every probe can worsen
overload. An HTTP response alone cannot prove all business subsystems are healthy.

## Verification

Run `uv run pytest tests/test_backend_observability.py --task separate-health-probes`.
Check dependency outage and draining separately from local liveness.

## Sources

- [Kubernetes probe semantics](https://kubernetes.io/docs/concepts/configuration/liveness-readiness-startup-probes/)
