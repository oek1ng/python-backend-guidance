"""Typed formats for the versioned, repository-owned evaluation data."""

import tomllib
from pathlib import Path
from typing import Literal, NotRequired, TypedDict, cast

type Split = Literal["development", "validation"]
type Outcome = Literal["passed", "failed", "error", "skipped"]


class Defect(TypedDict):
    solution: str
    must_fail: str
    related_failures: NotRequired[list[str]]


class Task(TypedDict):
    reference: str
    entrypoint: str
    tests: str
    prompt: str
    alternatives: NotRequired[list[str]]
    defects: list[Defect]


class Registry(TypedDict):
    schema_version: Literal[1]
    tasks: dict[str, Task]


class Query(TypedDict):
    split: Split
    query: str
    expected: list[str]


class Dataset(TypedDict):
    schema_version: Literal[1]
    queries: list[Query]


class RankedResult(TypedDict):
    expected: list[str]
    actual: list[str]
    rank: int | None


class RankedQuery(Query, RankedResult):
    pass


class GateMetrics(TypedDict):
    top1: float
    unsupported_false_positive_rate: float


class Metrics(GateMetrics):
    supported_queries: int
    unsupported_queries: int
    hit_at_3: float
    mrr: float


class SeedTargets(TypedDict):
    minimum_top1: float
    maximum_unsupported_false_positive_rate: float
    met: bool


class SearchReport(TypedDict):
    report_schema: Literal[1]
    kind: Literal["seed-retrieval-benchmark"]
    split: Split
    dataset_sha256: str
    guide_sha256: dict[str, str]
    catalog_size: int
    metrics: Metrics
    queries: list[RankedQuery]
    seed_targets: NotRequired[SeedTargets]


class Check(TypedDict):
    name: str
    outcome: Outcome


class Provenance(TypedDict):
    report_schema: Literal[1]
    task: str
    solution: str
    solution_sha256: str
    guide_sha256: str
    contract_sha256: str
    checks_sha256: str
    fixtures_sha256: str
    fixture_files_sha256: dict[str, str]
    dependency_versions: dict[str, str]
    package_version: str
    python: str
    platform: str
    pytest: str
    pytest_asyncio: str
    selected_check: str | None
    timeout_seconds: int


class GradeReport(Provenance):
    status: Literal["passed", "failed", "timeout", "infrastructure-error"]
    checks: list[Check]
    summary: dict[Outcome, int]
    exit_code: NotRequired[int]
    log: NotRequired[str]


class DefectResult(TypedDict):
    detected: bool
    result: GradeReport


class CalibrationTask(TypedDict):
    task: str
    passed: bool
    reference: GradeReport
    alternatives: list[GradeReport]
    defects: list[DefectResult]


class CalibrationReport(TypedDict):
    report_schema: Literal[1]
    kind: Literal["calibration"]
    passed: bool
    tasks: list[CalibrationTask]


def read_registry(path: Path) -> Registry:
    # This is a trusted checked-in schema-1 fixture, not candidate-provided input.
    # tests/test_guides.py checks its fields, files and complete catalog coverage.
    return cast(Registry, tomllib.loads(path.read_text(encoding="utf-8")))


def read_dataset(path: Path) -> Dataset:
    # The repository-owned schema-1 corpus is checked by test_search_benchmark.py.
    return cast(Dataset, tomllib.loads(path.read_text(encoding="utf-8")))
