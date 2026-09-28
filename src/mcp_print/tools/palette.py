"""User-supplied local color palette: loading, validation, lookup, and proximity search.

mcp-print ships no color library. Palette-based features read a JSON file
that the user points to explicitly via the ``MCP_PRINT_PALETTE_PATH``
environment variable. Nothing is downloaded, and there is no built-in
fallback table: if no palette is configured, palette features return an
error and every other tool keeps working.

Palette file schema::

    {
      "palette": "Optional label shown in results",
      "colors": [
        {"name": "Harbor Blue", "c": 88, "m": 42, "y": 8, "k": 4}
      ]
    }

Distances are computed from the stored CMYK numbers through a simple,
profile-less CMYK -> sRGB -> CIELAB conversion. They express approximate
similarity between entries of the user's own palette, not the accuracy of
any published color reference or how a color will print.
"""

from __future__ import annotations

import json
import math
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict

from mcp_print.tools.colors import (
    _cmyk_to_lab,
    _delta_e_2000,
    _hex_to_rgb,
    _rgb_to_lab,
    cmyk_to_rgb,
)

PALETTE_ENV_VAR = "MCP_PRINT_PALETTE_PATH"
SOURCE_LABEL = "user_palette"
DELTA_E_METHOD = "ciede2000"
APPROXIMATION_NOTE = (
    "Values come from your local palette file. Distances use a simple CMYK -> sRGB "
    "-> Lab conversion without an ICC profile, so they are approximate on-screen "
    "similarity within your palette, not catalog accuracy or a guarantee of "
    "printed results."
)

_MAX_FILE_BYTES = 10 * 1024 * 1024
_MAX_NAME_LENGTH = 200
_MAX_SEARCH_LIMIT = 100
_TOP_LEVEL_KEYS = {"palette", "colors"}
_ENTRY_KEYS = {"name", "c", "m", "y", "k"}
_CHANNELS = ("c", "m", "y", "k")


# ---------------------------------------------------------------------------
# Types & errors
# ---------------------------------------------------------------------------


class PaletteColorResult(TypedDict):
    name: str
    c: float
    m: float
    y: float
    k: float
    hex: str


class PaletteError(ValueError):
    """The palette file is missing, unreadable, or invalid."""


class PaletteNotConfiguredError(PaletteError):
    """``MCP_PRINT_PALETTE_PATH`` is not set."""


class PaletteColorNotFoundError(PaletteError):
    """A requested name is not in the palette (exact, normalized match)."""

    def __init__(self, message: str, suggestions: list[str]) -> None:
        super().__init__(message)
        self.suggestions = suggestions


@dataclass(frozen=True)
class Palette:
    label: str | None
    colors: tuple[dict, ...]


# ---------------------------------------------------------------------------
# Loading & validation
# ---------------------------------------------------------------------------

_CACHE: dict[tuple[str, int, int], Palette] = {}


def _normalize_key(name: str) -> str:
    """Canonical lookup key: lowercase, stripped, collapsed whitespace."""
    return re.sub(r"\s+", " ", name.strip().lower())


def _reject_constant(token: str) -> float:
    raise PaletteError(
        f"Palette file contains the non-standard JSON value {token}; "
        "use plain numbers between 0 and 100."
    )


def _palette_path() -> Path:
    raw = os.environ.get(PALETTE_ENV_VAR, "").strip()
    if not raw:
        raise PaletteNotConfiguredError(
            f"No color palette configured. Set {PALETTE_ENV_VAR} to the path of a "
            "local palette JSON file you are entitled to use (see the README section "
            "'Local color palette'). mcp-print does not ship or download color libraries."
        )
    return Path(os.path.expanduser(raw))


def _validate_entry(index: int, entry: object) -> dict:
    where = f"colors[{index}]"
    if not isinstance(entry, dict):
        raise PaletteError(f"{where} must be an object with name, c, m, y, k.")

    unknown = sorted(set(entry) - _ENTRY_KEYS)
    if unknown:
        raise PaletteError(
            f"{where} has unsupported field(s) {', '.join(unknown)}; "
            "allowed fields are name, c, m, y, k."
        )
    missing = [key for key in ("name", *_CHANNELS) if key not in entry]
    if missing:
        raise PaletteError(f"{where} is missing required field(s) {', '.join(missing)}.")

    name = entry["name"]
    if not isinstance(name, str) or not name.strip():
        raise PaletteError(f"{where}.name must be a non-empty string.")
    if len(name) > _MAX_NAME_LENGTH:
        raise PaletteError(f"{where}.name is longer than {_MAX_NAME_LENGTH} characters.")

    clean: dict = {"name": name.strip()}
    for key in _CHANNELS:
        value = entry[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise PaletteError(f"{where}.{key} must be a number, got {type(value).__name__}.")
        if isinstance(value, float) and not math.isfinite(value):
            raise PaletteError(f"{where}.{key} must be a finite number.")
        if not 0 <= value <= 100:
            raise PaletteError(f"{where}.{key} must be between 0 and 100.")
        clean[key] = value
    return clean


def _parse_palette(text: str) -> Palette:
    try:
        data = json.loads(text, parse_constant=_reject_constant)
    except json.JSONDecodeError as exc:
        raise PaletteError(
            f"Palette file is not valid JSON (line {exc.lineno}, column {exc.colno}: {exc.msg})."
        ) from None

    if not isinstance(data, dict):
        raise PaletteError('Palette file must be a JSON object like {"colors": [...]}.')
    unknown = sorted(set(data) - _TOP_LEVEL_KEYS)
    if unknown:
        raise PaletteError(
            f"Palette file has unsupported top-level field(s) {', '.join(unknown)}; "
            "allowed fields are palette, colors."
        )

    label = data.get("palette")
    if label is not None and (not isinstance(label, str) or not label.strip()):
        raise PaletteError('"palette" must be a non-empty string when present.')

    raw_colors = data.get("colors")
    if not isinstance(raw_colors, list):
        raise PaletteError('Palette file must contain a "colors" list.')
    if not raw_colors:
        raise PaletteError('Palette "colors" list is empty.')

    colors = [_validate_entry(i, entry) for i, entry in enumerate(raw_colors)]

    seen: dict[str, int] = {}
    for i, color in enumerate(colors):
        key = _normalize_key(color["name"])
        if key in seen:
            raise PaletteError(
                f"colors[{seen[key]}] and colors[{i}] have the same name "
                "(names are compared case- and whitespace-insensitively). "
                "Give each entry a unique name."
            )
        seen[key] = i

    return Palette(label=label.strip() if label else None, colors=tuple(colors))


def load_palette() -> Palette:
    """Load and validate the palette named by ``MCP_PRINT_PALETTE_PATH``.

    The parsed palette is cached per path, modification time, and size, so
    edits to the file are picked up without restarting the server.

    Raises:
        PaletteNotConfiguredError: If the environment variable is unset.
        PaletteError: If the file is missing, unreadable, or invalid.
    """
    path = _palette_path()
    try:
        stat = path.stat()
    except FileNotFoundError:
        raise PaletteError(f"Palette file not found: {path}") from None
    except OSError as exc:
        raise PaletteError(f"Cannot access palette file {path}: {exc.strerror}") from None
    if not path.is_file():
        raise PaletteError(f"Palette path is not a file: {path}")
    if stat.st_size > _MAX_FILE_BYTES:
        raise PaletteError(
            f"Palette file is larger than {_MAX_FILE_BYTES // (1024 * 1024)} MB: {path}"
        )

    cache_key = (str(path.resolve()), stat.st_mtime_ns, stat.st_size)
    cached = _CACHE.get(cache_key)
    if cached is not None:
        return cached

    try:
        text = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        raise PaletteError(f"Palette file is not UTF-8 text: {path}") from None
    except OSError as exc:
        raise PaletteError(f"Cannot read palette file {path}: {exc.strerror}") from None

    palette = _parse_palette(text)
    _CACHE.clear()
    _CACHE[cache_key] = palette
    return palette


# ---------------------------------------------------------------------------
# Name matching (suggestions only — never substituted for the requested name)
# ---------------------------------------------------------------------------


def _name_similarity(query: str, candidate: str) -> float:
    """Token-overlap similarity (0-1) with a substring bonus."""
    q_tokens = set(_normalize_key(query).split())
    c_tokens = set(_normalize_key(candidate).split())
    if not q_tokens or not c_tokens:
        return 0.0
    score = len(q_tokens & c_tokens) / max(len(q_tokens), len(c_tokens))
    q_core = " ".join(sorted(q_tokens))
    c_core = " ".join(sorted(c_tokens))
    if q_core in c_core or c_core in q_core:
        score += 0.3
    return min(score, 1.0)


def _color_result(entry: dict) -> PaletteColorResult:
    return {
        "name": entry["name"],
        "c": entry["c"],
        "m": entry["m"],
        "y": entry["y"],
        "k": entry["k"],
        "hex": cmyk_to_rgb(entry["c"], entry["m"], entry["y"], entry["k"])["hex"],
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def palette_lookup(name: str) -> dict:
    """Look up a color in the user palette by name.

    Matching is exact after normalizing case and whitespace. Names are
    returned exactly as written in the palette; no prefixes or finish
    variants are generated. When there is no exact match, close names are
    offered as suggestions but never returned as the result.

    Raises:
        PaletteNotConfiguredError: If no palette is configured.
        PaletteError: If the palette file is invalid.
        PaletteColorNotFoundError: If the name is not in the palette.
        ValueError: If ``name`` is empty.
    """
    if not isinstance(name, str) or not name.strip():
        raise ValueError("name must be a non-empty string")

    palette = load_palette()
    key = _normalize_key(name)
    for entry in palette.colors:
        if _normalize_key(entry["name"]) == key:
            return {
                "color": _color_result(entry),
                "source": SOURCE_LABEL,
                "palette": palette.label,
                "note": APPROXIMATION_NOTE,
            }

    scored = sorted(
        ((_name_similarity(name, e["name"]), e["name"]) for e in palette.colors),
        key=lambda item: -item[0],
    )
    suggestions = [n for score, n in scored if score >= 0.5][:5]
    raise PaletteColorNotFoundError(
        f"{name!r} is not in the configured palette.", suggestions
    )


def _target_lab(
    hex_color: str | None,
    c: float | None,
    m: float | None,
    y: float | None,
    k: float | None,
) -> tuple[tuple[float, float, float], str]:
    if hex_color is not None:
        r, g, b = _hex_to_rgb(hex_color)
        return _rgb_to_lab(r, g, b), f"hex {hex_color}"
    if all(v is not None for v in (c, m, y, k)):
        assert c is not None and m is not None and y is not None and k is not None
        for label, val in [("c", c), ("m", m), ("y", y), ("k", k)]:
            if not (0 <= val <= 100):
                raise ValueError(f"{label} must be between 0 and 100, got {val}")
        return _cmyk_to_lab(c, m, y, k), f"cmyk({c},{m},{y},{k})"
    raise ValueError("Provide either hex_color or all four CMYK values (c, m, y, k).")


def _ranked(palette: Palette, target_lab: tuple[float, float, float]) -> list[tuple[float, dict]]:
    scored = [
        (_delta_e_2000(target_lab, _cmyk_to_lab(e["c"], e["m"], e["y"], e["k"])), e)
        for e in palette.colors
    ]
    scored.sort(key=lambda item: item[0])
    return scored


def palette_search(
    *,
    hex_color: str | None = None,
    c: float | None = None,
    m: float | None = None,
    y: float | None = None,
    k: float | None = None,
    limit: int = 5,
) -> dict:
    """Find the palette entries closest to a HEX or CMYK value.

    Provide **either** ``hex_color`` or all four CMYK values. Matches are
    ranked by CIEDE2000 on approximate Lab values.

    Raises:
        PaletteNotConfiguredError: If no palette is configured.
        PaletteError: If the palette file is invalid.
        ValueError: If inputs are missing or out of range.
    """
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= _MAX_SEARCH_LIMIT:
        raise ValueError(f"limit must be an integer between 1 and {_MAX_SEARCH_LIMIT}, got {limit}")
    target_lab, search_type = _target_lab(hex_color, c, m, y, k)

    palette = load_palette()
    matches = [
        {**_color_result(entry), "delta_e": round(de, 2)}
        for de, entry in _ranked(palette, target_lab)[:limit]
    ]
    return {
        "matches": matches,
        "search_type": search_type,
        "delta_e_method": DELTA_E_METHOD,
        "source": SOURCE_LABEL,
        "palette": palette.label,
        "note": APPROXIMATION_NOTE,
    }


def nearest_palette_color(
    palette: Palette, c: float, m: float, y: float, k: float,
) -> tuple[dict, float]:
    """Return the closest palette entry to a CMYK color and its Delta E."""
    de, entry = _ranked(palette, _cmyk_to_lab(c, m, y, k))[0]
    return entry, round(de, 2)
