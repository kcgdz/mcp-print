"""Tests for barcode ink coverage estimation."""

import pytest

from mcp_print.tools.barcode import barcode_ink_coverage


class TestBarcodeInkCoverage:
    def test_ean13_basic(self) -> None:
        result = barcode_ink_coverage("ean13", 37.29, 25.93)
        assert result["coverage_percent"] > 0
        assert result["total_area_mm2"] > 0
        assert result["bar_area_mm2"] <= result["total_area_mm2"]
        assert result["recommended_ink"]
        assert result["print_method_suggestion"]

    def test_all_types(self) -> None:
        for bt in ("code128", "ean13", "qr", "datamatrix"):
            result = barcode_ink_coverage(bt, 30, 30)
            assert result["coverage_percent"] > 0

    def test_high_density_increases_coverage(self) -> None:
        low = barcode_ink_coverage("qr", 30, 30, bar_density=0.3)
        high = barcode_ink_coverage("qr", 30, 30, bar_density=0.8)
        assert high["coverage_percent"] > low["coverage_percent"]

    def test_coverage_capped_at_100(self) -> None:
        result = barcode_ink_coverage("code128", 30, 30, bar_density=1.0)
        assert result["coverage_percent"] <= 100

    def test_invalid_type_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown barcode_type"):
            barcode_ink_coverage("upc", 30, 30)  # type: ignore[arg-type]

    def test_negative_width_raises(self) -> None:
        with pytest.raises(ValueError, match="width_mm must be positive"):
            barcode_ink_coverage("qr", -1, 30)

    def test_zero_density_raises(self) -> None:
        with pytest.raises(ValueError, match="bar_density"):
            barcode_ink_coverage("qr", 30, 30, bar_density=0)
