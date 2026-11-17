+++
schema_version = 1
id = "bound-incoming-bodies"
title = "Bound actual incoming body bytes"
description = "Count decoded request chunks before assembling a body so absent or misleading Content-Length cannot bypass limits."
python = ">=3.12"
runtime = "asyncio"
tags = ["request-body", "input-size", "chunked", "payload-limit"]
aliases = ["incoming body size limit", "chunked upload limit"]
status = "draft"
example = "examples/bound_incoming_bodies.py"
[[sources]]
url = "https://docs.python.org/3.12/library/json.html"
checked = 2026-11-16
+++

# Bound actual incoming body bytes

## When to use

Use when a handler assembles a small request body before parsing. Large uploads
should stream to a bounded temporary sink with cleanup.

## Rules

1. Enforce transport limits before the application and count actual received bytes.
2. Limit decoded data separately when accepting compression.
3. Reject before appending beyond the accepted-body limit.
4. Apply parser depth/count limits and a read deadline as well.

## Reference example

```python
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
```

## Guarantees and assumptions

The application accumulates at most `limit` bytes before the final bytes copy.
The adapter supplies bounded decoded chunks and owns request-stream closure or
draining after rejection. Decoder buffers and CPU require earlier limits.

## Pitfalls

Reading the whole body and checking length afterward is too late to bound memory.
Content-Length may describe compressed bytes or be absent. A byte limit alone
does not stop slow uploads or deeply nested parser work.

## Verification

Run `uv run pytest tests/test_backend_data.py --task bound-incoming-bodies`.
Check multi-chunk overflow and exact-limit acceptance.

## Sources

- [Python JSON resource-consumption warning](https://docs.python.org/3.12/library/json.html)
