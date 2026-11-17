"""Input boundary: count decoded chunks, not an untrusted Content-Length."""

from collections.abc import AsyncIterable


async def collect_body(chunks: AsyncIterable[bytes], *, limit: int) -> bytes:
    if limit < 0:
        raise ValueError("limit must be nonnegative")
    result = bytearray()
    async for chunk in chunks:
        if len(result) + len(chunk) > limit:
            raise ValueError("request body too large")
        result.extend(chunk)
    return bytes(result)
