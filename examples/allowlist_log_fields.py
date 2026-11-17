"""Input boundary: build a safe event from approved scalar fields."""

from collections.abc import Mapping
from typing import Literal, TypedDict


class RequestEvent(TypedDict):
    event: Literal["request"]
    method: str
    route: str
    status: int


def request_event(
    method: str, route: str, status: int, headers: Mapping[str, str]
) -> RequestEvent:
    # headers is intentionally excluded, including credentials and cookies.
    return {"event": "request", "method": method, "route": route, "status": status}
