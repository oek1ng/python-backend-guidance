"""Message adapter: reject malformed deliveries without a requeue loop."""

import json
from collections.abc import Callable
from typing import Protocol, TypedDict, cast


class Envelope(TypedDict):
    id: str


class DeliveryChannel(Protocol):
    def basic_ack(self, delivery_tag: int) -> None: ...
    def basic_nack(self, delivery_tag: int, *, requeue: bool) -> None: ...


def decode_envelope(body: bytes) -> Envelope:
    """Input boundary: validate bytes before passing an envelope to a handler."""
    decoded: object = json.loads(body)
    if not isinstance(decoded, dict):
        raise ValueError("invalid envelope")
    message = cast(dict[str, object], decoded)  # JSON object keys are strings.
    if not isinstance(message.get("id"), str):
        raise ValueError("invalid envelope")
    return cast(Envelope, message)  # The required id field was checked above.


def consume_json(
    channel: DeliveryChannel, tag: int, body: bytes, handle: Callable[[Envelope], None]
) -> bool:
    try:
        message = decode_envelope(body)
    except ValueError:  # Includes UnicodeDecodeError for invalid UTF-8 bytes.
        channel.basic_nack(delivery_tag=tag, requeue=False)
        return False
    handle(message)
    channel.basic_ack(delivery_tag=tag)
    return True
