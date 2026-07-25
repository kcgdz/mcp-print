"""MCP server exposing professional print and color workflow tools."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from mcp_print.tools.barcode import barcode_ink_coverage
from mcp_print.tools.booklet import booklet_calculator
from mcp_print.tools.colors import (
    cmyk_to_rgb,
    color_delta_e,
    pantone_search,
    pantone_to_cmyk,
    rgb_to_cmyk,
)
from mcp_print.tools.cost import print_cost_estimate
from mcp_print.tools.icc import icc_profile_info
from mcp_print.tools.imposition import imposition_calculator
from mcp_print.tools.ink import ink_consumption
from mcp_print.tools.paper import paper_weight_convert
from mcp_print.tools.preflight import preflight_check
from mcp_print.tools.spot import spot_color_separator
from mcp_print.tools.substrate import substrate_simulator

mcp = FastMCP(
    "mcp-print",
    instructions=(
        "Professional print & color workflow tools — 2400+ Pantone colors "
        "with fuzzy matching, CMYK/RGB conversion, ink/cost estimation, "
        "Delta E, ICC profiles, spot color separation, barcode coverage, "
        "paper weight conversion, preflight checks, and substrate simulation."
    ),
)


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------


@mcp.tool()
def pantone_to_cmyk_tool(pantone_name: str) -> dict:
    """Convert a Pantone color name to its CMYK equivalent and HEX value.

    Supports fuzzy matching — accepts formats like "485C", "pantone 485",
    "485 coated", "Pantone 485 C", "Warm Red", etc.

    Args:
        pantone_name: Pantone color name or shorthand.

    Returns:
        Dict with name, c, m, y, k (0-100) and hex.
    """
    try:
        return pantone_to_cmyk(pantone_name)
    except ValueError as exc:
        return {"error": str(exc)}


@mcp.tool()
def pantone_search_tool(
    hex_color: str | None = None,
    c: float | None = None,
    m: float | None = None,
    y: float | None = None,
    k: float | None = None,
    limit: int = 5,
) -> dict:
    """Search for the closest Pantone colors by HEX or CMYK proximity.

    Provide either hex_color OR all four CMYK values. Returns the closest
    matches ranked by Delta E color difference.

    Args:
        hex_color: HEX color string (e.g. "#DA291C"). Optional.
        c: Cyan (0-100). Optional.
        m: Magenta (0-100). Optional.
        y: Yellow (0-100). Optional.
        k: Key/Black (0-100). Optional.
        limit: Number of results to return (default 5).

    Returns:
        Dict with matches list and search_type.
    """
    try:
        return pantone_search(hex_color=hex_color, c=c, m=m, y=y, k=k, limit=limit)
    except ValueError as exc:
        return {"error": str(exc)}


@mcp.tool()
def cmyk_to_rgb_tool(c: float, m: float, y: float, k: float) -> dict:
    """Convert CMYK values to RGB and HEX.

    Args:
        c: Cyan (0-100).
        m: Magenta (0-100).
        y: Yellow (0-100).
        k: Key/Black (0-100).

    Returns:
        Dict with r, g, b (0-255) and hex string.
    """
    try:
        return cmyk_to_rgb(c, m, y, k)
    except ValueError as exc:
        return {"error": str(exc)}


@mcp.tool()
def ink_consumption_tool(
    width_mm: float,
    height_mm: float,
    coverage_percent: float,
    print_method: str,
    quantity: int,
) -> dict:
    """Estimate ink consumption for a print job.

    Args:
        width_mm: Print area width in millimeters.
        height_mm: Print area height in millimeters.
        coverage_percent: Ink coverage percentage (0-100).
        print_method: One of offset, flexo, gravure, screen, or digital.
        quantity: Number of copies.

    Returns:
        Dict with ink_grams, ink_kg, and cost_estimate_usd.
    """
    try:
        return ink_consumption(width_mm, height_mm, coverage_percent, print_method, quantity)  # type: ignore[arg-type]
    except ValueError as exc:
        return {"error": str(exc)}


@mcp.tool()
def color_delta_e_tool(
    c1: float, m1: float, y1: float, k1: float,
    c2: float, m2: float, y2: float, k2: float,
) -> dict:
    """Calculate the Delta E (CIE76) color difference between two CMYK colors.

    Args:
        c1: First color cyan (0-100).
        m1: First color magenta (0-100).
        y1: First color yellow (0-100).
        k1: First color black (0-100).
        c2: Second color cyan (0-100).
        m2: Second color magenta (0-100).
        y2: Second color yellow (0-100).
        k2: Second color black (0-100).

    Returns:
        Dict with delta_e value and human-readable interpretation.
    """
    try:
        return color_delta_e(c1, m1, y1, k1, c2, m2, y2, k2)
    except ValueError as exc:
        return {"error": str(exc)}


@mcp.tool()
def paper_weight_converter_tool(
    value: float,
    from_unit: str,
    to_unit: str,
) -> dict:
    """Convert between paper weight units (GSM, lb text, lb cover).

    Args:
        value: The paper weight value to convert.
        from_unit: Source unit — gsm, lb_text, or lb_cover.
        to_unit: Target unit — gsm, lb_text, or lb_cover.

    Returns:
        Dict with the converted value, from_unit, and to_unit.
    """
    try:
        result = paper_weight_convert(value, from_unit, to_unit)  # type: ignore[arg-type]
        return {"value": result, "from_unit": from_unit, "to_unit": to_unit}
    except ValueError as exc:
        return {"error": str(exc)}


@mcp.tool()
def icc_profile_info_tool(file_path: str) -> dict:
    """Parse basic ICC profile metadata from a file.

    Reads the ICC header (128 bytes) and description tag.
    Works with .icc and .icm files.

    Args:
        file_path: Path to an ICC/ICM profile file.

    Returns:
        Dict with profile_name, color_space, device_class,
        creation_date, description, version, pcs, file_size.
    """
    try:
        return icc_profile_info(file_path)
    except (ValueError, FileNotFoundError) as exc:
        return {"error": str(exc)}


@mcp.tool()
def spot_color_separator_tool(
    colors: list[dict[str, float]],
    threshold: float = 5.0,
) -> dict:
    """Identify which colors in a design should be spot vs process colors.

    Colors close to a Pantone swatch (Delta E < threshold) are recommended
    as spot colors for consistency. Others are better as process (CMYK).

    Args:
        colors: List of CMYK dicts, each with keys c, m, y, k (0-100).
        threshold: Delta E cutoff for spot color recommendation (default 5.0).

    Returns:
        Dict with spot_colors, process_colors, and reasoning.
    """
    try:
        return spot_color_separator(colors, threshold)
    except ValueError as exc:
        return {"error": str(exc)}


@mcp.tool()
def barcode_ink_coverage_tool(
    barcode_type: str,
    width_mm: float,
    height_mm: float,
    bar_density: float = 0.5,
) -> dict:
    """Calculate ink coverage for common barcode types.

    Args:
        barcode_type: One of code128, ean13, qr, or datamatrix.
        width_mm: Barcode width in millimeters.
        height_mm: Barcode height in millimeters.
        bar_density: Bar/module density factor (0.0-1.0, default 0.5).

    Returns:
        Dict with coverage_percent, recommended_ink,
        print_method_suggestion, bar_area_mm2, total_area_mm2.
    """
    try:
        return barcode_ink_coverage(barcode_type, width_mm, height_mm, bar_density)  # type: ignore[arg-type]
    except ValueError as exc:
        return {"error": str(exc)}


@mcp.tool()
def print_cost_estimator_tool(
    width_mm: float,
    height_mm: float,
    quantity: int,
    num_colors: int,
    paper_gsm: float,
    print_method: str,
    sides: int = 1,
) -> dict:
    """Estimate full print job cost with detailed breakdown.

    Includes ink, plates, makeready, and run costs with realistic
    industry pricing.

    Args:
        width_mm: Print area width in millimeters.
        height_mm: Print area height in millimeters.
        quantity: Number of printed copies.
        num_colors: Number of ink colors (e.g. 4 for CMYK).
        paper_gsm: Paper weight in GSM.
        print_method: One of offset, flexo, gravure, screen, or digital.
        sides: Number of printed sides (1 or 2, default 1).

    Returns:
        Dict with ink_cost_usd, setup_cost_usd, total_cost_usd,
        cost_per_unit_usd, and breakdown dict.
    """
    try:
        return print_cost_estimate(
            width_mm, height_mm, quantity, num_colors,
            paper_gsm, print_method, sides,  # type: ignore[arg-type]
        )
    except ValueError as exc:
        return {"error": str(exc)}


@mcp.tool()
def preflight_check_tool(
    color_mode: str,
    resolution_dpi: float,
    has_bleed: bool,
    width_mm: float,
    height_mm: float,
    fonts_embedded: bool,
    bleed_mm: float = 0.0,
    total_ink_coverage_percent: float = 280.0,
    has_transparency: bool = False,
    target_method: str = "offset",
) -> dict:
    """Run pre-press preflight validation on declared file properties.

    Checks color mode, resolution, bleed, font embedding, ink coverage,
    and transparency against requirements for the target print method.

    Args:
        color_mode: File color mode — cmyk, rgb, grayscale, or spot.
        resolution_dpi: Image resolution in DPI.
        has_bleed: Whether the document includes bleed.
        width_mm: Document width in millimeters.
        height_mm: Document height in millimeters.
        fonts_embedded: Whether all fonts are embedded.
        bleed_mm: Bleed size in millimeters (default 0).
        total_ink_coverage_percent: Maximum total ink coverage (default 280).
        has_transparency: Whether the file contains transparency (default False).
        target_method: Print method — offset, digital, flexo, gravure, or screen.

    Returns:
        Dict with status, checks list, summary, and recommendation.
    """
    try:
        return preflight_check(
            color_mode=color_mode,
            resolution_dpi=resolution_dpi,
            has_bleed=has_bleed,
            width_mm=width_mm,
            height_mm=height_mm,
            fonts_embedded=fonts_embedded,
            bleed_mm=bleed_mm,
            total_ink_coverage_percent=total_ink_coverage_percent,
            has_transparency=has_transparency,
            target_method=target_method,
        )
    except ValueError as exc:
        return {"error": str(exc)}


@mcp.tool()
def substrate_simulator_tool(
    c: float,
    m: float,
    y: float,
    k: float,
    substrate: str = "uncoated",
    print_method: str = "offset",
) -> dict:
    """Simulate how CMYK colors shift on different paper substrates.

    Models dot gain (Murray-Davies), ink absorption, and paper tint for
    six substrate types across offset, digital, and flexo methods.

    Args:
        c: Cyan (0-100).
        m: Magenta (0-100).
        y: Yellow (0-100).
        k: Key/Black (0-100).
        substrate: One of glossy_coated, matte_coated, uncoated, newsprint,
                   kraft, or recycled (default uncoated).
        print_method: One of offset, digital, or flexo (default offset).

    Returns:
        Dict with original, simulated CMYK+HEX, substrate info,
        adjustments applied, delta_e_from_original, and warning.
    """
    try:
        return substrate_simulator(
            c=c, m=m, y=y, k=k,
            substrate=substrate, print_method=print_method,
        )
    except ValueError as exc:
        return {"error": str(exc)}


@mcp.tool()
def rgb_to_cmyk_tool(
    r: int | None = None,
    g: int | None = None,
    b: int | None = None,
    hex_color: str | None = None,
) -> dict:
    """Convert RGB or HEX to CMYK values.

    Provide either hex_color OR all three RGB values.

    Args:
        r: Red (0-255). Optional.
        g: Green (0-255). Optional.
        b: Blue (0-255). Optional.
        hex_color: HEX color string (e.g. "#DA291C"). Optional.

    Returns:
        Dict with c, m, y, k (0-100) and hex.
    """
    try:
        return rgb_to_cmyk(r=r, g=g, b=b, hex_color=hex_color)
    except ValueError as exc:
        return {"error": str(exc)}


@mcp.tool()
def imposition_calculator_tool(
    sheet_width_mm: float,
    sheet_height_mm: float,
    piece_width_mm: float,
    piece_height_mm: float,
    quantity: int,
    bleed_mm: float = 3.0,
    gripper_margin_mm: float = 10.0,
    gap_mm: float = 3.0,
    waste_percent: float = 5.0,
) -> dict:
    """Calculate n-up imposition — how many pieces fit on a press sheet.

    Tries both piece orientations and picks the layout with the most ups.
    Reserves a gripper margin along one sheet edge.

    Args:
        sheet_width_mm: Press sheet width in millimeters (e.g. 700).
        sheet_height_mm: Press sheet height in millimeters (e.g. 1000).
        piece_width_mm: Finished piece width in millimeters.
        piece_height_mm: Finished piece height in millimeters.
        quantity: Number of finished pieces required.
        bleed_mm: Bleed per side of each piece (default 3).
        gripper_margin_mm: Gripper edge reserved on the sheet (default 10).
        gap_mm: Cutting gap between pieces (default 3).
        waste_percent: Extra sheets for setup/waste (default 5).

    Returns:
        Dict with ups_per_sheet, layout, orientation, sheets_needed,
        sheets_with_waste, and sheet_utilization_percent.
    """
    try:
        return imposition_calculator(
            sheet_width_mm=sheet_width_mm,
            sheet_height_mm=sheet_height_mm,
            piece_width_mm=piece_width_mm,
            piece_height_mm=piece_height_mm,
            quantity=quantity,
            bleed_mm=bleed_mm,
            gripper_margin_mm=gripper_margin_mm,
            gap_mm=gap_mm,
            waste_percent=waste_percent,
        )
    except ValueError as exc:
        return {"error": str(exc)}


@mcp.tool()
def booklet_calculator_tool(
    page_count: int,
    paper_gsm: float,
    pages_per_signature: int = 16,
    paper_type: str = "uncoated",
    binding: str = "saddle_stitch",
    cover_gsm: float = 0.0,
    cover_paper_type: str = "coated",
) -> dict:
    """Calculate booklet signatures, page rounding, and spine thickness.

    Rounds pages up to a multiple of 4, groups them into signatures, and
    estimates spine thickness from paper caliper — useful for designing
    covers before printing.

    Args:
        page_count: Number of content pages (excluding cover).
        paper_gsm: Text paper weight in GSM.
        pages_per_signature: Pages per folded signature — 4, 8, 16, or 32.
        paper_type: Text stock — coated, uncoated, or bulky.
        binding: saddle_stitch or perfect_bound.
        cover_gsm: Cover paper GSM; 0 for self-cover (default 0).
        cover_paper_type: Cover stock — coated, uncoated, or bulky.

    Returns:
        Dict with total_pages, pages_added_for_signature, signatures,
        total_sheets, spine_thickness_mm, and binding_note.
    """
    try:
        return booklet_calculator(
            page_count=page_count,
            paper_gsm=paper_gsm,
            pages_per_signature=pages_per_signature,
            paper_type=paper_type,
            binding=binding,
            cover_gsm=cover_gsm,
            cover_paper_type=cover_paper_type,
        )
    except ValueError as exc:
        return {"error": str(exc)}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Run the MCP server over stdio."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
