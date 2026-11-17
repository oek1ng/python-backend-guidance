"""Composition root: validate configuration before accepting traffic."""

from collections.abc import Mapping
from typing import TypedDict


class Settings(TypedDict):
    port: int
    debug: bool


def read_settings(environment: Mapping[str, str]) -> Settings:
    try:
        port = int(environment["PORT"])
    except (KeyError, ValueError) as error:
        raise ValueError("PORT must be an integer") from error
    if not 1 <= port <= 65535:
        raise ValueError("PORT out of range")
    mode = environment.get("DEBUG", "false").lower()
    if mode not in {"true", "false"}:
        raise ValueError("DEBUG must be true or false")
    return {"port": port, "debug": mode == "true"}
