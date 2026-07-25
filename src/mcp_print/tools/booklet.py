"""Booklet signature and spine thickness calculation."""

from __future__ import annotations

from typing import TypedDict

# Bulk factor: caliper (mm) per 100 gsm for common stock types.
# Coated papers are denser (thinner per gram) than uncoated.
_BULK_MM_PER_100GSM: dict[str, float] = {
    "coated": 0.090,
    "uncoated": 0.125,
    "bulky": 0.180,
}

_BINDINGS = ("saddle_stitch", "perfect_bound")


class BookletResult(TypedDict):
    total_pages: int
    pages_added_for_signature: int
    signatures: int
    sheets_per_signature: int
    total_sheets: int
    spine_thickness_mm: float
    binding: str
    binding_note: str


def booklet_calculator(
    page_count: int,
    paper_gsm: float,
    pages_per_signature: int = 16,
    paper_type: str = "uncoated",
    binding: str = "saddle_stitch",
    cover_gsm: float = 0.0,
    cover_paper_type: str = "coated",
) -> BookletResult:
    """Calculate signatures, rounded page count, and spine thickness.

    Page counts are rounded up to the nearest multiple of 4 (folded sheet)
    and grouped into signatures. Spine thickness is estimated from paper
    caliper (bulk) so covers can be designed before the book is printed.

    Args:
        page_count: Number of content pages (excluding cover).
        paper_gsm: Text paper weight in GSM.
        pages_per_signature: Pages per folded signature — 4, 8, 16, or 32
            (default 16).
        paper_type: Text stock — coated, uncoated, or bulky (default uncoated).
        binding: saddle_stitch or perfect_bound (default saddle_stitch).
        cover_gsm: Cover paper weight in GSM; 0 for self-cover (default 0).
        cover_paper_type: Cover stock — coated, uncoated, or bulky.

    Returns:
        Dict with total_pages, pages_added_for_signature, signatures,
        sheets_per_signature, total_sheets, spine_thickness_mm, binding,
        and binding_note.

    Raises:
        ValueError: If inputs are out of range or the binding/paper type
            is unknown.
    """
    if page_count < 4:
        raise ValueError(f"page_count must be at least 4, got {page_count}")
    if paper_gsm <= 0:
        raise ValueError(f"paper_gsm must be positive, got {paper_gsm}")
    if pages_per_signature not in (4, 8, 16, 32):
        raise ValueError(
            f"pages_per_signature must be 4, 8, 16, or 32, got {pages_per_signature}"
        )
    pt = paper_type.lower()
    if pt not in _BULK_MM_PER_100GSM:
        raise ValueError(
            f"Unknown paper_type: {paper_type!r}. Choose from: coated, uncoated, bulky"
        )
    bind = binding.lower()
    if bind not in _BINDINGS:
        raise ValueError(
            f"Unknown binding: {binding!r}. Choose from: saddle_stitch, perfect_bound"
        )
    if cover_gsm < 0:
        raise ValueError(f"cover_gsm must be non-negative, got {cover_gsm}")
    cpt = cover_paper_type.lower()
    if cover_gsm > 0 and cpt not in _BULK_MM_PER_100GSM:
        raise ValueError(
            f"Unknown cover_paper_type: {cover_paper_type!r}. "
            f"Choose from: coated, uncoated, bulky"
        )

    total_pages = -(-page_count // 4) * 4
    signatures = -(-total_pages // pages_per_signature)
    sheets_per_signature = pages_per_signature // 4
    total_sheets = total_pages // 4

    caliper = paper_gsm / 100 * _BULK_MM_PER_100GSM[pt]
    # Each physical leaf (2 pages) contributes one caliper to the spine.
    spine = total_pages / 2 * caliper
    if cover_gsm > 0:
        cover_caliper = cover_gsm / 100 * _BULK_MM_PER_100GSM[cpt]
        spine += 2 * cover_caliper  # front + back cover

    if bind == "saddle_stitch":
        if total_pages > 64:
            note = (
                f"{total_pages} pages is too thick for saddle stitching "
                f"(max ~64) — consider perfect binding."
            )
        else:
            note = "Suitable for saddle stitching."
    else:
        if spine < 3.0:
            note = (
                f"Spine of {spine:.1f} mm is too thin for perfect binding "
                f"(min ~3 mm) — consider saddle stitching."
            )
        else:
            note = "Suitable for perfect binding."

    return {
        "total_pages": total_pages,
        "pages_added_for_signature": total_pages - page_count,
        "signatures": signatures,
        "sheets_per_signature": sheets_per_signature,
        "total_sheets": total_sheets,
        "spine_thickness_mm": round(spine, 2),
        "binding": bind,
        "binding_note": note,
    }
