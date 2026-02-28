"""Full print job cost estimation."""

from __future__ import annotations

from typing import Literal, TypedDict

from mcp_print.tools.ink import INK_RATES


class CostBreakdown(TypedDict):
    ink: float
    plates: float
    makeready: float
    run_cost: float


class PrintCostResult(TypedDict):
    ink_cost_usd: float
    setup_cost_usd: float
    total_cost_usd: float
    cost_per_unit_usd: float
    breakdown: CostBreakdown


PrintMethod = Literal["offset", "flexo", "gravure", "screen", "digital"]

# Plate cost per color (USD)
_PLATE_COST: dict[str, float] = {
    "offset":  35.0,
    "flexo":   30.0,
    "gravure": 45.0,
    "screen":  25.0,
    "digital": 0.0,
}

# Makeready / setup cost (USD)
_MAKEREADY_COST: dict[str, float] = {
    "offset":  100.0,
    "flexo":   80.0,
    "gravure": 150.0,
    "screen":  50.0,
    "digital": 0.0,
}

# Run cost per 1000 sheets (USD)
_RUN_COST_PER_1000: dict[str, float] = {
    "offset":  12.0,
    "flexo":   10.0,
    "gravure": 14.0,
    "screen":  25.0,
    "digital": 60.0,
}


def print_cost_estimate(
    width_mm: float,
    height_mm: float,
    quantity: int,
    num_colors: int,
    paper_gsm: float,
    print_method: PrintMethod,
    sides: int = 1,
) -> PrintCostResult:
    """Estimate full print job cost including ink, plates, makeready, and run costs.

    Args:
        width_mm: Print area width in millimeters.
        height_mm: Print area height in millimeters.
        quantity: Number of printed copies.
        num_colors: Number of ink colors (e.g. 4 for CMYK).
        paper_gsm: Paper weight in GSM (affects run cost slightly).
        print_method: One of ``offset``, ``flexo``, ``gravure``,
            ``screen``, or ``digital``.
        sides: Number of printed sides (1 or 2).

    Returns:
        Dict with cost breakdown and totals.

    Raises:
        ValueError: If inputs are out of range.
    """
    if width_mm <= 0:
        raise ValueError(f"width_mm must be positive, got {width_mm}")
    if height_mm <= 0:
        raise ValueError(f"height_mm must be positive, got {height_mm}")
    if quantity <= 0:
        raise ValueError(f"quantity must be positive, got {quantity}")
    if num_colors <= 0:
        raise ValueError(f"num_colors must be positive, got {num_colors}")
    if paper_gsm <= 0:
        raise ValueError(f"paper_gsm must be positive, got {paper_gsm}")
    if sides not in (1, 2):
        raise ValueError(f"sides must be 1 or 2, got {sides}")

    method = print_method.lower()
    if method not in INK_RATES:
        allowed = ", ".join(sorted(INK_RATES))
        raise ValueError(f"Unknown print_method: {print_method!r}. Choose from: {allowed}")

    # Ink cost: assume average 30% coverage per color
    rate_g_m2, cost_per_kg = INK_RATES[method]
    area_m2 = (width_mm / 1000) * (height_mm / 1000)
    avg_coverage = 0.30
    ink_grams = area_m2 * rate_g_m2 * avg_coverage * quantity * num_colors * sides
    ink_cost = (ink_grams / 1000) * cost_per_kg

    # Plates
    plate_cost = _PLATE_COST[method] * num_colors * sides

    # Makeready
    makeready = _MAKEREADY_COST[method] * sides

    # Run cost
    # Heavier paper costs slightly more to run
    paper_factor = 1.0 + max(0, (paper_gsm - 100)) / 500
    run_cost = (_RUN_COST_PER_1000[method] * (quantity / 1000)) * paper_factor * sides

    total = ink_cost + plate_cost + makeready + run_cost
    per_unit = total / quantity if quantity > 0 else 0

    return {
        "ink_cost_usd": round(ink_cost, 2),
        "setup_cost_usd": round(plate_cost + makeready, 2),
        "total_cost_usd": round(total, 2),
        "cost_per_unit_usd": round(per_unit, 4),
        "breakdown": {
            "ink": round(ink_cost, 2),
            "plates": round(plate_cost, 2),
            "makeready": round(makeready, 2),
            "run_cost": round(run_cost, 2),
        },
    }
