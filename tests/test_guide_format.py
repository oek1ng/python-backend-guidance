from datetime import date

import pytest

from python_backend_guidance.guide import GuideError, parse_guide

VALID = """+++
schema_version = 1
id = "example-guide"
title = "Example guide"
description = "A concrete behavior."
python = ">=3.12"
runtime = "asyncio"
tags = ["concurrency"]
status = "draft"
example = "examples/example_guide.py"

[[sources]]
url = "https://docs.python.org/3.12/library/asyncio-task.html"
checked = 2026-11-16
+++

# Example guide
"""


def test_valid_metadata_keeps_requirements_and_source_provenance() -> None:
    guide = parse_guide(VALID, filename="example-guide.md")

    assert guide.minimum_python == (3, 12)
    assert guide.runtime == "asyncio"
    assert guide.status == "draft"
    assert guide.example == "examples/example_guide.py"
    assert guide.sources[0].checked == date(2026, 11, 16)
    assert guide.content == VALID


@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        ("schema_version = 1", "schema_version = 2", "schema_version"),
        ("schema_version = 1", "schema_version = true", "schema_version"),
        ('title = "Example guide"', 'title = ""', "title"),
        ('id = "example-guide"', 'id = "Other Guide"', "id"),
        ('id = "example-guide"', 'id = "different-guide"', "filename"),
        ('python = ">=3.12"', 'python = ">=3.11"', "Python 3.12"),
        ('python = ">=3.12"', 'python = "latest"', "python"),
        ('tags = ["concurrency"]', 'tags = "concurrency"', "tags"),
        ('tags = ["concurrency"]', "tags = [1]", "tags"),
        ('status = "draft"', 'status = "verified"', "status"),
        ('status = "draft"', 'status = "reviewed"', "reviewed_by"),
        ('runtime = "asyncio"', 'runtime = ""', "runtime"),
        ("examples/example_guide.py", "../example.py", "example"),
        ("examples/example_guide.py", "examples/../example.py", "example"),
        ("checked = 2026-11-16", 'checked = "2026-11-16"', "checked"),
        ("https://docs.python.org", "file:///etc", "url"),
        ("https://docs.python.org", "https://user:secret@docs.python.org", "url"),
        ("[[sources]]", "[sources]", "sources"),
        ('tags = ["concurrency"]', 'tags = ["concurrency"]\naliases = [""]', "aliases"),
    ],
    ids=[
        "unknown-schema",
        "boolean-schema",
        "blank-title",
        "invalid-id",
        "mismatched-id",
        "unsupported-python-floor",
        "ambiguous-python",
        "tags-not-array",
        "tags-not-strings",
        "unknown-status",
        "unattributed-review",
        "blank-runtime",
        "example-outside-directory",
        "example-traversal",
        "date-not-a-date",
        "non-web-source",
        "source-credentials",
        "sources-not-an-array",
        "empty-alias",
    ],
)
def test_invalid_metadata_has_an_actionable_error(
    old: str, new: str, message: str
) -> None:
    with pytest.raises(GuideError, match=message):
        _ = parse_guide(VALID.replace(old, new), filename="example-guide.md")


def test_unterminated_front_matter_is_rejected() -> None:
    with pytest.raises(GuideError, match="closing"):
        _ = parse_guide(VALID.replace("\n+++\n", "\n"), filename="example-guide.md")


def test_invalid_toml_is_reported_with_its_filename() -> None:
    with pytest.raises(GuideError, match="example-guide.md: invalid TOML"):
        _ = parse_guide(
            VALID.replace("schema_version = 1", "schema_version = ["),
            filename="example-guide.md",
        )


def test_review_status_requires_a_named_and_dated_review() -> None:
    content = VALID.replace(
        'status = "draft"',
        'status = "reviewed"\nreviewed_by = "External reviewer"\n'
        "reviewed_on = 2026-11-16",
    )

    guide = parse_guide(content, filename="example-guide.md")

    assert guide.status == "reviewed"


def test_named_review_without_a_date_is_rejected() -> None:
    content = VALID.replace(
        'status = "draft"', 'status = "reviewed"\nreviewed_by = "Reviewer"'
    )

    with pytest.raises(GuideError, match="reviewed_on"):
        _ = parse_guide(content, filename="example-guide.md")


def test_library_and_service_requirements_are_preserved_without_installing_them() -> (
    None
):
    content = VALID.replace(
        "\n[[sources]]",
        '\nservices = ["PostgreSQL >=16"]\n'
        '[libraries]\nhttpx = ">=0.28"\n\n[[sources]]',
    )

    guide = parse_guide(content, filename="example-guide.md")

    assert guide.libraries == (("httpx", ">=0.28"),)
    assert guide.services == ("PostgreSQL >=16",)


def test_search_aliases_are_preserved_as_explicit_metadata() -> None:
    content = VALID.replace(
        "\n[[sources]]", '\naliases = ["parallel tasks"]\n\n[[sources]]'
    )

    guide = parse_guide(content, filename="example-guide.md")

    assert guide.aliases == ("parallel tasks",)


@pytest.mark.parametrize(
    ("python_version", "runtime", "compatible"),
    [
        ((3, 12), "asyncio", True),
        ((3, 11), "asyncio", False),
        ((3, 14), "trio", False),
        ((3, 14), None, True),
    ],
    ids=["supported", "too-old", "wrong-runtime", "runtime-unspecified"],
)
def test_compatibility_uses_explicit_project_constraints(
    python_version: tuple[int, int], runtime: str | None, compatible: bool
) -> None:
    guide = parse_guide(VALID, filename="example-guide.md")

    assert guide.applies_to(python_version, runtime) is compatible


def test_runtime_independent_guidance_applies_to_other_runtimes() -> None:
    guide = parse_guide(
        VALID.replace('runtime = "asyncio"', 'runtime = "any"'),
        filename="example-guide.md",
    )

    assert guide.applies_to((3, 12), "trio")


def test_a_newer_api_guide_does_not_raise_the_whole_catalogs_python_floor() -> None:
    guide = parse_guide(
        VALID.replace('python = ">=3.12"', 'python = ">=3.13"'),
        filename="example-guide.md",
    )

    assert not guide.applies_to((3, 12), "asyncio")
    assert guide.applies_to((3, 13), "asyncio")
