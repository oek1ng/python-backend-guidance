+++
schema_version = 1
id = "bound-subprocess-resources"
title = "Bound subprocess runtime and captured output"
description = "Stream a POSIX subprocess's combined output within byte and time budgets, then terminate and reap its owned process group."
python = ">=3.12"
runtime = "asyncio"
tags = ["subprocess", "output-limit", "process-groups", "termination"]
aliases = ["subprocess timeout output limit", "kill child process group"]
status = "draft"
example = "examples/bound_subprocess_resources.py"
services = ["POSIX process groups"]
[[sources]]
url = "https://docs.python.org/3.12/library/asyncio-subprocess.html"
checked = 2026-11-16
[[sources]]
url = "https://docs.python.org/3.12/library/os.html"
checked = 2026-11-16
+++

# Bound subprocess runtime and captured output

## When to use

Use for trusted tools whose output/runtime can exceed a request budget. Running
untrusted code needs an independently configured sandbox with CPU, memory and
filesystem controls.

## Rules

1. Launch an argv sequence and give owned descendants a process-group boundary.
2. Drain output incrementally and reject beyond a byte cap.
3. Cover reading and process exit with a finite timeout.
4. On failure or cancellation, terminate the group and reap the direct child.

## Reference example

```python
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
```

## Guarantees and assumptions

POSIX-only, trusted non-daemonizing tools. The accepted output buffer is bounded;
transport buffers and the final bytes copy add overhead. Launch itself is outside
the timeout. Cleanup assumes no repeated cancellation interrupts the final wait.

## Pitfalls

`communicate()` buffers all output in memory. Killing only the direct child can
leave descendants holding pipes open. A descendant can escape a process group;
use supervisor/cgroup boundaries when that must be prevented. After terminating
writers, drain buffered pipe bytes before waiting: a paused reader can otherwise
keep asyncio process cleanup waiting even after the child has exited.

## Verification

Run `uv run pytest tests/test_backend_files.py --task bound-subprocess-resources`.
Exercise actual child processes for overflow, stalled execution, nonzero exits and
success. Check group termination and direct-child reaping on timeout and external
cancellation, including descendants holding pipes after the group leader exits.

## Sources

- [Python asyncio subprocesses](https://docs.python.org/3.12/library/asyncio-subprocess.html)
- [Python process-group signals](https://docs.python.org/3.12/library/os.html)
