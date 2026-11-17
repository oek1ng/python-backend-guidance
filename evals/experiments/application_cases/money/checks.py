"""Exploratory invoice behavior checks, separate from agent authoring."""

import importlib.util
import os
import sys
import unittest
from collections.abc import Callable
from decimal import Decimal, Inexact, localcontext
from pathlib import Path
from typing import cast


def solution() -> Callable[[list[tuple[str, int]]], Decimal]:
    path = Path(os.environ["PBG_CANDIDATE"])
    spec = importlib.util.spec_from_file_location("app_candidate", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return cast(Callable[[list[tuple[str, int]]], Decimal], module.invoice_total)


class InvoiceChecks(unittest.TestCase):
    def test_rounds_units_before_multiplying(self) -> None:
        self.assertEqual(solution()([("2.675", 2), ("2.685", 1)]), Decimal("8.04"))

    def test_rejects_amount_just_above_limit_before_rounding(self) -> None:
        with self.assertRaises(ValueError):
            _ = solution()([("1000000000.0000000000000000001", 1)])

    def test_extreme_exponent_is_invalid_input(self) -> None:
        with self.assertRaises(ValueError):
            _ = solution()([("1e9999999", 1)])

    def test_ambient_decimal_context_does_not_change_policy(self) -> None:
        with localcontext() as context:
            context.traps[Inexact] = True
            self.assertEqual(solution()([("2.675", 1)]), Decimal("2.68"))

    def test_boolean_and_zero_quantity_are_invalid(self) -> None:
        for quantity in (True, 0):
            with self.subTest(quantity=quantity), self.assertRaises(ValueError):
                _ = solution()([("1.00", quantity)])

    def test_empty_invoice_is_zero(self) -> None:
        self.assertEqual(solution()([]), Decimal("0.00"))


if __name__ == "__main__":
    _ = unittest.main(verbosity=2)
