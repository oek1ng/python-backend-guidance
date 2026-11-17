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
