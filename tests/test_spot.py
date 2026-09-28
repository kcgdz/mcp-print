"""Tests for palette proximity reporting in the spot color separator."""

import pytest

from mcp_print.tools.palette import PaletteNotConfiguredError
from mcp_print.tools.spot import spot_color_separator


class TestSpotColorSeparator:
    def test_requires_palette(self) -> None:
        with pytest.raises(PaletteNotConfiguredError, match="No color palette configured"):
            spot_color_separator([{"c": 0, "m": 90, "y": 85, "k": 0}])

    def test_exact_palette_color_within_threshold(self, synthetic_palette) -> None:
        result = spot_color_separator([{"c": 0, "m": 90, "y": 85, "k": 0}], threshold=5.0)
        assert len(result["within_threshold"]) == 1
        assert result["beyond_threshold"] == []
        entry = result["within_threshold"][0]
        assert entry["nearest_palette_color"] == "Test Red"
        assert entry["nearest_palette_cmyk"] == {"c": 0, "m": 90, "y": 85, "k": 0}
        assert entry["delta_e"] == 0.0

    def test_far_color_beyond_threshold(self, synthetic_palette) -> None:
        result = spot_color_separator([{"c": 100, "m": 0, "y": 100, "k": 0}], threshold=1.0)
        assert result["within_threshold"] == []
        assert len(result["beyond_threshold"]) == 1
        assert result["beyond_threshold"][0]["delta_e"] > 1.0

    def test_mixed_results_and_metadata(self, synthetic_palette) -> None:
        colors = [
            {"c": 0, "m": 90, "y": 85, "k": 0},
            {"c": 100, "m": 0, "y": 100, "k": 0},
        ]
        result = spot_color_separator(colors, threshold=2.0)
        assert len(result["within_threshold"]) + len(result["beyond_threshold"]) == 2
        assert result["source"] == "user_palette"
        assert result["palette"] == "Synthetic test palette"
        assert result["delta_e_method"] == "ciede2000"
        assert result["threshold"] == 2.0
        assert "2 colors" in result["summary"]

    def test_makes_no_spot_or_process_recommendation(self, synthetic_palette) -> None:
        result = spot_color_separator([{"c": 0, "m": 90, "y": 85, "k": 0}])
        for legacy_key in ("spot_colors", "process_colors", "reasoning"):
            assert legacy_key not in result
        assert "nearest_pantone" not in result["within_threshold"][0]
        assert "does not by itself show" in result["note"]

    def test_empty_list_raises(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            spot_color_separator([])

    def test_invalid_threshold_raises(self) -> None:
        with pytest.raises(ValueError, match="threshold must be positive"):
            spot_color_separator([{"c": 0, "m": 0, "y": 0, "k": 0}], threshold=-1)

    def test_invalid_cmyk_raises_before_palette(self) -> None:
        with pytest.raises(ValueError, match="must be 0-100"):
            spot_color_separator([{"c": 200, "m": 0, "y": 0, "k": 0}])
