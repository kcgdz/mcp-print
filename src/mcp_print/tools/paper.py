"""Paper weight unit conversions."""

from __future__ import annotations

from typing import Literal

PaperUnit = Literal["gsm", "lb_text", "lb_cover"]

# Conversion factors relative to GSM.
# 1 lb (text / book) ≈ 1.4802 gsm
# 1 lb (cover / card) ≈ 2.7080 gsm
_TO_GSM: dict[str, float] = {
    "gsm":      1.0,
    "lb_text":  1.4802,
    "lb_cover": 2.7080,
}


def paper_weight_convert(
    value: float,
    from_unit: PaperUnit,
    to_unit: PaperUnit,
) -> float:
    """Convert a paper weight between GSM, lb (text), and lb (cover).

    Args:
        value: The numeric weight value.
        from_unit: Source unit — ``gsm``, ``lb_text``, or ``lb_cover``.
        to_unit: Target unit — ``gsm``, ``lb_text``, or ``lb_cover``.

    Returns:
        The converted weight value, rounded to 2 decimal places.

    Raises:
        ValueError: If the value is non-positive or units are unknown.
    """
    if value <= 0:
        raise ValueError(f"value must be positive, got {value}")

    fu = from_unit.lower()
    tu = to_unit.lower()
    if fu not in _TO_GSM:
        raise ValueError(f"Unknown from_unit: {from_unit!r}. Choose from: gsm, lb_text, lb_cover")
    if tu not in _TO_GSM:
        raise ValueError(f"Unknown to_unit: {to_unit!r}. Choose from: gsm, lb_text, lb_cover")

    gsm_value = value * _TO_GSM[fu]
    result = gsm_value / _TO_GSM[tu]
    return round(result, 2)
