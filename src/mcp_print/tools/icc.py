"""ICC profile header parser — no external dependencies, uses struct only."""

from __future__ import annotations

import struct
from pathlib import Path
from typing import TypedDict


class ICCProfileInfo(TypedDict):
    profile_name: str
    color_space: str
    device_class: str
    creation_date: str
    description: str
    version: str
    pcs: str
    file_size: int


# ICC device class signatures (4-byte ASCII)
_DEVICE_CLASSES: dict[bytes, str] = {
    b"scnr": "Input (Scanner)",
    b"mntr": "Display (Monitor)",
    b"prtr": "Output (Printer)",
    b"link": "DeviceLink",
    b"spac": "ColorSpace Conversion",
    b"abst": "Abstract",
    b"nmcl": "Named Color",
}

# Color space signatures
_COLOR_SPACES: dict[bytes, str] = {
    b"XYZ ": "XYZ",
    b"Lab ": "CIELAB",
    b"Luv ": "CIELUV",
    b"YCbr": "YCbCr",
    b"Yxy ": "CIE Yxy",
    b"RGB ": "RGB",
    b"GRAY": "Grayscale",
    b"HSV ": "HSV",
    b"HLS ": "HLS",
    b"CMYK": "CMYK",
    b"CMY ": "CMY",
    b"2CLR": "2 Color",
    b"3CLR": "3 Color",
    b"4CLR": "4 Color",
    b"5CLR": "5 Color",
    b"6CLR": "6 Color",
    b"7CLR": "7 Color",
    b"8CLR": "8 Color",
}


def _read_desc_tag(data: bytes, offset: int, size: int) -> str:
    """Try to read a 'desc' tag from profile data."""
    if size < 12:
        return ""
    tag_type = data[offset:offset + 4]
    if tag_type == b"desc":
        # ICC v2 textDescription type
        str_len = struct.unpack_from(">I", data, offset + 8)[0]
        if str_len > 0 and offset + 12 + str_len <= len(data):
            return data[offset + 12:offset + 12 + str_len].decode("ascii", errors="replace").rstrip("\x00")
    elif tag_type == b"mluc":
        # ICC v4 multiLocalizedUnicode type
        if size < 16:
            return ""
        count = struct.unpack_from(">I", data, offset + 8)[0]
        if count > 0 and size >= 28:
            str_offset = struct.unpack_from(">I", data, offset + 20)[0]
            str_len = struct.unpack_from(">I", data, offset + 24)[0]
            abs_offset = offset + str_offset
            if abs_offset + str_len <= len(data):
                return data[abs_offset:abs_offset + str_len].decode("utf-16-be", errors="replace").rstrip("\x00")
    return ""


def icc_profile_info(file_path: str) -> ICCProfileInfo:
    """Parse basic metadata from an ICC profile file.

    Reads only the 128-byte header and the ``desc`` tag.
    No external dependencies required.

    Args:
        file_path: Path to an ICC/ICM profile file.

    Returns:
        Dict with ``profile_name``, ``color_space``, ``device_class``,
        ``creation_date``, ``description``, ``version``, ``pcs``,
        and ``file_size``.

    Raises:
        ValueError: If the file is not a valid ICC profile.
        FileNotFoundError: If the file does not exist.
    """
    path = Path(file_path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"ICC profile not found: {file_path}")

    data = path.read_bytes()
    if len(data) < 128:
        raise ValueError(f"File too small to be an ICC profile ({len(data)} bytes)")

    # Validate signature at offset 36
    sig = data[36:40]
    if sig != b"acsp":
        raise ValueError(f"Not a valid ICC profile (expected 'acsp' signature, got {sig!r})")

    # Header fields
    profile_size = struct.unpack_from(">I", data, 0)[0]
    version_raw = struct.unpack_from(">I", data, 8)[0]
    major = (version_raw >> 24) & 0xFF
    minor = (version_raw >> 20) & 0x0F
    bugfix = (version_raw >> 16) & 0x0F
    version = f"{major}.{minor}.{bugfix}"

    device_class_sig = data[12:16]
    color_space_sig = data[16:20]
    pcs_sig = data[20:24]

    # Creation date/time (bytes 24-35)
    year, month, day, hour, minute, second = struct.unpack_from(">6H", data, 24)
    creation_date = f"{year:04d}-{month:02d}-{day:02d}T{hour:02d}:{minute:02d}:{second:02d}"

    device_class = _DEVICE_CLASSES.get(device_class_sig, device_class_sig.decode("ascii", errors="replace").strip())
    color_space = _COLOR_SPACES.get(color_space_sig, color_space_sig.decode("ascii", errors="replace").strip())
    pcs = _COLOR_SPACES.get(pcs_sig, pcs_sig.decode("ascii", errors="replace").strip())

    # Try to find the 'desc' tag for profile description
    description = ""
    if len(data) >= 132:
        tag_count = struct.unpack_from(">I", data, 128)[0]
        tag_table_end = 132 + tag_count * 12
        if tag_table_end <= len(data):
            for i in range(tag_count):
                tag_offset = 132 + i * 12
                tag_sig = data[tag_offset:tag_offset + 4]
                t_offset = struct.unpack_from(">I", data, tag_offset + 4)[0]
                t_size = struct.unpack_from(">I", data, tag_offset + 8)[0]
                if tag_sig == b"desc" and t_offset + t_size <= len(data):
                    description = _read_desc_tag(data, t_offset, t_size)
                    break

    profile_name = description or path.stem

    return {
        "profile_name": profile_name,
        "color_space": color_space,
        "device_class": device_class,
        "creation_date": creation_date,
        "description": description,
        "version": version,
        "pcs": pcs,
        "file_size": len(data),
    }
