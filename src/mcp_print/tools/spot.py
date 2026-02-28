"""Spot color vs process color separator."""

from __future__ import annotations

import math
from typing import TypedDict

from mcp_print.tools.colors import _cmyk_to_lab, _load_db, cmyk_to_rgb


class SpotColorEntry(TypedDict):
    color: dict[str, float]
    hex: str
    nearest_pantone: str
    delta_e: float
    reason: str


class SpotSeparatorResult(TypedDict):
    spot_colors: list[SpotColorEntry]
    process_colors: list[SpotColorEntry]
    reasoning: str


def _find_nearest_pantone(c: float, m: float, y: float, k: float) -> tuple[str, float]:
    """Find the nearest Pantone color and its Delta E distance."""
    target_lab = _cmyk_to_lab(c, m, y, k)
    best_name = ""
    best_de = float("inf")
    for entry in _load_db():
        entry_lab = _cmyk_to_lab(entry["c"], entry["m"], entry["y"], entry["k"])
        de = math.sqrt(sum((a - b) ** 2 for a, b in zip(target_lab, entry_lab)))
        if de < best_de:
            best_de = de
            best_name = entry["name"]
    return best_name, round(best_de, 2)


def spot_color_separator(
    colors: list[dict[str, float]],
    threshold: float = 5.0,
) -> SpotSeparatorResult:
    """Identify which colors should be spot vs process colors.

    Colors that closely match a Pantone swatch (Delta E < threshold)
    are recommended as spot colors for accuracy. Colors that are far
    from any Pantone are better reproduced as process (CMYK).

    Args:
        colors: List of CMYK dicts, each with keys ``c``, ``m``, ``y``, ``k`` (0-100).
        threshold: Delta E cutoff — colors below this are spot candidates (default 5.0).

    Returns:
        Dict with ``spot_colors``, ``process_colors``, and ``reasoning``.

    Raises:
        ValueError: If any color has invalid CMYK values.
    """
    if not colors:
        raise ValueError("colors list must not be empty")
    if threshold <= 0:
        raise ValueError(f"threshold must be positive, got {threshold}")

    spot: list[SpotColorEntry] = []
    process: list[SpotColorEntry] = []

    for i, color in enumerate(colors):
        c = color.get("c", 0)
        m = color.get("m", 0)
        y = color.get("y", 0)
        k = color.get("k", 0)
        for name, val in [("c", c), ("m", m), ("y", y), ("k", k)]:
            if not (0 <= val <= 100):
                raise ValueError(f"Color {i}: {name} must be 0-100, got {val}")

        rgb = cmyk_to_rgb(c, m, y, k)
        pantone_name, de = _find_nearest_pantone(c, m, y, k)

        entry: SpotColorEntry = {
            "color": {"c": c, "m": m, "y": y, "k": k},
            "hex": rgb["hex"],
            "nearest_pantone": pantone_name,
            "delta_e": de,
            "reason": "",
        }

        if de <= threshold:
            entry["reason"] = (
                f"Close match to {pantone_name} (Delta E = {de}). "
                f"Use as spot color for best accuracy."
            )
            spot.append(entry)
        else:
            entry["reason"] = (
                f"No close Pantone match (nearest: {pantone_name}, Delta E = {de}). "
                f"Reproduce as process (CMYK) color."
            )
            process.append(entry)

    reasoning = (
        f"Analyzed {len(colors)} colors with Delta E threshold {threshold}. "
        f"{len(spot)} recommended as spot colors, {len(process)} as process colors. "
        f"Spot colors have a close Pantone match and will be more consistent across "
        f"print runs. Process colors are better served by standard CMYK mixing."
    )

    return {
        "spot_colors": spot,
        "process_colors": process,
        "reasoning": reasoning,
    }
