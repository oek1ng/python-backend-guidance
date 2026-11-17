import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import cast

from evals.models import GradeReport, read_registry
from evals.run import LOG_LIMIT, calibrate, run_checks

ROOT = Path(__file__).resolve().parents[1]


def test_grading_requires_explicit_permission_to_execute_code(tmp_path: Path) -> None:
    output = tmp_path / "report.json"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "evals.run",
            "grade",
            "--task",
            "apply-operation-deadline",
            "--solution",
            "examples/apply_operation_deadline.py",
            "--output",
            str(output),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 2
    assert "--allow-code-execution" in result.stderr
    assert not output.exists()


def test_grading_runs_the_public_contract_and_records_provenance() -> None:
    solution = ROOT / "examples/apply_operation_deadline.py"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "evals.run",
            "grade",
            "--task",
            "apply-operation-deadline",
            "--solution",
            str(solution),
            "--allow-code-execution",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=20,
    )

    assert result.returncode == 0, result.stderr
    report = cast(GradeReport, json.loads(result.stdout))
    assert report["report_schema"] == 1
    assert report["status"] == "passed"
    assert (
        report["solution_sha256"] == hashlib.sha256(solution.read_bytes()).hexdigest()
    )
    assert all(check["outcome"] == "passed" for check in report["checks"])
    assert report["contract_sha256"] != ""
    assert report["fixtures_sha256"] != ""
    assert (
        report["runner_sha256"]
        == hashlib.sha256((ROOT / "evals/run.py").read_bytes()).hexdigest()
    )
    assert (
        report["registry_sha256"]
        == hashlib.sha256((ROOT / "evals/tasks.toml").read_bytes()).hexdigest()
    )
    assert (
        report["models_sha256"]
        == hashlib.sha256((ROOT / "evals/models.py").read_bytes()).hexdigest()
    )
    assert (
        report["lock_sha256"]
        == hashlib.sha256((ROOT / "uv.lock").read_bytes()).hexdigest()
    )
    assert (
        report["test_contracts_sha256"]
        == hashlib.sha256((ROOT / "tests/contracts.py").read_bytes()).hexdigest()
    )


def test_grader_bounds_subprocess_output() -> None:
    exit_code, log = run_checks(
        [sys.executable, "-c", "print('x' * 100000)"],
        environment=dict(os.environ),
        timeout=5,
    )

    assert exit_code == 0
    assert log.endswith("x" * 1000 + "\n")
    assert len(log.encode()) <= LOG_LIMIT


def test_grader_timeout_kills_descendants_holding_its_output_pipe() -> None:
    script = (
        "import subprocess, sys\n"
        "child = subprocess.Popen([sys.executable, '-c', "
        "'import time; time.sleep(30)'])\n"
        "print(child.pid, flush=True)\n"
    )

    exit_code, log = run_checks(
        [sys.executable, "-c", script], environment=dict(os.environ), timeout=1
    )

    assert exit_code is None
    pid = int(log.strip())
    # On Linux an orphaned child may briefly remain visible as a reaped zombie.
    status = Path(f"/proc/{pid}/stat")
    until = time.monotonic() + 1
    while status.exists() and status.read_text().split()[2] != "Z":
        assert time.monotonic() < until, "grader left a running descendant"
        time.sleep(0.01)
    assert not status.exists() or status.read_text().split()[2] == "Z"


def test_existing_report_is_not_overwritten(tmp_path: Path) -> None:
    output = tmp_path / "report.json"
    _ = output.write_text("previous results", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "-m", "evals.run", "calibrate", "--output", str(output)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 2
    assert "already exists" in result.stderr
    assert output.read_text(encoding="utf-8") == "previous results"


def test_calibration_rejects_collateral_contract_failures(tmp_path: Path) -> None:
    candidate = tmp_path / "multiple_defects.py"
    _ = candidate.write_text(
        "from collections.abc import Awaitable, Callable\n"
        "async def fetch_and_store[T, R](fetch: Callable[[], Awaitable[T]], "
        "store: Callable[[T], Awaitable[R]], *, deadline: float) -> R:\n"
        "    return await store(await fetch())\n",
        encoding="utf-8",
    )
    task = read_registry(ROOT / "evals/tasks.toml")["tasks"]["apply-operation-deadline"]
    task["defects"] = [
        {
            "solution": str(candidate),
            "must_fail": "test_expired_budget_does_not_start_work",
        }
    ]

    report = calibrate({"apply-operation-deadline": task}, timeout=20)

    assert not report["passed"]
    result = report["tasks"][0]["defects"][0]
    assert not result["detected"]
    failed = {
        check["name"]
        for check in result["result"]["checks"]
        if check["outcome"] == "failed"
    }
    assert "test_expired_budget_does_not_start_work" in failed
    assert "test_nonfinite_deadline_is_rejected" in failed
