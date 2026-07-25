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


class CMYKResult(TypedDict):
    c: float
    m: float
    y: float
    k: float
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
    method: str
    interpretation: str


class LabResult(TypedDict):
    l: float
    a: float
    b: float


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


def rgb_to_cmyk(
    r: int | None = None,
    g: int | None = None,
    b: int | None = None,
    hex_color: str | None = None,
) -> CMYKResult:
    """Convert RGB (0-255) or a HEX string to CMYK (0-100 per channel).

    Provide **either** ``hex_color`` or all three RGB values.

    Args:
        r: Red (0-255).
        g: Green (0-255).
        b: Blue (0-255).
        hex_color: HEX color string (e.g. ``"#DA291C"``).

    Returns:
        Dict with ``c``, ``m``, ``y``, ``k`` (0-100) and the ``hex`` echo.

    Raises:
        ValueError: If inputs are missing or out of range.
    """
    if hex_color is not None:
        r, g, b = _hex_to_rgb(hex_color)
    elif r is None or g is None or b is None:
        raise ValueError("Provide either hex_color or all three RGB values (r, g, b).")

    for name, val in [("r", r), ("g", g), ("b", b)]:
        if not (0 <= val <= 255):
            raise ValueError(f"{name} must be between 0 and 255, got {val}")

    r_f, g_f, b_f = r / 255, g / 255, b / 255
    k_f = 1 - max(r_f, g_f, b_f)
    if k_f >= 1.0:
        c_f = m_f = y_f = 0.0
    else:
        c_f = (1 - r_f - k_f) / (1 - k_f)
        m_f = (1 - g_f - k_f) / (1 - k_f)
        y_f = (1 - b_f - k_f) / (1 - k_f)

    return {
        "c": round(c_f * 100, 1),
        "m": round(m_f * 100, 1),
        "y": round(y_f * 100, 1),
        "k": round(k_f * 100, 1),
        "hex": f"#{r:02X}{g:02X}{b:02X}",
    }


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


def _delta_e_2000(
    lab1: tuple[float, float, float],
    lab2: tuple[float, float, float],
) -> float:
    """CIEDE2000 color difference (kL = kC = kH = 1)."""
    l1, a1, b1 = lab1
    l2, a2, b2 = lab2

    c1 = math.hypot(a1, b1)
    c2 = math.hypot(a2, b2)
    c_bar = (c1 + c2) / 2
    g = 0.5 * (1 - math.sqrt(c_bar ** 7 / (c_bar ** 7 + 25 ** 7)))
    a1p, a2p = a1 * (1 + g), a2 * (1 + g)
    c1p, c2p = math.hypot(a1p, b1), math.hypot(a2p, b2)

    h1p = math.degrees(math.atan2(b1, a1p)) % 360 if (a1p or b1) else 0.0
    h2p = math.degrees(math.atan2(b2, a2p)) % 360 if (a2p or b2) else 0.0

    dl = l2 - l1
    dc = c2p - c1p
    if c1p * c2p == 0:
        dhp = 0.0
    else:
        diff = h2p - h1p
        if abs(diff) <= 180:
            dhp = diff
        elif diff > 180:
            dhp = diff - 360
        else:
            dhp = diff + 360
    dh = 2 * math.sqrt(c1p * c2p) * math.sin(math.radians(dhp) / 2)

    l_bar = (l1 + l2) / 2
    c_bar_p = (c1p + c2p) / 2
    if c1p * c2p == 0:
        h_bar = h1p + h2p
    elif abs(h1p - h2p) <= 180:
        h_bar = (h1p + h2p) / 2
    elif h1p + h2p < 360:
        h_bar = (h1p + h2p + 360) / 2
    else:
        h_bar = (h1p + h2p - 360) / 2

    t = (
        1
        - 0.17 * math.cos(math.radians(h_bar - 30))
        + 0.24 * math.cos(math.radians(2 * h_bar))
        + 0.32 * math.cos(math.radians(3 * h_bar + 6))
        - 0.20 * math.cos(math.radians(4 * h_bar - 63))
    )
    sl = 1 + 0.015 * (l_bar - 50) ** 2 / math.sqrt(20 + (l_bar - 50) ** 2)
    sc = 1 + 0.045 * c_bar_p
    sh = 1 + 0.015 * c_bar_p * t
    d_theta = 30 * math.exp(-(((h_bar - 275) / 25) ** 2))
    rc = 2 * math.sqrt(c_bar_p ** 7 / (c_bar_p ** 7 + 25 ** 7))
    rt = -rc * math.sin(math.radians(2 * d_theta))

    return math.sqrt(
        (dl / sl) ** 2
        + (dc / sc) ** 2
        + (dh / sh) ** 2
        + rt * (dc / sc) * (dh / sh)
    )


def color_delta_e(
    c1: float, m1: float, y1: float, k1: float,
    c2: float, m2: float, y2: float, k2: float,
    method: str = "cie76",
) -> DeltaEResult:
    """Calculate Delta E between two CMYK colors.

    Args:
        c1, m1, y1, k1: First color CMYK values (0-100 each).
        c2, m2, y2, k2: Second color CMYK values (0-100 each).
        method: ``cie76`` (fast, legacy) or ``ciede2000``
            (industry standard, perceptually accurate).

    Returns:
        Dict with ``delta_e``, ``method``, and human-readable
        ``interpretation``.

    Raises:
        ValueError: If any CMYK value is outside 0-100 or method is unknown.
    """
    for name, val in [
        ("c1", c1), ("m1", m1), ("y1", y1), ("k1", k1),
        ("c2", c2), ("m2", m2), ("y2", y2), ("k2", k2),
    ]:
        if not (0 <= val <= 100):
            raise ValueError(f"{name} must be between 0 and 100, got {val}")

    meth = method.lower()
    if meth not in ("cie76", "ciede2000"):
        raise ValueError(f"Unknown method: {method!r}. Choose from: cie76, ciede2000")

    lab1 = _cmyk_to_lab(c1, m1, y1, k1)
    lab2 = _cmyk_to_lab(c2, m2, y2, k2)
    if meth == "ciede2000":
        de = _delta_e_2000(lab1, lab2)
    else:
        de = math.sqrt(sum((a - b) ** 2 for a, b in zip(lab1, lab2)))
    de = round(de, 2)

    if de < 1:
        interp = "excellent — imperceptible difference"
    elif de < 3:
        interp = "good — barely perceptible"
    elif de < 6:
        interp = "fair — noticeable difference"
    else:
        interp = "poor — obvious difference"

    return {"delta_e": de, "method": meth, "interpretation": interp}


# ---------------------------------------------------------------------------
# Lab conversion public API
# ---------------------------------------------------------------------------


def _lab_to_rgb(l_star: float, a_star: float, b_star: float) -> tuple[int, int, int]:
    """Convert CIELAB (D65) to sRGB (0-255), clamped to gamut."""
    fy = (l_star + 16) / 116
    fx = fy + a_star / 500
    fz = fy - b_star / 200
    delta = 6 / 29

    def f_inv(t: float) -> float:
        if t > delta:
            return t ** 3
        return 3 * delta ** 2 * (t - 4 / 29)

    xn, yn, zn = 0.95047, 1.00000, 1.08883
    x, y, z = f_inv(fx) * xn, f_inv(fy) * yn, f_inv(fz) * zn

    rl = 3.2404542 * x - 1.5371385 * y - 0.4985314 * z
    gl = -0.9692660 * x + 1.8760108 * y + 0.0415560 * z
    bl = 0.0556434 * x - 0.2040259 * y + 1.0572252 * z

    def gamma(v: float) -> int:
        v = max(0.0, min(1.0, v))
        s = 12.92 * v if v <= 0.0031308 else 1.055 * v ** (1 / 2.4) - 0.055
        return round(max(0.0, min(1.0, s)) * 255)

    return gamma(rl), gamma(gl), gamma(bl)


def lab_convert(
    *,
    l: float | None = None,
    a: float | None = None,
    b: float | None = None,
    c: float | None = None,
    m: float | None = None,
    y: float | None = None,
    k: float | None = None,
    hex_color: str | None = None,
) -> dict:
    """Convert between CIELAB and CMYK/RGB/HEX.

    Provide exactly one input: Lab (l, a, b), CMYK (c, m, y, k), or
    hex_color. Returns the color expressed in every space.

    Args:
        l: Lightness L* (0-100).
        a: a* axis (green-red, typically -128 to 127).
        b: b* axis (blue-yellow, typically -128 to 127).
        c: Cyan (0-100).
        m: Magenta (0-100).
        y: Yellow (0-100).
        k: Key/Black (0-100).
        hex_color: HEX color string.

    Returns:
        Dict with ``lab``, ``cmyk``, ``rgb``, ``hex``, and ``source``.

    Raises:
        ValueError: If no input, conflicting inputs, or out-of-range values.
    """
    has_lab = all(v is not None for v in (l, a, b))
    has_cmyk = all(v is not None for v in (c, m, y, k))
    has_hex = hex_color is not None

    if sum([has_lab, has_cmyk, has_hex]) != 1:
        raise ValueError(
            "Provide exactly one input: Lab (l, a, b), CMYK (c, m, y, k), or hex_color."
        )

    if has_lab:
        assert l is not None and a is not None and b is not None
        if not (0 <= l <= 100):
            raise ValueError(f"l must be between 0 and 100, got {l}")
        r_v, g_v, b_v = _lab_to_rgb(l, a, b)
        lab = (round(l, 2), round(a, 2), round(b, 2))
        source = "lab"
    elif has_cmyk:
        assert c is not None and m is not None and y is not None and k is not None
        rgb = cmyk_to_rgb(c, m, y, k)
        r_v, g_v, b_v = rgb["r"], rgb["g"], rgb["b"]
        lab = tuple(round(v, 2) for v in _cmyk_to_lab(c, m, y, k))
        source = f"cmyk({c},{m},{y},{k})"
    else:
        assert hex_color is not None
        r_v, g_v, b_v = _hex_to_rgb(hex_color)
        lab = tuple(round(v, 2) for v in _rgb_to_lab(r_v, g_v, b_v))
        source = f"hex {hex_color}"

    cmyk = rgb_to_cmyk(r=r_v, g=g_v, b=b_v)
    return {
        "lab": {"l": lab[0], "a": lab[1], "b": lab[2]},
        "cmyk": {"c": cmyk["c"], "m": cmyk["m"], "y": cmyk["y"], "k": cmyk["k"]},
        "rgb": {"r": r_v, "g": g_v, "b": b_v},
        "hex": f"#{r_v:02X}{g_v:02X}{b_v:02X}",
        "source": source,
    }
