"""Tests for ink consumption estimation."""

import pytest

from mcp_print.tools.ink import ink_consumption


class TestInkConsumption:
    def test_basic_offset(self) -> None:
        result = ink_consumption(210, 297, 40, "offset", 1000)
        assert result["ink_grams"] > 0
        assert abs(result["ink_kg"] - result["ink_grams"] / 1000) < 0.001
        assert result["cost_estimate_usd"] > 0

    def test_all_methods(self) -> None:
        for method in ("offset", "flexo", "gravure", "screen", "digital"):
            result = ink_consumption(100, 100, 50, method, 100)
            assert result["ink_grams"] > 0

    def test_zero_coverage(self) -> None:
        result = ink_consumption(210, 297, 0, "offset", 1000)
        assert result["ink_grams"] == 0
        assert result["cost_estimate_usd"] == 0

    def test_screen_uses_most_ink(self) -> None:
        screen = ink_consumption(100, 100, 100, "screen", 1)
        digital = ink_consumption(100, 100, 100, "digital", 1)
        assert screen["ink_grams"] > digital["ink_grams"]

    def test_invalid_method_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown print_method"):
            ink_consumption(100, 100, 50, "letterpress", 100)  # type: ignore[arg-type]

    def test_negative_width_raises(self) -> None:
        with pytest.raises(ValueError, match="width_mm must be positive"):
            ink_consumption(-1, 100, 50, "offset", 100)

    def test_zero_quantity_raises(self) -> None:
        with pytest.raises(ValueError, match="quantity must be positive"):
            ink_consumption(100, 100, 50, "offset", 0)
