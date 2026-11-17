"""Mutation: kill only the direct child instead of its owned process group."""

import asyncio
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
    assert process.stdout is not None
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
        if process.returncode is None:
            process.kill()
        while await process.stdout.read(65536) != b"":
            pass
        _ = await process.wait()
