# mcp-print

MCP server for professional print and color workflows. Gives AI assistants the ability to work with 2400+ Pantone colors, CMYK/RGB conversion, ink and cost estimation, ICC profile analysis, spot color separation, barcode coverage, Delta E color difference, and paper weight conversion — all offline, no API keys needed.

## Who is this for?

- **Print designers** checking Pantone-to-CMYK conversions without leaving their editor
- **Prepress engineers** estimating ink costs, verifying color accuracy, and analyzing ICC profiles
- **Packaging teams** converting paper weights, comparing spot colors, and costing print runs

## Install

```bash
pip install mcp-print
```

## Configure with Claude Code

Add to your Claude Code MCP config (`~/.claude/settings.json` or project `.mcp.json`):

```json
{
  "mcpServers": {
    "print": {
      "command": "python",
      "args": ["-m", "mcp_print"]
    }
  }
}
```

Restart Claude Code — all ten tools below will be available immediately.

## Tools

| Tool | Description |
|---|---|
| `pantone_to_cmyk_tool` | Convert a Pantone name to CMYK + HEX (2400+ colors, fuzzy matching) |
| `pantone_search_tool` | Find closest Pantone colors by HEX or CMYK proximity |
| `cmyk_to_rgb_tool` | Convert CMYK values to RGB + HEX |
| `color_delta_e_tool` | Calculate Delta E (CIE76) between two CMYK colors |
| `ink_consumption_tool` | Estimate ink usage and cost for a print run |
| `print_cost_estimator_tool` | Full job cost: ink + plates + makeready + run |
| `icc_profile_info_tool` | Parse ICC/ICM profile metadata from a file |
| `spot_color_separator_tool` | Recommend spot vs process colors for a design |
| `barcode_ink_coverage_tool` | Ink coverage % for Code128, EAN-13, QR, DataMatrix |
| `paper_weight_converter_tool` | Convert between GSM, lb text, and lb cover |

## Usage Examples

Once configured, just ask Claude naturally:

### 1. Pantone lookup (with fuzzy matching)

> "What's the CMYK breakdown for Pantone 485 C?"

Works with any format: `"485C"`, `"pantone 485"`, `"485 coated"`, `"Warm Red"`.

```json
{ "name": "Pantone 485 C", "c": 0, "m": 95, "y": 100, "k": 0, "hex": "#FF0D0D" }
```

### 2. Find closest Pantone to a HEX color

> "What Pantone colors are closest to #DA291C?"

```json
{
  "matches": [
    { "name": "Pantone 485 C", "c": 0, "m": 95, "y": 100, "k": 0, "hex": "#FF0D0D" },
    { "name": "Pantone 485 M", "c": 1, "m": 93, "y": 99, "k": 2, "hex": "#FA0E03" }
  ],
  "search_type": "hex #DA291C"
}
```

### 3. Color conversion

> "Convert CMYK 100/44/0/0 to RGB"

```json
{ "r": 0, "g": 143, "b": 255, "hex": "#008FFF" }
```

### 4. Ink estimation

> "How much ink do I need for 10,000 A4 flyers at 35% coverage on an offset press?"

```json
{ "ink_grams": 327.44, "ink_kg": 0.3274, "cost_estimate_usd": 8.19 }
```

### 5. Full print job costing

> "Cost estimate: 5000 copies of an A4 flyer, 4-color offset, 120gsm, double-sided"

```json
{
  "total_cost_usd": 628.14,
  "cost_per_unit_usd": 0.1256,
  "breakdown": { "ink": 11.34, "plates": 280.0, "makeready": 200.0, "run_cost": 136.8 }
}
```

### 6. Color matching QC

> "Compare our brand blue (100/72/0/18) against the proof (98/70/2/20) — is the Delta E acceptable?"

```json
{ "delta_e": 3.41, "interpretation": "fair — noticeable difference" }
```

### 7. Spot vs process recommendation

> "Should these colors be spot or process?" (with a list of CMYK values)

```json
{
  "spot_colors": [{ "nearest_pantone": "Pantone 485 C", "delta_e": 0.0, "reason": "Close match..." }],
  "process_colors": [{ "nearest_pantone": "Pantone 375 C", "delta_e": 8.2, "reason": "No close match..." }]
}
```

### 8. ICC profile inspection

> "What color space is this ICC profile using?"

```json
{
  "profile_name": "ISOcoated_v2",
  "color_space": "CMYK",
  "device_class": "Output (Printer)",
  "version": "2.4.0"
}
```

### 9. Barcode ink coverage

> "What's the ink coverage for an EAN-13 barcode at 37mm x 26mm?"

```json
{
  "coverage_percent": 52.0,
  "recommended_ink": "Process Black (K: 100)",
  "print_method_suggestion": "offset — good resolution for medium modules"
}
```

### 10. Paper weight conversion

> "What's 80 lb text in GSM?"

```json
{ "value": 118.42, "from_unit": "lb_text", "to_unit": "gsm" }
```

## Pantone Database

The built-in database contains **2400+ Pantone colors** covering:

- **Numeric series** (100-699): Yellows, oranges, reds, pinks, purples, blues, greens, grays, browns
- **7000 series** (7400-7547): Extended gamut colors
- **Special named colors**: Black, White, Warm Red, Reflex Blue, Process Blue, Cool/Warm Grays 1-11, Hexachrome series, and more
- **Three finishes per color**: Coated (C), Uncoated (U), and Matte (M)

Fuzzy matching handles typos and format variations — `"485C"`, `"pantone 485"`, `"485 coated"` all find the right color.

## Development

```bash
git clone https://github.com/mcp-print/mcp-print.git
cd mcp-print
pip install -e .
pip install pytest
pytest tests/ -v
```

## License

MIT
