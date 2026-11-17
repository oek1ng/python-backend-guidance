+++
schema_version = 1
id = "ack-after-commit"
title = "Acknowledge a message after committing its effect"
description = "Use manual RabbitMQ acknowledgements after a successful local database commit so failures remain eligible for redelivery."
python = ">=3.12"
runtime = "sync"
tags = ["acknowledgements", "rabbitmq", "commit", "redelivery"]
aliases = ["ack message after commit", "manual consumer acknowledgement"]
status = "draft"
example = "examples/ack_after_commit.py"
services = ["PostgreSQL >=16", "RabbitMQ >=4.1"]
libraries = {psycopg = ">=3.2,<4", pika = ">=1.3,<2"}
[[sources]]
url = "https://www.rabbitmq.com/docs/confirms"
checked = 2026-11-16
+++

# Acknowledge a message after committing its effect

## When to use

Use for a manual-ack consumer that persists a local effect. Follow the broker's
delivery-tag and channel rules; other brokers expose different protocols.

## Rules

1. Disable automatic acknowledgement and configure finite prefetch.
2. Commit the effect before acknowledging this delivery.
3. Make redelivery safe because commit and ack are not one atomic operation.
4. Distinguish transient handling failures from permanent poison messages.

## Reference example

Requires `effects(id text PRIMARY KEY)`, an idle autocommit database connection,
and a live Pika channel on its owning thread.

```python
"""Application workflow: acknowledge a delivery only after its local effect commits."""

from collections.abc import Callable
from typing import Protocol

from psycopg import Connection


class Acknowledgements(Protocol):
    def basic_ack(self, delivery_tag: int) -> None: ...


class EffectRecorder:
    def __init__(self, connection: Connection[tuple[object, ...]]) -> None:
        self.connection = connection

    def __call__(self, identity: str) -> None:
        with self.connection.transaction():
            _ = self.connection.execute(
                "INSERT INTO effects (id) VALUES (%s) ON CONFLICT DO NOTHING",
                (identity,),
            )


class DeliveryAcknowledger:
    def __init__(self, channel: Acknowledgements) -> None:
        self.channel = channel

    def __call__(self, tag: int) -> None:
        self.channel.basic_ack(delivery_tag=tag)


def handle_delivery(
    record_effect: Callable[[str], None],
    acknowledge: Callable[[int], None],
    tag: int,
    message_id: str,
) -> None:
    record_effect(message_id)
    acknowledge(tag)


def process_delivery(
    channel: Acknowledgements,
    tag: int,
    connection: Connection[tuple[object, ...]],
    message_id: str,
) -> None:
    handle_delivery(
        EffectRecorder(connection), DeliveryAcknowledger(channel), tag, message_id
    )
```

## Guarantees and assumptions

A commit exception leaves the delivery unacknowledged. Repeated insertion of the
same effect ID is harmless. This is a minimal durable marker, not a general
idempotency wrapper for external effects.

## Pitfalls

Acknowledging before commit can lose work. A crash after commit and before ack
causes redelivery, which is expected. Publisher confirms do not prove that a
consumer applied the effect.

## Verification

Run `uv run pytest tests/integration/test_message_contracts.py --task ack-after-commit`.
A deferred PostgreSQL constraint fails at commit; closing the channel must
make the real RabbitMQ delivery available again. On success, inspect the effect
from a separate database connection, close the delivery channel, and confirm
that a new channel cannot retrieve the acknowledged message.

## Sources

- [RabbitMQ acknowledgements and publisher confirms](https://www.rabbitmq.com/docs/confirms)
