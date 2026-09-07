#!/usr/bin/env python3
"""Generate original GramLab custom-emoji WebP and WebM fixtures."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

WIDTH = 100
HEIGHT = 100
FRAMES = 4
FPS = 4


def rgba_frame(index: int, width: int = WIDTH, height: int = HEIGHT) -> bytes:
    pixels = bytearray(width * height * 4)
    left = 10 + index * 18
    top = 35 + (index % 2) * 20
    colors = ((240, 48, 72), (48, 190, 240), (248, 184, 40), (112, 72, 232))
    red, green, blue = colors[index % len(colors)]
    for y in range(height):
        for x in range(width):
            offset = (y * width + x) * 4
            if 8 <= x < 24 and 8 <= y < 24:
                pixels[offset : offset + 4] = bytes((32, 220, 96, 255))
            elif left <= x < left + 24 and top <= y < top + 24:
                pixels[offset : offset + 4] = bytes((red, green, blue, 255))
    return bytes(pixels)


def thumbnail_rgba() -> bytes:
    size = 16
    pixels = bytearray(size * size * 4)
    for y in range(size):
        for x in range(size):
            if abs(x - 7) + abs(y - 7) <= 5:
                offset = (y * size + x) * 4
                pixels[offset : offset + 4] = bytes((88, 104, 240, 255))
    return bytes(pixels)


def run_encoder(command: list[str], data: bytes) -> bytes:
    result = subprocess.run(command, input=data, capture_output=True, check=False)  # noqa: S603
    if result.returncode:
        raise RuntimeError(result.stderr.decode(errors="replace"))
    return result.stdout


def run_encoder_file(command: list[str], data: bytes, suffix: str) -> bytes:
    with tempfile.TemporaryDirectory(prefix="gramlab-custom-emoji-") as temporary:
        destination = Path(temporary) / f"encoded{suffix}"
        result = subprocess.run(  # noqa: S603
            [*command, str(destination)], input=data, capture_output=True, check=False
        )
        if result.returncode:
            raise RuntimeError(result.stderr.decode(errors="replace"))
        return destination.read_bytes()


def ffmpeg_profile(ffmpeg: str) -> dict[str, object]:
    result = subprocess.run(  # noqa: S603
        [ffmpeg, "-version"], capture_output=True, text=True, check=True
    )
    lines = result.stdout.splitlines()
    libavcodec = (
        next(line for line in lines if line.startswith("libavcodec"))
        .split("/")[0]
        .split(maxsplit=1)[1]
    )
    normalized_libavcodec = ".".join(part.strip(".") for part in libavcodec.split())
    return {
        "ffmpeg": lines[0],
        "libavcodec": normalized_libavcodec,
        "libvpx": "enabled; exact library revision unavailable from selected executable",
        "libwebp": "enabled; exact library revision unavailable from selected executable",
    }


def generated_files(ffmpeg: str) -> dict[str, bytes]:
    common = [ffmpeg, "-hide_banner", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba"]
    webp = run_encoder(
        [
            *common,
            "-s",
            "100x100",
            "-r",
            "1",
            "-i",
            "pipe:0",
            "-frames:v",
            "1",
            "-c:v",
            "libwebp",
            "-pix_fmt",
            "bgra",
            "-lossless",
            "1",
            "-compression_level",
            "6",
            "-threads",
            "1",
            "-f",
            "webp",
            "pipe:1",
        ],
        rgba_frame(0),
    )
    thumbnail = run_encoder(
        [
            *common,
            "-s",
            "16x16",
            "-r",
            "1",
            "-i",
            "pipe:0",
            "-frames:v",
            "1",
            "-c:v",
            "libwebp",
            "-pix_fmt",
            "bgra",
            "-lossless",
            "1",
            "-compression_level",
            "6",
            "-threads",
            "1",
            "-f",
            "webp",
            "pipe:1",
        ],
        thumbnail_rgba(),
    )
    animation = run_encoder_file(
        [
            *common,
            "-s",
            "100x100",
            "-r",
            str(FPS),
            "-i",
            "pipe:0",
            "-fflags",
            "+bitexact",
            "-frames:v",
            str(FRAMES),
            "-an",
            "-c:v",
            "libvpx-vp9",
            "-lossless",
            "1",
            "-pix_fmt",
            "yuva420p",
            "-flags:v",
            "+bitexact",
            "-deadline",
            "good",
            "-cpu-used",
            "0",
            "-row-mt",
            "0",
            "-tile-columns",
            "0",
            "-frame-parallel",
            "0",
            "-threads",
            "1",
            "-f",
            "webm",
            "-y",
        ],
        b"".join(rgba_frame(index) for index in range(FRAMES)),
        ".webm",
    )
    files = {
        "emoji-static.webp": webp,
        "emoji-thumbnail.webp": thumbnail,
        "emoji-animated.webm": animation,
        "emoji-truncated-invalid.webm": animation[:64],
    }
    records = []
    for name in sorted(files):
        record: dict[str, object] = {
            "filename": name,
            "sha256": hashlib.sha256(files[name]).hexdigest(),
            "valid": name != "emoji-truncated-invalid.webm",
            "provenance": {"license": "MIT", "source": "original GramLab generator"},
        }
        if name.endswith(".webp"):
            size = 16 if "thumbnail" in name else 100
            record.update(mime="image/webp", width=size, height=size, codec="webp", alpha=True)
        else:
            record.update(mime="video/webm", codec="vp9")
            if record["valid"]:
                record.update(
                    width=WIDTH, height=HEIGHT, frames=FRAMES, duration_seconds=1.0, alpha=True
                )
        records.append(record)
    manifest = {
        "generator_profile": {
            **ffmpeg_profile(ffmpeg),
            "reproducibility": (
                "byte-identical under this recorded encoder profile; other versions may differ"
            ),
            "webp_flags": "libwebp bgra lossless=1 compression_level=6 threads=1",
            "webm_flags": (
                "fflags=+bitexact libvpx-vp9 lossless=1 yuva420p flags:v=+bitexact "
                "deadline=good cpu-used=0 row-mt=0 tile-columns=0 frame-parallel=0 threads=1"
            ),
        },
        "fixtures": records,
    }
    files["manifest.json"] = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
    return files


def write_exact(directory: Path, files: dict[str, bytes]) -> None:
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError("output directory must be an existing non-symlink directory")
    for name, contents in files.items():
        destination = directory / name
        if destination.exists() or destination.is_symlink():
            if destination.is_symlink() or not destination.is_file():
                raise ValueError(f"refusing non-regular destination: {destination}")
            if destination.read_bytes() != contents:
                raise ValueError(f"refusing to overwrite differing file: {destination}")
        destination.write_bytes(contents)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_directory", type=Path)
    parser.add_argument("--ffmpeg", default="ffmpeg")
    args = parser.parse_args()
    write_exact(args.output_directory, generated_files(args.ffmpeg))


if __name__ == "__main__":
    main()
