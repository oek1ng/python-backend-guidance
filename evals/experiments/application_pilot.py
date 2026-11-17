"""Explore guide use in isolated application edits; not a security sandbox."""

import argparse
import hashlib
import json
import os
import random
import re
import signal
import subprocess
import time
from pathlib import Path
from typing import Literal, TypedDict, cast

from evals.run import run_checks

ROOT = Path(__file__).resolve().parents[2]
CASES = Path(__file__).with_name("application_cases")
IMAGE = "sha256:55abbe5e2b9b5b9a21645a4ce9d671d39aebc4c0150738c2a0fd147376a85ee5"
MODEL = "openai/gpt-6.1-sol#medium"
AGENT = "pbg-application-pilot"
SEED = 20261117
STEPS = 10
TIMEOUT = 180
PROMPT = (
    "Read TASK.md, GUIDANCE.md, SKILL.md and solution.py. Fix only solution.py. "
    "Use the guidance interface only when available and relevant. When using "
    "the skill, find a focused capability query before retrieving a guide; "
    "a result is not automatically applicable. Make no changes outside "
    "solution.py. Your code will be checked separately in an isolated "
    "environment. Do not claim to have run tests."
)
SYSTEM = (
    "You are editing a small Python 3.12+ application. Preserve the documented "
    "public interface and type annotations. Only edit solution.py. Do not "
    "attempt to read graders or use tools outside the provided permissions. "
    "This is a noninteractive evaluation; finish without asking questions."
)

type Condition = Literal["baseline", "direct", "workflow"]


class Trial(TypedDict):
    id: str
    task: str
    condition: Condition
    repeat: int
    directory: str
    input_sha256: dict[str, str]


class Manifest(TypedDict):
    schema_version: Literal[1]
    model: str
    opencode_version: str
    instructions_sha256: str
    image: str
    seed: int
    steps: int
    timeout_seconds: int
    prompt: str
    source_sha256: dict[str, str]
    schedule: list[Trial]


GUIDES = {
    "inventory": "bound-concurrent-work",
    "money": "quantize-money",
    "tax": None,
}


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def api(
    method: str, path: str, body: dict[str, object] | None = None
) -> dict[str, object]:
    command = ["opencode", "api", method, path]
    if body is not None:
        command.extend(["--data", json.dumps(body)])
    response = subprocess.run(
        command, capture_output=True, text=True, check=True, timeout=30
    )
    if response.stdout.strip() == "":
        return {}
    return cast(dict[str, object], json.loads(response.stdout))


def prepare(output: Path) -> None:
    wheel = ROOT / "dist/python_backend_guidance-0.1.0-py3-none-any.whl"
    if not wheel.is_file():
        raise FileNotFoundError("Build the wheel before preparing the experiment")
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    rng = random.Random(SEED)
    schedule: list[Trial] = []
    skill = (ROOT / "skills/python-backend-guidance/SKILL.md").read_text(
        encoding="utf-8"
    )
    for repeat in (1, 2):
        tasks = list(GUIDES)
        rng.shuffle(tasks)
        for task in tasks:
            conditions: list[Condition] = ["baseline", "direct", "workflow"]
            rng.shuffle(conditions)
            for condition in conditions:
                name = f"{len(schedule) + 1:02d}-{task}-r{repeat}-{condition}"
                directory = output / "runs" / name
                directory.mkdir(mode=0o700, parents=True)
                guide_id = GUIDES[task]
                guidance = (
                    (
                        ROOT / "src/python_backend_guidance/guides" / f"{guide_id}.md"
                    ).read_text(encoding="utf-8")
                    if condition == "direct" and guide_id is not None
                    else "# Guidance\n\nNo preselected guide is supplied.\n"
                )
                config = {
                    "$schema": "https://opencode.ai/config.json",
                    "default_agent": AGENT,
                    "snapshots": False,
                    "formatter": False,
                    "agents": {
                        AGENT: {
                            "description": "Edit one isolated application file",
                            "mode": "primary",
                            "model": MODEL,
                            "steps": STEPS,
                            "system": SYSTEM,
                            "permissions": [
                                {"action": "*", "resource": "*", "effect": "deny"},
                                *[
                                    {
                                        "action": "read",
                                        "resource": path,
                                        "effect": "allow",
                                    }
                                    for path in (
                                        "TASK.md",
                                        "GUIDANCE.md",
                                        "SKILL.md",
                                        "solution.py",
                                    )
                                ],
                                {
                                    "action": "edit",
                                    "resource": "solution.py",
                                    "effect": "allow",
                                },
                                *(
                                    [
                                        {
                                            "action": "shell",
                                            "resource": (
                                                f"python-backend-guidance {verb} *"
                                            ),
                                            "effect": "allow",
                                        }
                                        for verb in ("search", "retrieve", "list")
                                    ]
                                    if condition == "workflow"
                                    else []
                                ),
                            ],
                        }
                    },
                }
                files = {
                    "TASK.md": (CASES / task / "task.md").read_text(encoding="utf-8"),
                    "GUIDANCE.md": guidance,
                    "SKILL.md": (
                        skill
                        if condition == "workflow"
                        else "# No skill is supplied for this run.\n"
                    ),
                    "solution.py": (CASES / task / "base.py").read_text(
                        encoding="utf-8"
                    ),
                    "opencode.json": json.dumps(config, indent=2) + "\n",
                }
                for filename, content in files.items():
                    _ = (directory / filename).write_text(content, encoding="utf-8")
                schedule.append(
                    {
                        "id": name,
                        "task": task,
                        "condition": condition,
                        "repeat": repeat,
                        "directory": str(directory),
                        "input_sha256": {
                            filename: digest(content.encode())
                            for filename, content in files.items()
                        },
                    }
                )
    sources = [
        *CASES.rglob("*"),
        ROOT / "skills/python-backend-guidance/SKILL.md",
        *(
            ROOT / "src/python_backend_guidance/guides" / f"{guide_id}.md"
            for guide_id in GUIDES.values()
            if guide_id is not None
        ),
        ROOT / "evals/experiments/application_pilot.py",
        wheel,
    ]
    version = subprocess.run(
        ["opencode", "--version"],
        capture_output=True,
        text=True,
        check=True,
        timeout=15,
    ).stdout.strip()
    manifest: Manifest = {
        "schema_version": 1,
        "model": MODEL,
        "opencode_version": version,
        "instructions_sha256": digest(
            Path.home().joinpath(".config/opencode/AGENTS.md").read_bytes()
        ),
        "image": IMAGE,
        "seed": SEED,
        "steps": STEPS,
        "timeout_seconds": TIMEOUT,
        "prompt": PROMPT,
        "source_sha256": {
            str(path.relative_to(ROOT)): digest(path.read_bytes())
            for path in sorted(sources)
            if path.is_file()
        },
        "schedule": schedule,
    }
    _ = (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Prepared {len(schedule)} trials; no model calls made.")


def read_manifest(output: Path) -> Manifest:
    # Manifest is generated by prepare() and has immutable checked-in task IDs.
    return cast(Manifest, json.loads((output / "manifest.json").read_text()))


def verify_sources(manifest: Manifest) -> None:
    for name, expected in manifest["source_sha256"].items():
        if digest((ROOT / name).read_bytes()) != expected:
            raise RuntimeError(f"Experiment source changed: {name}")


def grade(output: Path, task: str, solution: Path, *, label: str) -> dict[str, object]:
    if task not in GUIDES:
        raise ValueError(f"Unknown task: {task}")
    cidfile = output / f"docker-{label}.cid"
    command = [
        "docker",
        "run",
        "--rm",
        "--cidfile",
        str(cidfile),
        "--network",
        "none",
        "--read-only",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--pids-limit",
        "64",
        "--memory",
        "512m",
        "--cpus",
        "1",
        "--tmpfs",
        "/tmp:rw,nosuid,nodev,size=64m",
        "--mount",
        f"type=bind,src={solution.resolve()},dst=/candidate/solution.py,readonly",
        "--mount",
        (
            "type=bind,src="
            f"{(CASES / task / 'checks.py').resolve()},"
            "dst=/app/evals/experiments/checks.py,readonly"
        ),
        "-e",
        "PBG_CANDIDATE=/candidate/solution.py",
        IMAGE,
        "python",
        "/app/evals/experiments/checks.py",
    ]
    try:
        exit_code, log = run_checks(command, environment=dict(os.environ), timeout=45)
    finally:
        # A killed Docker client cannot be relied on to stop its container.
        if cidfile.is_file():
            _ = subprocess.run(
                ["docker", "rm", "--force", cidfile.read_text().strip()],
                capture_output=True,
                timeout=15,
                check=False,
            )
    match = re.search(r"Ran (\d+) tests", log)
    return {
        "status": "passed"
        if exit_code == 0
        else "timeout"
        if exit_code is None
        else "failed",
        "exit_code": exit_code,
        "checks": int(match[1]) if match is not None else 0,
        "log": log,
    }


def calibrate(output: Path) -> None:
    verify_sources(read_manifest(output))
    results: dict[str, dict[str, dict[str, object]]] = {}
    for task in GUIDES:
        reference = grade(
            output, task, CASES / task / "reference.py", label=f"ref-{task}"
        )
        defect = grade(output, task, CASES / task / "base.py", label=f"base-{task}")
        results[task] = {"reference": reference, "base": defect}
    passed = all(
        row["reference"]["status"] == "passed" and row["base"]["status"] == "failed"
        for row in results.values()
    )
    _ = (output / "calibration.json").write_text(
        json.dumps({"passed": passed, "tasks": results}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Calibration passed: {passed}")
    if not passed:
        raise RuntimeError("Reference/defect sandbox calibration failed")


def run_trial(output: Path, trial: Trial, *, cli_bin: Path) -> None:
    directory = Path(trial["directory"])
    result_path = directory / "result.json"
    if result_path.exists():
        return
    if (directory / "started.json").exists():
        raise RuntimeError(f"Refusing to repeat a started trial: {trial['id']}")
    for filename, expected in trial["input_sha256"].items():
        if digest((directory / filename).read_bytes()) != expected:
            raise RuntimeError(f"Input changed before trial: {directory / filename}")
    info = cast(
        dict[str, object],
        api(
            "post",
            "/api/session",
            {
                "title": f"PBG application pilot {trial['id']}",
                "agent": AGENT,
                "model": {
                    "providerID": "openai",
                    "id": "gpt-6.1-sol",
                    "variant": "medium",
                },
                "location": {"directory": str(directory)},
            },
        )["data"],
    )
    session_id = cast(str, info["id"])
    environment = dict(os.environ)
    _ = environment.pop("OPENCODE_SESSION_ID", None)
    environment["PATH"] = f"{cli_bin}:{environment.get('PATH', '')}"
    command = [
        "opencode",
        "--standalone",
        "run",
        "--session",
        session_id,
        "--agent",
        AGENT,
        "--model",
        MODEL,
        "--format",
        "json",
        "--title",
        f"PBG application pilot {trial['id']}",
        read_manifest(output)["prompt"],
    ]
    with (directory / "started.json").open("x", encoding="utf-8") as record:
        _ = record.write(
            json.dumps({"session_id": session_id, "command": command}) + "\n"
        )
    started = time.monotonic()
    timed_out = False
    with (directory / "events.ndjson").open("w", encoding="utf-8") as events:
        with (directory / "agent.stderr").open("w", encoding="utf-8") as errors:
            process = subprocess.Popen(
                command,
                cwd=directory,
                env=environment,
                stdout=events,
                stderr=errors,
                start_new_session=True,
            )
            try:
                exit_code = process.wait(timeout=TIMEOUT)
            except subprocess.TimeoutExpired:
                timed_out = True
                os.killpg(process.pid, signal.SIGKILL)
                exit_code = process.wait()
                _ = api("post", f"/api/session/{session_id}/interrupt", {})
    solution = directory / "solution.py"
    grade_result = (
        grade(output, trial["task"], solution, label=trial["id"])
        if solution.is_file() and not solution.is_symlink()
        else {"status": "missing", "checks": 0}
    )
    result: dict[str, object] = {
        "trial": trial["id"],
        "task": trial["task"],
        "condition": trial["condition"],
        "repeat": trial["repeat"],
        "session_id": session_id,
        "agent_exit_code": exit_code,
        "agent_timeout": timed_out,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "model": MODEL,
        "grade": grade_result,
    }
    if solution.is_file() and not solution.is_symlink():
        result["solution_sha256"] = digest(solution.read_bytes())
    try:
        session = cast(
            dict[str, object], api("get", f"/api/session/{session_id}")["data"]
        )
        result["session_outcome"] = session.get("outcome")
        result["tokens"] = session.get("tokens")
        result["reported_cost"] = session.get("cost")
        transcript = api(
            "get", f"/api/experimental/session/{session_id}/export?sanitize=true"
        )
        _ = (directory / "transcript.json").write_text(
            json.dumps(transcript, indent=2) + "\n", encoding="utf-8"
        )
        _ = api("patch", f"/api/session/{session_id}", {"archived": True})
    except (
        KeyError,
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
    ) as error:
        result["session_metadata_error"] = type(error).__name__
    _ = result_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(
        trial["id"],
        "agent=",
        exit_code,
        "grade=",
        cast(dict[str, object], result["grade"])["status"],
        "seconds=",
        result["elapsed_seconds"],
        flush=True,
    )


def run(output: Path, *, cli_bin: Path, limit: int) -> None:
    manifest = read_manifest(output)
    verify_sources(manifest)
    calibration = cast(
        dict[str, object], json.loads((output / "calibration.json").read_text())
    )
    if calibration["passed"] is not True:
        raise RuntimeError("Calibrate before running any agents")
    if not 1 <= limit <= len(manifest["schedule"]):
        raise ValueError("Limit must select between 1 and 18 trials")
    if not (cli_bin / "python-backend-guidance").is_file():
        raise ValueError("Frozen installed CLI is unavailable")
    executable = str(cli_bin / "python-backend-guidance")
    exported = subprocess.run(
        [executable, "export-skill"],
        capture_output=True,
        text=True,
        check=True,
        timeout=15,
    ).stdout
    if exported != (ROOT / "skills/python-backend-guidance/SKILL.md").read_text(
        encoding="utf-8"
    ):
        raise RuntimeError("Frozen CLI skill differs from the experiment source")
    for guide_id in GUIDES.values():
        if guide_id is None:
            continue
        retrieved = subprocess.run(
            [executable, "retrieve", guide_id],
            capture_output=True,
            text=True,
            check=True,
            timeout=15,
        ).stdout
        if retrieved != (
            ROOT / "src/python_backend_guidance/guides" / f"{guide_id}.md"
        ).read_text(encoding="utf-8"):
            raise RuntimeError(f"Frozen CLI guide differs: {guide_id}")
    for trial in manifest["schedule"][:limit]:
        verify_sources(manifest)
        run_trial(output, trial, cli_bin=cli_bin)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    _ = parser.add_argument("command", choices=["prepare", "calibrate", "run"])
    _ = parser.add_argument("--output", type=Path, required=True)
    _ = parser.add_argument("--cli-bin", type=Path, help="Frozen installed CLI bin")
    _ = parser.add_argument("--limit", type=int, default=18)
    args = parser.parse_args(argv)
    if args.command == "prepare":
        prepare(args.output)
    elif args.command == "calibrate":
        calibrate(args.output)
    else:
        if args.cli_bin is None:
            parser.error("--cli-bin is required for agent runs")
        run(args.output, cli_bin=args.cli_bin, limit=args.limit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
