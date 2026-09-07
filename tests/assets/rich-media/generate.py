#!/usr/bin/env python3
"""Generate GramLab's deterministic, original rich-media PNG fixtures."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import zlib
from pathlib import Path

_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_VALID_FIXTURES = {
    "photo-square-16x16.png": (16, 16),
    "photo-tall-8x48.png": (8, 48),
    "photo-wide-48x8.png": (48, 8),
    "photo-landscape-48x12.png": (48, 12),
}
_INVALID_FIXTURE = "photo-truncated-invalid.png"


def _chunk(kind: bytes, payload: bytes) -> bytes:
    checksum = zlib.crc32(kind + payload)
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", checksum)


def _pixel(x: int, y: int, width: int, height: int) -> bytes:
    corners = {
        (0, 0): (255, 32, 32, 255),
        (width - 1, 0): (32, 220, 64, 255),
        (0, height - 1): (32, 96, 255, 255),
        (width - 1, height - 1): (255, 224, 32, 255),
    }
    if (x, y) in corners:
        return bytes(corners[x, y])
    red = (x * 37 + y * 11) % 192 + 32
    green = (x * 13 + y * 43) % 192 + 32
    blue = 240 if (x + y) % 3 == 0 else 48
    if x * max(height - 1, 1) == y * max(width - 1, 1):
        return bytes((255, 255, 255, 255))
    return bytes((red, green, blue, 255))


def _png(width: int, height: int) -> bytes:
    scanlines = b"".join(
        b"\x00" + b"".join(_pixel(x, y, width, height) for x in range(width)) for y in range(height)
    )
    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return (
        _PNG_SIGNATURE
        + _chunk(b"IHDR", header)
        + _chunk(b"IDAT", zlib.compress(scanlines, level=9))
        + _chunk(b"IEND", b"")
    )


def _manifest(files: dict[str, bytes]) -> bytes:
    fixtures: list[dict[str, object]] = []
    for filename in sorted(files):
        record: dict[str, object] = {
            "filename": filename,
            "valid": filename != _INVALID_FIXTURE,
            "mime": "image/png",
            "sha256": hashlib.sha256(files[filename]).hexdigest(),
            "provenance": {"license": "MIT", "source": "original GramLab generator"},
        }
        if filename in _VALID_FIXTURES:
            record["width"] = _VALID_FIXTURES[filename][0]
            record["height"] = _VALID_FIXTURES[filename][1]
        fixtures.append(record)
    return (json.dumps({"fixtures": fixtures}, indent=2, sort_keys=True) + "\n").encode()


def generated_files() -> dict[str, bytes]:
    """Return every generated file as deterministic bytes."""
    files = {filename: _png(width, height) for filename, (width, height) in _VALID_FIXTURES.items()}
    files[_INVALID_FIXTURE] = files["photo-square-16x16.png"][:32]
    files["manifest.json"] = _manifest(files)
    return files


def _write_exact(output_directory: Path, filename: str, contents: bytes) -> None:
    destination = output_directory / filename
    if destination.exists() or destination.is_symlink():
        if not destination.is_file() or destination.is_symlink():
            raise ValueError(f"refusing non-regular destination: {destination}")
        if destination.read_bytes() != contents:
            raise ValueError(f"refusing to overwrite differing file: {destination}")
        return
    destination.write_bytes(contents)


def generate(output_directory: Path) -> None:
    """Write fixtures only inside an explicitly selected safe directory."""
    if output_directory.is_symlink() or not output_directory.is_dir():
        raise ValueError("output directory must be an existing, non-symlink directory")
    for filename, contents in generated_files().items():
        _write_exact(output_directory, filename, contents)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_directory", type=Path)
    arguments = parser.parse_args()
    generate(arguments.output_directory)


if __name__ == "__main__":
    main()
