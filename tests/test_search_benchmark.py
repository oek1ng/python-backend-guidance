import hashlib
from pathlib import Path

import pytest

from evals.models import GateMetrics, RankedResult, read_dataset
from evals.search import evaluate, main, meets_seed_targets, summarize
from python_backend_guidance.catalog import load_guides

ROOT = Path(__file__).resolve().parents[1]


def test_metrics_distinguish_ranking_from_unsupported_topic_refusals() -> None:
    rows: list[RankedResult] = [
        {"expected": ["a"], "actual": ["a"], "rank": 1},
        {"expected": ["b"], "actual": ["a", "b"], "rank": 2},
        {"expected": [], "actual": ["a"], "rank": None},
        {"expected": [], "actual": [], "rank": None},
    ]

    assert summarize(rows) == {
        "supported_queries": 2,
        "unsupported_queries": 2,
        "top1": 0.5,
        "hit_at_3": 1.0,
        "mrr": 0.75,
        "unsupported_false_positive_rate": 0.5,
    }


def test_a_split_without_negative_queries_cannot_claim_refusal_quality() -> None:
    with pytest.raises(ValueError, match="supported and unsupported"):
        _ = summarize([{"expected": ["a"], "actual": ["a"], "rank": 1}])


@pytest.mark.parametrize(
    ("top1", "false_positives", "passes"),
    [(0.9, 0.1, True), (0.89, 0, False), (1, 0.11, False)],
    ids=["exact-boundaries", "ranking-regression", "refusal-regression"],
)
def test_seed_gate_requires_both_ranking_and_refusal_quality(
    top1: float, false_positives: float, passes: bool
) -> None:
    metrics: GateMetrics = {
        "top1": top1,
        "unsupported_false_positive_rate": false_positives,
    }

    assert meets_seed_targets(metrics) is passes


def test_seed_queries_have_valid_labels_and_no_cross_split_duplicates() -> None:
    dataset = read_dataset(ROOT / "evals/search/queries.toml")
    ids = {guide.id for guide in load_guides()}
    queries = dataset["queries"]

    assert dataset["schema_version"] == 1
    assert len({row["query"].casefold() for row in queries}) == len(queries)
    assert {row["split"] for row in queries} == {"development", "validation"}
    for split in ("development", "validation"):
        assert any(
            len(row["expected"]) != 0 for row in queries if row["split"] == split
        )
        assert any(
            len(row["expected"]) == 0 for row in queries if row["split"] == split
        )
        covered = set().union(
            *(set(row["expected"]) for row in queries if row["split"] == split)
        )
        assert covered == ids
    assert set().union(*(set(row["expected"]) for row in queries)) == ids


def test_retrieval_report_identifies_the_ranking_implementation() -> None:
    report = evaluate("validation")

    assert (
        report["search_sha256"]
        == hashlib.sha256((ROOT / "evals/search.py").read_bytes()).hexdigest()
    )
    assert (
        report["catalog_sha256"]
        == hashlib.sha256(
            (ROOT / "src/python_backend_guidance/catalog.py").read_bytes()
        ).hexdigest()
    )
    assert (
        report["models_sha256"]
        == hashlib.sha256((ROOT / "evals/models.py").read_bytes()).hexdigest()
    )
    assert (
        report["lock_sha256"]
        == hashlib.sha256((ROOT / "uv.lock").read_bytes()).hexdigest()
    )


def test_external_query_corpus_is_measured_separately(tmp_path: Path) -> None:
    corpus = tmp_path / "reviewed-queries.toml"
    _ = corpus.write_text(
        "schema_version = 1\n"
        '[[queries]]\nsplit = "validation"\n'
        'query = "bounded async concurrency"\n'
        'expected = ["bound-concurrent-work"]\n'
        '[[queries]]\nsplit = "validation"\n'
        'query = "xylophone tuning"\nexpected = []\n',
        encoding="utf-8",
    )

    report = evaluate("validation", dataset_path=corpus)

    assert report["metrics"]["supported_queries"] == 1
    assert report["metrics"]["unsupported_queries"] == 1
    assert report["kind"] == "external-retrieval-benchmark"
    assert report["dataset_sha256"] == hashlib.sha256(corpus.read_bytes()).hexdigest()
    assert "seed_targets" not in report


def test_external_dataset_rejects_unknown_labels(tmp_path: Path) -> None:
    corpus = tmp_path / "bad-queries.toml"
    _ = corpus.write_text(
        "schema_version = 1\n"
        '[[queries]]\nsplit = "validation"\n'
        'query = "unknown thing"\nexpected = ["missing-guide"]\n',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Unknown guide label"):
        _ = evaluate("validation", dataset_path=corpus)


def test_seed_gate_is_not_applied_to_external_corpora(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    corpus = tmp_path / "queries.toml"

    with pytest.raises(SystemExit) as raised:
        _ = main(["--dataset", str(corpus), "--check"])

    assert raised.value.code == 2
    assert "bundled seed" in capsys.readouterr().err


def test_challenge_corpus_keeps_near_misses_separate_from_the_seed() -> None:
    corpus = ROOT / "evals/search/challenge.toml"

    report = evaluate("validation", dataset_path=corpus)

    assert report["metrics"]["supported_queries"] == 6
    assert report["metrics"]["unsupported_queries"] == 20
    assert "seed_targets" not in report
