"""Shared fixtures. Palettes here are synthetic and brand-free."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mcp_print.tools import palette as palette_module
from mcp_print.tools.palette import PALETTE_ENV_VAR

SYNTHETIC_COLORS = [
    {"name": "Test Red", "c": 0, "m": 90, "y": 85, "k": 0},
    {"name": "Test Teal", "c": 80, "m": 10, "y": 45, "k": 5},
    {"name": "Test Ochre", "c": 10, "m": 35, "y": 95, "k": 10},
    {"name": "Test Slate", "c": 60, "m": 45, "y": 35, "k": 40},
    {"name": "Paper White", "c": 0, "m": 0, "y": 0, "k": 0},
]


@pytest.fixture(autouse=True)
def _isolate_palette_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Never let a developer's own palette leak into tests."""
    monkeypatch.delenv(PALETTE_ENV_VAR, raising=False)
    palette_module._CACHE.clear()


@pytest.fixture
def write_palette(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Write raw palette content to a temp file and point the env var at it."""

    def _write(content: object, *, raw: bool = False, name: str = "palette.json") -> Path:
        path = tmp_path / name
        text = content if raw else json.dumps(content)
        assert isinstance(text, str)
        path.write_text(text, encoding="utf-8")
        monkeypatch.setenv(PALETTE_ENV_VAR, str(path))
        return path

    return _write


@pytest.fixture
def synthetic_palette(write_palette) -> Path:
    return write_palette({"palette": "Synthetic test palette", "colors": SYNTHETIC_COLORS})
