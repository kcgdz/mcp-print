"""Full job quote — imposition + press sheets + cost in one pass."""

from __future__ import annotations

from typing import TypedDict

from mcp_print.tools.cost import print_cost_estimate
from mcp_print.tools.imposition import imposition_calculator


class QuoteResult(TypedDict):
    imposition: dict
    cost: dict
    quantity: int
    cost_per_piece: float
    currency: str
    summary: str


def full_job_quote(
    *,
    sheet_width_mm: float,
    sheet_height_mm: float,
    piece_width_mm: float,
    piece_height_mm: float,
    quantity: int,
    num_colors: int,
    paper_gsm: float,
    print_method: str,
    sides: int = 1,
    bleed_mm: float = 3.0,
    waste_percent: float = 5.0,
    currency: str = "USD",
    ink_price_per_kg: float | None = None,
    plate_price: float | None = None,
    makeready_price: float | None = None,
    run_price_per_1000: float | None = None,
    paper_price_per_sheet: float = 0.0,
) -> QuoteResult:
    """Produce a complete quote: imposition layout plus full sheet-based cost.

    Runs the imposition calculation first, then costs the actual press
    sheets (including waste) rather than the finished pieces — the way a
    real print shop quotes a job.

    Args:
        sheet_width_mm: Press sheet width in millimeters.
        sheet_height_mm: Press sheet height in millimeters.
        piece_width_mm: Finished piece width in millimeters.
        piece_height_mm: Finished piece height in millimeters.
        quantity: Number of finished pieces required.
        num_colors: Number of ink colors (e.g. 4 for CMYK).
        paper_gsm: Paper weight in GSM.
        print_method: offset, flexo, gravure, screen, or digital.
        sides: Printed sides (1 or 2).
        bleed_mm: Bleed per piece side (default 3).
        waste_percent: Extra sheets for setup/waste (default 5).
        currency: Currency label (default USD).
        ink_price_per_kg: Override ink price per kg. Optional.
        plate_price: Override plate price per color. Optional.
        makeready_price: Override makeready price. Optional.
        run_price_per_1000: Override run price per 1000 sheets. Optional.
        paper_price_per_sheet: Paper price per press sheet; 0 to exclude.

    Returns:
        Dict with imposition, cost (sheet-based), quantity,
        cost_per_piece, currency, and a one-line summary.

    Raises:
        ValueError: If any input is invalid (propagated from the
            underlying calculators).
    """
    imposition = imposition_calculator(
        sheet_width_mm=sheet_width_mm,
        sheet_height_mm=sheet_height_mm,
        piece_width_mm=piece_width_mm,
        piece_height_mm=piece_height_mm,
        quantity=quantity,
        bleed_mm=bleed_mm,
        waste_percent=waste_percent,
    )
    sheets = imposition["sheets_with_waste"]

    cost = print_cost_estimate(
        width_mm=sheet_width_mm,
        height_mm=sheet_height_mm,
        quantity=sheets,
        num_colors=num_colors,
        paper_gsm=paper_gsm,
        print_method=print_method,  # type: ignore[arg-type]
        sides=sides,
        currency=currency,
        ink_price_per_kg=ink_price_per_kg,
        plate_price=plate_price,
        makeready_price=makeready_price,
        run_price_per_1000=run_price_per_1000,
        paper_price_per_sheet=paper_price_per_sheet,
    )

    per_piece = round(cost["total_cost"] / quantity, 4)
    summary = (
        f"{quantity} pieces at {imposition['ups_per_sheet']}-up on "
        f"{sheets} sheets ({imposition['layout']}, incl. waste) — "
        f"total {cost['total_cost']} {currency}, "
        f"{per_piece} {currency}/piece."
    )
    return {
        "imposition": dict(imposition),
        "cost": dict(cost),
        "quantity": quantity,
        "cost_per_piece": per_piece,
        "currency": currency,
        "summary": summary,
    }
