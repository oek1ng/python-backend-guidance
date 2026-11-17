from pathlib import Path

import pytest

from evals.models import GateMetrics, RankedResult, read_dataset
from evals.search import meets_seed_targets, summarize
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
