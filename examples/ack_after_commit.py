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
