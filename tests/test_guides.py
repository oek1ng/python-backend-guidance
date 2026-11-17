import ast
from pathlib import Path

import pytest

from evals.models import read_registry
from python_backend_guidance.catalog import load_guides
from python_backend_guidance.guide import Guide

ROOT = Path(__file__).resolve().parents[1]


def test_catalog_contains_unique_guide_identifiers() -> None:
    guides = load_guides()

    assert len(guides) != 0
    assert len({guide.id for guide in guides}) == len(guides)


def test_every_guide_has_a_registered_public_contract_and_calibration_defect() -> None:
    registry = read_registry(ROOT / "evals/tasks.toml")
    guides = {guide.id: guide for guide in load_guides()}

    assert registry["schema_version"] == 1
    assert set(registry["tasks"]) == set(guides)
    for task_id, task in registry["tasks"].items():
        assert task["reference"] == guides[task_id].example
        assert task["entrypoint"] != ""
        assert (ROOT / task["tests"]).is_file()
        assert (ROOT / task["prompt"]).is_file()
        assert len(task["defects"]) != 0
        for defect in task["defects"]:
            assert (ROOT / defect["solution"]).is_file()
            assert defect["must_fail"] != ""


@pytest.mark.parametrize(
    "guide", load_guides(), ids=[guide.id for guide in load_guides()]
)
def test_each_guide_has_the_required_editorial_sections_and_sources(
    guide: Guide,
) -> None:
    for section in (
        "When to use",
        "Rules",
        "Reference example",
        "Guarantees and assumptions",
        "Pitfalls",
        "Verification",
        "Sources",
    ):
        assert f"## {section}" in guide.content
    for source in guide.sources:
        assert source.url in guide.content.split("## Sources", 1)[1]


@pytest.mark.parametrize(
    "guide", load_guides(), ids=[guide.id for guide in load_guides()]
)
def test_reference_example_in_guide_matches_the_executable_file(guide: Guide) -> None:
    snippet = guide.content.split("```python\n", 1)[1].split("\n```", 1)[0]
    example = (ROOT / guide.example).read_text(encoding="utf-8")

    assert guide.minimum_python >= (3, 12)
    assert snippet.rstrip() == example.rstrip()


@pytest.mark.parametrize(
    "guide", load_guides(), ids=[guide.id for guide in load_guides()]
)
def test_reference_example_names_its_architectural_role(guide: Guide) -> None:
    example = (ROOT / guide.example).read_text(encoding="utf-8")
    role = ast.get_docstring(ast.parse(example))

    assert role is not None
    assert role.startswith(
        (
            "Domain policy:",
            "Input boundary:",
            "Application boundary:",
            "Application policy:",
            "Application workflow:",
            "Authentication adapter:",
            "HTTP adapter:",
            "Message adapter:",
            "Persistence adapter:",
            "File adapter:",
            "Process adapter:",
            "Observability adapter:",
            "Observability boundary:",
            "Composition root:",
        )
    )


@pytest.mark.parametrize(
    "guide", load_guides(), ids=[guide.id for guide in load_guides()]
)
def test_reference_example_does_not_nest_functions(guide: Guide) -> None:
    example = (ROOT / guide.example).read_text(encoding="utf-8")
    tree = ast.parse(example)

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            assert not any(
                isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
                for child in ast.walk(node)
                if child is not node
            ), f"{guide.example}:{node.lineno}"
