"""Report-generation adapter: stream bounded output and clean up owned processes."""

import asyncio
import os
import signal
from collections.abc import Sequence


async def capture_report(
    argv: Sequence[str], *, timeout_seconds: float, output_limit_bytes: int
) -> bytes:
    if timeout_seconds <= 0 or output_limit_bytes < 0:
        raise ValueError("invalid report budget")
    process = await asyncio.create_subprocess_exec(
        *argv,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        start_new_session=True,
    )
    output = bytearray()
    assert process.stdout is not None
    try:
        async with asyncio.timeout(timeout_seconds):
            while (chunk := await process.stdout.read(4096)) != b"":
                if len(output) + len(chunk) > output_limit_bytes:
                    raise ValueError("report output too large")
                output.extend(chunk)
            if await process.wait() != 0:
                raise RuntimeError("report generator failed")
        return bytes(output)
    finally:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        while await process.stdout.read(65536) != b"":
            pass
        _ = await process.wait()
