import json
from importlib.metadata import version
from typing import Never, cast

import pytest

from python_backend_guidance.cli import SearchResult, main


@pytest.mark.parametrize(
    ("query", "expected_ids"),
    [
        ("bounded async concurrency", ["bound-concurrent-work"]),
        ("retry transient reads", ["retry-transient-reads"]),
        ("workflow deadline", ["apply-operation-deadline"]),
        ("xylophone", []),
    ],
    ids=["concurrency", "retries", "deadline", "no-match"],
)
def test_search_returns_json_results(
    query: str, expected_ids: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    result = main(["search", query, "--limit", "1"])

    captured = capsys.readouterr()
    assert result == 0
    assert captured.err == ""
    guides = cast(list[SearchResult], json.loads(captured.out))
    assert [guide["id"] for guide in guides] == expected_ids


def test_search_exposes_external_requirements_before_retrieval(
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = main(["search", "PostgreSQL lost updates", "--limit", "1"])

    matches = cast(list[SearchResult], json.loads(capsys.readouterr().out))
    assert result == 0
    assert matches[0]["libraries"] == {"psycopg": ">=3.2,<4"}
    assert matches[0]["services"] == ["PostgreSQL >=16"]


def test_retrieve_prints_the_guide_with_compatibility_metadata(
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = main(["retrieve", "bound-concurrent-work"])

    captured = capsys.readouterr()
    assert result == 0
    assert captured.err == ""
    assert "# Bound concurrent work" in captured.out
    assert 'python = ">=3.12"' in captured.out


def test_unknown_guide_fails_without_printing_unrelated_guidance(
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = main(["retrieve", "does-not-exist"])

    captured = capsys.readouterr()
    assert result == 1
    assert captured.out == ""
    assert "Guide not found: does-not-exist" in captured.err


def test_list_exposes_coverage_and_review_status(
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = main(["list"])

    guides = cast(list[SearchResult], json.loads(capsys.readouterr().out))
    assert result == 0
    assert len(guides) == 60
    assert [guide["id"] for guide in guides] == sorted(guide["id"] for guide in guides)
    assert {"bound-concurrent-work", "parameterize-sql", "verify-token-claims"} <= {
        guide["id"] for guide in guides
    }
    assert all(guide["status"] == "draft" for guide in guides)
    assert {guide["runtime"] for guide in guides} == {"any", "sync", "asyncio"}


@pytest.mark.parametrize(
    "constraints",
    [["--python", "3.11"], ["--runtime", "trio"]],
    ids=["older-project", "different-runtime"],
)
def test_search_does_not_offer_incompatible_guides(
    constraints: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    result = main(["search", "concurrency", *constraints])

    assert result == 0
    assert json.loads(capsys.readouterr().out) == []


def test_retrieve_refuses_an_explicitly_incompatible_project(
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = main(["retrieve", "bound-concurrent-work", "--python", "3.11"])

    captured = capsys.readouterr()
    assert result == 1
    assert captured.out == ""
    assert "Incompatible guide" in captured.err


def test_catalog_errors_have_no_traceback_or_partial_output(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from python_backend_guidance.guide import GuideError

    def invalid_catalog() -> Never:
        raise GuideError("broken.md: missing closing +++ delimiter")

    monkeypatch.setattr("python_backend_guidance.cli.load_guides", invalid_catalog)

    result = main(["list"])

    captured = capsys.readouterr()
    assert result == 1
    assert captured.out == ""
    assert "broken.md" in captured.err
    assert "Traceback" not in captured.err


@pytest.mark.parametrize(
    "arguments",
    [
        ["search", "   "],
        ["search", "concurrency", "--limit", "0"],
        ["retrieve"],
        ["list", "--python", "latest"],
    ],
    ids=["blank-query", "nonpositive-limit", "missing-id", "ambiguous-project-python"],
)
def test_invalid_arguments_return_usage_error(
    arguments: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit) as raised:
        _ = main(arguments)

    captured = capsys.readouterr()
    assert raised.value.code == 2
    assert captured.out == ""
    assert "error:" in captured.err


def test_version_matches_the_installed_distribution(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as raised:
        _ = main(["--version"])

    assert raised.value.code == 0
    assert capsys.readouterr().out.strip() == version("python-backend-guidance")
