"""Persistence adapter: install constraints that arbitrate concurrent writers."""

from psycopg import Connection


def create_reservations(connection: Connection[tuple[object, ...]]) -> None:
    _ = connection.execute(
        "CREATE TABLE reservations ("
        "id bigint PRIMARY KEY, "
        "account bigint NOT NULL REFERENCES accounts(id), "
        "reference text NOT NULL UNIQUE, "
        "quantity integer NOT NULL CHECK (quantity > 0))"
    )
