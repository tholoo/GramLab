#!/usr/bin/env python3
"""Regenerate and independently decode the committed custom-emoji fixtures."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

from generate import FRAMES, HEIGHT, WIDTH, generated_files, rgba_frame, thumbnail_rgba


def command(args: list[str], *, ok: bool = True) -> subprocess.CompletedProcess[bytes]:
    result = subprocess.run(args, capture_output=True, check=False)  # noqa: S603
    if (result.returncode == 0) != ok:
        raise RuntimeError(
            f"unexpected exit {result.returncode}: {result.stderr.decode(errors='replace')}"
        )
    return result


def decode_rgba(ffmpeg: str, path: Path, decoder: str | None = None) -> bytes:
    args = [ffmpeg, "-hide_banner", "-loglevel", "error"]
    if decoder:
        args += ["-c:v", decoder]
    args += ["-i", str(path), "-f", "rawvideo", "-pix_fmt", "rgba", "pipe:1"]
    return command(args).stdout


def pixel(frame: bytes, width: int, x: int, y: int) -> tuple[int, int, int, int]:
    offset = (y * width + x) * 4
    return (frame[offset], frame[offset + 1], frame[offset + 2], frame[offset + 3])


def require_visible_rgba(actual: bytes, expected: bytes, name: str) -> None:
    if len(actual) != len(expected):
        raise ValueError(f"unexpected decoded size: {name}")
    for offset in range(0, len(expected), 4):
        if actual[offset + 3] != expected[offset + 3]:
            raise ValueError(f"alpha differs from specified geometry: {name}")
        if expected[offset + 3] and actual[offset : offset + 3] != expected[offset : offset + 3]:
            raise ValueError(f"opaque color differs from specified geometry: {name}")


def require_color(
    actual: tuple[int, int, int, int], expected: tuple[int, int, int], name: str
) -> None:
    if actual[3] != 255 or any(
        abs(actual[channel] - expected[channel]) > 20 for channel in range(3)
    ):
        raise ValueError(f"unexpected decoded color: {name}: {actual}")


def require_animation_geometry(frame: bytes, index: int) -> None:
    left = 10 + index * 18
    top = 35 + (index % 2) * 20
    colors = ((240, 48, 72), (48, 190, 240), (248, 184, 40), (112, 72, 232))
    for y in range(HEIGHT):
        for x in range(WIDTH):
            expected_alpha = (
                255
                if (8 <= x < 24 and 8 <= y < 24) or (left <= x < left + 24 and top <= y < top + 24)
                else 0
            )
            if pixel(frame, WIDTH, x, y)[3] != expected_alpha:
                raise ValueError(f"frame {index} alpha geometry differs at {(x, y)}")
    require_color(pixel(frame, WIDTH, 12, 12), (32, 220, 96), f"frame {index} marker")
    require_color(pixel(frame, WIDTH, left + 12, top + 12), colors[index], f"frame {index} square")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ffmpeg", default="ffmpeg")
    parser.add_argument("--ffprobe", default="ffprobe")
    args = parser.parse_args()
    directory = Path(__file__).resolve().parent

    generated = generated_files(args.ffmpeg)
    for name, expected in generated.items():
        if (actual := (directory / name).read_bytes()) != expected:
            raise ValueError(f"fixture differs from repeated generation: {name}")
        if name.endswith(".webp") and (b"VP8L" not in actual or b"VP8 " in actual):
            raise ValueError(f"WebP is not encoded as lossless VP8L: {name}")

    manifest = json.loads((directory / "manifest.json").read_text())
    for record in manifest["fixtures"]:
        contents = (directory / record["filename"]).read_bytes()
        if hashlib.sha256(contents).hexdigest() != record["sha256"]:
            raise ValueError(f"SHA-256 mismatch: {record['filename']}")

    static = decode_rgba(args.ffmpeg, directory / "emoji-static.webp")
    require_visible_rgba(static, rgba_frame(0), "static WebP")
    thumbnail = decode_rgba(args.ffmpeg, directory / "emoji-thumbnail.webp")
    require_visible_rgba(thumbnail, thumbnail_rgba(), "thumbnail WebP")

    animation = decode_rgba(args.ffmpeg, directory / "emoji-animated.webm", "libvpx-vp9")
    frame_size = WIDTH * HEIGHT * 4
    if len(animation) != FRAMES * frame_size:
        raise ValueError(f"expected {FRAMES} decoded frames, got {len(animation) // frame_size}")
    frames = [animation[index * frame_size : (index + 1) * frame_size] for index in range(FRAMES)]
    if len({hashlib.sha256(frame).digest() for frame in frames}) != FRAMES:
        raise ValueError("animation frames do not visibly change")
    for index, frame in enumerate(frames):
        require_animation_geometry(frame, index)

    with tempfile.TemporaryDirectory(prefix="gramlab-custom-emoji-") as temporary:
        generated_animation = Path(temporary) / "generated.webm"
        generated_animation.write_bytes(generated["emoji-animated.webm"])
        decoded_generated = decode_rgba(args.ffmpeg, generated_animation, "libvpx-vp9")
        if decoded_generated != animation:
            raise ValueError("repeated WebM encode has different decoded pixels")

    probe = command(
        [
            args.ffprobe,
            "-v",
            "error",
            "-count_frames",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=codec_name,width,height,nb_read_frames,r_frame_rate:stream_tags=alpha_mode",
            "-show_entries",
            "format=format_name,duration:packet=pts_time,duration_time",
            "-show_packets",
            "-of",
            "json",
            str(directory / "emoji-animated.webm"),
        ]
    )
    metadata = json.loads(probe.stdout)
    if metadata["format"]["format_name"] != "matroska,webm" or len(metadata["streams"]) != 1:
        raise ValueError(f"unexpected WebM container: {metadata['format']}")
    if float(metadata["format"]["duration"]) != 1.0:
        raise ValueError(f"unexpected WebM container duration: {metadata['format']['duration']}")
    stream = metadata["streams"][0]
    if (stream["codec_name"], stream["width"], stream["height"], stream["nb_read_frames"]) != (
        "vp9",
        WIDTH,
        HEIGHT,
        str(FRAMES),
    ):
        raise ValueError(f"unexpected WebM stream metadata: {stream}")
    if stream.get("tags", {}).get("alpha_mode") != "1":
        raise ValueError("WebM stream does not declare alpha mode")
    timestamps = [float(packet["pts_time"]) for packet in metadata["packets"]]
    durations = [float(packet["duration_time"]) for packet in metadata["packets"]]
    if (
        stream["r_frame_rate"] != "4/1"
        or timestamps != [0.0, 0.25, 0.5, 0.75]
        or durations != [0.25] * FRAMES
    ):
        raise ValueError("unexpected WebM frame timing")

    command(
        [args.ffprobe, "-v", "error", str(directory / "emoji-truncated-invalid.webm")], ok=False
    )
    command(
        [
            args.ffmpeg,
            "-v",
            "error",
            "-i",
            str(directory / "emoji-truncated-invalid.webm"),
            "-f",
            "null",
            "-",
        ],
        ok=False,
    )
    print(
        json.dumps(
            {
                "decoded_frames": FRAMES,
                "alpha": True,
                "changing_frames": FRAMES,
                "static_webp": [100, 100],
                "thumbnail_webp": [16, 16],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
