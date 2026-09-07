#!/usr/bin/env python3
"""Regenerate and independently decode the committed JPEG photo fixtures."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from jpeg_generate import (
    COLORS,
    HEIGHT,
    INVALID_FIXTURE,
    MANIFEST,
    VALID_FIXTURE,
    WIDTH,
    generated_files,
    load_media_toolchain,
    select_executable,
)


def command(args: list[str], *, ok: bool = True) -> subprocess.CompletedProcess[bytes]:
    result = subprocess.run(args, capture_output=True, check=False)  # noqa: S603
    if (result.returncode == 0) != ok:
        raise RuntimeError(
            f"unexpected exit {result.returncode}: {result.stderr.decode(errors='replace')}"
        )
    return result


def pixel(rgb: bytes, x: int, y: int) -> tuple[int, int, int]:
    offset = (y * WIDTH + x) * 3
    return (rgb[offset], rgb[offset + 1], rgb[offset + 2])


def require_color(actual: tuple[int, int, int], expected: tuple[int, int, int], name: str) -> None:
    if any(abs(actual[channel] - expected[channel]) > 8 for channel in range(3)):
        raise ValueError(f"unexpected decoded color at {name}: {actual}; expected {expected}")


def main() -> None:
    directory = Path(__file__).resolve().parent
    toolchain = load_media_toolchain()
    ffmpeg = select_executable("ffmpeg", toolchain)
    ffprobe = select_executable("ffprobe", toolchain)

    generated = generated_files(ffmpeg, toolchain)
    for name, expected in generated.items():
        if (directory / name).read_bytes() != expected:
            raise ValueError(f"fixture differs from repeated generation: {name}")

    manifest = json.loads((directory / MANIFEST).read_text())
    for record in manifest["fixtures"]:
        contents = (directory / record["filename"]).read_bytes()
        if hashlib.sha256(contents).hexdigest() != record["sha256"]:
            raise ValueError(f"SHA-256 mismatch: {record['filename']}")

    valid_path = directory / VALID_FIXTURE
    probe = command(
        [
            ffprobe,
            "-v",
            "error",
            "-count_frames",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=codec_name,width,height,pix_fmt,color_range,nb_read_frames",
            "-of",
            "json",
            str(valid_path),
        ]
    )
    streams = json.loads(probe.stdout)["streams"]
    if len(streams) != 1:
        raise ValueError(f"expected one image stream, got {len(streams)}")
    stream = streams[0]
    expected_metadata = {
        "codec_name": "mjpeg",
        "width": WIDTH,
        "height": HEIGHT,
        "pix_fmt": "yuvj444p",
        "color_range": "pc",
        "nb_read_frames": "1",
    }
    if stream != expected_metadata:
        raise ValueError(f"unexpected JPEG stream metadata: {stream}")

    decoded = command(
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(valid_path),
            "-frames:v",
            "1",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "pipe:1",
        ]
    ).stdout
    if len(decoded) != WIDTH * HEIGHT * 3:
        raise ValueError(f"unexpected decoded byte count: {len(decoded)}")
    interiors = (
        (range(8, WIDTH // 2 - 8), range(8, HEIGHT // 2 - 8), COLORS[0], "top-left"),
        (range(WIDTH // 2 + 8, WIDTH - 8), range(8, HEIGHT // 2 - 8), COLORS[1], "top-right"),
        (range(8, WIDTH // 2 - 8), range(HEIGHT // 2 + 8, HEIGHT - 8), COLORS[2], "bottom-left"),
        (
            range(WIDTH // 2 + 8, WIDTH - 8),
            range(HEIGHT // 2 + 8, HEIGHT - 8),
            COLORS[3],
            "bottom-right",
        ),
    )
    sampled_pixels = 0
    for xs, ys, expected_color, name in interiors:
        for y in ys:
            for x in xs:
                require_color(pixel(decoded, x, y), expected_color, f"{name} {(x, y)}")
                sampled_pixels += 1
    if sampled_pixels != 512:
        raise ValueError(f"unexpected interior sample count: {sampled_pixels}")

    invalid_path = directory / INVALID_FIXTURE
    command([ffmpeg, "-v", "error", "-i", str(invalid_path), "-f", "null", "-"], ok=False)
    print(json.dumps({"alpha": False, "format": "mjpeg", "height": HEIGHT, "width": WIDTH}))


if __name__ == "__main__":
    main()
