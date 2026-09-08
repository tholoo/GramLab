"""Retain original guest raw frames and losslessly encode host PNG derivatives."""

from __future__ import annotations

import hashlib
import json
import re
import shlex
import stat
import struct
import subprocess
import uuid
import zlib
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

COUNT = 24
WIDTH, HEIGHT = 320, 640
# Verified Android 36 x86_64 profile only: packed RGBA8888, sRGB, opaque screen.
RAW_HEADER = struct.pack("<4I", WIDTH, HEIGHT, 1, 1)
MAX_FRAME_BYTES = len(RAW_HEADER) + WIDTH * HEIGHT * 4
MAX_MANIFEST_BYTES = 8192
UPTIME_QUANTUM_NS = 10_000_000
UPTIME = r"(?:0|[1-9][0-9]{0,8})\.[0-9]{2}"
RECORD = re.compile(
    rf"FRAME ([0-9]{{2}}) ({UPTIME}) ({UPTIME}) ([1-9][0-9]{{0,7}}) ([a-f0-9]{{64}})"
)


@dataclass(frozen=True)
class Frame:
    name: str
    start_ns: int
    end_ns: int
    size: int
    sha256: str


def capture_command(directory: str, token: str) -> tuple[str, ...]:
    """Quote the complete script for ADB's outer shell and the explicit inner sh."""
    script = f"""set -eu
umask 077
mkdir {shlex.quote(directory)}
printf 'GRAMLAB_SCREENSHOT_BURST 2 RAW_RGBA_8888_SRGB {token} {COUNT}\\n'
i=0
while [ "$i" -lt {COUNT} ]; do
    frame={shlex.quote(directory)}/edited-burst-$(printf '%02d' "$i").raw
    read -r start ignored < /proc/uptime
    screencap "$frame"
    read -r end ignored < /proc/uptime
    [ -s "$frame" ]
    bytes=$(toybox wc -c < "$frame")
    digest=$(toybox sha256sum "$frame")
    digest=${{digest%% *}}
    printf 'FRAME %02d %s %s %d %s\\n' "$i" "$start" "$end" "$bytes" "$digest"
    sleep 0.08
    i=$((i + 1))
done
printf 'END {COUNT}\\n'
"""
    if re.fullmatch(r"[a-f0-9]{32}", token) is None:
        raise ValueError("Invalid screenshot burst token")
    return "shell", "-T", "sh", "-c", shlex.quote(script)


def parse_manifest(raw: str, token: str) -> list[Frame]:
    """Keep /proc/uptime's truncated centiseconds as conservative interval bounds."""
    if len(raw.encode()) > MAX_MANIFEST_BYTES:
        raise ValueError("Screenshot burst manifest exceeds its bound")
    lines = raw.split("\n")
    if (
        len(lines) != COUNT + 3
        or lines[0] != f"GRAMLAB_SCREENSHOT_BURST 2 RAW_RGBA_8888_SRGB {token} {COUNT}"
        or lines[-2:] != [f"END {COUNT}", ""]
    ):
        raise ValueError("Incomplete or unrelated screenshot burst manifest")
    frames: list[Frame] = []
    for index, line in enumerate(lines[1:-2]):
        match = RECORD.fullmatch(line)
        if match is None or match[1] != f"{index:02d}":
            raise ValueError("Malformed or unordered screenshot burst record")
        start = int(match[2].replace(".", "")) * UPTIME_QUANTUM_NS
        end = (int(match[3].replace(".", "")) + 1) * UPTIME_QUANTUM_NS
        size = int(match[4])
        # The animation oracle separately retains its strict half-period bound.
        # Framing admits slow captures so their original raw frames survive a timing red.
        if end <= start or end - start > 60_000_000_000 or size != MAX_FRAME_BYTES:
            raise ValueError("Unbounded screenshot burst record")
        if frames and frames[-1].end_ns > start:
            raise ValueError("Screenshot burst acquisition bounds overlap or regress")
        frames.append(Frame(f"edited-burst-{index:02d}.raw", start, end, size, match[5]))
    return frames


def raw_pixels(value: bytes) -> bytes:
    """Accept only the source-verified framing; never guess or convert pixel layouts."""
    if len(value) != MAX_FRAME_BYTES or value[:16] != RAW_HEADER:
        raise ValueError("Unsupported raw screenshot header or exact packed length")
    pixels = value[16:]
    # Screencap's buffer is premultiplied. Opaque pixels need no alpha conversion.
    if pixels[3::4] != b"\xff" * (WIDTH * HEIGHT):
        raise ValueError("Unsupported nonopaque raw screenshot alpha")
    return pixels


def encode_png(pixels: bytes) -> bytes:
    """Encode verified RGBA bytes with no filtering, color conversion or geometry change."""
    if len(pixels) != WIDTH * HEIGHT * 4:
        raise ValueError("Invalid RGBA pixel length")

    def chunk(kind: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
        )

    stride = WIDTH * 4
    scanlines = b"".join(b"\x00" + pixels[y : y + stride] for y in range(0, len(pixels), stride))
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", WIDTH, HEIGHT, 8, 6, 0, 0, 0))
        + chunk(b"sRGB", b"\x00")
        + chunk(b"IDAT", zlib.compress(scanlines))
        + chunk(b"IEND", b"")
    )


def validate_transfer(directory: Path, frames: list[Frame]) -> list[bytes]:
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError("Screenshot burst transfer is not a directory")
    if {path.name for path in directory.iterdir()} != {frame.name for frame in frames}:
        raise ValueError("Screenshot burst transfer has missing or unexpected files")
    pixels = []
    for frame in frames:
        path = directory / frame.name
        status = path.lstat()
        if not stat.S_ISREG(status.st_mode) or status.st_size != frame.size:
            raise ValueError("Screenshot burst transfer has an invalid file")
        with path.open("rb") as stream:
            value = stream.read(MAX_FRAME_BYTES + 1)
        if len(value) != frame.size or hashlib.sha256(value).hexdigest() != frame.sha256:
            raise ValueError("Screenshot burst transfer changed original raw bytes")
        pixels.append(raw_pixels(value))
    return pixels


def capture_burst(
    guest: Callable[..., subprocess.CompletedProcess[str]], output: Path
) -> tuple[list[int], list[int]]:
    token = uuid.uuid4().hex
    basename = f"custom-emoji-burst-{token}"
    remote = f"/data/local/tmp/{basename}"
    local = output / basename
    if local.exists() or local.is_symlink():
        raise ValueError("Screenshot burst staging path already exists")
    result = guest(*capture_command(remote, token), timeout=60)
    if (
        len(result.stdout.encode()) > MAX_MANIFEST_BYTES
        or len(result.stderr.encode()) > MAX_MANIFEST_BYTES
    ):
        raise ValueError("Screenshot burst command output exceeds its bound")
    with (output / "edited-burst-manifest.txt").open("x") as stream:
        stream.write(result.stdout)
    with (output / "edited-burst-stderr.txt").open("x") as stream:
        stream.write(result.stderr)
    if result.returncode:
        raise RuntimeError("Original guest screenshot burst command failed")
    frames = parse_manifest(result.stdout, token)
    transferred = guest("pull", remote, str(local), timeout=60)
    if transferred.returncode:
        raise RuntimeError("Original guest screenshot burst transfer failed")
    pixels = validate_transfer(local, frames)
    names = [Path(frame.name).with_suffix(".png").name for frame in frames]
    metadata_name = "edited-burst-derivation.json"
    if any(
        (output / name).exists() or (output / name).is_symlink() for name in [*names, metadata_name]
    ):
        raise ValueError("Screenshot burst output path already exists")
    # All original raw files have passed framing and digest checks before encoding.
    derived = local / "png"
    derived.mkdir()
    records = []
    for frame, name, rgba in zip(frames, names, pixels, strict=True):
        png = encode_png(rgba)
        with (derived / name).open("xb") as stream:
            stream.write(png)
        records.append(
            {
                "raw_path": f"{basename}/{frame.name}",
                "raw_size": frame.size,
                "raw_sha256": frame.sha256,
                "start_ns": frame.start_ns,
                "end_ns": frame.end_ns,
                "rgba_sha256": hashlib.sha256(rgba).hexdigest(),
                "png_path": name,
                "png_size": len(png),
                "png_sha256": hashlib.sha256(png).hexdigest(),
            }
        )
    metadata = {
        "schema": 1,
        "input_format": "android-screencap-raw",
        "raw_header_le_uint32": [WIDTH, HEIGHT, 1, 1],
        "opaque": True,
        "derivation": "lossless-png-rgba8",
        "manifest_path": "edited-burst-manifest.txt",
        "manifest_sha256": hashlib.sha256(result.stdout.encode()).hexdigest(),
        "frames": records,
    }
    with (derived / metadata_name).open("x") as stream:
        json.dump(metadata, stream, sort_keys=True, indent=2)
        stream.write("\n")
    published: list[Path] = []
    try:
        for name in [*names, metadata_name]:
            # Keep raw originals and staged derivatives; never overwrite prior evidence.
            destination = output / name
            destination.hardlink_to(derived / name)
            published.append(destination)
    except BaseException:
        for destination in published:
            destination.unlink()
        raise
    return [frame.start_ns for frame in frames], [frame.end_ns for frame in frames]
