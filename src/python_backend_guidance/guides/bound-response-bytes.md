+++
schema_version = 1
id = "bound-response-bytes"
title = "Bound decoded HTTP response bytes"
description = "Stream outbound response bodies, enforce a decoded byte limit, and close the response when rejecting it."
python = ">=3.12"
runtime = "sync"
tags = ["http", "streaming", "response-size", "decompression"]
aliases = ["streaming download payload size", "compressed response limit"]
status = "draft"
example = "examples/bound_response_bytes.py"
libraries = {httpx = ">=0.28,<1"}
[[sources]]
url = "https://www.python-httpx.org/quickstart/"
checked = 2026-11-16
+++

# Bound decoded HTTP response bytes

## When to use

Use when a downstream response may be large or untrusted. For large accepted
objects, stream to a bounded sink instead of assembling bytes in memory.

## Rules

1. Inspect status before consuming a success payload.
2. Count actual decoded bytes, including compressed responses.
3. Reject before appending a chunk that exceeds the accepted limit.
4. Own the streaming response with a context manager.

## Reference example

```python
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
```

## Guarantees and assumptions

At most `limit` bytes are accepted into the result. The supplied client remains
caller-owned. HTTPX decoding and internal buffering happen before yielded chunks;
this helper is not a hard bound on decoder CPU or transient allocation.

## Pitfalls

Checking Content-Length alone misses absent, misleading, or compressed lengths.
For hostile compressed bodies, disable unsupported encodings or use a bounded
decompressor and transport limits; do not claim this accumulator alone stops bombs.

## Verification

Run `uv run pytest tests/integration/test_http_contracts.py --task bound-response-bytes`.
Check compressed oversized content and an exact-limit response.

## Sources

- [HTTPX streaming and content decoding](https://www.python-httpx.org/quickstart/)
