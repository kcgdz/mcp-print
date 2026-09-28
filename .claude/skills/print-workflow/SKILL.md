---
name: print-workflow
description: Professional print and color workflow assistance. Use when user mentions printing, CMYK, ICC profiles, ink consumption, barcodes, color palettes, or color management.
---

# Print Workflow Skill

You have access to the mcp-print MCP server with professional printing tools.

## Available tools:

| Tool | Purpose |
|---|---|
| `palette_lookup_tool` | Look up a color by name in the user's local palette → CMYK + HEX |
| `palette_search_tool` | Find the closest entries in the user's local palette to a HEX or CMYK value |
| `cmyk_to_rgb_tool` | Convert CMYK → RGB + HEX |
| `rgb_to_cmyk_tool` | Convert RGB/HEX → CMYK |
| `lab_convert_tool` | Convert between Lab, CMYK, RGB, and HEX |
| `color_delta_e_tool` | Delta E (CIEDE2000 or CIE76) between two CMYK colors |
| `ink_consumption_tool` | Estimate ink grams/kg/cost for a print run |
| `print_cost_estimator_tool` | Full job cost: ink + plates + makeready + run |
| `full_job_quote_tool` | Imposition + sheet-based costing in one call |
| `icc_profile_info_tool` | Parse ICC/ICM profile metadata from file |
| `spot_color_separator_tool` | Report how close design colors are to the user's local palette |
| `barcode_ink_coverage_tool` | Ink coverage % for Code128/EAN13/QR/DataMatrix |
| `paper_weight_converter_tool` | Convert GSM ↔ lb text ↔ lb cover |

## Local palette

mcp-print ships no color library. The palette tools and `spot_color_separator_tool`
only work when the user has set `MCP_PRINT_PALETTE_PATH` to their own palette JSON
file. If a tool returns a "No color palette configured" error, explain how to
configure one (see the project README) — do not invent CMYK values for named
colors, and do not claim that any published color system is built in.

## When to use each tool:
- User asks for a named color from their palette → `palette_lookup_tool`
- User asks which palette color is closest to a value → `palette_search_tool`
- User asks about color accuracy or matching → `color_delta_e_tool`
- User asks about ink usage → `ink_consumption_tool`
- User asks about print job cost → `print_cost_estimator_tool` or `full_job_quote_tool`
- User mentions ICC profile → `icc_profile_info_tool`
- User asks how close design colors are to their palette → `spot_color_separator_tool`
- User asks about barcodes → `barcode_ink_coverage_tool`
- User asks about paper weight → `paper_weight_converter_tool`

## Response style:
- Always show color values as HEX codes in backticks (e.g. `#1D8EE1`)
- Round ink weights to 2 decimal places
- For cost estimates, show a breakdown table
- Suggest print method when relevant
- When showing palette matches, include the Delta E score and say the values come from the user's palette
- Palette distances are approximate (no ICC profile): never present them as official catalog values or a guarantee of printed results
- Closeness to a palette color alone does not mean a spot ink is more accurate or more suitable; leave the spot-vs-process decision to the user and their printer
