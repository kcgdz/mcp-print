"""Real-file PDF preflight — reads an actual PDF instead of declared values.

Requires the optional ``pypdf`` dependency: ``pip install mcp-print[pdf]``.
"""

from __future__ import annotations

from pathlib import Path
from typing import TypedDict

_PT_TO_MM = 25.4 / 72.0

# Minimum bleed (mm) by print method — mirrors preflight.py expectations.
_MIN_BLEED_MM: dict[str, float] = {
    "offset": 3.0,
    "digital": 2.0,
    "flexo": 3.0,
    "gravure": 3.0,
    "screen": 3.0,
}


class PdfPreflightResult(TypedDict):
    status: str
    file: str
    page_count: int
    checks: list[dict]
    pages: list[dict]
    summary: str
    recommendation: str


def _require_pypdf():
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise ValueError(
            "PDF preflight requires the optional pypdf dependency. "
            "Install it with: pip install mcp-print[pdf]"
        ) from exc
    return PdfReader


def _box_size_mm(box) -> tuple[float, float]:
    """Width/height of a PDF box in millimeters."""
    w = float(box.width) * _PT_TO_MM
    h = float(box.height) * _PT_TO_MM
    return round(w, 1), round(h, 1)


def _walk_fonts(page) -> tuple[list[str], list[str]]:
    """Return (embedded, not_embedded) font base names on a page."""
    embedded: list[str] = []
    missing: list[str] = []
    try:
        resources = page.get("/Resources")
        fonts = resources.get("/Font") if resources else None
        if not fonts:
            return embedded, missing
        for key in fonts:
            font = fonts[key].get_object()
            name = str(font.get("/BaseFont", key))
            descriptor = font.get("/FontDescriptor")
            if descriptor is None and font.get("/DescendantFonts"):
                try:
                    descendant = font["/DescendantFonts"][0].get_object()
                    descriptor = descendant.get("/FontDescriptor")
                except (KeyError, IndexError):
                    descriptor = None
            has_file = False
            if descriptor is not None:
                descriptor = descriptor.get_object()
                has_file = any(
                    k in descriptor
                    for k in ("/FontFile", "/FontFile2", "/FontFile3")
                )
            # Standard 14 fonts have no descriptor but render everywhere.
            is_standard = descriptor is None and name.lstrip("/") in {
                "Helvetica", "Helvetica-Bold", "Helvetica-Oblique",
                "Helvetica-BoldOblique", "Times-Roman", "Times-Bold",
                "Times-Italic", "Times-BoldItalic", "Courier", "Courier-Bold",
                "Courier-Oblique", "Courier-BoldOblique", "Symbol", "ZapfDingbats",
            }
            if has_file or is_standard:
                embedded.append(name)
            else:
                missing.append(name)
    except Exception:  # noqa: BLE001, S110 — malformed resources: report what was parsed
        pass
    return embedded, missing


def _walk_images(page) -> list[dict]:
    """Collect image XObject info: pixel dims and color space."""
    images: list[dict] = []
    try:
        resources = page.get("/Resources")
        xobjects = resources.get("/XObject") if resources else None
        if not xobjects:
            return images
        for key in xobjects:
            obj = xobjects[key].get_object()
            if obj.get("/Subtype") != "/Image":
                continue
            cs = obj.get("/ColorSpace")
            cs_name = str(cs) if not isinstance(cs, list) else str(cs[0])
            images.append({
                "name": str(key),
                "width_px": int(obj.get("/Width", 0)),
                "height_px": int(obj.get("/Height", 0)),
                "color_space": cs_name.lstrip("/"),
            })
    except Exception:  # noqa: BLE001, S110 — malformed resources: report what was parsed
        pass
    return images


def pdf_preflight(file_path: str, target_method: str = "offset") -> PdfPreflightResult:
    """Run preflight checks on an actual PDF file.

    Inspects page geometry (trim/bleed boxes), font embedding, and image
    color spaces directly from the file.

    Args:
        file_path: Path to the PDF file.
        target_method: Print method — offset, digital, flexo, gravure,
            or screen (default offset).

    Returns:
        Dict with status, page_count, checks, per-page geometry,
        summary, and recommendation.

    Raises:
        ValueError: If pypdf is missing, the file is unreadable, or the
            method is unknown.
        FileNotFoundError: If the file does not exist.
    """
    method = target_method.lower()
    if method not in _MIN_BLEED_MM:
        raise ValueError(
            f"Unknown target_method: {target_method!r}. "
            f"Choose from: {', '.join(sorted(_MIN_BLEED_MM))}"
        )
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF file not found: {file_path}")

    PdfReader = _require_pypdf()
    try:
        reader = PdfReader(str(path))
        page_count = len(reader.pages)
    except Exception as exc:
        raise ValueError(f"Could not read PDF: {exc}") from exc

    checks: list[dict] = []
    pages: list[dict] = []
    all_missing_fonts: list[str] = []
    rgb_images = 0
    total_images = 0
    min_bleed_found: float | None = None

    for i, page in enumerate(reader.pages, start=1):
        media_w, media_h = _box_size_mm(page.mediabox)
        info: dict = {"page": i, "media_mm": {"width": media_w, "height": media_h}}

        trim = page.trimbox
        bleed = page.bleedbox
        trim_w, trim_h = _box_size_mm(trim)
        info["trim_mm"] = {"width": trim_w, "height": trim_h}
        bleed_each = round((float(trim.left) - float(bleed.left)) * _PT_TO_MM, 1)
        info["bleed_mm"] = max(0.0, bleed_each)
        if min_bleed_found is None or info["bleed_mm"] < min_bleed_found:
            min_bleed_found = info["bleed_mm"]

        embedded, missing = _walk_fonts(page)
        info["fonts_embedded"] = embedded
        info["fonts_not_embedded"] = missing
        all_missing_fonts.extend(f for f in missing if f not in all_missing_fonts)

        images = _walk_images(page)
        info["images"] = images
        total_images += len(images)
        rgb_images += sum(1 for img in images if "RGB" in img["color_space"].upper())

        pages.append(info)

    # Check: bleed
    min_bleed = _MIN_BLEED_MM[method]
    bleed_val = min_bleed_found or 0.0
    if bleed_val >= min_bleed:
        checks.append({
            "name": "bleed", "status": "pass",
            "message": f"{bleed_val} mm bleed meets the {min_bleed} mm minimum for {method}.",
        })
    elif bleed_val > 0:
        checks.append({
            "name": "bleed", "status": "warning",
            "message": f"{bleed_val} mm bleed is below the {min_bleed} mm minimum for {method}.",
        })
    else:
        checks.append({
            "name": "bleed", "status": "fail",
            "message": "No bleed box found — add bleed before production.",
        })

    # Check: fonts
    if all_missing_fonts:
        checks.append({
            "name": "fonts", "status": "fail",
            "message": f"Fonts not embedded: {', '.join(all_missing_fonts)}.",
        })
    else:
        checks.append({
            "name": "fonts", "status": "pass",
            "message": "All fonts are embedded.",
        })

    # Check: image color spaces
    if total_images == 0:
        checks.append({
            "name": "image_color", "status": "pass",
            "message": "No raster images found.",
        })
    elif rgb_images and method != "digital":
        checks.append({
            "name": "image_color", "status": "warning",
            "message": f"{rgb_images} of {total_images} images are RGB — convert to CMYK for {method}.",
        })
    else:
        checks.append({
            "name": "image_color", "status": "pass",
            "message": f"{total_images} image(s), color spaces suitable for {method}.",
        })

    # Check: consistent page sizes
    sizes = {(p["trim_mm"]["width"], p["trim_mm"]["height"]) for p in pages}
    if len(sizes) <= 1:
        checks.append({
            "name": "page_size", "status": "pass",
            "message": "All pages share the same trim size.",
        })
    else:
        checks.append({
            "name": "page_size", "status": "warning",
            "message": f"Mixed trim sizes found: {sorted(sizes)}.",
        })

    failed = sum(1 for ch in checks if ch["status"] == "fail")
    warned = sum(1 for ch in checks if ch["status"] == "warning")
    passed = len(checks) - failed - warned
    status = "fail" if failed else ("warning" if warned else "pass")
    summary = f"{passed} passed, {warned} warnings, {failed} failed out of {len(checks)} checks."
    if status == "pass":
        recommendation = "File is ready for production."
    elif status == "warning":
        recommendation = "File is usable but review the warnings before production."
    else:
        recommendation = "Fix the failed checks before sending to production."

    return {
        "status": status,
        "file": str(path),
        "page_count": page_count,
        "checks": checks,
        "pages": pages,
        "summary": summary,
        "recommendation": recommendation,
    }
