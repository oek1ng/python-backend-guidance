"""Persistence adapter: retry PostgreSQL conflicts around whole transactions."""

import random
import time
from collections.abc import Callable

from psycopg import Connection
from psycopg.errors import DeadlockDetected, SerializationFailure


def run_transaction[T](
    connection: Connection[tuple[object, ...]],
    operation: Callable[[Connection[tuple[object, ...]]], T],
    *,
    attempts: int = 3,
) -> T:
    if attempts < 1:
        raise ValueError("attempts must be positive")
    attempt = 0
    while True:
        try:
            with connection.transaction():
                _ = connection.execute("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE")
                return operation(connection)
        except (SerializationFailure, DeadlockDetected):
            if attempt == attempts - 1:
                raise
            time.sleep(random.uniform(0, min(0.05 * 2**attempt, 0.5)))
            attempt += 1
