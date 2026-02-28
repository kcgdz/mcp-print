"""Pre-press file validation (preflight check)."""

from __future__ import annotations

from typing import Literal, TypedDict

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

PrintMethod = Literal["offset", "digital", "flexo", "gravure", "screen"]
ColorMode = Literal["cmyk", "rgb", "grayscale", "spot"]
CheckStatus = Literal["pass", "warning", "fail"]


class CheckResult(TypedDict):
    name: str
    status: CheckStatus
    message: str


class PreflightResult(TypedDict):
    status: CheckStatus
    checks: list[CheckResult]
    summary: str
    recommendation: str


# ---------------------------------------------------------------------------
# Per-method requirements
# ---------------------------------------------------------------------------

_MIN_DPI: dict[str, int] = {
    "offset": 300,
    "digital": 150,
    "flexo": 300,
    "gravure": 300,
    "screen": 200,
}

_MIN_BLEED_MM: dict[str, float] = {
    "offset": 3.0,
    "digital": 2.0,
    "flexo": 3.0,
    "gravure": 3.0,
    "screen": 2.0,
}

_CMYK_REQUIRED_METHODS: set[str] = {"offset", "flexo", "gravure", "screen"}


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------


def _check_color_mode(color_mode: str, target_method: str) -> CheckResult:
    if color_mode == "grayscale":
        return {"name": "color_mode", "status": "pass", "message": "Grayscale is acceptable for all methods."}
    if target_method in _CMYK_REQUIRED_METHODS:
        if color_mode in ("cmyk", "spot"):
            return {"name": "color_mode", "status": "pass", "message": f"{color_mode.upper()} is correct for {target_method}."}
        return {
            "name": "color_mode",
            "status": "fail",
            "message": f"{color_mode.upper()} is not suitable for {target_method}; convert to CMYK.",
        }
    # digital
    if color_mode == "rgb":
        return {"name": "color_mode", "status": "warning", "message": "RGB can work for digital but CMYK is preferred for color accuracy."}
    return {"name": "color_mode", "status": "pass", "message": f"{color_mode.upper()} is correct for {target_method}."}


def _check_resolution(resolution_dpi: float, target_method: str) -> CheckResult:
    min_dpi = _MIN_DPI[target_method]
    if resolution_dpi >= min_dpi:
        return {"name": "resolution", "status": "pass", "message": f"{resolution_dpi} DPI meets the minimum of {min_dpi} DPI for {target_method}."}
    if resolution_dpi >= min_dpi * 0.75:
        return {
            "name": "resolution",
            "status": "warning",
            "message": f"{resolution_dpi} DPI is below the recommended {min_dpi} DPI for {target_method}; may appear soft.",
        }
    return {
        "name": "resolution",
        "status": "fail",
        "message": f"{resolution_dpi} DPI is too low for {target_method} (minimum {min_dpi} DPI).",
    }


def _check_bleed(has_bleed: bool, bleed_mm: float, target_method: str) -> CheckResult:
    min_bleed = _MIN_BLEED_MM[target_method]
    if not has_bleed:
        return {"name": "bleed", "status": "fail", "message": f"No bleed detected; {target_method} requires at least {min_bleed} mm bleed."}
    if bleed_mm >= min_bleed:
        return {"name": "bleed", "status": "pass", "message": f"{bleed_mm} mm bleed meets the {min_bleed} mm minimum for {target_method}."}
    return {
        "name": "bleed",
        "status": "warning",
        "message": f"{bleed_mm} mm bleed is below the recommended {min_bleed} mm for {target_method}.",
    }


def _check_fonts(fonts_embedded: bool) -> CheckResult:
    if fonts_embedded:
        return {"name": "fonts", "status": "pass", "message": "All fonts are embedded."}
    return {"name": "fonts", "status": "fail", "message": "Fonts are not embedded; this will cause text rendering issues."}


def _check_ink_coverage(total_ink_coverage_percent: float) -> CheckResult:
    if total_ink_coverage_percent <= 300:
        return {"name": "ink_coverage", "status": "pass", "message": f"Total ink coverage {total_ink_coverage_percent}% is within safe limits."}
    if total_ink_coverage_percent <= 340:
        return {
            "name": "ink_coverage",
            "status": "warning",
            "message": f"Total ink coverage {total_ink_coverage_percent}% exceeds 300%; may cause drying issues.",
        }
    return {
        "name": "ink_coverage",
        "status": "fail",
        "message": f"Total ink coverage {total_ink_coverage_percent}% exceeds 340%; risk of smearing and set-off.",
    }


def _check_transparency(has_transparency: bool) -> CheckResult:
    if not has_transparency:
        return {"name": "transparency", "status": "pass", "message": "No transparency detected."}
    return {
        "name": "transparency",
        "status": "warning",
        "message": "File contains transparency; flatten before sending to press to avoid rendering issues.",
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_VALID_METHODS: set[str] = {"offset", "digital", "flexo", "gravure", "screen"}
_VALID_COLOR_MODES: set[str] = {"cmyk", "rgb", "grayscale", "spot"}


def preflight_check(
    *,
    color_mode: str,
    resolution_dpi: float,
    has_bleed: bool,
    width_mm: float,
    height_mm: float,
    fonts_embedded: bool,
    bleed_mm: float = 0.0,
    total_ink_coverage_percent: float = 280.0,
    has_transparency: bool = False,
    target_method: str = "offset",
) -> PreflightResult:
    """Run pre-press preflight validation on declared file properties.

    Args:
        color_mode: File color mode — cmyk, rgb, grayscale, or spot.
        resolution_dpi: Image resolution in DPI.
        has_bleed: Whether the document includes bleed.
        width_mm: Document width in millimeters.
        height_mm: Document height in millimeters.
        fonts_embedded: Whether all fonts are embedded.
        bleed_mm: Bleed size in millimeters (default 0).
        total_ink_coverage_percent: Maximum total ink coverage (default 280).
        has_transparency: Whether the file contains transparency (default False).
        target_method: Print method — offset, digital, flexo, gravure, or screen.

    Returns:
        Dict with status, checks list, summary, and recommendation.

    Raises:
        ValueError: If inputs are invalid.
    """
    # Validate inputs
    target_method = target_method.lower()
    color_mode = color_mode.lower()

    if target_method not in _VALID_METHODS:
        raise ValueError(f"Invalid target_method: {target_method!r}. Must be one of {sorted(_VALID_METHODS)}.")
    if color_mode not in _VALID_COLOR_MODES:
        raise ValueError(f"Invalid color_mode: {color_mode!r}. Must be one of {sorted(_VALID_COLOR_MODES)}.")
    if resolution_dpi <= 0:
        raise ValueError(f"resolution_dpi must be positive, got {resolution_dpi}.")
    if width_mm <= 0:
        raise ValueError(f"width_mm must be positive, got {width_mm}.")
    if height_mm <= 0:
        raise ValueError(f"height_mm must be positive, got {height_mm}.")
    if bleed_mm < 0:
        raise ValueError(f"bleed_mm must be non-negative, got {bleed_mm}.")
    if total_ink_coverage_percent < 0:
        raise ValueError(f"total_ink_coverage_percent must be non-negative, got {total_ink_coverage_percent}.")

    # Run checks
    checks: list[CheckResult] = [
        _check_color_mode(color_mode, target_method),
        _check_resolution(resolution_dpi, target_method),
        _check_bleed(has_bleed, bleed_mm, target_method),
        _check_fonts(fonts_embedded),
        _check_ink_coverage(total_ink_coverage_percent),
        _check_transparency(has_transparency),
    ]

    # Overall status = worst status
    statuses = [ch["status"] for ch in checks]
    if "fail" in statuses:
        overall: CheckStatus = "fail"
    elif "warning" in statuses:
        overall = "warning"
    else:
        overall = "pass"

    # Summary
    n_pass = statuses.count("pass")
    n_warn = statuses.count("warning")
    n_fail = statuses.count("fail")
    summary = f"{n_pass} passed, {n_warn} warnings, {n_fail} failed out of {len(checks)} checks."

    # Recommendation
    if overall == "pass":
        recommendation = "File is ready for production."
    elif overall == "warning":
        recommendation = "Review warnings before sending to press."
    else:
        failed_names = [ch["name"] for ch in checks if ch["status"] == "fail"]
        recommendation = f"Fix failed checks before production: {', '.join(failed_names)}."

    return {
        "status": overall,
        "checks": checks,
        "summary": summary,
        "recommendation": recommendation,
    }
