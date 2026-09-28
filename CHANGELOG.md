# Changelog

## v0.6.0 — 2026-09-28 (breaking)

The bundled Pantone color table has been removed from the distribution because
its source and redistribution rights could not be verified. Palette features
now use a local palette file supplied by the user. Earlier release notes below
are left as published.

### Removed
- `src/mcp_print/data/pantone_colors.json` (2,415 entries) and
  `scripts/generate_pantone_db.py`, which produced it
- `pantone_to_cmyk_tool` and `pantone_search_tool` (no deprecated aliases)
- MCP resource `mcp-print://pantone-database` (no replacement; user palettes are
  never exposed in bulk)
- Python API `mcp_print.tools.colors.pantone_to_cmyk` / `pantone_search`
- `cmyk.png` README screenshot (it presented a table value as a standard build)

### Added
- Local palette loader: set `MCP_PRINT_PALETTE_PATH` to a JSON file
  (`{"palette": "...", "colors": [{"name", "c", "m", "y", "k"}]}`). Strict
  validation with clear errors for missing/unreadable files, invalid JSON,
  empty lists, non-numeric/boolean/NaN/Infinity/out-of-range values, unknown
  fields, and duplicate names. No download and no built-in fallback.
- `palette_lookup_tool` — exact (case/whitespace-insensitive) lookup; names are
  kept as written, no prefixes or finish variants are generated; near names are
  returned only as `suggestions`
- `palette_search_tool` — nearest palette entries to a HEX/CMYK value, with
  per-match `delta_e` (CIEDE2000 on approximate Lab)
- Synthetic sample palette: `examples/example-palette.json`

### Changed
- `spot_color_separator_tool` requires a configured palette (returns an error
  otherwise) and only reports approximate proximity; it no longer recommends
  spot vs process. Output keys: `spot_colors` → `within_threshold`,
  `process_colors` → `beyond_threshold`, `nearest_pantone` →
  `nearest_palette_color` (+ `nearest_palette_cmyk`), `reason`/`reasoning` →
  `summary` + `note`. Distance metric changed from CIE76 to CIEDE2000.
- Package description, server instructions, README, and the `print-workflow`
  skill no longer describe a built-in Pantone library.
- Dependency pinned to `mcp>=1.0.0,<2`: mcp 2.x removed `FastMCP`, so fresh
  installs could not start the server
- Builds: the wheel excludes JSON files and the sdist uses an explicit include
  list, so palette files in the working tree are not packaged.

## v0.5.0 — 2026-07-25

Five new tools (15 → 20), CIEDE2000, parametric pricing, and real-file PDF preflight.

### Added
- `lab_convert_tool` — convert between CIELAB (spectrophotometer readings), CMYK, RGB, and HEX
- `dot_gain_compensation_tool` — inverse of substrate simulation: file values that hit target tints on press
- `ink_limit_check_tool` — total ink coverage (TAC) check with automatic GCR reduction
- `full_job_quote_tool` — imposition + sheet-based costing in one call, the way a print shop quotes
- `pdf_preflight_tool` — preflight a real PDF file: trim/bleed boxes, font embedding, image color spaces (optional `pip install mcp-print[pdf]`)
- CIEDE2000 Delta E — `color_delta_e_tool` now defaults to the industry-standard formula (`method="cie76"` still available)
- Parametric pricing in `print_cost_estimator_tool` — override ink/plate/makeready/run prices in any currency, plus paper cost per sheet
- MCP resources: `mcp-print://pantone-database` and `mcp-print://substrate-profiles`
- MCP prompts: `preflight_job` and `quote_job`
- Python 3.14 in the CI matrix; publish workflow now gated on tests and creates GitHub Releases automatically

### Changed
- `print_cost_estimator_tool` output keys are currency-neutral: `total_cost`, `cost_per_unit`, etc. (previously `total_cost_usd`, ...) with a `currency` field

## v0.4.1 — 2026-07-25

- README: Optiraj attribution and v0.4.0 documentation updates

## v0.4.0 — 2026-07-25

### Added
- `rgb_to_cmyk_tool` — RGB/HEX to CMYK conversion
- `imposition_calculator_tool` — n-up press sheet layout with bleed, gripper, gap, and waste handling
- `booklet_calculator_tool` — signature count, page rounding, spine thickness, binding suitability

### Fixed
- Server failed to start with newer MCP SDK versions (`FastMCP` no longer accepts `description`)

## v0.3.0 and earlier

Initial releases: Pantone database (2,415 colors), CMYK/RGB conversion, Delta E,
ink and cost estimation, ICC profile parsing, spot color separation, barcode ink
coverage, paper weight conversion, preflight checks, substrate simulation.
