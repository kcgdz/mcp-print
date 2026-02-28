---
name: print-workflow
description: Professional print and color workflow assistance. Use when user mentions printing, CMYK, Pantone, ICC profiles, ink consumption, barcodes, or color management.
---

# Print Workflow Skill

You have access to the mcp-print MCP server with professional printing tools.

## Available tools:

| Tool | Purpose |
|---|---|
| `pantone_to_cmyk_tool` | Look up Pantone color → CMYK + HEX (fuzzy matching, 2400+ colors) |
| `pantone_search_tool` | Find closest Pantone by HEX or CMYK proximity (top N matches) |
| `cmyk_to_rgb_tool` | Convert CMYK → RGB + HEX |
| `color_delta_e_tool` | Delta E (CIE76) between two CMYK colors |
| `ink_consumption_tool` | Estimate ink grams/kg/cost for a print run |
| `print_cost_estimator_tool` | Full job cost: ink + plates + makeready + run |
| `icc_profile_info_tool` | Parse ICC/ICM profile metadata from file |
| `spot_color_separator_tool` | Recommend spot vs process for a color list |
| `barcode_ink_coverage_tool` | Ink coverage % for Code128/EAN13/QR/DataMatrix |
| `paper_weight_converter_tool` | Convert GSM ↔ lb text ↔ lb cover |

## When to use each tool:
- User asks about Pantone colors → `pantone_to_cmyk_tool`, `pantone_search_tool`
- User asks about color accuracy or matching → `color_delta_e_tool`
- User asks about ink usage → `ink_consumption_tool`
- User asks about print job cost → `print_cost_estimator_tool`
- User mentions ICC profile → `icc_profile_info_tool`
- User asks about spot vs process colors → `spot_color_separator_tool`
- User asks about barcodes → `barcode_ink_coverage_tool`
- User asks about paper weight → `paper_weight_converter_tool`

## Response style:
- Always show color values as HEX codes in backticks (e.g. `#DA291C`)
- Round ink weights to 2 decimal places
- For cost estimates, show a breakdown table
- Suggest print method when relevant
- When showing Pantone matches, include the Delta E score for context
- For spot/process recommendations, explain the reasoning clearly
