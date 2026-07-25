"""Tests for booklet signature and spine calculation."""

import pytest

from mcp_print.tools.booklet import booklet_calculator


class TestBookletCalculator:
    def test_exact_signature_fit(self) -> None:
        result = booklet_calculator(page_count=32, paper_gsm=90)
        assert result["total_pages"] == 32
        assert result["pages_added_for_signature"] == 0
        assert result["signatures"] == 2
        assert result["total_sheets"] == 8

    def test_page_rounding_to_multiple_of_four(self) -> None:
        result = booklet_calculator(page_count=30, paper_gsm=90)
        assert result["total_pages"] == 32
        assert result["pages_added_for_signature"] == 2

    def test_spine_thickness_scales_with_pages(self) -> None:
        thin = booklet_calculator(page_count=32, paper_gsm=90)
        thick = booklet_calculator(page_count=320, paper_gsm=90, binding="perfect_bound")
        assert thick["spine_thickness_mm"] > thin["spine_thickness_mm"] * 5

    def test_coated_thinner_than_bulky(self) -> None:
        coated = booklet_calculator(64, 100, paper_type="coated")
        bulky = booklet_calculator(64, 100, paper_type="bulky")
        assert coated["spine_thickness_mm"] < bulky["spine_thickness_mm"]

    def test_cover_adds_thickness(self) -> None:
        no_cover = booklet_calculator(64, 90)
        with_cover = booklet_calculator(64, 90, cover_gsm=300)
        assert with_cover["spine_thickness_mm"] > no_cover["spine_thickness_mm"]

    def test_saddle_stitch_warning_when_thick(self) -> None:
        result = booklet_calculator(page_count=128, paper_gsm=90, binding="saddle_stitch")
        assert "perfect" in result["binding_note"].lower()

    def test_perfect_bound_warning_when_thin(self) -> None:
        result = booklet_calculator(page_count=8, paper_gsm=80, binding="perfect_bound")
        assert "thin" in result["binding_note"].lower()

    def test_signature_sizes(self) -> None:
        result = booklet_calculator(page_count=64, paper_gsm=90, pages_per_signature=8)
        assert result["signatures"] == 8
        assert result["sheets_per_signature"] == 2

    def test_too_few_pages_raises(self) -> None:
        with pytest.raises(ValueError, match="at least 4"):
            booklet_calculator(page_count=2, paper_gsm=90)

    def test_invalid_signature_raises(self) -> None:
        with pytest.raises(ValueError, match="pages_per_signature"):
            booklet_calculator(page_count=32, paper_gsm=90, pages_per_signature=6)

    def test_invalid_paper_type_raises(self) -> None:
        with pytest.raises(ValueError, match="paper_type"):
            booklet_calculator(page_count=32, paper_gsm=90, paper_type="glossy")

    def test_invalid_binding_raises(self) -> None:
        with pytest.raises(ValueError, match="binding"):
            booklet_calculator(page_count=32, paper_gsm=90, binding="spiral")
