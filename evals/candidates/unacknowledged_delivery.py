"""Mutation: commit the effect but omit acknowledgement of the delivery."""

from psycopg import Connection

from examples.ack_after_commit import Acknowledgements


def process_delivery(
    channel: Acknowledgements,
    tag: int,
    connection: Connection[tuple[object, ...]],
    message_id: str,
) -> None:
    # channel and tag are intentionally unused: acknowledgement is the mutation.
    with connection.transaction():
        _ = connection.execute("INSERT INTO effects VALUES (%s)", (message_id,))
