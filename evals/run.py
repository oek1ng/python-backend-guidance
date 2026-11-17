"""Offline contract grading and calibration; not a security sandbox or agent runner."""

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from collections import Counter
from importlib.metadata import version
from pathlib import Path
from typing import Literal

from evals.models import (
    CalibrationReport,
    CalibrationTask,
    Check,
    DefectResult,
    GradeReport,
    Outcome,
    Task,
    read_registry,
)
from python_backend_guidance.catalog import load_guides

ROOT = Path(__file__).resolve().parents[1]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def grade(
    task_id: str,
    task: Task,
    solution: Path,
    *,
    timeout: int,
    selected_check: str | None = None,
) -> GradeReport:
    solution = solution.resolve()
    if not solution.is_file() or solution.suffix != ".py":
        raise ValueError(f"Solution must be an existing Python module: {solution}")
    guide = next(guide for guide in load_guides() if guide.id == task_id)
    report: GradeReport = {
        "status": "infrastructure-error",
        "checks": [],
        "summary": {},
        "report_schema": 1,
        "task": task_id,
        "solution": str(solution),
        "solution_sha256": digest(solution),
        "guide_sha256": hashlib.sha256(guide.content.encode()).hexdigest(),
        "contract_sha256": digest(ROOT / task["prompt"]),
        "checks_sha256": digest(ROOT / task["tests"]),
        "fixtures_sha256": digest(ROOT / "tests/conftest.py"),
        "fixture_files_sha256": {
            str(path.relative_to(ROOT)): digest(path)
            for parent in (ROOT / task["tests"]).parents
            if parent.is_relative_to(ROOT / "tests")
            and (path := parent / "conftest.py").is_file()
        },
        "dependency_versions": {
            name: version(name) for name, _requirement in guide.libraries
        },
        "package_version": version("python-backend-guidance"),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "pytest": version("pytest"),
        "pytest_asyncio": version("pytest-asyncio"),
        "selected_check": selected_check,
        "timeout_seconds": timeout,
    }
    with tempfile.TemporaryDirectory(prefix="pbg-grade-") as temporary:
        workspace = Path(temporary)
        junit = workspace / "results.xml"
        command = [
            sys.executable,
            "-m",
            "pytest",
            "-p",
            "pytest_asyncio.plugin",
            task["tests"],
            "--task",
            task_id,
            "--solution",
            str(solution),
            "--junitxml",
            str(junit),
            "-o",
            f"cache_dir={workspace / 'cache'}",
            "-q",
        ]
        if selected_check is not None:
            command.extend(["-k", selected_check])
        environment = {
            "PATH": os.environ.get("PATH", ""),
            "HOME": str(workspace),
            "TMPDIR": str(workspace),
            "LANG": "C.UTF-8",
            "PYTHONNOUSERSITE": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
        }
        if "SYSTEMROOT" in os.environ:
            environment["SYSTEMROOT"] = os.environ["SYSTEMROOT"]
        for name in ("PBG_POSTGRES_DSN", "PBG_AMQP_URL"):
            if name in os.environ:
                environment[name] = os.environ[name]
        try:
            result = subprocess.run(
                command,
                cwd=ROOT,
                env=environment,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            report["status"] = "timeout"
            return report

        checks: list[Check] = []
        if junit.is_file():
            for case in ET.parse(junit).iter("testcase"):
                outcome: Outcome = "passed"
                outcomes: tuple[tuple[str, Outcome], ...] = (
                    ("error", "error"),
                    ("failure", "failed"),
                    ("skipped", "skipped"),
                )
                for tag, outcome_name in outcomes:
                    if case.find(tag) is not None:
                        outcome = outcome_name
                        break
                checks.append({"name": case.attrib["name"], "outcome": outcome})
        summary = dict(Counter(check["outcome"] for check in checks))
        if result.returncode == 0 and len(checks) != 0 and set(summary) == {"passed"}:
            status = "passed"
        elif result.returncode == 1 and len(checks) != 0:
            status = "failed"
        else:
            status = "infrastructure-error"
        report["status"] = status
        report["exit_code"] = result.returncode
        report["checks"] = checks
        report["summary"] = summary
        report["log"] = (result.stdout + result.stderr)[-16000:]
        return report


def calibrate(tasks: dict[str, Task], *, timeout: int) -> CalibrationReport:
    results: list[CalibrationTask] = []
    for task_id, task in tasks.items():
        reference = grade(task_id, task, ROOT / task["reference"], timeout=timeout)
        alternatives = [
            grade(task_id, task, ROOT / path, timeout=timeout)
            for path in task.get("alternatives", [])
        ]
        reference_checks = Counter(check["name"] for check in reference["checks"])
        defects: list[DefectResult] = []
        for defect in task["defects"]:
            result = grade(
                task_id,
                task,
                ROOT / defect["solution"],
                timeout=timeout,
            )
            expected_failures = {
                defect["must_fail"],
                *defect.get("related_failures", []),
            }
            detected = (
                reference["status"] == "passed"
                and result["status"] == "failed"
                and expected_failures <= set(reference_checks)
                and Counter(check["name"] for check in result["checks"])
                == reference_checks
                and all(
                    check["outcome"]
                    == ("failed" if check["name"] in expected_failures else "passed")
                    for check in result["checks"]
                )
            )
            defects.append({"detected": detected, "result": result})
        results.append(
            {
                "task": task_id,
                "passed": reference["status"] == "passed"
                and all(result["status"] == "passed" for result in alternatives)
                and bool(defects)
                and all(defect["detected"] for defect in defects),
                "reference": reference,
                "alternatives": alternatives,
                "defects": defects,
            }
        )
    return {
        "report_schema": 1,
        "kind": "calibration",
        "passed": bool(results) and all(result["passed"] for result in results),
        "tasks": results,
    }


class Arguments(argparse.Namespace):
    command: Literal["grade", "calibrate"] = "calibrate"
    task: str = ""
    solution: Path = Path()
    timeout: int = 30
    output: Path | None = None
    allow_code_execution: bool = False


def main(argv: list[str] | None = None) -> int:
    tasks = read_registry(ROOT / "evals/tasks.toml")["tasks"]
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    single = commands.add_parser(
        "grade", help="Execute one trusted solution's contract"
    )
    _ = single.add_argument("--task", choices=tasks, required=True)
    _ = single.add_argument("--solution", type=Path, required=True)
    _ = single.add_argument("--allow-code-execution", action="store_true")
    calibration = commands.add_parser(
        "calibrate", help="Check shipped references/defects"
    )
    for command in (single, calibration):
        _ = command.add_argument("--timeout", type=int, default=30)
        _ = command.add_argument("--output", type=Path)
    args = parser.parse_args(argv, namespace=Arguments())
    if args.timeout < 1:
        parser.error("--timeout must be positive")
    if args.output is not None and args.output.exists():
        parser.error("--output already exists; choose a new report path")
    if args.command == "grade" and not args.allow_code_execution:
        parser.error(
            "grading executes solution code; use --allow-code-execution only for "
            "trusted code, or run inside an independently configured sandbox"
        )
    try:
        report: GradeReport | CalibrationReport
        if args.command == "grade":
            report = grade(
                args.task, tasks[args.task], args.solution, timeout=args.timeout
            )
            passed = report["status"] == "passed"
        else:
            report = calibrate(tasks, timeout=args.timeout)
            passed = report["passed"]
        text = json.dumps(report, indent=2) + "\n"
        if args.output is not None:
            with args.output.open("x", encoding="utf-8") as output:
                _ = output.write(text)
            print(f"Report: {args.output}", file=sys.stderr)
        else:
            print(text, end="")
        return 0 if passed else 1
    except (OSError, ValueError, ET.ParseError) as error:
        print(f"Evaluation error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
