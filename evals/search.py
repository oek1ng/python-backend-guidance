"""Measure retrieval on a small, hand-authored seed corpus without a model."""

import argparse
import hashlib
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from evals.models import (
    GateMetrics,
    Metrics,
    RankedQuery,
    RankedResult,
    SearchReport,
    Split,
    read_dataset,
)
from python_backend_guidance.catalog import load_guides, search_guides

DATASET = Path(__file__).with_name("search") / "queries.toml"
TOP1_TARGET = 0.9
FALSE_POSITIVE_TARGET = 0.1


def meets_seed_targets(metrics: GateMetrics) -> bool:
    return (
        metrics["top1"] >= TOP1_TARGET
        and metrics["unsupported_false_positive_rate"] <= FALSE_POSITIVE_TARGET
    )


def summarize(rows: Sequence[RankedResult]) -> Metrics:
    positives = [row for row in rows if len(row["expected"]) != 0]
    negatives = [row for row in rows if len(row["expected"]) == 0]
    if len(positives) == 0 or len(negatives) == 0:
        raise ValueError("A benchmark split needs supported and unsupported queries")
    return {
        "supported_queries": len(positives),
        "unsupported_queries": len(negatives),
        "top1": sum(row["rank"] == 1 for row in positives) / len(positives),
        "hit_at_3": sum(
            row["rank"] is not None and row["rank"] <= 3 for row in positives
        )
        / len(positives),
        "mrr": sum(
            1 / row["rank"] if row["rank"] is not None else 0 for row in positives
        )
        / len(positives),
        "unsupported_false_positive_rate": sum(bool(row["actual"]) for row in negatives)
        / len(negatives),
    }


def evaluate(split: Split) -> SearchReport:
    guides = load_guides()
    dataset = read_dataset(DATASET)
    rows: list[RankedQuery] = []
    for item in dataset["queries"]:
        if item["split"] != split:
            continue
        actual = [guide.id for guide in search_guides(item["query"], guides)]
        expected = item["expected"]
        rank = next(
            (index for index, guide in enumerate(actual, 1) if guide in expected),
            None,
        )
        rows.append(
            {
                "query": item["query"],
                "split": item["split"],
                "expected": expected,
                "actual": actual,
                "rank": rank,
            }
        )
    return {
        "report_schema": 1,
        "kind": "seed-retrieval-benchmark",
        "split": split,
        "dataset_sha256": hashlib.sha256(DATASET.read_bytes()).hexdigest(),
        "guide_sha256": {
            guide.id: hashlib.sha256(guide.content.encode()).hexdigest()
            for guide in guides
        },
        "catalog_size": len(guides),
        "metrics": summarize(rows),
        "queries": rows,
    }


class Arguments(argparse.Namespace):
    split: Split = "validation"
    output: Path | None = None
    check: bool = False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    _ = parser.add_argument(
        "--split", choices=["development", "validation"], default="validation"
    )
    _ = parser.add_argument("--output", type=Path)
    _ = parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if the seed regression targets are missed",
    )
    args = parser.parse_args(argv, namespace=Arguments())
    try:
        report = evaluate(args.split)
        report["seed_targets"] = {
            "minimum_top1": TOP1_TARGET,
            "maximum_unsupported_false_positive_rate": FALSE_POSITIVE_TARGET,
            "met": meets_seed_targets(report["metrics"]),
        }
        text = json.dumps(report, indent=2) + "\n"
        if args.output is not None:
            with args.output.open("x", encoding="utf-8") as output:
                _ = output.write(text)
            print(f"Report: {args.output}", file=sys.stderr)
            print(
                f"Top-1: {report['metrics']['top1']:.1%}; unsupported false positives: "
                f"{report['metrics']['unsupported_false_positive_rate']:.1%}",
                file=sys.stderr,
            )
        else:
            print(text, end="")
        return 1 if args.check and not report["seed_targets"]["met"] else 0
    except (OSError, ValueError) as error:
        print(f"Retrieval benchmark error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
