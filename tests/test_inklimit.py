"""Tests for total ink coverage checking and GCR reduction."""

import pytest

from mcp_print.tools.inklimit import ink_limit_check


class TestInkLimitCheck:
    def test_within_limit_unchanged(self) -> None:
        result = ink_limit_check(50, 40, 30, 20)
        assert result["within_limit"] is True
        assert result["gcr_applied"] == 0.0
        assert result["adjusted"] == result["original"]

    def test_over_limit_reduced(self) -> None:
        result = ink_limit_check(90, 85, 80, 70, print_condition="newsprint")
        assert result["original_tac"] == 325.0
        assert result["adjusted_tac"] <= 240.1
        assert result["within_limit"] is True

    def test_gcr_moves_gray_to_k(self) -> None:
        result = ink_limit_check(95, 90, 85, 50, tac_limit=300)
        assert result["adjusted"]["k"] > 50
        assert result["adjusted"]["c"] < 95
        assert result["gcr_applied"] > 0

    def test_explicit_limit_overrides_condition(self) -> None:
        result = ink_limit_check(80, 80, 80, 80, tac_limit=350, print_condition="newsprint")
        assert result["tac_limit"] == 350

    def test_adjusted_tac_never_above_limit(self) -> None:
        for cmyk in [(100, 100, 100, 100), (90, 90, 90, 0), (100, 50, 100, 90)]:
            result = ink_limit_check(*cmyk, tac_limit=280)
            assert result["adjusted_tac"] <= 280.1

    def test_unknown_condition_raises(self) -> None:
        with pytest.raises(ValueError, match="print_condition"):
            ink_limit_check(50, 50, 50, 50, print_condition="parchment")

    def test_invalid_limit_raises(self) -> None:
        with pytest.raises(ValueError, match="tac_limit"):
            ink_limit_check(50, 50, 50, 50, tac_limit=50)

    def test_out_of_range_raises(self) -> None:
        with pytest.raises(ValueError, match="between 0 and 100"):
            ink_limit_check(150, 50, 50, 50)
