"""Tests for the user-supplied local palette loader, lookup, and search."""

from __future__ import annotations

import json
import os

import pytest

from mcp_print.tools.palette import (
    PaletteColorNotFoundError,
    PaletteError,
    PaletteNotConfiguredError,
    load_palette,
    palette_lookup,
    palette_search,
)


def _entry(**overrides: object) -> dict:
    return {"name": "Swatch", "c": 10, "m": 20, "y": 30, "k": 40, **overrides}


class TestLoadPalette:
    def test_not_configured(self) -> None:
        with pytest.raises(PaletteNotConfiguredError, match="MCP_PRINT_PALETTE_PATH"):
            load_palette()

    def test_blank_env_is_not_configured(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MCP_PRINT_PALETTE_PATH", "   ")
        with pytest.raises(PaletteNotConfiguredError):
            load_palette()

    def test_missing_file(self, tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MCP_PRINT_PALETTE_PATH", str(tmp_path / "nope.json"))
        with pytest.raises(PaletteError, match="not found"):
            load_palette()

    def test_directory_is_rejected(self, tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MCP_PRINT_PALETTE_PATH", str(tmp_path))
        with pytest.raises(PaletteError, match="not a file"):
            load_palette()

    def test_valid_palette(self, synthetic_palette) -> None:
        palette = load_palette()
        assert palette.label == "Synthetic test palette"
        assert len(palette.colors) == 5
        assert palette.colors[0]["name"] == "Test Red"

    def test_label_is_optional(self, write_palette) -> None:
        write_palette({"colors": [_entry()]})
        assert load_palette().label is None

    def test_utf8_bom_accepted(self, tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
        path = tmp_path / "bom.json"
        path.write_text(json.dumps({"colors": [_entry()]}), encoding="utf-8-sig")
        monkeypatch.setenv("MCP_PRINT_PALETTE_PATH", str(path))
        assert len(load_palette().colors) == 1

    def test_reloads_after_file_change(self, write_palette) -> None:
        path = write_palette({"colors": [_entry(name="First")]})
        assert load_palette().colors[0]["name"] == "First"
        path.write_text(json.dumps({"colors": [_entry(name="Second"), _entry(name="Third")]}))
        stat = path.stat()
        os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 10_000_000))
        assert [c["name"] for c in load_palette().colors] == ["Second", "Third"]

    @pytest.mark.parametrize(
        "raw, message",
        [
            ("{not json", "not valid JSON"),
            ("", "not valid JSON"),
            ("[]", "must be a JSON object"),
            ('{"colors": {}}', '"colors" list'),
            ("{}", '"colors" list'),
            ('{"colors": []}', "empty"),
            ('{"colors": [], "extra": 1}', "unsupported top-level"),
            ('{"palette": "", "colors": [1]}', '"palette" must be'),
            ('{"colors": [1]}', r"colors\[0\] must be an object"),
        ],
    )
    def test_invalid_structure(self, write_palette, raw: str, message: str) -> None:
        write_palette(raw, raw=True)
        with pytest.raises(PaletteError, match=message):
            load_palette()

    @pytest.mark.parametrize("token", ["NaN", "Infinity", "-Infinity"])
    def test_non_standard_constants_rejected(self, write_palette, token: str) -> None:
        write_palette(f'{{"colors": [{{"name": "A", "c": {token}, "m": 0, "y": 0, "k": 0}}]}}', raw=True)
        with pytest.raises(PaletteError, match="non-standard JSON value"):
            load_palette()

    def test_overflowing_float_rejected(self, write_palette) -> None:
        write_palette('{"colors": [{"name": "A", "c": 1e400, "m": 0, "y": 0, "k": 0}]}', raw=True)
        with pytest.raises(PaletteError, match="finite"):
            load_palette()

    def test_huge_int_rejected(self, write_palette) -> None:
        write_palette('{"colors": [{"name": "A", "c": 1' + "0" * 400 + ', "m": 0, "y": 0, "k": 0}]}', raw=True)
        with pytest.raises(PaletteError, match="between 0 and 100"):
            load_palette()

    @pytest.mark.parametrize(
        "overrides, message",
        [
            ({"c": True}, r"colors\[0\]\.c must be a number, got bool"),
            ({"m": False}, r"\.m must be a number, got bool"),
            ({"y": "50"}, r"\.y must be a number, got str"),
            ({"k": None}, r"\.k must be a number"),
            ({"c": -0.1}, "between 0 and 100"),
            ({"k": 100.5}, "between 0 and 100"),
            ({"name": ""}, "non-empty string"),
            ({"name": "   "}, "non-empty string"),
            ({"name": 42}, "non-empty string"),
            ({"name": "x" * 201}, "longer than"),
            ({"hex": "#FFFFFF"}, "unsupported field"),
        ],
    )
    def test_invalid_entry(self, write_palette, overrides: dict, message: str) -> None:
        write_palette({"colors": [_entry(**overrides)]})
        with pytest.raises(PaletteError, match=message):
            load_palette()

    def test_missing_field(self, write_palette) -> None:
        entry = _entry()
        del entry["k"]
        write_palette({"colors": [entry]})
        with pytest.raises(PaletteError, match="missing required field"):
            load_palette()

    def test_error_points_at_bad_index(self, write_palette) -> None:
        write_palette({"colors": [_entry(name="A"), _entry(name="B", m=500)]})
        with pytest.raises(PaletteError, match=r"colors\[1\]\.m"):
            load_palette()

    def test_duplicate_names_rejected(self, write_palette) -> None:
        write_palette({"colors": [_entry(name="Deep  Blue"), _entry(name="Other"), _entry(name="deep blue")]})
        with pytest.raises(PaletteError, match=r"colors\[0\] and colors\[2\] have the same name"):
            load_palette()

    def test_errors_do_not_echo_values(self, write_palette) -> None:
        write_palette({"colors": [_entry(name="Secret Swatch", c="SECRET-VALUE")]})
        with pytest.raises(PaletteError) as exc_info:
            load_palette()
        assert "SECRET-VALUE" not in str(exc_info.value)
        assert "Secret Swatch" not in str(exc_info.value)


class TestPaletteLookup:
    def test_requires_palette(self) -> None:
        with pytest.raises(PaletteNotConfiguredError):
            palette_lookup("Test Red")

    def test_exact_match(self, synthetic_palette) -> None:
        result = palette_lookup("Test Red")
        assert result["color"] == {"name": "Test Red", "c": 0, "m": 90, "y": 85, "k": 0, "hex": "#FF1926"}
        assert result["source"] == "user_palette"
        assert result["palette"] == "Synthetic test palette"
        assert "approximate" in result["note"]

    def test_case_and_whitespace_insensitive_keeps_original_name(self, synthetic_palette) -> None:
        result = palette_lookup("  test   TEAL ")
        assert result["color"]["name"] == "Test Teal"

    def test_no_prefix_or_variant_generation(self, synthetic_palette) -> None:
        for query in ("Test Red C", "Pantone Test Red", "Test Red coated", "TestRed"):
            with pytest.raises(PaletteColorNotFoundError):
                palette_lookup(query)

    def test_partial_name_is_suggestion_not_result(self, synthetic_palette) -> None:
        with pytest.raises(PaletteColorNotFoundError) as exc_info:
            palette_lookup("Teal")
        assert "Test Teal" in exc_info.value.suggestions

    def test_unknown_without_suggestions(self, synthetic_palette) -> None:
        with pytest.raises(PaletteColorNotFoundError) as exc_info:
            palette_lookup("Nothing Alike")
        assert exc_info.value.suggestions == []

    def test_empty_name(self, synthetic_palette) -> None:
        with pytest.raises(ValueError, match="non-empty"):
            palette_lookup("  ")


class TestPaletteSearch:
    def test_requires_palette(self) -> None:
        with pytest.raises(PaletteNotConfiguredError):
            palette_search(hex_color="#FF0000")

    def test_input_validated_before_palette(self) -> None:
        with pytest.raises(ValueError, match="Provide either"):
            palette_search()

    def test_exact_cmyk_ranks_first_with_zero_delta(self, synthetic_palette) -> None:
        result = palette_search(c=80, m=10, y=45, k=5, limit=2)
        assert [m["name"] for m in result["matches"]][0] == "Test Teal"
        assert result["matches"][0]["delta_e"] == 0.0
        assert len(result["matches"]) == 2
        assert result["search_type"].startswith("cmyk")
        assert result["delta_e_method"] == "ciede2000"
        assert result["source"] == "user_palette"

    def test_hex_search_sorted_by_delta_e(self, synthetic_palette) -> None:
        result = palette_search(hex_color="#F22", limit=5)
        assert result["matches"][0]["name"] == "Test Red"
        deltas = [m["delta_e"] for m in result["matches"]]
        assert deltas == sorted(deltas)
        assert result["search_type"] == "hex #F22"

    def test_limit_capped_by_palette_size(self, synthetic_palette) -> None:
        assert len(palette_search(hex_color="#808080", limit=50)["matches"]) == 5

    @pytest.mark.parametrize("limit", [0, -1, 101, True, 2.5])
    def test_invalid_limit(self, synthetic_palette, limit) -> None:
        with pytest.raises(ValueError, match="limit must be"):
            palette_search(hex_color="#808080", limit=limit)

    def test_invalid_hex(self, synthetic_palette) -> None:
        with pytest.raises(ValueError, match="Invalid hex"):
            palette_search(hex_color="#ZZZZZZ")

    def test_out_of_range_cmyk(self, synthetic_palette) -> None:
        with pytest.raises(ValueError, match="between 0 and 100"):
            palette_search(c=101, m=0, y=0, k=0)


def test_example_palette_in_repo_is_valid(monkeypatch: pytest.MonkeyPatch) -> None:
    from pathlib import Path

    example = Path(__file__).resolve().parent.parent / "examples" / "example-palette.json"
    monkeypatch.setenv("MCP_PRINT_PALETTE_PATH", str(example))
    assert len(load_palette().colors) == 5
