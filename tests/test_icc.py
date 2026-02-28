"""Tests for ICC profile parser."""

import struct
import tempfile
from pathlib import Path

import pytest

from mcp_print.tools.icc import icc_profile_info


def _make_minimal_icc(
    color_space: bytes = b"CMYK",
    device_class: bytes = b"prtr",
    pcs: bytes = b"XYZ ",
) -> bytes:
    """Build a minimal valid ICC profile (header only, no tags)."""
    header = bytearray(128)
    # Profile size (128 bytes header + 4 bytes tag count)
    struct.pack_into(">I", header, 0, 132)
    # Version 2.4.0
    struct.pack_into(">I", header, 8, 0x02400000)
    # Device class
    header[12:16] = device_class
    # Color space
    header[16:20] = color_space
    # PCS
    header[20:24] = pcs
    # Date/time: 2024-01-15 10:30:00
    struct.pack_into(">6H", header, 24, 2024, 1, 15, 10, 30, 0)
    # Signature
    header[36:40] = b"acsp"
    # Tag count = 0
    tag_count = struct.pack(">I", 0)
    return bytes(header) + tag_count


class TestICCProfileInfo:
    def test_parse_minimal_cmyk(self) -> None:
        data = _make_minimal_icc()
        with tempfile.NamedTemporaryFile(suffix=".icc", delete=False) as f:
            f.write(data)
            f.flush()
            result = icc_profile_info(f.name)
        assert result["color_space"] == "CMYK"
        assert result["device_class"] == "Output (Printer)"
        assert result["version"] == "2.4.0"
        assert result["creation_date"] == "2024-01-15T10:30:00"
        assert result["pcs"] == "XYZ"

    def test_parse_rgb_monitor(self) -> None:
        data = _make_minimal_icc(color_space=b"RGB ", device_class=b"mntr")
        with tempfile.NamedTemporaryFile(suffix=".icc", delete=False) as f:
            f.write(data)
            f.flush()
            result = icc_profile_info(f.name)
        assert result["color_space"] == "RGB"
        assert result["device_class"] == "Display (Monitor)"

    def test_file_not_found(self) -> None:
        with pytest.raises(FileNotFoundError):
            icc_profile_info("/nonexistent/path/profile.icc")

    def test_invalid_signature(self) -> None:
        data = bytearray(_make_minimal_icc())
        data[36:40] = b"XXXX"
        with tempfile.NamedTemporaryFile(suffix=".icc", delete=False) as f:
            f.write(bytes(data))
            f.flush()
            with pytest.raises(ValueError, match="Not a valid ICC"):
                icc_profile_info(f.name)

    def test_file_too_small(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".icc", delete=False) as f:
            f.write(b"tiny")
            f.flush()
            with pytest.raises(ValueError, match="too small"):
                icc_profile_info(f.name)
