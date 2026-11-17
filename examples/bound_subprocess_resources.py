"""Process adapter: bound output and time, then clean up the process group."""

import asyncio
import os
import signal
from collections.abc import Sequence


async def run_bounded(argv: Sequence[str], *, timeout: float, limit: int) -> bytes:
    if timeout <= 0 or limit < 0:
        raise ValueError("invalid subprocess budget")
    process = await asyncio.create_subprocess_exec(
        *argv,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        start_new_session=True,
    )
    result = bytearray()
    assert process.stdout is not None  # stdout=PIPE creates the reader.
    try:
        async with asyncio.timeout(timeout):
            while (chunk := await process.stdout.read(4096)) != b"":
                if len(result) + len(chunk) > limit:
                    raise ValueError("subprocess output too large")
                result.extend(chunk)
            if await process.wait() != 0:
                raise RuntimeError("subprocess failed")
        return bytes(result)
    finally:
        # Kill the group even if the leader exited but descendants kept pipes open.
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        # Unblock a paused pipe transport before waiting for process cleanup.
        while await process.stdout.read(65536) != b"":
            pass
        _ = await process.wait()
