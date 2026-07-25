"""Tests for full job quote."""

import pytest

from mcp_print.tools.quote import full_job_quote


class TestFullJobQuote:
    def test_basic_quote(self) -> None:
        result = full_job_quote(
            sheet_width_mm=700, sheet_height_mm=1000,
            piece_width_mm=210, piece_height_mm=297,
            quantity=10000, num_colors=4, paper_gsm=120,
            print_method="offset",
        )
        assert result["imposition"]["ups_per_sheet"] == 9
        assert result["cost"]["total_cost"] > 0
        assert result["cost_per_piece"] > 0
        assert "10000 pieces" in result["summary"]

    def test_costs_sheets_not_pieces(self) -> None:
        # Cost is per press sheet (incl. waste), so the costed quantity
        # must match sheets_with_waste, not the piece quantity.
        result = full_job_quote(
            sheet_width_mm=700, sheet_height_mm=1000,
            piece_width_mm=210, piece_height_mm=297,
            quantity=9000, num_colors=4, paper_gsm=100,
            print_method="offset", paper_price_per_sheet=0.5,
        )
        sheets = result["imposition"]["sheets_with_waste"]
        assert result["cost"]["paper_cost"] == round(0.5 * sheets, 2)

    def test_custom_currency_propagates(self) -> None:
        result = full_job_quote(
            sheet_width_mm=700, sheet_height_mm=1000,
            piece_width_mm=210, piece_height_mm=297,
            quantity=1000, num_colors=4, paper_gsm=100,
            print_method="offset", currency="TRY",
            ink_price_per_kg=400, plate_price=1200,
            makeready_price=3000, run_price_per_1000=350,
            paper_price_per_sheet=15,
        )
        assert result["currency"] == "TRY"
        assert result["cost"]["currency"] == "TRY"
        assert "TRY" in result["summary"]

    def test_invalid_piece_raises(self) -> None:
        with pytest.raises(ValueError, match="does not fit"):
            full_job_quote(
                sheet_width_mm=300, sheet_height_mm=300,
                piece_width_mm=500, piece_height_mm=500,
                quantity=100, num_colors=4, paper_gsm=100,
                print_method="offset",
            )
