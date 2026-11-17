"""Exploratory tax-table behavior checks; no tax guide is supplied."""

import importlib.util
import os
import sys
import unittest
from collections.abc import Mapping
from pathlib import Path
from typing import Protocol, cast


class ChooseRate(Protocol):
    def __call__(
        self,
        destination: str,
        category: str,
        matrix: Mapping[str, Mapping[str, int]],
        *,
        exempt: bool = False,
    ) -> int: ...


def solution() -> ChooseRate:
    path = Path(os.environ["PBG_CANDIDATE"])
    spec = importlib.util.spec_from_file_location("app_candidate", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return cast(ChooseRate, getattr(module, "choose_rate"))


class TaxChecks(unittest.TestCase):
    matrix: Mapping[str, Mapping[str, int]] = {
        "home": {"books": 800, "food": 500},
        "export": {"books": 0, "food": 1200},
    }

    def test_selects_exact_destination_and_category(self) -> None:
        self.assertEqual(solution()("home", "food", self.matrix), 500)
        self.assertEqual(solution()("export", "food", self.matrix), 1200)

    def test_unknown_pair_is_not_replaced_with_home_rate(self) -> None:
        with self.assertRaises(LookupError):
            _ = solution()("missing", "books", self.matrix)
        with self.assertRaises(LookupError):
            _ = solution()("home", "missing", self.matrix)

    def test_exemption_still_checks_pair(self) -> None:
        self.assertEqual(solution()("export", "food", self.matrix, exempt=True), 0)
        with self.assertRaises(LookupError):
            _ = solution()("missing", "food", self.matrix, exempt=True)

    def test_invalid_configured_rate_is_rejected(self) -> None:
        for rate in (True, -1, 10001):
            with self.subTest(rate=rate), self.assertRaises(ValueError):
                _ = solution()(
                    "export",
                    "food",
                    {"home": {"food": rate}, "export": {"food": rate}},
                )


if __name__ == "__main__":
    _ = unittest.main(verbosity=2)
