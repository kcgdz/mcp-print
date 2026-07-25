"""Total ink coverage (TAC) checking and GCR-based reduction."""

from __future__ import annotations

from typing import TypedDict

# Typical TAC limits by print condition.
_TAC_LIMITS: dict[str, float] = {
    "offset_coated": 330.0,
    "offset_uncoated": 300.0,
    "digital": 280.0,
    "newsprint": 240.0,
    "flexo": 320.0,
    "gravure": 340.0,
    "screen": 300.0,
}


class InkLimitResult(TypedDict):
    original: dict
    adjusted: dict
    original_tac: float
    adjusted_tac: float
    tac_limit: float
    within_limit: bool
    gcr_applied: float
    note: str


def ink_limit_check(
    c: float,
    m: float,
    y: float,
    k: float,
    tac_limit: float | None = None,
    print_condition: str = "offset_coated",
) -> InkLimitResult:
    """Check total ink coverage and reduce it with GCR when over limit.

    GCR (Gray Component Replacement) moves the shared gray component of
    CMY into the K channel — same visual color, less total ink. If GCR
    alone cannot reach the limit, remaining CMY are scaled down
    proportionally.

    Args:
        c: Cyan (0-100).
        m: Magenta (0-100).
        y: Yellow (0-100).
        k: Key/Black (0-100).
        tac_limit: Explicit TAC limit (100-400). Overrides print_condition.
        print_condition: One of offset_coated, offset_uncoated, digital,
            newsprint, flexo, gravure, or screen (default offset_coated).

    Returns:
        Dict with original/adjusted CMYK, TAC values, limit,
        within_limit flag, gcr_applied amount, and note.

    Raises:
        ValueError: If values are out of range or condition is unknown.
    """
    for name, val in [("c", c), ("m", m), ("y", y), ("k", k)]:
        if not (0 <= val <= 100):
            raise ValueError(f"{name} must be between 0 and 100, got {val}")

    if tac_limit is not None:
        if not (100 <= tac_limit <= 400):
            raise ValueError(f"tac_limit must be between 100 and 400, got {tac_limit}")
        limit = tac_limit
    else:
        cond = print_condition.lower()
        if cond not in _TAC_LIMITS:
            raise ValueError(
                f"Unknown print_condition: {print_condition!r}. "
                f"Choose from: {', '.join(sorted(_TAC_LIMITS))}"
            )
        limit = _TAC_LIMITS[cond]

    original_tac = c + m + y + k
    if original_tac <= limit:
        return {
            "original": {"c": c, "m": m, "y": y, "k": k},
            "adjusted": {"c": c, "m": m, "y": y, "k": k},
            "original_tac": round(original_tac, 1),
            "adjusted_tac": round(original_tac, 1),
            "tac_limit": limit,
            "within_limit": True,
            "gcr_applied": 0.0,
            "note": "Total ink coverage is within the limit — no adjustment needed.",
        }

    # GCR: replacing X% of the common CMY gray with K reduces TAC by 2X
    # (three channels drop by X, K rises by X).
    excess = original_tac - limit
    gray = min(c, m, y)
    headroom_k = 100 - k
    gcr = min(gray, headroom_k, excess / 2)

    c2, m2, y2, k2 = c - gcr, m - gcr, y - gcr, k + gcr
    adjusted_tac = c2 + m2 + y2 + k2

    note_parts = [f"GCR applied: {gcr:.1f}% of gray component moved to K."]
    if adjusted_tac > limit:
        # Scale CMY down proportionally for the remainder.
        remaining = adjusted_tac - limit
        cmy_sum = c2 + m2 + y2
        if cmy_sum > 0:
            scale = max(0.0, (cmy_sum - remaining) / cmy_sum)
            c2, m2, y2 = c2 * scale, m2 * scale, y2 * scale
            note_parts.append(
                "GCR alone was not enough — CMY scaled down; expect a slight "
                "color shift, verify with a proof."
            )
        adjusted_tac = c2 + m2 + y2 + k2

    return {
        "original": {"c": c, "m": m, "y": y, "k": k},
        "adjusted": {
            "c": round(c2, 1), "m": round(m2, 1),
            "y": round(y2, 1), "k": round(k2, 1),
        },
        "original_tac": round(original_tac, 1),
        "adjusted_tac": round(adjusted_tac, 1),
        "tac_limit": limit,
        "within_limit": adjusted_tac <= limit + 0.05,
        "gcr_applied": round(gcr, 1),
        "note": " ".join(note_parts),
    }
