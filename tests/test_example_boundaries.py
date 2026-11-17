import pytest

from examples.ack_after_commit import handle_delivery
from examples.restrict_outbound_destinations import fetch_configured
from examples.reuse_http_clients import fetch_with_reader


def test_delivery_workflow_does_not_acknowledge_a_failed_effect() -> None:
    acknowledgements: list[int] = []

    def record_effect(message_id: str) -> None:
        raise RuntimeError(message_id)

    with pytest.raises(RuntimeError, match="message"):
        handle_delivery(record_effect, acknowledgements.append, 3, "message")

    assert acknowledgements == []


def test_destination_policy_rejects_unknown_ids_before_fetching() -> None:
    requests: list[str] = []

    def fetch(url: str) -> bytes:
        requests.append(url)
        return b"ok"

    with pytest.raises(KeyError):
        _ = fetch_configured("unknown", {"known": "https://example.test"}, fetch)

    assert requests == []


def test_batch_workflow_uses_borrowed_reader_in_order() -> None:
    urls: list[str] = []

    def read(url: str) -> str:
        urls.append(url)
        return url.upper()

    result = fetch_with_reader(read, ["first", "second"])

    assert result == ["FIRST", "SECOND"]
    assert urls == ["first", "second"]
