"""Dot gain compensation — inverse of the press gain curve."""

from __future__ import annotations

import math
from typing import TypedDict

from mcp_print.tools.substrate import _SUBSTRATES


class DotGainResult(TypedDict):
    compensated: dict
    target_on_press: dict
    dot_gain_percent: float
    source: str


def _compensate_value(target: float, gain: float) -> float:
    """Solve v + (gain/100) * v * (1 - v/100) = target for v.

    This is the inverse of the midtone-weighted gain model used by the
    substrate simulator. The quadratic has one root in [0, 100].
    """
    if target <= 0:
        return 0.0
    if gain == 0:
        return target
    # -(g/10000) v^2 + (1 + g/100) v - target = 0
    a = -gain / 10000
    b = 1 + gain / 100
    c = -target
    disc = b * b - 4 * a * c
    if disc < 0:
        return 100.0
    v = (-b + math.sqrt(disc)) / (2 * a)
    return max(0.0, min(100.0, v))


def dot_gain_compensation(
    *,
    c: float,
    m: float,
    y: float,
    k: float,
    dot_gain_percent: float | None = None,
    substrate: str | None = None,
    print_method: str = "offset",
) -> DotGainResult:
    """Calculate file values that produce the desired tints on press.

    The inverse of substrate simulation: give the CMYK you want to SEE
    printed, get the CMYK to put in the file so that dot gain lands on
    target. Provide either an explicit ``dot_gain_percent`` or a
    ``substrate`` name to look the gain up.

    Args:
        c: Target cyan on press (0-100).
        m: Target magenta on press (0-100).
        y: Target yellow on press (0-100).
        k: Target black on press (0-100).
        dot_gain_percent: Known midtone dot gain (0-60). Optional.
        substrate: Substrate name to look up gain from — glossy_coated,
            matte_coated, uncoated, newsprint, kraft, or recycled. Optional.
        print_method: offset, digital, or flexo (used with substrate).

    Returns:
        Dict with compensated CMYK (file values), target_on_press echo,
        dot_gain_percent used, and source.

    Raises:
        ValueError: If inputs are out of range or neither/both of
            dot_gain_percent and substrate are given.
    """
    for name, val in [("c", c), ("m", m), ("y", y), ("k", k)]:
        if not (0 <= val <= 100):
            raise ValueError(f"{name} must be between 0 and 100, got {val}")

    if (dot_gain_percent is None) == (substrate is None):
        raise ValueError("Provide exactly one of dot_gain_percent or substrate.")

    if dot_gain_percent is not None:
        if not (0 <= dot_gain_percent <= 60):
            raise ValueError(
                f"dot_gain_percent must be between 0 and 60, got {dot_gain_percent}"
            )
        gain = dot_gain_percent
        source = f"explicit gain {gain}%"
    else:
        assert substrate is not None
        sub = substrate.lower()
        if sub not in _SUBSTRATES:
            raise ValueError(
                f"Unknown substrate: {substrate!r}. Must be one of {sorted(_SUBSTRATES)}."
            )
        method = print_method.lower()
        gains = _SUBSTRATES[sub]["dot_gain"]
        if method not in gains:
            raise ValueError(
                f"Unknown print_method: {print_method!r}. Must be one of {sorted(gains)}."
            )
        gain = gains[method]
        source = f"{sub} / {method} ({gain}% gain)"

    compensated = {
        ch: round(_compensate_value(val, gain), 1)
        for ch, val in (("c", c), ("m", m), ("y", y), ("k", k))
    }
    return {
        "compensated": compensated,
        "target_on_press": {"c": c, "m": m, "y": y, "k": k},
        "dot_gain_percent": gain,
        "source": source,
    }
