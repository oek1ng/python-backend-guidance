+++
schema_version = 1
id = "quarantine-poison-messages"
title = "Quarantine poison messages instead of hot-loop requeueing"
description = "Reject permanently invalid RabbitMQ payloads without immediate requeue and route them to an observable dead-letter queue."
python = ">=3.12"
runtime = "sync"
tags = ["poison-messages", "dead-letter", "nack", "rabbitmq"]
aliases = ["poison message retry loop", "dead letter malformed payload"]
status = "draft"
example = "examples/quarantine_poison_messages.py"
services = ["RabbitMQ >=4.1"]
libraries = {pika = ">=1.3,<2"}
[[sources]]
url = "https://www.rabbitmq.com/docs/4.1/dlx"
checked = 2026-11-16
+++

# Quarantine poison messages instead of hot-loop requeueing

## When to use

Use for permanently invalid envelopes that retrying cannot repair. Transient
dependency failures need a separate bounded, delayed retry policy.

## Rules

1. Classify parsing/schema failures separately from handler failures.
2. Reject permanent failures without requeue.
3. Provision and monitor a dead-letter route before relying on quarantine.
4. Make replay an explicit operation after correction; retain event identity.

## Reference example

```python
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
```

## Guarantees and assumptions

The broker supplies a bounded body on the channel's owning thread. Invalid
envelopes are rejected; handler failures propagate and remain unacknowledged.
The application must resolve those deliveries without an immediate retry loop.

## Pitfalls

`nack(requeue=True)` on every failure creates a hot poison-message loop.
Without a DLX, rejection can discard a message. DLX reliability depends on queue
type and configuration; the example does not promise lossless quarantine.

## Verification

Run `uv run pytest tests/integration/test_message_contracts.py --task quarantine-poison-messages`.
Use a real DLX route and verify handler errors remain eligible for redelivery.

## Sources

- [RabbitMQ dead-letter exchanges and safety](https://www.rabbitmq.com/docs/4.1/dlx)
