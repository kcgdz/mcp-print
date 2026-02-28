"""Tests for paper weight conversion."""

import pytest

from mcp_print.tools.paper import paper_weight_convert


class TestPaperWeightConvert:
    def test_gsm_to_gsm(self) -> None:
        assert paper_weight_convert(120, "gsm", "gsm") == 120.0

    def test_gsm_to_lb_text(self) -> None:
        result = paper_weight_convert(120, "gsm", "lb_text")
        assert 79 <= result <= 82

    def test_lb_text_to_gsm(self) -> None:
        result = paper_weight_convert(80, "lb_text", "gsm")
        assert 118 <= result <= 119

    def test_lb_cover_to_gsm(self) -> None:
        result = paper_weight_convert(100, "lb_cover", "gsm")
        assert 270 <= result <= 271

    def test_roundtrip_text(self) -> None:
        gsm = paper_weight_convert(60, "lb_text", "gsm")
        back = paper_weight_convert(gsm, "gsm", "lb_text")
        assert abs(back - 60) < 0.1

    def test_zero_raises(self) -> None:
        with pytest.raises(ValueError, match="must be positive"):
            paper_weight_convert(0, "gsm", "lb_text")

    def test_unknown_unit_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown from_unit"):
            paper_weight_convert(100, "lbs", "gsm")  # type: ignore[arg-type]
