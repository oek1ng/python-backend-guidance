import asyncio
import io
import os
import signal
import sys
from contextlib import suppress
from pathlib import Path
from typing import Never

import pytest

from tests.contracts import CopyStream, ReplaceFile, RunBounded, RunTool, WithWorkspace


@pytest.mark.contract("avoid-shell-interpolation")
class TestShellArguments:
    def test_metacharacters_remain_one_literal_argument(
        self, implementation: RunTool, tmp_path: Path
    ) -> None:
        executable = tmp_path / "echo-argument"
        _ = executable.write_text('#!/bin/sh\nprintf "%s" "$1"\n')
        executable.chmod(0o700)
        argument = "literal; echo injected"

        assert implementation(str(executable), argument) == argument

    def test_nonzero_tool_exit_is_reported(
        self, implementation: RunTool, tmp_path: Path
    ) -> None:
        import subprocess

        executable = tmp_path / "fail"
        _ = executable.write_text("#!/bin/sh\nexit 2\n")
        executable.chmod(0o700)

        with pytest.raises(subprocess.CalledProcessError):
            _ = implementation(str(executable), "argument")


@pytest.mark.contract("bound-subprocess-resources")
class TestSubprocessBudget:
    async def test_subprocess_output_limit_is_enforced(
        self, implementation: RunBounded
    ) -> None:
        with pytest.raises(ValueError):
            await asyncio.wait_for(
                implementation(
                    [sys.executable, "-c", "print('x' * 1000000)"],
                    timeout=2,
                    limit=100,
                ),
                timeout=5,
            )

    async def test_stalled_subprocess_is_terminated(
        self, implementation: RunBounded
    ) -> None:
        with pytest.raises(TimeoutError):
            await implementation(
                [sys.executable, "-c", "import time; time.sleep(30)"],
                timeout=0.1,
                limit=100,
            )

    async def test_bounded_subprocess_returns_output(
        self, implementation: RunBounded
    ) -> None:
        assert (
            await implementation(
                [sys.executable, "-c", "print('ok')"], timeout=2, limit=10
            )
            == b"ok\n"
        )

    async def test_nonzero_subprocess_exit_is_reported(
        self, implementation: RunBounded
    ) -> None:
        with pytest.raises(RuntimeError):
            await implementation(
                [sys.executable, "-c", "raise SystemExit(2)"], timeout=2, limit=100
            )

    @pytest.mark.parametrize("stop", ["timeout", "cancel"])
    async def test_subprocess_group_is_terminated_and_child_reaped(
        self, implementation: RunBounded, tmp_path: Path, stop: str
    ) -> None:
        connected: asyncio.Future[tuple[asyncio.StreamReader, asyncio.StreamWriter]] = (
            asyncio.get_running_loop().create_future()
        )

        def accept(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
            connected.set_result((reader, writer))

        address = tmp_path / "ready.sock"
        # The descendant holds stdout and a separate liveness socket open. The
        # timeout case also exercises cleanup after the group leader has exited.
        script = (
            "import os, socket, sys, time\n"
            "leader = os.getpid()\n"
            "if os.fork() == 0:\n"
            "    with socket.socket(socket.AF_UNIX) as ready:\n"
            "        ready.connect(sys.argv[1])\n"
            "        ready.sendall(f'{leader} {os.getpid()}\\n'.encode())\n"
            "        time.sleep(15)\n"
            "elif sys.argv[2] == 'timeout':\n"
            "    os._exit(0)\n"
            "else:\n"
            "    time.sleep(15)\n"
        )
        pids: list[int] = []
        async with await asyncio.start_unix_server(accept, path=address):
            task = asyncio.create_task(
                implementation(
                    [sys.executable, "-c", script, str(address), stop],
                    timeout=2 if stop == "timeout" else 10,
                    limit=100,
                )
            )
            try:
                reader, _writer = await asyncio.wait_for(asyncio.shield(connected), 5)
                pids = [
                    int(value)
                    for value in (await asyncio.wait_for(reader.readline(), 5)).split()
                ]
                assert len(pids) == 2

                if stop == "cancel":
                    _ = task.cancel()
                done, _ = await asyncio.wait({task}, timeout=5)

                assert task in done, "owned descendants kept the operation alive"
                with pytest.raises(
                    TimeoutError if stop == "timeout" else asyncio.CancelledError
                ):
                    await task
                assert await asyncio.wait_for(reader.read(1), 1) == b""
                with pytest.raises(ChildProcessError):
                    _ = os.waitpid(pids[0], os.WNOHANG)
            finally:
                # Also clean up a defective candidate's surviving processes.
                for pid in reversed(pids):
                    with suppress(ProcessLookupError):
                        os.kill(pid, signal.SIGKILL)
                done, _ = await asyncio.wait({task}, timeout=2)
                if task not in done:
                    _ = task.cancel()
                _ = await asyncio.gather(task, return_exceptions=True)
                if connected.done() and not connected.cancelled():
                    _, writer = connected.result()
                    writer.close()
                    await writer.wait_closed()


@pytest.mark.contract("stream-large-files")
class TestFileStreaming:
    def test_file_limit_prevents_full_write(self, implementation: CopyStream) -> None:
        destination = io.BytesIO()

        with pytest.raises(ValueError):
            _ = implementation(io.BytesIO(b"abcdef"), destination, limit=5)
        assert len(destination.getvalue()) <= 5

    def test_stream_copy_preserves_bytes(self, implementation: CopyStream) -> None:
        destination = io.BytesIO()

        assert implementation(io.BytesIO(b"abcdef"), destination, limit=6) == 6
        assert destination.getvalue() == b"abcdef"


@pytest.mark.contract("replace-files-atomically")
class TestAtomicReplacement:
    def test_pre_replace_failure_preserves_old_file(
        self,
        implementation: ReplaceFile,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        target = tmp_path / "file"
        _ = target.write_bytes(b"old")

        def fail(fd: int) -> Never:
            raise OSError("disk failure")

        monkeypatch.setattr(os, "fsync", fail)

        with pytest.raises(OSError):
            implementation(target, b"new")
        assert target.read_bytes() == b"old"
        assert list(tmp_path.iterdir()) == [target]

    def test_atomic_replacement_publishes_complete_file(
        self, implementation: ReplaceFile, tmp_path: Path
    ) -> None:
        target = tmp_path / "file"
        _ = target.write_bytes(b"old")

        implementation(target, b"new")
        assert target.read_bytes() == b"new"
        assert list(tmp_path.iterdir()) == [target]


@pytest.mark.contract("own-temporary-files")
class TestTemporaryWorkspaces:
    def test_workspace_is_removed_on_error(self, implementation: WithWorkspace) -> None:
        paths: list[Path] = []

        def fail(path: Path) -> Never:
            paths.append(path)
            _ = (path / "data").write_bytes(b"data")
            raise ValueError

        with pytest.raises(ValueError):
            implementation(fail)
        assert not paths[0].exists()

    def test_workspace_result_is_returned(self, implementation: WithWorkspace) -> None:
        assert implementation(lambda path: path.is_dir()) is True
