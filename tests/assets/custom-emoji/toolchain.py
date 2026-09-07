"""Validate the optional pinned media-toolchain profile."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MediaToolchain:
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


def load_media_toolchain() -> MediaToolchain | None:
    profile_path = os.environ.get("GRAMLAB_MEDIA_TOOLCHAIN")
    if not profile_path:
        return None
    value = json.loads(Path(profile_path).read_text())
    if not isinstance(value, dict) or value.get("schema") != 1:
        raise ValueError("GRAMLAB_MEDIA_TOOLCHAIN must use schema 1")
    if set(value) != {"schema", "nixpkgs_revision", "package", "versions", "executables"}:
        raise ValueError("GRAMLAB_MEDIA_TOOLCHAIN has unexpected fields")
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


def select_executable(name: str, override: str | None, toolchain: MediaToolchain | None) -> str:
    selected = override or (toolchain.executables[name] if toolchain else name)
    located = shutil.which(selected)
    if located is None:
        raise ValueError(f"selected {name} executable was not found: {selected}")
    resolved = Path(located).resolve(strict=True)
    if toolchain is not None:
        expected = Path(toolchain.executables[name]).resolve(strict=True)
        if resolved != expected:
            raise ValueError(f"selected {name} does not match GRAMLAB_MEDIA_TOOLCHAIN: {resolved}")
        version_line = subprocess.run(  # noqa: S603
            [str(resolved), "-version"], capture_output=True, text=True, check=True
        ).stdout.splitlines()[0]
        expected_version = toolchain.versions["ffmpeg"]
        version_parts = version_line.split()
        if (
            len(version_parts) < 3
            or version_parts[:2] != [name, "version"]
            or version_parts[2] != expected_version
        ):
            raise ValueError(f"selected {name} version does not match GRAMLAB_MEDIA_TOOLCHAIN")
    return str(resolved)
