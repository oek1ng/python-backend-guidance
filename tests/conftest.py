import asyncio
import importlib.util
import random
import sys
from functools import cache
from hashlib import sha256
from pathlib import Path
from types import ModuleType

import pytest

from evals.models import Task, read_registry

ROOT = Path(__file__).resolve().parents[1]


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption("--solution", type=Path, help="Candidate module for one contract")
    parser.addoption("--task", help="Task ID corresponding to --solution")


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    task: object = config.getoption("--task")
    if task is None:
        return
    selected: list[pytest.Item] = []
    deselected: list[pytest.Item] = []
    for item in items:
        marker = item.get_closest_marker("contract")
        target = (
            selected if marker is not None and marker.args[0] == task else deselected
        )
        target.append(item)
    items[:] = selected
    config.hook.pytest_deselected(items=deselected)


@cache
def load_solution(path: Path) -> ModuleType:
    name = "_pbg_solution_" + sha256(str(path).encode()).hexdigest()[:12]
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise pytest.UsageError(f"Cannot load solution module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def contract_task(request: pytest.FixtureRequest) -> Task:
    marker = request.node.get_closest_marker("contract")
    if marker is None:
        raise pytest.UsageError("A solution test requires a contract(task) marker")
    tasks = read_registry(ROOT / "evals/tasks.toml")
    task_id: object = marker.args[0]
    if not isinstance(task_id, str):
        raise pytest.UsageError("contract task ID must be a string")
    if request.config.getoption("--solution") is not None and (
        request.config.getoption("--task") != task_id
    ):
        raise pytest.UsageError("--solution requires the matching --task")
    return tasks["tasks"][task_id]


@pytest.fixture
def solution_module(request: pytest.FixtureRequest, contract_task: Task) -> ModuleType:
    candidate: object = request.config.getoption("--solution")
    if candidate is not None and not isinstance(candidate, Path):
        raise pytest.UsageError("--solution must be a path")
    path = (
        candidate.resolve()
        if candidate is not None
        else ROOT / contract_task["reference"]
    )
    return load_solution(path)


@pytest.fixture
def implementation(solution_module: ModuleType, contract_task: Task) -> object:
    # A plugin boundary: each consuming test declares its task-specific contract.
    entrypoint: object = getattr(solution_module, contract_task["entrypoint"])
    return entrypoint


@pytest.fixture
def retry_delays(
    solution_module: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> list[float]:
    delays: list[float] = []

    async def sleep(delay: float) -> None:
        delays.append(delay)

    def uniform(low: float, high: float) -> float:
        return high

    # Also support ordinary "from asyncio/random import ..." aliases.
    for name, value in list(vars(solution_module).items()):
        if value is asyncio.sleep:
            monkeypatch.setattr(solution_module, name, sleep)
        elif value is random.uniform:
            monkeypatch.setattr(solution_module, name, uniform)
    monkeypatch.setattr(asyncio, "sleep", sleep)
    monkeypatch.setattr(random, "uniform", uniform)
    return delays
