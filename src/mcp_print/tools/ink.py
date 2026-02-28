"""Ink consumption estimation for various print methods."""

from __future__ import annotations

from typing import Literal, TypedDict


class InkResult(TypedDict):
    ink_grams: float
    ink_kg: float
    cost_estimate_usd: float


# Ink consumption rates in g/m² at 100 % coverage (midpoint of typical range).
# Each entry: (rate_g_per_m2, cost_usd_per_kg)
INK_RATES: dict[str, tuple[float, float]] = {
    "offset":  (1.5,  25.0),
    "flexo":   (1.0,  20.0),
    "gravure": (2.5,  22.0),
    "screen":  (10.0, 18.0),
    "digital": (0.65, 80.0),
}

PrintMethod = Literal["offset", "flexo", "gravure", "screen", "digital"]


def ink_consumption(
    width_mm: float,
    height_mm: float,
    coverage_percent: float,
    print_method: PrintMethod,
    quantity: int,
) -> InkResult:
    """Estimate ink consumption for a print job.

    Args:
        width_mm: Print area width in millimeters.
        height_mm: Print area height in millimeters.
        coverage_percent: Ink coverage percentage (0-100).
        print_method: One of ``offset``, ``flexo``, ``gravure``,
            ``screen``, or ``digital``.
        quantity: Number of printed copies.

    Returns:
        Dict with ``ink_grams``, ``ink_kg``, and ``cost_estimate_usd``.

    Raises:
        ValueError: If inputs are out of range or the print method is unknown.
    """
    if width_mm <= 0:
        raise ValueError(f"width_mm must be positive, got {width_mm}")
    if height_mm <= 0:
        raise ValueError(f"height_mm must be positive, got {height_mm}")
    if not (0 <= coverage_percent <= 100):
        raise ValueError(f"coverage_percent must be 0-100, got {coverage_percent}")
    if quantity <= 0:
        raise ValueError(f"quantity must be positive, got {quantity}")

    method = print_method.lower()
    if method not in INK_RATES:
        allowed = ", ".join(sorted(INK_RATES))
        raise ValueError(
            f"Unknown print_method: {print_method!r}. Choose from: {allowed}"
        )

    rate_g_m2, cost_per_kg = INK_RATES[method]
    area_m2 = (width_mm / 1000) * (height_mm / 1000)
    coverage_frac = coverage_percent / 100

    ink_grams = area_m2 * rate_g_m2 * coverage_frac * quantity
    ink_kg = ink_grams / 1000
    cost_usd = ink_kg * cost_per_kg

    return {
        "ink_grams": round(ink_grams, 2),
        "ink_kg": round(ink_kg, 4),
        "cost_estimate_usd": round(cost_usd, 2),
    }
