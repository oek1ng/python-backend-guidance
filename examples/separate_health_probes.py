"""Application policy: separate process liveness from admission readiness."""

from typing import Literal, TypedDict


class Health(TypedDict):
    live: Literal[True]
    ready: bool


def health(*, started: bool, draining: bool, database_ready: bool) -> Health:
    return {
        "live": True,
        "ready": started and not draining and database_ready,
    }
