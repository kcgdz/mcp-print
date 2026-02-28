"""Tests for spot color separator."""

import pytest

from mcp_print.tools.spot import spot_color_separator


class TestSpotColorSeparator:
    def test_exact_pantone_match_is_spot(self) -> None:
        # Pantone 485 C exact values
        colors = [{"c": 0, "m": 95, "y": 100, "k": 0}]
        result = spot_color_separator(colors, threshold=5.0)
        assert len(result["spot_colors"]) == 1
        assert len(result["process_colors"]) == 0
        assert "485" in result["spot_colors"][0]["nearest_pantone"]

    def test_far_color_is_process(self) -> None:
        # A weird color unlikely to match any Pantone
        colors = [{"c": 37, "m": 13, "y": 67, "k": 3}]
        result = spot_color_separator(colors, threshold=1.0)
        # With threshold=1.0, most colors won't be spot
        assert len(result["process_colors"]) >= 1

    def test_mixed_results(self) -> None:
        colors = [
            {"c": 0, "m": 95, "y": 100, "k": 0},  # Should match 485 C
            {"c": 37, "m": 13, "y": 67, "k": 3},   # Unlikely match
        ]
        result = spot_color_separator(colors, threshold=2.0)
        total = len(result["spot_colors"]) + len(result["process_colors"])
        assert total == 2
        assert "reasoning" in result

    def test_empty_list_raises(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            spot_color_separator([])

    def test_invalid_threshold_raises(self) -> None:
        with pytest.raises(ValueError, match="threshold must be positive"):
            spot_color_separator([{"c": 0, "m": 0, "y": 0, "k": 0}], threshold=-1)

    def test_invalid_cmyk_raises(self) -> None:
        with pytest.raises(ValueError, match="must be 0-100"):
            spot_color_separator([{"c": 200, "m": 0, "y": 0, "k": 0}])
