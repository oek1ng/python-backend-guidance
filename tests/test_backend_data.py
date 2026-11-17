from collections.abc import AsyncGenerator, Mapping
from datetime import UTC, datetime
from decimal import Decimal, Inexact, localcontext

import pytest

from tests.contracts import (
    CollectBody,
    DecodeEvent,
    Money,
    ParseInstant,
    ParseOrder,
    PatchProfile,
)


@pytest.mark.contract("version-message-payloads")
class TestMessageVersions:
    def test_unknown_message_version_is_rejected(
        self, implementation: DecodeEvent
    ) -> None:
        with pytest.raises(ValueError):
            _ = implementation({"version": 3, "user_id": "a"})

    def test_old_and_new_envelopes_normalize_identically(
        self, implementation: DecodeEvent
    ) -> None:
        assert implementation({"version": 1, "user_id": "a", "extra": True}) == {
            "user_id": "a"
        }
        assert implementation({"version": 2, "subject": {"id": "a"}}) == {
            "user_id": "a"
        }

    @pytest.mark.parametrize(
        "event",
        [
            {"version": True, "user_id": "a"},
            {"version": 2, "subject": None},
            {"version": 1, "user_id": ""},
        ],
        ids=["boolean-version", "malformed-subject", "empty-identity"],
    )
    def test_invalid_versioned_shape_is_rejected(
        self, implementation: DecodeEvent, event: Mapping[str, object]
    ) -> None:
        with pytest.raises(ValueError):
            _ = implementation(event)


@pytest.mark.contract("validate-boundary-data")
class TestBoundaryValidation:
    def test_boolean_is_not_an_order_quantity(self, implementation: ParseOrder) -> None:
        with pytest.raises(ValueError):
            _ = implementation({"sku": "book", "quantity": True})

    def test_valid_order_is_normalized(self, implementation: ParseOrder) -> None:
        assert implementation({"sku": "book", "quantity": 2}) == {
            "sku": "book",
            "quantity": 2,
        }

    def test_unknown_fields_are_rejected_by_this_contract(
        self, implementation: ParseOrder
    ) -> None:
        with pytest.raises(ValueError):
            _ = implementation({"sku": "book", "quantity": 2, "admin": True})


@pytest.mark.contract("bound-incoming-bodies")
class TestRequestLimits:
    async def test_chunked_request_cannot_bypass_limit(
        self, implementation: CollectBody
    ) -> None:
        async def chunks() -> AsyncGenerator[bytes, None]:
            yield b"abc"
            yield b"def"

        with pytest.raises(ValueError):
            await implementation(chunks(), limit=5)

    async def test_exact_body_limit_is_accepted(
        self, implementation: CollectBody
    ) -> None:
        async def chunks() -> AsyncGenerator[bytes, None]:
            yield b"abc"

        assert await implementation(chunks(), limit=3) == b"abc"


@pytest.mark.contract("distinguish-patch-null")
class TestPatchSemantics:
    def test_explicit_null_clears_a_field(self, implementation: PatchProfile) -> None:
        assert implementation({"nickname": "old"}, {"nickname": None}) == {
            "nickname": None
        }

    def test_absent_field_preserves_current_value(
        self, implementation: PatchProfile
    ) -> None:
        original = {"nickname": "old"}

        assert implementation(original, {}) == original
        assert original == {"nickname": "old"}


@pytest.mark.contract("use-aware-timestamps")
class TestInstants:
    def test_naive_timestamp_is_rejected(self, implementation: ParseInstant) -> None:
        with pytest.raises(ValueError):
            _ = implementation("2024-01-01T10:00:00")

    def test_offset_is_converted_to_utc(self, implementation: ParseInstant) -> None:
        assert implementation("2024-01-01T10:00:00+02:00") == datetime(
            2024, 1, 1, 8, tzinfo=UTC
        )


@pytest.mark.contract("quantize-money")
class TestMoney:
    def test_decimal_rounding_is_explicit(self, implementation: Money) -> None:
        assert implementation("2.675") == Decimal("2.68")
        assert implementation("2.685") == Decimal("2.68")

    @pytest.mark.parametrize("value", [0.1, "NaN", "Infinity", "1e100"])
    def test_unsupported_money_inputs_are_rejected(
        self, implementation: Money, value: object
    ) -> None:
        with pytest.raises(ValueError):
            _ = implementation(value)

    def test_amount_just_above_limit_is_rejected_before_rounding(
        self, implementation: Money
    ) -> None:
        with pytest.raises(ValueError):
            _ = implementation("1000000000.0000000000000000001")

    def test_extreme_exponent_is_reported_as_invalid_input(
        self, implementation: Money
    ) -> None:
        with pytest.raises(ValueError):
            _ = implementation("1e9999999")

    def test_rounding_does_not_inherit_ambient_decimal_traps(
        self, implementation: Money
    ) -> None:
        with localcontext() as context:
            context.traps[Inexact] = True

            assert implementation("2.675") == Decimal("2.68")
