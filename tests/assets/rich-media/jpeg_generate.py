#!/usr/bin/env python3
"""Generate GramLab's deterministic, original JPEG photo fixtures."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

WIDTH = 64
HEIGHT = 48
VALID_FIXTURE = "photo-quadrants-64x48.jpg"
INVALID_FIXTURE = "photo-quadrants-truncated-invalid.jpg"
MANIFEST = "jpeg-manifest.json"
COLORS = (
    (224, 48, 48),
    (48, 192, 64),
    (48, 80, 224),
    (224, 192, 48),
)


@dataclass(frozen=True)
class MediaToolchain:
    """Validated fields from the generated media-toolchain profile."""

    nixpkgs_revision: str
    package: str
    versions: dict[str, str]
    executables: dict[str, str]

    def portable_profile(self) -> dict[str, object]:
        return {
            "schema": 1,
            "nixpkgs_revision": self.nixpkgs_revision,
            "package": self.package,
            "versions": self.versions,
        }


def load_media_toolchain() -> MediaToolchain:
    """Load the required pinned media-toolchain profile."""
    profile_path = os.environ.get("GRAMLAB_MEDIA_TOOLCHAIN")
    if not profile_path:
        raise ValueError("GRAMLAB_MEDIA_TOOLCHAIN is required")
    value = json.loads(Path(profile_path).read_text())
    expected = {"schema", "nixpkgs_revision", "package", "versions", "executables"}
    if not isinstance(value, dict) or value.get("schema") != 1 or set(value) != expected:
        raise ValueError("GRAMLAB_MEDIA_TOOLCHAIN must use the expected schema 1 fields")
    versions = value["versions"]
    executables = value["executables"]
    if (
        not isinstance(value["nixpkgs_revision"], str)
        or not isinstance(value["package"], str)
        or not isinstance(versions, dict)
        or set(versions) != {"ffmpeg", "libvpx", "libwebp"}
        or not all(isinstance(item, str) for item in versions.values())
        or not isinstance(executables, dict)
        or set(executables) != {"ffmpeg", "ffprobe"}
        or not all(isinstance(item, str) for item in executables.values())
    ):
        raise ValueError("GRAMLAB_MEDIA_TOOLCHAIN has invalid fields")
    return MediaToolchain(
        nixpkgs_revision=value["nixpkgs_revision"],
        package=value["package"],
        versions=versions,
        executables=executables,
    )


def select_executable(name: str, toolchain: MediaToolchain) -> str:
    """Select an executable only from the active pinned profile."""
    selected = toolchain.executables[name]
    located = shutil.which(selected)
    if located is None:
        raise ValueError(f"profile-selected {name} executable was not found")
    resolved = Path(located).resolve(strict=True)
    expected = Path(selected).resolve(strict=True)
    if resolved != expected:
        raise ValueError(f"selected {name} does not match GRAMLAB_MEDIA_TOOLCHAIN")
    version_line = subprocess.run(  # noqa: S603
        [str(resolved), "-version"], capture_output=True, text=True, check=True
    ).stdout.splitlines()[0]
    if version_line.split()[:3] != [name, "version", toolchain.versions["ffmpeg"]]:
        raise ValueError(f"selected {name} version does not match GRAMLAB_MEDIA_TOOLCHAIN")
    return str(resolved)


def source_rgb() -> bytes:
    """Return the specified opaque four-quadrant RGB source image."""
    pixels = bytearray()
    for y in range(HEIGHT):
        for x in range(WIDTH):
            quadrant = (2 if y >= HEIGHT // 2 else 0) + (1 if x >= WIDTH // 2 else 0)
            pixels.extend(COLORS[quadrant])
    return bytes(pixels)


def encoder_arguments(ffmpeg: str) -> list[str]:
    """Return the complete pinned MJPEG encoder invocation."""
    return [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-s",
        f"{WIDTH}x{HEIGHT}",
        "-r",
        "1",
        "-i",
        "pipe:0",
        "-frames:v",
        "1",
        "-an",
        "-c:v",
        "mjpeg",
        "-pix_fmt",
        "yuvj444p",
        "-color_range",
        "pc",
        "-q:v",
        "2",
        "-threads",
        "1",
        "-fflags",
        "+bitexact",
        "-flags:v",
        "+bitexact",
        "-f",
        "image2pipe",
        "pipe:1",
    ]


def encode_jpeg(ffmpeg: str) -> bytes:
    """Encode the source pixels as one deterministic JPEG image."""
    result = subprocess.run(  # noqa: S603
        encoder_arguments(ffmpeg), input=source_rgb(), capture_output=True, check=False
    )
    if result.returncode:
        raise RuntimeError(result.stderr.decode(errors="replace"))
    return result.stdout


def generated_files(ffmpeg: str, toolchain: MediaToolchain) -> dict[str, bytes]:
    """Return both JPEG fixtures and their portable manifest."""
    valid = encode_jpeg(ffmpeg)
    files = {VALID_FIXTURE: valid, INVALID_FIXTURE: valid[:32]}
    command = encoder_arguments("ffmpeg")
    records: list[dict[str, object]] = []
    for filename in sorted(files):
        record: dict[str, object] = {
            "filename": filename,
            "mime": "image/jpeg",
            "sha256": hashlib.sha256(files[filename]).hexdigest(),
            "valid": filename == VALID_FIXTURE,
            "provenance": {"license": "MIT", "source": "original GramLab generator"},
        }
        if filename == VALID_FIXTURE:
            record.update(width=WIDTH, height=HEIGHT, format="mjpeg", alpha=False)
        records.append(record)
    manifest = {
        "generator_profile": {
            "toolchain": toolchain.portable_profile(),
            "encoder_arguments": command,
            "reproducibility": (
                "byte-identical under this recorded encoder profile; other versions may differ"
            ),
        },
        "fixtures": records,
    }
    files[MANIFEST] = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
    return files


def write_exact(directory: Path, files: dict[str, bytes]) -> None:
    """Write only missing or byte-identical regular files in a safe directory."""
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError("output directory must be an existing, non-symlink directory")
    for name, contents in files.items():
        destination = directory / name
        if destination.exists() or destination.is_symlink():
            if destination.is_symlink() or not destination.is_file():
                raise ValueError(f"refusing non-regular destination: {destination}")
            if destination.read_bytes() != contents:
                raise ValueError(f"refusing to overwrite differing file: {destination}")
            continue
        destination.write_bytes(contents)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_directory", type=Path)
    arguments = parser.parse_args()
    toolchain = load_media_toolchain()
    ffmpeg = select_executable("ffmpeg", toolchain)
    write_exact(arguments.output_directory, generated_files(ffmpeg, toolchain))


if __name__ == "__main__":
    main()
