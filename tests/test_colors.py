"""Tests for color conversion utilities and Pantone database."""

import pytest

from mcp_print.tools.colors import cmyk_to_rgb, color_delta_e, pantone_search, pantone_to_cmyk


class TestCmykToRgb:
    def test_pure_black(self) -> None:
        result = cmyk_to_rgb(0, 0, 0, 100)
        assert result == {"r": 0, "g": 0, "b": 0, "hex": "#000000"}

    def test_pure_white(self) -> None:
        result = cmyk_to_rgb(0, 0, 0, 0)
        assert result == {"r": 255, "g": 255, "b": 255, "hex": "#FFFFFF"}

    def test_pure_cyan(self) -> None:
        result = cmyk_to_rgb(100, 0, 0, 0)
        assert result == {"r": 0, "g": 255, "b": 255, "hex": "#00FFFF"}

    def test_mid_gray(self) -> None:
        result = cmyk_to_rgb(0, 0, 0, 50)
        assert result["r"] == result["g"] == result["b"]
        assert 127 <= result["r"] <= 128

    def test_invalid_raises(self) -> None:
        with pytest.raises(ValueError, match="must be between 0 and 100"):
            cmyk_to_rgb(101, 0, 0, 0)

    def test_negative_raises(self) -> None:
        with pytest.raises(ValueError, match="must be between 0 and 100"):
            cmyk_to_rgb(-1, 0, 0, 0)


class TestPantoneToCmyk:
    def test_known_color(self) -> None:
        result = pantone_to_cmyk("Pantone 485 C")
        assert result["c"] == 0
        assert result["m"] == 95
        assert result["y"] == 100
        assert result["k"] == 0
        assert result["hex"].startswith("#")
        assert result["name"] == "Pantone 485 C"

    def test_case_insensitive(self) -> None:
        result = pantone_to_cmyk("pantone 485 c")
        assert result["m"] == 95

    def test_shorthand_no_space(self) -> None:
        result = pantone_to_cmyk("485C")
        assert result["name"] == "Pantone 485 C"

    def test_shorthand_no_suffix(self) -> None:
        result = pantone_to_cmyk("pantone 485")
        assert result["name"] == "Pantone 485 C"

    def test_coated_word(self) -> None:
        result = pantone_to_cmyk("485 coated")
        assert result["name"] == "Pantone 485 C"

    def test_uncoated_variant(self) -> None:
        result = pantone_to_cmyk("Pantone 485 U")
        assert result["name"] == "Pantone 485 U"

    def test_named_color(self) -> None:
        result = pantone_to_cmyk("Pantone Warm Red C")
        assert result["m"] > 0

    def test_named_color_shorthand(self) -> None:
        result = pantone_to_cmyk("warm red")
        assert "Warm Red" in result["name"]

    def test_unknown_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown Pantone color"):
            pantone_to_cmyk("Pantone 99999 C")

    def test_black(self) -> None:
        result = pantone_to_cmyk("Pantone Black C")
        assert result["k"] == 100

    def test_7000_series(self) -> None:
        result = pantone_to_cmyk("Pantone 7462 C")
        assert result["name"] == "Pantone 7462 C"


class TestColorDeltaE:
    def test_identical_colors(self) -> None:
        result = color_delta_e(50, 30, 20, 10, 50, 30, 20, 10)
        assert result["delta_e"] == 0.0
        assert "excellent" in result["interpretation"]

    def test_very_different_colors(self) -> None:
        result = color_delta_e(0, 0, 0, 0, 100, 100, 100, 100)
        assert result["delta_e"] > 6
        assert "poor" in result["interpretation"]

    def test_invalid_value_raises(self) -> None:
        with pytest.raises(ValueError):
            color_delta_e(0, 0, 0, 0, 0, 0, 0, 101)


class TestPantoneSearch:
    def test_search_by_hex(self) -> None:
        result = pantone_search(hex_color="#FF0000")
        assert len(result["matches"]) == 5
        assert result["search_type"].startswith("hex")

    def test_search_by_cmyk(self) -> None:
        result = pantone_search(c=0, m=95, y=100, k=0, limit=3)
        assert len(result["matches"]) == 3
        assert result["search_type"].startswith("cmyk")

    def test_search_finds_close_match(self) -> None:
        # Search for Pantone 485 C values — should find 485 C as closest
        result = pantone_search(c=0, m=95, y=100, k=0, limit=1)
        assert result["matches"][0]["name"] == "Pantone 485 C"

    def test_search_requires_input(self) -> None:
        with pytest.raises(ValueError, match="Provide either"):
            pantone_search()

    def test_short_hex(self) -> None:
        result = pantone_search(hex_color="#F00")
        assert len(result["matches"]) > 0

    def test_invalid_hex_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid hex"):
            pantone_search(hex_color="#ZZZZZZ")
