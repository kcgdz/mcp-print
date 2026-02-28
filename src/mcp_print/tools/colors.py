"""Pantone color database, fuzzy matching, color math, and proximity search."""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import TypedDict


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

class CMYKColor(TypedDict):
    c: float
    m: float
    y: float
    k: float


class RGBResult(TypedDict):
    r: int
    g: int
    b: int
    hex: str


class PantoneResult(TypedDict):
    name: str
    c: float
    m: float
    y: float
    k: float
    hex: str


class DeltaEResult(TypedDict):
    delta_e: float
    interpretation: str


class PantoneSearchResult(TypedDict):
    matches: list[PantoneResult]
    search_type: str


# ---------------------------------------------------------------------------
# Pantone database — loaded once from JSON
# ---------------------------------------------------------------------------

_DB: list[dict] | None = None


def _load_db() -> list[dict]:
    """Load the Pantone color database from JSON (cached)."""
    global _DB
    if _DB is None:
        db_path = Path(__file__).resolve().parent.parent / "data" / "pantone_colors.json"
        with open(db_path, encoding="utf-8") as f:
            _DB = json.load(f)
    return _DB


def _build_lookup() -> dict[str, dict]:
    """Build a normalized-name -> color dict for exact lookups."""
    return {_normalize_key(e["name"]): e for e in _load_db()}


# ---------------------------------------------------------------------------
# Fuzzy / flexible matching
# ---------------------------------------------------------------------------

_SUFFIX_MAP = {
    "coated": "C",
    "uncoated": "U",
    "matte": "M",
}


def _normalize_key(name: str) -> str:
    """Create a canonical key: lowercase, stripped, collapsed whitespace."""
    return re.sub(r"\s+", " ", name.strip().lower())


def _expand_query(raw: str) -> list[str]:
    """Generate candidate lookup keys from a user query.

    Handles formats like:
      - "Pantone 485 C"
      - "485C", "485 C", "485 coated", "pantone 485"
      - "Warm Red C", "warm red", "pantone warm red"
    """
    q = raw.strip()
    candidates: list[str] = []

    # Normalised as-is
    candidates.append(_normalize_key(q))

    # Ensure "pantone" prefix
    ql = q.lower().strip()
    if not ql.startswith("pantone"):
        candidates.append(_normalize_key("pantone " + q))

    # Replace long suffix words with letter codes
    for word, letter in _SUFFIX_MAP.items():
        if word in ql:
            replaced = ql.replace(word, letter)
            candidates.append(_normalize_key(replaced))
            if not replaced.startswith("pantone"):
                candidates.append(_normalize_key("pantone " + replaced))

    # Handle "485C" (no space before suffix letter)
    m = re.match(r"^(?:pantone\s*)?(\S+?)([CcUuMm])$", ql)
    if m:
        num, suffix = m.group(1), m.group(2).upper()
        candidates.append(_normalize_key(f"pantone {num} {suffix}"))

    # If no suffix at all, try appending C (most common)
    has_suffix = any(ql.rstrip().endswith(s) for s in ("c", "u", "m", " coated", " uncoated", " matte"))
    if not has_suffix:
        for s in ("c", "u", "m"):
            candidates.append(_normalize_key(ql + " " + s))
            if not ql.startswith("pantone"):
                candidates.append(_normalize_key("pantone " + ql + " " + s))

    return candidates


def _fuzzy_score(query: str, candidate_name: str) -> float:
    """Simple similarity score (0-1) between a query and a Pantone name.

    Uses token overlap + substring matching — good enough for
    'pantone 485' matching 'Pantone 485 C'.
    """
    q_tokens = set(query.lower().split())
    c_tokens = set(candidate_name.lower().split())
    if not q_tokens:
        return 0.0
    # Exclude common words that don't help distinguish colors
    noise = {"pantone", "c", "u", "m"}
    q_meaningful = q_tokens - noise
    c_meaningful = c_tokens - noise
    if not q_meaningful:
        # Query is only noise words like "Pantone C" — use full token set
        overlap = len(q_tokens & c_tokens)
        return overlap / max(len(q_tokens), len(c_tokens))
    overlap = len(q_meaningful & c_meaningful)
    score = overlap / max(len(q_meaningful), len(c_meaningful))
    # Bonus if the meaningful part of query is a substring of candidate
    q_core = " ".join(sorted(q_meaningful))
    c_core = " ".join(sorted(c_meaningful))
    if q_core in c_core or c_core in q_core:
        score += 0.3
    return min(score, 1.0)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def pantone_to_cmyk(pantone_name: str) -> PantoneResult:
    """Look up CMYK values for a Pantone color name with fuzzy matching.

    Handles variations like ``"485C"``, ``"pantone 485"``,
    ``"485 coated"``, ``"Pantone 485 C"``, etc.

    Args:
        pantone_name: Pantone color name or shorthand.

    Returns:
        Dict with ``name``, ``c``, ``m``, ``y``, ``k``, and ``hex``.

    Raises:
        ValueError: If no matching color is found.
    """
    lookup = _build_lookup()
    candidates = _expand_query(pantone_name)
    for key in candidates:
        if key in lookup:
            entry = lookup[key]
            rgb = cmyk_to_rgb(entry["c"], entry["m"], entry["y"], entry["k"])
            return {
                "name": entry["name"],
                "c": entry["c"],
                "m": entry["m"],
                "y": entry["y"],
                "k": entry["k"],
                "hex": rgb["hex"],
            }

    # Fallback: fuzzy best-match
    best_score = 0.0
    best_entry = None
    for entry in _load_db():
        score = _fuzzy_score(pantone_name, entry["name"])
        if score > best_score:
            best_score = score
            best_entry = entry
    if best_entry and best_score >= 0.5:
        rgb = cmyk_to_rgb(best_entry["c"], best_entry["m"], best_entry["y"], best_entry["k"])
        return {
            "name": best_entry["name"],
            "c": best_entry["c"],
            "m": best_entry["m"],
            "y": best_entry["y"],
            "k": best_entry["k"],
            "hex": rgb["hex"],
        }

    raise ValueError(
        f"Unknown Pantone color: {pantone_name!r}. "
        f"Try a format like 'Pantone 485 C', '485C', or '485 coated'."
    )


def pantone_search(
    *,
    hex_color: str | None = None,
    c: float | None = None,
    m: float | None = None,
    y: float | None = None,
    k: float | None = None,
    limit: int = 5,
) -> PantoneSearchResult:
    """Search for the closest Pantone colors by HEX or CMYK proximity.

    Provide **either** ``hex_color`` or CMYK values. Returns the closest
    ``limit`` matches ranked by Delta E.

    Args:
        hex_color: HEX color string (e.g. ``"#DA291C"``).
        c: Cyan (0-100).
        m: Magenta (0-100).
        y: Yellow (0-100).
        k: Key/Black (0-100).
        limit: Number of results to return (default 5).

    Returns:
        Dict with ``matches`` list and ``search_type``.

    Raises:
        ValueError: If neither hex nor CMYK is provided, or values are invalid.
    """
    if hex_color is not None:
        r, g, b = _hex_to_rgb(hex_color)
        target_lab = _rgb_to_lab(r, g, b)
        search_type = f"hex {hex_color}"
    elif all(v is not None for v in (c, m, y, k)):
        assert c is not None and m is not None and y is not None and k is not None
        for name, val in [("c", c), ("m", m), ("y", y), ("k", k)]:
            if not (0 <= val <= 100):
                raise ValueError(f"{name} must be between 0 and 100, got {val}")
        target_lab = _cmyk_to_lab(c, m, y, k)
        search_type = f"cmyk({c},{m},{y},{k})"
    else:
        raise ValueError("Provide either hex_color or all four CMYK values (c, m, y, k).")

    scored: list[tuple[float, dict]] = []
    for entry in _load_db():
        entry_lab = _cmyk_to_lab(entry["c"], entry["m"], entry["y"], entry["k"])
        de = math.sqrt(sum((a - b) ** 2 for a, b in zip(target_lab, entry_lab)))
        scored.append((de, entry))
    scored.sort(key=lambda x: x[0])

    matches: list[PantoneResult] = []
    for de, entry in scored[:limit]:
        rgb = cmyk_to_rgb(entry["c"], entry["m"], entry["y"], entry["k"])
        matches.append({
            "name": entry["name"],
            "c": entry["c"],
            "m": entry["m"],
            "y": entry["y"],
            "k": entry["k"],
            "hex": rgb["hex"],
        })
    return {"matches": matches, "search_type": search_type}


# ---------------------------------------------------------------------------
# CMYK <-> RGB conversion
# ---------------------------------------------------------------------------


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    """Clamp a numeric value to [lo, hi]."""
    return max(lo, min(hi, value))


def cmyk_to_rgb(c: float, m: float, y: float, k: float) -> RGBResult:
    """Convert CMYK (0-100 per channel) to RGB and HEX.

    Args:
        c: Cyan (0-100).
        m: Magenta (0-100).
        y: Yellow (0-100).
        k: Key/Black (0-100).

    Returns:
        Dict with ``r``, ``g``, ``b`` (0-255) and ``hex`` string.

    Raises:
        ValueError: If any input is outside 0-100.
    """
    for name, val in [("c", c), ("m", m), ("y", y), ("k", k)]:
        if not (0 <= val <= 100):
            raise ValueError(f"{name} must be between 0 and 100, got {val}")

    c_f, m_f, y_f, k_f = c / 100, m / 100, y / 100, k / 100
    r = round(255 * (1 - c_f) * (1 - k_f))
    g = round(255 * (1 - m_f) * (1 - k_f))
    b = round(255 * (1 - y_f) * (1 - k_f))
    r = int(_clamp(r, 0, 255))
    g = int(_clamp(g, 0, 255))
    b = int(_clamp(b, 0, 255))
    return {"r": r, "g": g, "b": b, "hex": f"#{r:02X}{g:02X}{b:02X}"}


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Parse a hex color string to (r, g, b)."""
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = h[0] * 2 + h[1] * 2 + h[2] * 2
    if len(h) != 6:
        raise ValueError(f"Invalid hex color: {hex_color!r}")
    try:
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    except ValueError:
        raise ValueError(f"Invalid hex color: {hex_color!r}")


# ---------------------------------------------------------------------------
# Color-space conversions for Delta E
# ---------------------------------------------------------------------------

def _linearize(v: int) -> float:
    """sRGB (0-255) to linear."""
    s = v / 255.0
    return s / 12.92 if s <= 0.04045 else ((s + 0.055) / 1.055) ** 2.4


def _rgb_to_xyz(r: int, g: int, b: int) -> tuple[float, float, float]:
    """Convert sRGB to CIE XYZ (D65)."""
    rl, gl, bl = _linearize(r), _linearize(g), _linearize(b)
    x = 0.4124564 * rl + 0.3575761 * gl + 0.1804375 * bl
    y = 0.2126729 * rl + 0.7151522 * gl + 0.0721750 * bl
    z = 0.0193339 * rl + 0.1191920 * gl + 0.9503041 * bl
    return x, y, z


def _rgb_to_lab(r: int, g: int, b: int) -> tuple[float, float, float]:
    """Convert sRGB to CIELAB."""
    return _xyz_to_lab(*_rgb_to_xyz(r, g, b))


def _cmyk_to_xyz(c: float, m: float, y: float, k: float) -> tuple[float, float, float]:
    """Convert CMYK to CIE XYZ (D65) via an intermediate RGB step."""
    rgb = cmyk_to_rgb(c, m, y, k)
    return _rgb_to_xyz(rgb["r"], rgb["g"], rgb["b"])


def _xyz_to_lab(x: float, y: float, z: float) -> tuple[float, float, float]:
    """Convert CIE XYZ to CIELAB (D65 illuminant)."""
    xn, yn, zn = 0.95047, 1.00000, 1.08883

    def f(t: float) -> float:
        delta = 6 / 29
        if t > delta ** 3:
            return t ** (1 / 3)
        return t / (3 * delta ** 2) + 4 / 29

    fx, fy, fz = f(x / xn), f(y / yn), f(z / zn)
    l_star = 116 * fy - 16
    a_star = 500 * (fx - fy)
    b_star = 200 * (fy - fz)
    return l_star, a_star, b_star


def _cmyk_to_lab(c: float, m: float, y: float, k: float) -> tuple[float, float, float]:
    """Convert CMYK to CIELAB."""
    return _xyz_to_lab(*_cmyk_to_xyz(c, m, y, k))


def color_delta_e(
    c1: float, m1: float, y1: float, k1: float,
    c2: float, m2: float, y2: float, k2: float,
) -> DeltaEResult:
    """Calculate Delta E (CIE76) between two CMYK colors.

    Args:
        c1, m1, y1, k1: First color CMYK values (0-100 each).
        c2, m2, y2, k2: Second color CMYK values (0-100 each).

    Returns:
        Dict with ``delta_e`` and human-readable ``interpretation``.

    Raises:
        ValueError: If any CMYK value is outside 0-100.
    """
    for name, val in [
        ("c1", c1), ("m1", m1), ("y1", y1), ("k1", k1),
        ("c2", c2), ("m2", m2), ("y2", y2), ("k2", k2),
    ]:
        if not (0 <= val <= 100):
            raise ValueError(f"{name} must be between 0 and 100, got {val}")

    l1, a1, b1 = _cmyk_to_lab(c1, m1, y1, k1)
    l2, a2, b2 = _cmyk_to_lab(c2, m2, y2, k2)
    de = math.sqrt((l2 - l1) ** 2 + (a2 - a1) ** 2 + (b2 - b1) ** 2)
    de = round(de, 2)

    if de < 1:
        interp = "excellent — imperceptible difference"
    elif de < 3:
        interp = "good — barely perceptible"
    elif de < 6:
        interp = "fair — noticeable difference"
    else:
        interp = "poor — obvious difference"

    return {"delta_e": de, "interpretation": interp}
