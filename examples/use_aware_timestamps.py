"""Input boundary: require an offset and normalize instants to UTC."""

from datetime import UTC, datetime


def parse_instant(value: str) -> datetime:
    instant = datetime.fromisoformat(value)
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError("an explicit UTC offset is required")
    return instant.astimezone(UTC)
