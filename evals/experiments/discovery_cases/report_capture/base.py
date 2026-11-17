"""Report-generation adapter: capture a command's output within a deadline."""

import asyncio
from collections.abc import Sequence
from contextlib import suppress


async def capture_report(
    argv: Sequence[str], *, timeout_seconds: float, output_limit_bytes: int
) -> bytes:
    if timeout_seconds <= 0 or output_limit_bytes < 0:
        raise ValueError("invalid report budget")
    process = await asyncio.create_subprocess_exec(
        *argv,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    try:
        async with asyncio.timeout(timeout_seconds):
            output, _ = await process.communicate()
        if len(output) > output_limit_bytes:
            raise ValueError("report output too large")
        if process.returncode != 0:
            raise RuntimeError("report generator failed")
        return output
    finally:
        with suppress(ProcessLookupError):
            process.kill()
        _ = await process.wait()
