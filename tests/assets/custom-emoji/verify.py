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
    result = subprocess.run(args, capture_output=True, check=False)
    if (result.returncode == 0) != ok:
        raise RuntimeError(f"unexpected exit {result.returncode}: {result.stderr.decode(errors='replace')}")
    return result


def decode_rgba(ffmpeg: str, path: Path, decoder: str | None = None) -> bytes:
    args = [ffmpeg, "-hide_banner", "-loglevel", "error"]
    if decoder:
        args += ["-c:v", decoder]
    args += ["-i", str(path), "-f", "rawvideo", "-pix_fmt", "rgba", "pipe:1"]
    return command(args).stdout


def pixel(frame: bytes, width: int, x: int, y: int) -> tuple[int, int, int, int]:
    offset = (y * width + x) * 4
    return tuple(frame[offset : offset + 4])  # type: ignore[return-value]


def require_visible_rgba(actual: bytes, expected: bytes, name: str) -> None:
    if len(actual) != len(expected):
        raise ValueError(f"unexpected decoded size: {name}")
    for offset in range(0, len(expected), 4):
        if actual[offset + 3] != expected[offset + 3]:
            raise ValueError(f"alpha differs from specified geometry: {name}")
        if expected[offset + 3] and any(
            abs(actual[offset + channel] - expected[offset + channel]) > 20 for channel in range(3)
        ):
            raise ValueError(f"opaque color differs from specified geometry: {name}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ffmpeg", default="ffmpeg")
    parser.add_argument("--ffprobe", default="ffprobe")
    args = parser.parse_args()
    directory = Path(__file__).resolve().parent

    generated = generated_files(args.ffmpeg)
    for name in ("emoji-static.webp", "emoji-thumbnail.webp"):
        expected = generated[name]
        if (actual := (directory / name).read_bytes()) != expected:
            raise ValueError(f"fixture differs from repeated generation: {name}")

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
        if pixel(frame, WIDTH, 0, 0)[3] != 0 or pixel(frame, WIDTH, 12, 12)[3] != 255:
            raise ValueError(f"frame {index} lacks specified transparent/opaque regions")
        moving_x = 10 + index * 18 + 12
        moving_y = 35 + (index % 2) * 20 + 12
        if pixel(frame, WIDTH, moving_x, moving_y)[3] != 255:
            raise ValueError(f"frame {index} lacks specified moving opaque square")

    with tempfile.TemporaryDirectory(prefix="gramlab-custom-emoji-") as temporary:
        generated_animation = Path(temporary) / "generated.webm"
        generated_animation.write_bytes(generated["emoji-animated.webm"])
        decoded_generated = decode_rgba(args.ffmpeg, generated_animation, "libvpx-vp9")
        if decoded_generated != animation:
            raise ValueError("repeated WebM encode has different decoded pixels")

    probe = command([
        args.ffprobe, "-v", "error", "-count_frames", "-select_streams", "v:0",
        "-show_entries", "stream=codec_name,width,height,nb_read_frames,r_frame_rate:stream_tags=alpha_mode",
        "-show_entries", "format=format_name:packet=pts_time,duration_time", "-show_packets", "-of", "json",
        str(directory / "emoji-animated.webm"),
    ])
    metadata = json.loads(probe.stdout)
    stream = metadata["streams"][0]
    if (stream["codec_name"], stream["width"], stream["height"], stream["nb_read_frames"]) != (
        "vp9", WIDTH, HEIGHT, str(FRAMES)
    ):
        raise ValueError(f"unexpected WebM stream metadata: {stream}")
    if stream.get("tags", {}).get("alpha_mode") != "1":
        raise ValueError("WebM stream does not declare alpha mode")
    if stream["r_frame_rate"] != "4/1" or abs(
        sum(float(packet["duration_time"]) for packet in metadata["packets"]) - 1.0
    ) > 0.001:
        raise ValueError("unexpected WebM frame timing")

    command([args.ffprobe, "-v", "error", str(directory / "emoji-truncated-invalid.webm")], ok=False)
    command([args.ffmpeg, "-v", "error", "-i", str(directory / "emoji-truncated-invalid.webm"),
             "-f", "null", "-"], ok=False)
    print(json.dumps({"decoded_frames": FRAMES, "alpha": True, "changing_frames": FRAMES,
                      "static_webp": [100, 100], "thumbnail_webp": [16, 16]}, sort_keys=True))


if __name__ == "__main__":
    main()
