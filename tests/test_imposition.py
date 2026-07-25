"""Tests for sheet imposition calculation."""

import pytest

from mcp_print.tools.imposition import imposition_calculator


class TestImpositionCalculator:
    def test_a4_flyers_on_70x100(self) -> None:
        result = imposition_calculator(
            sheet_width_mm=700, sheet_height_mm=1000,
            piece_width_mm=210, piece_height_mm=297,
            quantity=10000,
        )
        assert result["ups_per_sheet"] == 9
        assert result["sheets_needed"] == 1112
        assert result["sheets_with_waste"] >= result["sheets_needed"]

    def test_business_cards(self) -> None:
        result = imposition_calculator(
            sheet_width_mm=450, sheet_height_mm=320,
            piece_width_mm=85, piece_height_mm=55,
            quantity=1000,
        )
        assert result["ups_per_sheet"] >= 20
        assert result["sheets_needed"] == -(-1000 // result["ups_per_sheet"])

    def test_rotation_picked_when_better(self) -> None:
        # A tall narrow piece on a wide sheet should rotate for more ups.
        result = imposition_calculator(
            sheet_width_mm=1000, sheet_height_mm=210,
            piece_width_mm=100, piece_height_mm=900,
            quantity=10,
            bleed_mm=0, gripper_margin_mm=0, gap_mm=0,
        )
        assert result["orientation"] == "rotated"
        assert result["ups_per_sheet"] == 2

    def test_bleed_and_gap_reduce_ups(self) -> None:
        loose = imposition_calculator(
            700, 1000, 210, 297, 100, bleed_mm=0, gap_mm=0, gripper_margin_mm=0,
        )
        tight = imposition_calculator(
            700, 1000, 210, 297, 100, bleed_mm=5, gap_mm=10, gripper_margin_mm=15,
        )
        assert tight["ups_per_sheet"] <= loose["ups_per_sheet"]

    def test_utilization_range(self) -> None:
        result = imposition_calculator(700, 1000, 210, 297, 100)
        assert 0 < result["sheet_utilization_percent"] <= 100

    def test_waste_percent_zero(self) -> None:
        result = imposition_calculator(700, 1000, 210, 297, 100, waste_percent=0)
        assert result["sheets_with_waste"] == result["sheets_needed"]

    def test_piece_too_big_raises(self) -> None:
        with pytest.raises(ValueError, match="does not fit"):
            imposition_calculator(200, 200, 500, 500, 10)

    def test_negative_dimension_raises(self) -> None:
        with pytest.raises(ValueError, match="must be positive"):
            imposition_calculator(-700, 1000, 210, 297, 100)

    def test_zero_quantity_raises(self) -> None:
        with pytest.raises(ValueError, match="quantity"):
            imposition_calculator(700, 1000, 210, 297, 0)

    def test_invalid_waste_raises(self) -> None:
        with pytest.raises(ValueError, match="waste_percent"):
            imposition_calculator(700, 1000, 210, 297, 100, waste_percent=150)
