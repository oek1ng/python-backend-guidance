+++
schema_version = 1
id = "correlate-request-logs"
title = "Snapshot request correlation into log records"
description = "Attach the active request ID at log emission so concurrent and queued logs retain the correct correlation."
python = ">=3.12"
runtime = "any"
tags = ["logging", "correlation", "request-id", "contextvars"]
aliases = ["request log correlation", "trace context log record"]
status = "draft"
example = "examples/correlate_request_logs.py"
[[sources]]
url = "https://docs.python.org/3.12/library/logging.html"
checked = 2026-11-16
[[sources]]
url = "https://docs.python.org/3.12/library/contextvars.html"
checked = 2026-11-16
+++

# Snapshot request correlation into log records

## When to use

Use when logs from many requests interleave or pass through an asynchronous log
queue. Reuse the existing tracing/correlation facility when available.

## Rules

1. Establish a bounded correlation ID at the request boundary.
2. Store it in request-local context and restore that context on exit.
3. Copy it onto the record before crossing the logging queue/thread boundary.
4. Treat inbound correlation IDs as untrusted metadata, not identity.

## Reference example

```python
"""Observability adapter: attach request context when a record is emitted."""

import logging
from contextvars import ContextVar
from typing import override

correlation_id: ContextVar[str] = ContextVar("correlation_id", default="-")


class CorrelationFilter(logging.Filter):
    @override
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = correlation_id.get()
        return True
```

## Guarantees and assumptions

Attach the filter to the producer-side handler, such as QueueHandler before
enqueueing, or the emitting logger. An ancestor logger's filter does not
automatically filter descendants' records. The caller owns setting/resetting context.

## Pitfalls

Looking up ContextVar in the queue listener reads the listener's context.
A global request variable misattributes concurrent logs. Correlation IDs aid
diagnosis but are not suitable high-cardinality metric labels.

## Verification

Run `uv run pytest tests/test_backend_observability.py --task correlate-request-logs`.
Verify the emitted record preserves the ID after context restoration and uses a
neutral value outside a request.

## Sources

- [Python logging filters](https://docs.python.org/3.12/library/logging.html)
- [Python context variables](https://docs.python.org/3.12/library/contextvars.html)
