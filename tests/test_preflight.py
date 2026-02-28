"""Tests for preflight check tool."""

import pytest

from mcp_print.tools.preflight import preflight_check


class TestPreflightAllPass:
    def test_all_checks_pass(self) -> None:
        result = preflight_check(
            color_mode="cmyk",
            resolution_dpi=300,
            has_bleed=True,
            width_mm=210,
            height_mm=297,
            fonts_embedded=True,
            bleed_mm=3.0,
            total_ink_coverage_percent=280,
            has_transparency=False,
            target_method="offset",
        )
        assert result["status"] == "pass"
        assert all(ch["status"] == "pass" for ch in result["checks"])
        assert "6 passed" in result["summary"]
        assert result["recommendation"] == "File is ready for production."


class TestColorMode:
    def test_rgb_fails_for_offset(self) -> None:
        result = preflight_check(
            color_mode="rgb", resolution_dpi=300, has_bleed=True,
            width_mm=210, height_mm=297, fonts_embedded=True, bleed_mm=3,
            target_method="offset",
        )
        cm = next(ch for ch in result["checks"] if ch["name"] == "color_mode")
        assert cm["status"] == "fail"
        assert result["status"] == "fail"

    def test_rgb_warns_for_digital(self) -> None:
        result = preflight_check(
            color_mode="rgb", resolution_dpi=300, has_bleed=True,
            width_mm=210, height_mm=297, fonts_embedded=True, bleed_mm=3,
            target_method="digital",
        )
        cm = next(ch for ch in result["checks"] if ch["name"] == "color_mode")
        assert cm["status"] == "warning"

    def test_grayscale_always_passes(self) -> None:
        for method in ("offset", "digital", "flexo", "gravure", "screen"):
            result = preflight_check(
                color_mode="grayscale", resolution_dpi=300, has_bleed=True,
                width_mm=210, height_mm=297, fonts_embedded=True, bleed_mm=3,
                target_method=method,
            )
            cm = next(ch for ch in result["checks"] if ch["name"] == "color_mode")
            assert cm["status"] == "pass"

    def test_spot_passes_for_offset(self) -> None:
        result = preflight_check(
            color_mode="spot", resolution_dpi=300, has_bleed=True,
            width_mm=210, height_mm=297, fonts_embedded=True, bleed_mm=3,
            target_method="offset",
        )
        cm = next(ch for ch in result["checks"] if ch["name"] == "color_mode")
        assert cm["status"] == "pass"

    def test_rgb_fails_for_flexo(self) -> None:
        result = preflight_check(
            color_mode="rgb", resolution_dpi=300, has_bleed=True,
            width_mm=210, height_mm=297, fonts_embedded=True, bleed_mm=3,
            target_method="flexo",
        )
        cm = next(ch for ch in result["checks"] if ch["name"] == "color_mode")
        assert cm["status"] == "fail"


class TestResolution:
    def test_low_dpi_fails(self) -> None:
        result = preflight_check(
            color_mode="cmyk", resolution_dpi=100, has_bleed=True,
            width_mm=210, height_mm=297, fonts_embedded=True, bleed_mm=3,
            target_method="offset",
        )
        res = next(ch for ch in result["checks"] if ch["name"] == "resolution")
        assert res["status"] == "fail"

    def test_medium_dpi_warns(self) -> None:
        # 75% of 300 = 225; anything between 225-299 should warn
        result = preflight_check(
            color_mode="cmyk", resolution_dpi=250, has_bleed=True,
            width_mm=210, height_mm=297, fonts_embedded=True, bleed_mm=3,
            target_method="offset",
        )
        res = next(ch for ch in result["checks"] if ch["name"] == "resolution")
        assert res["status"] == "warning"

    def test_digital_lower_requirement(self) -> None:
        result = preflight_check(
            color_mode="cmyk", resolution_dpi=150, has_bleed=True,
            width_mm=210, height_mm=297, fonts_embedded=True, bleed_mm=2,
            target_method="digital",
        )
        res = next(ch for ch in result["checks"] if ch["name"] == "resolution")
        assert res["status"] == "pass"


class TestBleed:
    def test_no_bleed_fails(self) -> None:
        result = preflight_check(
            color_mode="cmyk", resolution_dpi=300, has_bleed=False,
            width_mm=210, height_mm=297, fonts_embedded=True,
            target_method="offset",
        )
        bl = next(ch for ch in result["checks"] if ch["name"] == "bleed")
        assert bl["status"] == "fail"

    def test_insufficient_bleed_warns(self) -> None:
        result = preflight_check(
            color_mode="cmyk", resolution_dpi=300, has_bleed=True,
            width_mm=210, height_mm=297, fonts_embedded=True, bleed_mm=2,
            target_method="offset",
        )
        bl = next(ch for ch in result["checks"] if ch["name"] == "bleed")
        assert bl["status"] == "warning"

    def test_digital_lower_bleed_requirement(self) -> None:
        result = preflight_check(
            color_mode="cmyk", resolution_dpi=300, has_bleed=True,
            width_mm=210, height_mm=297, fonts_embedded=True, bleed_mm=2,
            target_method="digital",
        )
        bl = next(ch for ch in result["checks"] if ch["name"] == "bleed")
        assert bl["status"] == "pass"


class TestFonts:
    def test_fonts_not_embedded_fails(self) -> None:
        result = preflight_check(
            color_mode="cmyk", resolution_dpi=300, has_bleed=True,
            width_mm=210, height_mm=297, fonts_embedded=False, bleed_mm=3,
            target_method="offset",
        )
        fonts = next(ch for ch in result["checks"] if ch["name"] == "fonts")
        assert fonts["status"] == "fail"


class TestInkCoverage:
    def test_high_coverage_warns(self) -> None:
        result = preflight_check(
            color_mode="cmyk", resolution_dpi=300, has_bleed=True,
            width_mm=210, height_mm=297, fonts_embedded=True, bleed_mm=3,
            total_ink_coverage_percent=320,
            target_method="offset",
        )
        ink = next(ch for ch in result["checks"] if ch["name"] == "ink_coverage")
        assert ink["status"] == "warning"

    def test_excessive_coverage_fails(self) -> None:
        result = preflight_check(
            color_mode="cmyk", resolution_dpi=300, has_bleed=True,
            width_mm=210, height_mm=297, fonts_embedded=True, bleed_mm=3,
            total_ink_coverage_percent=350,
            target_method="offset",
        )
        ink = next(ch for ch in result["checks"] if ch["name"] == "ink_coverage")
        assert ink["status"] == "fail"


class TestTransparency:
    def test_transparency_warns(self) -> None:
        result = preflight_check(
            color_mode="cmyk", resolution_dpi=300, has_bleed=True,
            width_mm=210, height_mm=297, fonts_embedded=True, bleed_mm=3,
            has_transparency=True,
            target_method="offset",
        )
        tr = next(ch for ch in result["checks"] if ch["name"] == "transparency")
        assert tr["status"] == "warning"


class TestOverallStatus:
    def test_worst_status_is_fail(self) -> None:
        """Overall status should be fail when any check fails."""
        result = preflight_check(
            color_mode="rgb", resolution_dpi=300, has_bleed=True,
            width_mm=210, height_mm=297, fonts_embedded=True, bleed_mm=3,
            has_transparency=True,
            target_method="offset",
        )
        assert result["status"] == "fail"

    def test_summary_format(self) -> None:
        result = preflight_check(
            color_mode="cmyk", resolution_dpi=300, has_bleed=True,
            width_mm=210, height_mm=297, fonts_embedded=True, bleed_mm=3,
            target_method="offset",
        )
        assert "out of 6 checks" in result["summary"]

    def test_recommendation_lists_failed(self) -> None:
        result = preflight_check(
            color_mode="rgb", resolution_dpi=300, has_bleed=False,
            width_mm=210, height_mm=297, fonts_embedded=False, bleed_mm=0,
            target_method="offset",
        )
        assert "color_mode" in result["recommendation"]
        assert "bleed" in result["recommendation"]
        assert "fonts" in result["recommendation"]


class TestValidation:
    def test_negative_dpi_raises(self) -> None:
        with pytest.raises(ValueError, match="resolution_dpi must be positive"):
            preflight_check(
                color_mode="cmyk", resolution_dpi=-1, has_bleed=True,
                width_mm=210, height_mm=297, fonts_embedded=True, bleed_mm=3,
            )

    def test_invalid_method_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid target_method"):
            preflight_check(
                color_mode="cmyk", resolution_dpi=300, has_bleed=True,
                width_mm=210, height_mm=297, fonts_embedded=True,
                target_method="letterpress",
            )

    def test_invalid_color_mode_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid color_mode"):
            preflight_check(
                color_mode="lab", resolution_dpi=300, has_bleed=True,
                width_mm=210, height_mm=297, fonts_embedded=True,
            )

    def test_negative_width_raises(self) -> None:
        with pytest.raises(ValueError, match="width_mm must be positive"):
            preflight_check(
                color_mode="cmyk", resolution_dpi=300, has_bleed=True,
                width_mm=-10, height_mm=297, fonts_embedded=True,
            )
