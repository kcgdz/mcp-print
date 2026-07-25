"""Sheet imposition (n-up) layout calculation."""

from __future__ import annotations

from typing import TypedDict


class ImpositionResult(TypedDict):
    ups_per_sheet: int
    layout: str
    orientation: str
    sheets_needed: int
    sheets_with_waste: int
    sheet_utilization_percent: float
    piece_with_bleed_mm: dict
    usable_sheet_mm: dict


def _grid_fit(
    avail_w: float, avail_h: float,
    piece_w: float, piece_h: float,
    gap: float,
) -> tuple[int, int, int]:
    """Number of pieces fitting in a simple grid: (total, cols, rows)."""
    if piece_w > avail_w or piece_h > avail_h:
        return 0, 0, 0
    cols = int((avail_w + gap) // (piece_w + gap))
    rows = int((avail_h + gap) // (piece_h + gap))
    return cols * rows, cols, rows


def imposition_calculator(
    sheet_width_mm: float,
    sheet_height_mm: float,
    piece_width_mm: float,
    piece_height_mm: float,
    quantity: int,
    bleed_mm: float = 3.0,
    gripper_margin_mm: float = 10.0,
    gap_mm: float = 3.0,
    waste_percent: float = 5.0,
) -> ImpositionResult:
    """Calculate how many pieces fit on a press sheet (n-up imposition).

    Tries both piece orientations on a straight grid and picks the best.
    The gripper margin is reserved along one long edge of the sheet.

    Args:
        sheet_width_mm: Press sheet width in millimeters.
        sheet_height_mm: Press sheet height in millimeters.
        piece_width_mm: Finished piece width in millimeters.
        piece_height_mm: Finished piece height in millimeters.
        quantity: Number of finished pieces required.
        bleed_mm: Bleed on each side of a piece (default 3).
        gripper_margin_mm: Gripper edge reserved on the sheet (default 10).
        gap_mm: Gap between pieces for cutting (default 3).
        waste_percent: Extra sheets for setup/waste (default 5).

    Returns:
        Dict with ups_per_sheet, layout, orientation, sheets_needed,
        sheets_with_waste, sheet_utilization_percent, and dimension echoes.

    Raises:
        ValueError: If dimensions are non-positive, quantity < 1, or the
            piece does not fit on the sheet at all.
    """
    for name, val in [
        ("sheet_width_mm", sheet_width_mm), ("sheet_height_mm", sheet_height_mm),
        ("piece_width_mm", piece_width_mm), ("piece_height_mm", piece_height_mm),
    ]:
        if val <= 0:
            raise ValueError(f"{name} must be positive, got {val}")
    if quantity < 1:
        raise ValueError(f"quantity must be at least 1, got {quantity}")
    if bleed_mm < 0 or gripper_margin_mm < 0 or gap_mm < 0:
        raise ValueError("bleed_mm, gripper_margin_mm, and gap_mm must be non-negative")
    if not (0 <= waste_percent <= 100):
        raise ValueError(f"waste_percent must be between 0 and 100, got {waste_percent}")

    pw = piece_width_mm + 2 * bleed_mm
    ph = piece_height_mm + 2 * bleed_mm
    avail_w = sheet_width_mm
    avail_h = sheet_height_mm - gripper_margin_mm

    normal, n_cols, n_rows = _grid_fit(avail_w, avail_h, pw, ph, gap_mm)
    rotated, r_cols, r_rows = _grid_fit(avail_w, avail_h, ph, pw, gap_mm)

    if normal == 0 and rotated == 0:
        raise ValueError(
            f"Piece ({pw:.1f} x {ph:.1f} mm incl. bleed) does not fit on the "
            f"usable sheet area ({avail_w:.1f} x {avail_h:.1f} mm)."
        )

    if rotated > normal:
        ups, cols, rows, orientation = rotated, r_cols, r_rows, "rotated"
        used_w, used_h = ph, pw
    else:
        ups, cols, rows, orientation = normal, n_cols, n_rows, "normal"
        used_w, used_h = pw, ph

    sheets_needed = -(-quantity // ups)  # ceil division
    sheets_with_waste = -(-(sheets_needed * (100 + waste_percent)) // 100)

    piece_area = used_w * used_h * ups
    sheet_area = sheet_width_mm * sheet_height_mm
    utilization = round(piece_area / sheet_area * 100, 1)

    return {
        "ups_per_sheet": ups,
        "layout": f"{cols} x {rows}",
        "orientation": orientation,
        "sheets_needed": sheets_needed,
        "sheets_with_waste": int(sheets_with_waste),
        "sheet_utilization_percent": utilization,
        "piece_with_bleed_mm": {"width": round(pw, 1), "height": round(ph, 1)},
        "usable_sheet_mm": {"width": round(avail_w, 1), "height": round(avail_h, 1)},
    }
