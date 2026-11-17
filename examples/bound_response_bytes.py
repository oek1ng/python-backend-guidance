"""HTTP adapter: count decoded bytes while streaming a response."""

from collections.abc import Iterable

import httpx


def collect_limited(chunks: Iterable[bytes], *, limit: int) -> bytes:
    """Application policy: never accumulate more than the decoded-byte budget."""
    if limit < 0:
        raise ValueError("limit must be nonnegative")
    result = bytearray()
    for chunk in chunks:
        if len(result) + len(chunk) > limit:
            raise ValueError("response too large")
        result.extend(chunk)
    return bytes(result)


def read_limited(client: httpx.Client, url: str, *, limit: int) -> bytes:
    if limit < 0:
        raise ValueError("limit must be nonnegative")
    with client.stream("GET", url) as response:
        _ = response.raise_for_status()
        return collect_limited(response.iter_bytes(chunk_size=4096), limit=limit)
