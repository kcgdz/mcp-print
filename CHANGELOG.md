# Changelog

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
