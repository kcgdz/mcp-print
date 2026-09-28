"""Server-level tests: tool registry and behavior with and without a palette."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

import pytest

from mcp_print.server import mcp

PACKAGE_DIR = Path(__file__).resolve().parent.parent / "src" / "mcp_print"


def _call(name: str, arguments: dict) -> dict:
    result = asyncio.run(mcp.call_tool(name, arguments))
    content = result[0] if isinstance(result, tuple) else result
    return json.loads(content[0].text)


class TestRegistry:
    def test_palette_tools_registered(self) -> None:
        names = {t.name for t in asyncio.run(mcp.list_tools())}
        assert {"palette_lookup_tool", "palette_search_tool", "spot_color_separator_tool"} <= names
        assert "pantone_to_cmyk_tool" not in names
        assert "pantone_search_tool" not in names
        assert len(names) == 20

    def test_no_bulk_palette_resource(self) -> None:
        uris = {str(r.uri) for r in asyncio.run(mcp.list_resources())}
        assert uris == {"mcp-print://substrate-profiles"}

    def test_no_bundled_color_data(self) -> None:
        assert not (PACKAGE_DIR / "data").exists()
        assert list(PACKAGE_DIR.rglob("*.json")) == []

    def test_instructions_make_no_bundled_library_claim(self) -> None:
        assert "Pantone" not in (mcp.instructions or "")
        assert "MCP_PRINT_PALETTE_PATH" in (mcp.instructions or "")


class TestWithoutPalette:
    def test_palette_tools_return_clear_errors(self) -> None:
        for name, args in [
            ("palette_lookup_tool", {"name": "Anything"}),
            ("palette_search_tool", {"hex_color": "#336699"}),
            ("spot_color_separator_tool", {"colors": [{"c": 10, "m": 20, "y": 30, "k": 0}]}),
        ]:
            result = _call(name, args)
            assert "MCP_PRINT_PALETTE_PATH" in result["error"], name

    @pytest.mark.parametrize(
        "name, args, key",
        [
            ("cmyk_to_rgb_tool", {"c": 0, "m": 0, "y": 0, "k": 100}, "hex"),
            ("rgb_to_cmyk_tool", {"hex_color": "#336699"}, "c"),
            ("lab_convert_tool", {"hex_color": "#336699"}, "lab"),
            ("color_delta_e_tool", {"c1": 0, "m1": 0, "y1": 0, "k1": 0, "c2": 0, "m2": 0, "y2": 0, "k2": 10}, "delta_e"),
            ("ink_consumption_tool", {"width_mm": 210, "height_mm": 297, "coverage_percent": 30, "print_method": "offset", "quantity": 1000}, "ink_grams"),
            ("print_cost_estimator_tool", {"width_mm": 210, "height_mm": 297, "quantity": 1000, "num_colors": 4, "paper_gsm": 120, "print_method": "offset"}, "total_cost"),
            ("icc_profile_info_tool", {"file_path": "does-not-exist.icc"}, "error"),
            ("paper_weight_converter_tool", {"value": 80, "from_unit": "lb_text", "to_unit": "gsm"}, "value"),
            ("substrate_simulator_tool", {"c": 50, "m": 30, "y": 20, "k": 10}, "simulated"),
            ("ink_limit_check_tool", {"c": 90, "m": 90, "y": 90, "k": 90}, "within_limit"),
        ],
    )
    def test_independent_tools_work(self, name: str, args: dict, key: str) -> None:
        assert key in _call(name, args)


class TestWithPalette:
    def test_lookup_and_search(self, synthetic_palette) -> None:
        found = _call("palette_lookup_tool", {"name": "test ochre"})
        assert found["color"]["name"] == "Test Ochre"
        assert found["source"] == "user_palette"

        missing = _call("palette_lookup_tool", {"name": "Ochre"})
        assert "error" in missing
        assert missing["suggestions"] == ["Test Ochre"]

        search = _call("palette_search_tool", {"c": 60, "m": 45, "y": 35, "k": 40, "limit": 1})
        assert search["matches"][0]["name"] == "Test Slate"

    def test_invalid_palette_reported(self, write_palette) -> None:
        write_palette("{broken", raw=True)
        result = _call("palette_search_tool", {"hex_color": "#336699"})
        assert "not valid JSON" in result["error"]
        assert "hex" in _call("cmyk_to_rgb_tool", {"c": 0, "m": 0, "y": 0, "k": 0})


def test_stdio_server_starts_without_palette() -> None:
    """Launch the real server over stdio and call a tool, with no palette configured."""
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    env = {k: v for k, v in os.environ.items() if k != "MCP_PRINT_PALETTE_PATH"}
    env["PYTHONPATH"] = str(PACKAGE_DIR.parent) + os.pathsep + env.get("PYTHONPATH", "")
    params = StdioServerParameters(command=sys.executable, args=["-m", "mcp_print"], env=env)

    async def run() -> tuple[set[str], dict, dict]:
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = {t.name for t in (await session.list_tools()).tools}
                ok = await session.call_tool("cmyk_to_rgb_tool", {"c": 100, "m": 0, "y": 0, "k": 0})
                err = await session.call_tool("palette_lookup_tool", {"name": "Anything"})
                return tools, json.loads(ok.content[0].text), json.loads(err.content[0].text)

    tools, ok, err = asyncio.run(asyncio.wait_for(run(), timeout=60))
    assert "palette_lookup_tool" in tools
    assert ok["hex"] == "#00FFFF"
    assert "MCP_PRINT_PALETTE_PATH" in err["error"]
