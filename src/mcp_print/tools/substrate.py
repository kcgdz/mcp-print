"""Substrate color shift simulator — models dot gain, ink absorption, and paper tint."""

from __future__ import annotations

from typing import TypedDict

from mcp_print.tools.colors import cmyk_to_rgb, color_delta_e

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


class SubstrateProfile(TypedDict):
    dot_gain: dict[str, float]  # per print method
    absorption: float  # 0-1, K increase factor
    whiteness: float  # 0-100 (100 = perfect white)
    tint: dict[str, float]  # CMYK offsets from paper color


class SubstrateResult(TypedDict):
    original: dict  # {c, m, y, k, hex}
    simulated: dict  # {c, m, y, k, hex}
    substrate: str
    print_method: str
    adjustments: dict  # {dot_gain_applied, absorption_k_added, tint_offsets}
    delta_e_from_original: float
    warning: str


# ---------------------------------------------------------------------------
# Substrate profiles
# ---------------------------------------------------------------------------

_SUBSTRATES: dict[str, SubstrateProfile] = {
    "glossy_coated": {
        "dot_gain": {"offset": 12, "digital": 5, "flexo": 15},
        "absorption": 0.02,
        "whiteness": 95,
        "tint": {"c": 0, "m": 0, "y": 0, "k": 0},
    },
    "matte_coated": {
        "dot_gain": {"offset": 18, "digital": 8, "flexo": 20},
        "absorption": 0.05,
        "whiteness": 92,
        "tint": {"c": 0, "m": 0, "y": 1, "k": 0},
    },
    "uncoated": {
        "dot_gain": {"offset": 22, "digital": 12, "flexo": 25},
        "absorption": 0.10,
        "whiteness": 88,
        "tint": {"c": 0, "m": 1, "y": 2, "k": 0},
    },
    "newsprint": {
        "dot_gain": {"offset": 30, "digital": 18, "flexo": 35},
        "absorption": 0.18,
        "whiteness": 72,
        "tint": {"c": 0, "m": 2, "y": 5, "k": 3},
    },
    "kraft": {
        "dot_gain": {"offset": 25, "digital": 15, "flexo": 30},
        "absorption": 0.15,
        "whiteness": 55,
        "tint": {"c": 0, "m": 6, "y": 15, "k": 8},
    },
    "recycled": {
        "dot_gain": {"offset": 25, "digital": 14, "flexo": 28},
        "absorption": 0.12,
        "whiteness": 78,
        "tint": {"c": 0, "m": 1, "y": 3, "k": 2},
    },
}

_VALID_METHODS: set[str] = {"offset", "digital", "flexo"}


# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------


def _apply_dot_gain(value: float, gain_percent: float) -> float:
    """Apply midtone-weighted dot gain: heavier effect at 50%, less at extremes."""
    return value + (gain_percent / 100) * value * (1 - value / 100)


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def substrate_simulator(
    *,
    c: float,
    m: float,
    y: float,
    k: float,
    substrate: str = "uncoated",
    print_method: str = "offset",
) -> SubstrateResult:
    """Simulate how CMYK values shift on a given substrate and print method.

    Models dot gain (Murray-Davies), ink absorption, and paper tint.

    Args:
        c: Cyan (0-100).
        m: Magenta (0-100).
        y: Yellow (0-100).
        k: Key/Black (0-100).
        substrate: One of glossy_coated, matte_coated, uncoated, newsprint,
                   kraft, or recycled.
        print_method: One of offset, digital, or flexo.

    Returns:
        Dict with original, simulated, substrate info, adjustments,
        delta_e_from_original, and warning message.

    Raises:
        ValueError: If inputs are invalid.
    """
    # Validate
    for name, val in [("c", c), ("m", m), ("y", y), ("k", k)]:
        if not (0 <= val <= 100):
            raise ValueError(f"{name} must be between 0 and 100, got {val}.")

    substrate = substrate.lower()
    print_method = print_method.lower()

    if substrate not in _SUBSTRATES:
        raise ValueError(f"Unknown substrate: {substrate!r}. Must be one of {sorted(_SUBSTRATES)}.")
    if print_method not in _VALID_METHODS:
        raise ValueError(f"Unknown print_method: {print_method!r}. Must be one of {sorted(_VALID_METHODS)}.")

    profile = _SUBSTRATES[substrate]
    gain = profile["dot_gain"].get(print_method, profile["dot_gain"]["offset"])

    # Step 1: dot gain
    c_new = _apply_dot_gain(c, gain)
    m_new = _apply_dot_gain(m, gain)
    y_new = _apply_dot_gain(y, gain)
    k_new = _apply_dot_gain(k, gain)

    # Step 2: ink absorption — K increases
    absorption_k = profile["absorption"] * (100 - k)  # more room to absorb when K is low
    k_new += absorption_k

    # Step 3: paper tint
    tint = profile["tint"]
    c_new += tint["c"]
    m_new += tint["m"]
    y_new += tint["y"]
    k_new += tint["k"]

    # Clamp
    c_new = round(_clamp(c_new), 1)
    m_new = round(_clamp(m_new), 1)
    y_new = round(_clamp(y_new), 1)
    k_new = round(_clamp(k_new), 1)

    # Convert to HEX
    orig_rgb = cmyk_to_rgb(c, m, y, k)
    sim_rgb = cmyk_to_rgb(c_new, m_new, y_new, k_new)

    # Delta E
    de_result = color_delta_e(c, m, y, k, c_new, m_new, y_new, k_new)
    delta_e = de_result["delta_e"]

    # Warning
    if delta_e < 3:
        warning = "Minimal color shift — output should closely match proof."
    elif delta_e < 6:
        warning = "Noticeable color shift — consider adjusting ink density or substrate."
    elif delta_e < 10:
        warning = "Significant color shift — substrate compensation curves recommended."
    else:
        warning = "Severe color shift — this substrate may not be suitable for color-critical work."

    return {
        "original": {"c": c, "m": m, "y": y, "k": k, "hex": orig_rgb["hex"]},
        "simulated": {"c": c_new, "m": m_new, "y": y_new, "k": k_new, "hex": sim_rgb["hex"]},
        "substrate": substrate,
        "print_method": print_method,
        "adjustments": {
            "dot_gain_applied": gain,
            "absorption_k_added": round(absorption_k, 2),
            "tint_offsets": tint,
        },
        "delta_e_from_original": delta_e,
        "warning": warning,
    }
