import logging
from typing import Never

import pytest

from tests.contracts import (
    CorrelationFilter,
    CorrelationModule,
    ErrorModule,
    MakeMetricLabels,
    MakeRequestEvent,
    ProbeHealth,
    ReadBackend,
)


@pytest.mark.contract("allowlist-log-fields")
class TestLogPrivacy:
    def test_request_credentials_are_not_logged(
        self, implementation: MakeRequestEvent
    ) -> None:
        event = implementation(
            "GET",
            "/orders/{id}",
            200,
            {"Authorization": "Bearer secret", "Cookie": "x"},
        )

        assert event == {
            "event": "request",
            "method": "GET",
            "route": "/orders/{id}",
            "status": 200,
        }

    def test_unknown_headers_are_excluded(
        self, implementation: MakeRequestEvent
    ) -> None:
        assert "private" not in repr(
            implementation("GET", "/", 200, {"X-New": "private"})
        )


@pytest.mark.contract("correlate-request-logs")
class TestCorrelation:
    def test_log_record_captures_current_request(
        self, implementation: CorrelationFilter, solution_module: CorrelationModule
    ) -> None:
        record = logging.LogRecord("test", logging.INFO, "", 0, "message", (), None)
        token = solution_module.correlation_id.set("request-a")
        try:
            assert implementation().filter(record)
        finally:
            solution_module.correlation_id.reset(token)

        assert vars(record)["correlation_id"] == "request-a"

    def test_background_record_has_neutral_context(
        self, implementation: CorrelationFilter
    ) -> None:
        record = logging.LogRecord("test", logging.INFO, "", 0, "message", (), None)

        _ = implementation().filter(record)
        assert vars(record)["correlation_id"] == "-"


@pytest.mark.contract("bound-metric-labels")
class TestMetricCardinality:
    def test_arbitrary_paths_do_not_create_labels(
        self, implementation: MakeMetricLabels
    ) -> None:
        assert implementation("/orders/private-user-123", 200) == {
            "route": "unmatched",
            "status_class": "2xx",
        }

    def test_route_template_and_status_class_are_preserved(
        self, implementation: MakeMetricLabels
    ) -> None:
        assert implementation("/orders/{id}", 503) == {
            "route": "/orders/{id}",
            "status_class": "5xx",
        }


@pytest.mark.contract("preserve-error-causes")
class TestErrorBoundary:
    def test_public_error_retains_internal_cause(
        self, implementation: ReadBackend, solution_module: ErrorModule
    ) -> None:
        cause = OSError("secret endpoint")

        def fail() -> Never:
            raise cause

        with pytest.raises(solution_module.BackendUnavailable) as raised:
            implementation(fail)
        assert raised.value.__cause__ is cause
        assert "secret" not in str(raised.value)

    def test_programming_error_is_not_reclassified(
        self, implementation: ReadBackend
    ) -> None:
        def fail() -> Never:
            raise TypeError("bug")

        with pytest.raises(TypeError, match="bug"):
            implementation(fail)


@pytest.mark.contract("separate-health-probes")
class TestHealth:
    def test_dependency_outage_does_not_fail_liveness(
        self, implementation: ProbeHealth
    ) -> None:
        assert implementation(started=True, draining=False, database_ready=False) == {
            "live": True,
            "ready": False,
        }

    def test_draining_process_is_not_ready(self, implementation: ProbeHealth) -> None:
        assert implementation(started=True, draining=True, database_ready=True) == {
            "live": True,
            "ready": False,
        }
