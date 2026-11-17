"""Exploratory report-generator checks; never mounted in an authoring workspace."""

import asyncio
import importlib.util
import os
import signal
import sys
import tempfile
import unittest
from collections.abc import Awaitable, Sequence
from contextlib import suppress
from pathlib import Path
from typing import Protocol, cast


class CaptureReport(Protocol):
    def __call__(
        self, argv: Sequence[str], *, timeout_seconds: float, output_limit_bytes: int
    ) -> Awaitable[bytes]: ...


def solution() -> CaptureReport:
    spec = importlib.util.spec_from_file_location(
        "report_candidate", Path(os.environ["PBG_CANDIDATE"])
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return cast(CaptureReport, module.capture_report)


async def capture(argv: Sequence[str], *, seconds: float, limit: int) -> bytes:
    return await solution()(argv, timeout_seconds=seconds, output_limit_bytes=limit)


class ReportChecks(unittest.IsolatedAsyncioTestCase):
    async def test_success_combines_output(self) -> None:
        argv = [
            sys.executable,
            "-c",
            "import os; os.write(1,b'first'); os.write(2,b'second')",
        ]

        output = await asyncio.wait_for(capture(argv, seconds=3, limit=16), 5)

        self.assertIn(b"first", output)
        self.assertIn(b"second", output)

    async def test_nonzero_exit_fails(self) -> None:
        with self.assertRaises(RuntimeError):
            _ = await asyncio.wait_for(
                capture(
                    [sys.executable, "-c", "raise SystemExit(2)"], seconds=3, limit=16
                ),
                5,
            )

    async def test_invalid_budget_does_not_launch_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / "started"
            argv = [
                sys.executable,
                "-c",
                f"from pathlib import Path; Path({str(marker)!r}).touch()",
            ]

            with self.assertRaises(ValueError):
                _ = await capture(argv, seconds=0, limit=16)
            with self.assertRaises(ValueError):
                _ = await capture(argv, seconds=3, limit=-1)

            self.assertFalse(marker.exists())

    async def test_output_limit_does_not_wait_for_process_exit(self) -> None:
        argv = [
            sys.executable,
            "-c",
            "import os,time; os.write(1,b'x'*101); time.sleep(15)",
        ]

        with self.assertRaises(ValueError):
            _ = await asyncio.wait_for(capture(argv, seconds=10, limit=100), 3)

    async def check_helper_cleanup(self, *, cancel: bool) -> None:
        # The helper owns a separate socket, so EOF proves it was terminated:
        # waiting for its inherited stdout alone does not demonstrate cleanup.
        script = (
            "import os,socket,sys,time\n"
            "leader=os.getpid()\n"
            "if os.fork()==0:\n"
            " with socket.socket(socket.AF_UNIX) as ready:\n"
            "  ready.connect(sys.argv[1])\n"
            "  ready.sendall(f'{leader} {os.getpid()}\\n'.encode())\n"
            "  time.sleep(15)\n"
            "elif sys.argv[2]=='timeout':\n"
            " os._exit(0)\n"
            "else:\n"
            " time.sleep(15)\n"
        )
        connected: asyncio.Future[tuple[asyncio.StreamReader, asyncio.StreamWriter]] = (
            asyncio.get_running_loop().create_future()
        )

        def accept(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
            connected.set_result((reader, writer))

        with tempfile.TemporaryDirectory() as directory:
            address = Path(directory) / "ready.sock"
            pids: list[int] = []
            writer: asyncio.StreamWriter | None = None
            async with await asyncio.start_unix_server(accept, path=address):
                task = asyncio.create_task(
                    capture(
                        [
                            sys.executable,
                            "-c",
                            script,
                            str(address),
                            "cancel" if cancel else "timeout",
                        ],
                        seconds=10 if cancel else 0.3,
                        limit=32,
                    )
                )
                try:
                    reader, writer = await asyncio.wait_for(connected, 3)
                    pids = [int(value) for value in (await reader.readline()).split()]
                    self.assertEqual(len(pids), 2)
                    if cancel:
                        _ = task.cancel()
                    with self.assertRaises(
                        asyncio.CancelledError if cancel else TimeoutError
                    ):
                        _ = await asyncio.wait_for(task, 3)
                    self.assertEqual(await asyncio.wait_for(reader.read(1), 1), b"")
                    with self.assertRaises(ChildProcessError):
                        _ = os.waitpid(pids[0], os.WNOHANG)
                finally:
                    for pid in reversed(pids):
                        with suppress(ProcessLookupError):
                            os.kill(pid, signal.SIGKILL)
                    if not task.done():
                        _ = task.cancel()
                    _ = await asyncio.wait_for(
                        asyncio.gather(task, return_exceptions=True), 3
                    )
                    if writer is not None:
                        writer.close()
                        await writer.wait_closed()

    async def test_timeout_after_leader_exit_stops_helper(self) -> None:
        await self.check_helper_cleanup(cancel=False)

    async def test_parent_cancellation_stops_helper(self) -> None:
        await self.check_helper_cleanup(cancel=True)


if __name__ == "__main__":
    _ = unittest.main(verbosity=2)
