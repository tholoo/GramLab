"""Retain one original guest screenshot burst without per-frame host transfers."""

from __future__ import annotations

import hashlib
import re
import shlex
import stat
import subprocess
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

COUNT = 24
MAX_FRAME_BYTES = 4 * 1024 * 1024
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
printf 'GRAMLAB_SCREENSHOT_BURST 1 {token} {COUNT}\\n'
i=0
while [ "$i" -lt {COUNT} ]; do
    frame={shlex.quote(directory)}/edited-burst-$(printf '%02d' "$i").png
    read -r start ignored < /proc/uptime
    screencap -p "$frame"
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
        or lines[0] != f"GRAMLAB_SCREENSHOT_BURST 1 {token} {COUNT}"
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
        # Framing admits slow captures so their original PNGs survive a timing red.
        if end <= start or end - start > 60_000_000_000 or size > MAX_FRAME_BYTES:
            raise ValueError("Unbounded screenshot burst record")
        if frames and frames[-1].end_ns > start:
            raise ValueError("Screenshot burst acquisition bounds overlap or regress")
        frames.append(Frame(f"edited-burst-{index:02d}.png", start, end, size, match[5]))
    return frames


def validate_transfer(directory: Path, frames: list[Frame]) -> None:
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError("Screenshot burst transfer is not a directory")
    if {path.name for path in directory.iterdir()} != {frame.name for frame in frames}:
        raise ValueError("Screenshot burst transfer has missing or unexpected files")
    for frame in frames:
        path = directory / frame.name
        status = path.lstat()
        if not stat.S_ISREG(status.st_mode) or status.st_size != frame.size:
            raise ValueError("Screenshot burst transfer has an invalid file")
        with path.open("rb") as stream:
            value = stream.read(MAX_FRAME_BYTES + 1)
        if (
            len(value) != frame.size
            or not value.startswith(b"\x89PNG\r\n\x1a\n")
            or hashlib.sha256(value).hexdigest() != frame.sha256
        ):
            raise ValueError("Screenshot burst transfer changed original PNG bytes")


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
    validate_transfer(local, frames)
    if any(
        (output / frame.name).exists() or (output / frame.name).is_symlink() for frame in frames
    ):
        raise ValueError("Screenshot burst output path already exists")
    published: list[Path] = []
    try:
        for frame in frames:
            # Keep transferred originals, and never overwrite a prior capture.
            destination = output / frame.name
            destination.hardlink_to(local / frame.name)
            published.append(destination)
    except BaseException:
        for destination in published:
            destination.unlink()
        raise
    return [frame.start_ns for frame in frames], [frame.end_ns for frame in frames]
