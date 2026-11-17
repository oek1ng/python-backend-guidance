"""Input boundary: normalize versioned envelopes into one internal shape."""

from collections.abc import Mapping
from typing import TypedDict, cast


class UserEvent(TypedDict):
    user_id: str


def decode_event(event: Mapping[str, object]) -> UserEvent:
    version = event.get("version")
    if type(version) is not int:
        raise ValueError("integer version required")
    if version == 1:
        identity = event.get("user_id")
    elif version == 2:
        subject = event.get("subject")
        identity = (
            cast(dict[object, object], subject).get("id")
            if isinstance(subject, dict)
            else None
        )
    else:
        raise ValueError("unsupported version")
    if not isinstance(identity, str) or identity == "":
        raise ValueError("invalid identity")
    return {"user_id": identity}
