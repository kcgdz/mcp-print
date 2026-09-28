"""Approximate similarity of design colors to a user-supplied palette."""

from __future__ import annotations

from typing import TypedDict

from mcp_print.tools.colors import cmyk_to_rgb
from mcp_print.tools.palette import (
    APPROXIMATION_NOTE,
    DELTA_E_METHOD,
    SOURCE_LABEL,
    load_palette,
    nearest_palette_color,
)


class PaletteProximityEntry(TypedDict):
    color: dict[str, float]
    hex: str
    nearest_palette_color: str
    nearest_palette_cmyk: dict[str, float]
    delta_e: float


class SpotSeparatorResult(TypedDict):
    within_threshold: list[PaletteProximityEntry]
    beyond_threshold: list[PaletteProximityEntry]
    threshold: float
    delta_e_method: str
    source: str
    palette: str | None
    summary: str
    note: str


_DECISION_NOTE = (
    " Closeness to a palette color does not by itself show that printing it as a "
    "spot ink would be more accurate or more suitable; that decision depends on "
    "ink availability, press setup, substrate, cost, brand requirements, and "
    "measured proofs, none of which this tool evaluates."
)


def spot_color_separator(
    colors: list[dict[str, float]],
    threshold: float = 5.0,
) -> SpotSeparatorResult:
    """Report how close each design color is to the user's palette.

    Each CMYK color is compared with every entry of the palette configured
    through ``MCP_PRINT_PALETTE_PATH`` and grouped by whether its nearest
    entry is within ``threshold`` (CIEDE2000 on approximate Lab values).
    No spot/process recommendation is made.

    Args:
        colors: List of CMYK dicts, each with keys ``c``, ``m``, ``y``, ``k`` (0-100).
        threshold: Delta E cutoff for grouping (default 5.0).

    Returns:
        Dict with ``within_threshold``, ``beyond_threshold``, ``summary``,
        and ``note``.

    Raises:
        PaletteNotConfiguredError: If no palette is configured.
        PaletteError: If the palette file is invalid.
        ValueError: If any color has invalid CMYK values.
    """
    if not colors:
        raise ValueError("colors list must not be empty")
    if threshold <= 0:
        raise ValueError(f"threshold must be positive, got {threshold}")

    checked: list[dict[str, float]] = []
    for i, color in enumerate(colors):
        c = color.get("c", 0)
        m = color.get("m", 0)
        y = color.get("y", 0)
        k = color.get("k", 0)
        for name, val in [("c", c), ("m", m), ("y", y), ("k", k)]:
            if not (0 <= val <= 100):
                raise ValueError(f"Color {i}: {name} must be 0-100, got {val}")
        checked.append({"c": c, "m": m, "y": y, "k": k})

    palette = load_palette()
    within: list[PaletteProximityEntry] = []
    beyond: list[PaletteProximityEntry] = []

    for color in checked:
        nearest, de = nearest_palette_color(palette, **color)
        entry: PaletteProximityEntry = {
            "color": color,
            "hex": cmyk_to_rgb(**color)["hex"],
            "nearest_palette_color": nearest["name"],
            "nearest_palette_cmyk": {ch: nearest[ch] for ch in ("c", "m", "y", "k")},
            "delta_e": de,
        }
        (within if de <= threshold else beyond).append(entry)

    summary = (
        f"Compared {len(checked)} colors with {len(palette.colors)} palette entries "
        f"(Delta E {DELTA_E_METHOD}, threshold {threshold}): {len(within)} within "
        f"threshold, {len(beyond)} beyond."
    )

    return {
        "within_threshold": within,
        "beyond_threshold": beyond,
        "threshold": threshold,
        "delta_e_method": DELTA_E_METHOD,
        "source": SOURCE_LABEL,
        "palette": palette.label,
        "summary": summary,
        "note": APPROXIMATION_NOTE + _DECISION_NOTE,
    }
