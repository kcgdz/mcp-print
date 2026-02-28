"""Barcode ink coverage estimation."""

from __future__ import annotations

from typing import Literal, TypedDict


class BarcodeResult(TypedDict):
    coverage_percent: float
    recommended_ink: str
    print_method_suggestion: str
    bar_area_mm2: float
    total_area_mm2: float


BarcodeType = Literal["code128", "ean13", "qr", "datamatrix"]

# Typical ink coverage ratios and bar characteristics per barcode type.
# coverage_ratio: fraction of the barcode area that is dark bars/modules.
# module_notes: guidance for print method selection.
_BARCODE_SPECS: dict[str, dict] = {
    "code128": {
        "coverage_ratio": 0.50,
        "min_module_mm": 0.25,
        "description": "Code 128 — linear barcode",
        "recommended_ink": "Process Black (K: 100)",
        "notes": "Requires crisp edges for reliable scanning.",
    },
    "ean13": {
        "coverage_ratio": 0.52,
        "min_module_mm": 0.264,
        "description": "EAN-13 — retail barcode",
        "recommended_ink": "Process Black (K: 100)",
        "notes": "Standard retail barcode; tight bar width tolerances.",
    },
    "qr": {
        "coverage_ratio": 0.45,
        "min_module_mm": 0.33,
        "description": "QR Code — 2D matrix barcode",
        "recommended_ink": "Process Black (K: 100)",
        "notes": "Error correction tolerates some print variation.",
    },
    "datamatrix": {
        "coverage_ratio": 0.48,
        "min_module_mm": 0.30,
        "description": "Data Matrix — compact 2D barcode",
        "recommended_ink": "Process Black (K: 100)",
        "notes": "Small modules; digital or offset recommended.",
    },
}


def _suggest_print_method(min_module_mm: float, density: float) -> str:
    """Suggest a print method based on module size and density."""
    if min_module_mm < 0.3 or density > 0.7:
        return "digital — finest resolution, best for small modules and high density"
    if min_module_mm < 0.5:
        return "offset — good resolution for medium modules, cost-effective at volume"
    return "flexo — suitable for larger modules, common in packaging"


def barcode_ink_coverage(
    barcode_type: BarcodeType,
    width_mm: float,
    height_mm: float,
    bar_density: float = 0.5,
) -> BarcodeResult:
    """Calculate ink coverage percentage for a barcode.

    Args:
        barcode_type: One of ``code128``, ``ean13``, ``qr``, or ``datamatrix``.
        width_mm: Barcode width in millimeters.
        height_mm: Barcode height in millimeters.
        bar_density: Bar/module density factor (0.0-1.0, default 0.5).
            Higher values mean denser bar patterns.

    Returns:
        Dict with ``coverage_percent``, ``recommended_ink``,
        ``print_method_suggestion``, ``bar_area_mm2``, and ``total_area_mm2``.

    Raises:
        ValueError: If inputs are invalid.
    """
    if width_mm <= 0:
        raise ValueError(f"width_mm must be positive, got {width_mm}")
    if height_mm <= 0:
        raise ValueError(f"height_mm must be positive, got {height_mm}")
    if not (0 < bar_density <= 1.0):
        raise ValueError(f"bar_density must be between 0 (exclusive) and 1.0, got {bar_density}")

    bt = barcode_type.lower()
    if bt not in _BARCODE_SPECS:
        allowed = ", ".join(sorted(_BARCODE_SPECS))
        raise ValueError(f"Unknown barcode_type: {barcode_type!r}. Choose from: {allowed}")

    spec = _BARCODE_SPECS[bt]
    total_area = width_mm * height_mm
    base_coverage = spec["coverage_ratio"]
    # Adjust coverage by density factor (0.5 is baseline)
    adjusted_coverage = base_coverage * (bar_density / 0.5)
    adjusted_coverage = min(adjusted_coverage, 1.0)

    bar_area = total_area * adjusted_coverage
    coverage_pct = round(adjusted_coverage * 100, 1)

    method = _suggest_print_method(spec["min_module_mm"], bar_density)

    return {
        "coverage_percent": coverage_pct,
        "recommended_ink": spec["recommended_ink"],
        "print_method_suggestion": method,
        "bar_area_mm2": round(bar_area, 2),
        "total_area_mm2": round(total_area, 2),
    }
