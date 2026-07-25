"""Tests for dot gain compensation."""

import pytest

from mcp_print.tools.dotgain import dot_gain_compensation
from mcp_print.tools.substrate import _apply_dot_gain


class TestDotGainCompensation:
    def test_roundtrip_with_simulator_curve(self) -> None:
        result = dot_gain_compensation(c=50, m=40, y=30, k=20, dot_gain_percent=22)
        for ch, target in (("c", 50), ("m", 40), ("y", 30), ("k", 20)):
            file_val = result["compensated"][ch]
            on_press = _apply_dot_gain(file_val, 22)
            assert abs(on_press - target) < 0.2

    def test_compensated_below_target(self) -> None:
        result = dot_gain_compensation(c=50, m=50, y=50, k=50, dot_gain_percent=20)
        for ch in "cmyk":
            assert result["compensated"][ch] < 50

    def test_zero_gain_identity(self) -> None:
        result = dot_gain_compensation(c=50, m=40, y=30, k=20, dot_gain_percent=0)
        assert result["compensated"] == {"c": 50, "m": 40, "y": 30, "k": 20}

    def test_extremes_unchanged(self) -> None:
        result = dot_gain_compensation(c=0, m=100, y=0, k=100, dot_gain_percent=25)
        assert result["compensated"]["c"] == 0
        assert result["compensated"]["m"] == 100

    def test_substrate_lookup(self) -> None:
        result = dot_gain_compensation(
            c=50, m=50, y=50, k=50, substrate="newsprint", print_method="offset",
        )
        assert result["dot_gain_percent"] == 30
        assert "newsprint" in result["source"]

    def test_neither_input_raises(self) -> None:
        with pytest.raises(ValueError, match="exactly one"):
            dot_gain_compensation(c=50, m=50, y=50, k=50)

    def test_both_inputs_raise(self) -> None:
        with pytest.raises(ValueError, match="exactly one"):
            dot_gain_compensation(
                c=50, m=50, y=50, k=50, dot_gain_percent=20, substrate="uncoated",
            )

    def test_unknown_substrate_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown substrate"):
            dot_gain_compensation(c=50, m=50, y=50, k=50, substrate="vellum")

    def test_out_of_range_raises(self) -> None:
        with pytest.raises(ValueError, match="between 0 and 100"):
            dot_gain_compensation(c=150, m=50, y=50, k=50, dot_gain_percent=20)
