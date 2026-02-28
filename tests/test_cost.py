"""Tests for print cost estimator."""

import pytest

from mcp_print.tools.cost import print_cost_estimate


class TestPrintCostEstimate:
    def test_basic_offset(self) -> None:
        result = print_cost_estimate(
            width_mm=210, height_mm=297, quantity=5000,
            num_colors=4, paper_gsm=120, print_method="offset",
        )
        assert result["total_cost_usd"] > 0
        assert result["cost_per_unit_usd"] > 0
        assert result["ink_cost_usd"] >= 0
        assert result["setup_cost_usd"] >= 0
        bd = result["breakdown"]
        assert bd["ink"] >= 0
        assert bd["plates"] >= 0
        assert bd["makeready"] >= 0
        assert bd["run_cost"] >= 0
        # Total should equal sum of breakdown
        assert abs(result["total_cost_usd"] - sum(bd.values())) < 0.02

    def test_digital_no_setup(self) -> None:
        result = print_cost_estimate(
            width_mm=210, height_mm=297, quantity=100,
            num_colors=4, paper_gsm=100, print_method="digital",
        )
        assert result["breakdown"]["plates"] == 0
        assert result["breakdown"]["makeready"] == 0

    def test_two_sides_costs_more(self) -> None:
        one = print_cost_estimate(
            width_mm=210, height_mm=297, quantity=1000,
            num_colors=4, paper_gsm=100, print_method="offset", sides=1,
        )
        two = print_cost_estimate(
            width_mm=210, height_mm=297, quantity=1000,
            num_colors=4, paper_gsm=100, print_method="offset", sides=2,
        )
        assert two["total_cost_usd"] > one["total_cost_usd"]

    def test_heavier_paper_costs_more(self) -> None:
        light = print_cost_estimate(
            width_mm=210, height_mm=297, quantity=1000,
            num_colors=4, paper_gsm=80, print_method="offset",
        )
        heavy = print_cost_estimate(
            width_mm=210, height_mm=297, quantity=1000,
            num_colors=4, paper_gsm=300, print_method="offset",
        )
        assert heavy["total_cost_usd"] > light["total_cost_usd"]

    def test_invalid_sides_raises(self) -> None:
        with pytest.raises(ValueError, match="sides must be 1 or 2"):
            print_cost_estimate(210, 297, 100, 4, 100, "offset", sides=3)

    def test_invalid_method_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown print_method"):
            print_cost_estimate(210, 297, 100, 4, 100, "letterpress")  # type: ignore[arg-type]

    def test_zero_quantity_raises(self) -> None:
        with pytest.raises(ValueError, match="quantity must be positive"):
            print_cost_estimate(210, 297, 0, 4, 100, "offset")
