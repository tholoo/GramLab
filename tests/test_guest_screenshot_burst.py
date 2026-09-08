"""Real shell framing and explicit external screenshot-transfer boundary controls.

Authored raw RGBA fixtures substitute screencap output; these are not native animation evidence.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import shlex
import struct
import subprocess
from pathlib import Path
from typing import Any

import pytest
from custom_emoji_visual import capture_intervals
from PIL import Image
from probes.guest_screenshot_burst import (
    capture_burst,
    capture_command,
    encode_png,
    parse_manifest,
    raw_pixels,
)

TOKEN = "0123456789abcdef0123456789abcdef"  # noqa: S105 - public test correlation nonce
# Independent row/column/channel pattern exposes flips, channel swaps and rescaling.
PIXELS = bytes(
    component
    for y in range(640)
    for x in range(320)
    for component in (x % 256, y % 256, (x * 17 + y * 31) % 256, 255)
)
RAW = struct.pack("<4I", 320, 640, 1, 1) + PIXELS


def authored_frame(index: int, value: bytes = RAW) -> bytes:
    # Each sample has a unique opaque first pixel; the remaining spatial pattern persists.
    return value[:16] + bytes((index, 255 - index, index * 7, 255)) + value[20:]


def manifest(token: str = TOKEN, value: bytes = RAW) -> str:
    lines = [f"GRAMLAB_SCREENSHOT_BURST 2 RAW_RGBA_8888_SRGB {token} 24"]
    for index in range(24):
        raw = authored_frame(index, value)
        digest = hashlib.sha256(raw).hexdigest()
        tick = 12345 + index * 20
        start = f"{tick // 100}.{tick % 100:02d}"
        end = f"{(tick + 7) // 100}.{(tick + 7) % 100:02d}"
        lines.append(f"FRAME {index:02d} {start} {end} {len(raw)} {digest}")
    return "\n".join([*lines, "END 24", ""])


def test_guest_centiseconds_bound_acquisition_without_host_clock_or_transfer_time() -> None:
    frames = parse_manifest(manifest(), TOKEN)
    assert len(frames) == 24
    assert frames[0].start_ns == 123_450_000_000
    assert frames[0].end_ns == 123_530_000_000
    assert frames[-1].start_ns == 128_050_000_000
    assert frames[-1].end_ns == 128_130_000_000
    assert [frame.name for frame in frames] == [f"edited-burst-{i:02d}.raw" for i in range(24)]
    # Quantization can read the same centisecond before/after a short acquisition.
    short = manifest().replace("123.52", "123.45")
    assert parse_manifest(short, TOKEN)[0].end_ns == 123_460_000_000


@pytest.mark.parametrize(
    "change",
    [
        lambda text: text.replace(TOKEN, "f" * 32),
        lambda text: text.replace("END 24\n", ""),
        lambda text: text + "unframed output\n",
        lambda text: text.replace("FRAME 01", "FRAME 00"),
        lambda text: text.replace("FRAME 01", "FRAME 02"),
        lambda text: text.replace("123.45", "123.450"),
        lambda text: text.replace("123.45", "-123.45"),
        lambda text: text.replace("123.52", "123.43"),
        lambda text: text.replace("123.65", "123.52"),
        lambda text: text.replace("\n", "\r\n"),
        lambda text: text.replace("FRAME 00 ", "FRAME 00 0 "),
        lambda text: text + "x" * 8192,
    ],
)
def test_reject_malformed_incomplete_unrelated_and_nonmonotonic_records(change: Any) -> None:
    with pytest.raises(ValueError):
        parse_manifest(change(manifest()), TOKEN)


def test_slow_actual_capture_is_retained_for_the_unchanged_strict_timing_oracle() -> None:
    frames = parse_manifest(manifest().replace("128.12", "128.55"), TOKEN)
    assert frames[-1].end_ns - frames[-1].start_ns == 510_000_000
    with pytest.raises(ValueError, match="shorter than half"):
        capture_intervals([frame.start_ns for frame in frames], [frame.end_ns for frame in frames])


@pytest.mark.parametrize("failure", [None, "command", "missing"])
def test_actual_posix_shell_quotes_paths_and_requires_every_successful_file(
    tmp_path: Path, failure: str | None
) -> None:
    commands = tmp_path / "commands"
    commands.mkdir()
    # Only the external screencap command is substituted with an authored raw copy.
    # Real sh, /proc/uptime, sleep, wc and sha256sum execute the production loop.
    capture = commands / "screencap"
    capture.write_text(
        "#!/bin/sh\nset -eu\n"
        '[ "$#" -eq 1 ]\ncase "$1" in *-03.raw)\n'
        + ({"command": "exit 7\n", "missing": "exit 0\n"}.get(failure or "", ":\n"))
        + ';; esac\ncp "$BURST_FIXTURE" "$1"\n'
    )
    capture.chmod(0o755)
    toybox = commands / "toybox"
    toybox.write_text('#!/bin/sh\nexec "$@"\n')
    toybox.chmod(0o755)
    fixture = tmp_path / "fixture.raw"
    fixture.write_bytes(RAW)
    directory = tmp_path / "guest ' quoted; $(touch SHOULD_NOT_EXIST)"
    command = capture_command(str(directory), TOKEN)
    assert command[:4] == ("shell", "-T", "sh", "-c")
    result = subprocess.run(  # noqa: S603
        ["sh", "-c", " ".join(command[2:])],  # noqa: S607
        capture_output=True,
        text=True,
        timeout=15,
        cwd=tmp_path,
        env=os.environ
        | {
            "PATH": str(commands) + os.pathsep + os.environ["PATH"],
            "BURST_FIXTURE": str(fixture),
        },
    )
    assert not (tmp_path / "SHOULD_NOT_EXIST").exists()
    if failure:
        assert result.returncode != 0
        with pytest.raises(ValueError, match="Incomplete"):
            parse_manifest(result.stdout, TOKEN)
        assert len(list(directory.iterdir())) == 3
    else:
        assert result.returncode == 0, result.stderr
        frames = parse_manifest(result.stdout, TOKEN)
        assert len(frames) == 24
        assert all((directory / frame.name).read_bytes() == RAW for frame in frames)
        assert all(frame.end_ns > frame.start_ns for frame in frames)
        # Twenty-three inter-frame sleeps alone account for at least 1.84 seconds.
        assert frames[-1].start_ns - frames[0].start_ns >= 1_830_000_000


class TransferredGuest:
    """Independently supplied records/raw files at the external guest boundary."""

    def __init__(self, fault: str | None = None, value: bytes = RAW) -> None:
        self.fault = fault
        self.value = value
        self.calls: list[tuple[str, ...]] = []

    def __call__(self, *arguments: str, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        self.calls.append(arguments)
        assert kwargs == {"timeout": 60}
        if arguments[0] == "shell":
            # The command is quoted once for ADB, whose remote shell invokes sh -c.
            script = shlex.split(arguments[-1])[0]
            prefix = "printf 'GRAMLAB_SCREENSHOT_BURST 2 RAW_RGBA_8888_SRGB "
            token = script.split(prefix)[1].split(" ")[0]
            return subprocess.CompletedProcess(
                arguments, 9 if self.fault == "capture" else 0, manifest(token, self.value), ""
            )
        assert arguments[0] == "pull" and len(arguments) == 3
        directory = Path(arguments[2])
        directory.mkdir()
        for index in range(24):
            (directory / f"edited-burst-{index:02d}.raw").write_bytes(
                authored_frame(index, self.value)
            )
        first = directory / "edited-burst-00.raw"
        if self.fault == "missing":
            first.unlink()
        elif self.fault == "extra":
            (directory / "extra.raw").write_bytes(RAW)
        elif self.fault == "symlink":
            fixture = directory.parent / "external-fixture.raw"
            first.rename(fixture)
            first.symlink_to(fixture)
        elif self.fault == "permuted":
            last = directory / "edited-burst-23.raw"
            first_bytes, last_bytes = first.read_bytes(), last.read_bytes()
            first.write_bytes(last_bytes)
            last.write_bytes(first_bytes)
        elif self.fault == "changed":
            data = bytearray(first.read_bytes())
            data[-4] ^= 1
            first.write_bytes(data)
        return subprocess.CompletedProcess(arguments, 1 if self.fault == "pull" else 0, "", "")


def test_one_guest_capture_session_then_one_transfer_retains_original_bytes(tmp_path: Path) -> None:
    guest = TransferredGuest()
    starts, ends = capture_burst(guest, tmp_path)
    assert starts == [123_450_000_000 + index * 200_000_000 for index in range(24)]
    assert ends == [123_530_000_000 + index * 200_000_000 for index in range(24)]
    assert [command[0] for command in guest.calls] == ["shell", "pull"]
    assert len(list(tmp_path.glob("edited-burst-*.png"))) == 24
    metadata = json.loads((tmp_path / "edited-burst-derivation.json").read_text())
    assert metadata["input_format"] == "android-screencap-raw"
    assert metadata["derivation"] == "lossless-png-rgba8"
    assert len(metadata["frames"]) == 24
    assert len({frame["raw_sha256"] for frame in metadata["frames"]}) == 24
    assert len({(tmp_path / frame["raw_path"]).stat().st_ino for frame in metadata["frames"]}) == 24
    manifest_bytes = (tmp_path / "edited-burst-manifest.txt").read_bytes()
    assert metadata["manifest_sha256"] == hashlib.sha256(manifest_bytes).hexdigest()
    records = manifest_bytes.decode().splitlines()[1:-1]
    for index, frame in enumerate(metadata["frames"]):
        raw = tmp_path / frame["raw_path"]
        png = tmp_path / frame["png_path"]
        assert raw.name == f"edited-burst-{index:02d}.raw"
        expected = authored_frame(index)
        assert raw.read_bytes() == expected
        assert png.name == f"edited-burst-{index:02d}.png"
        assert frame["raw_size"] == len(expected)
        assert frame["raw_sha256"] == hashlib.sha256(expected).hexdigest()
        assert frame["png_size"] == png.stat().st_size
        assert frame["png_sha256"] == hashlib.sha256(png.read_bytes()).hexdigest()
        assert frame["rgba_sha256"] == hashlib.sha256(expected[16:]).hexdigest()
        assert frame["start_ns"] == starts[index] == 123_450_000_000 + index * 200_000_000
        assert frame["end_ns"] == ends[index] == 123_530_000_000 + index * 200_000_000
        record = records[index].split()
        assert record[:2] == ["FRAME", f"{index:02d}"]
        assert record[4:] == [str(len(expected)), hashlib.sha256(expected).hexdigest()]
        with Image.open(png) as decoded:
            assert decoded.mode == "RGBA" and decoded.size == (320, 640)
            assert decoded.tobytes() == expected[16:]
    assert (tmp_path / "edited-burst-manifest.txt").is_file()
    assert (tmp_path / "edited-burst-stderr.txt").read_text() == ""


@pytest.mark.parametrize(
    "fault", ["capture", "pull", "missing", "extra", "symlink", "changed", "permuted"]
)
def test_failed_capture_or_transfer_never_publishes_a_successful_subset(
    tmp_path: Path, fault: str
) -> None:
    guest = TransferredGuest(fault)
    with pytest.raises((ValueError, RuntimeError)):
        capture_burst(guest, tmp_path)
    assert not list(tmp_path.glob("edited-burst-*.png"))
    assert len(guest.calls) == (1 if fault == "capture" else 2)
    if fault == "changed":
        staged = sorted(tmp_path.glob("custom-emoji-burst-*/*.raw"))
        assert len(staged) == 24
        assert staged[0].read_bytes() != authored_frame(0)
        for index, path in enumerate(staged[1:], 1):
            assert path.read_bytes() == authored_frame(index)
    assert (tmp_path / "edited-burst-manifest.txt").is_file()


def test_capture_does_not_overwrite_an_existing_original_frame(tmp_path: Path) -> None:
    existing = tmp_path / "edited-burst-13.png"
    existing.write_bytes(b"retained prior evidence")
    with pytest.raises(ValueError, match="already exists"):
        capture_burst(TransferredGuest(), tmp_path)
    assert existing.read_bytes() == b"retained prior evidence"
    assert len(list(tmp_path.glob("edited-burst-*.png"))) == 1


@pytest.mark.parametrize("failed_name", ["edited-burst-13.png", "edited-burst-derivation.json"])
def test_publication_failure_removes_only_its_new_links_and_keeps_transferred_originals(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failed_name: str
) -> None:
    actual = Path.hardlink_to

    def interrupted(path: Path, target: str | Path) -> None:
        if path.name == failed_name:
            raise OSError("injected link failure")
        actual(path, target)

    monkeypatch.setattr(Path, "hardlink_to", interrupted)
    with pytest.raises(OSError, match="injected link failure"):
        capture_burst(TransferredGuest(), tmp_path)
    assert not list(tmp_path.glob("edited-burst-*.png"))
    assert not (tmp_path / "edited-burst-derivation.json").exists()
    staged = list(tmp_path.glob("custom-emoji-burst-*"))
    assert len(staged) == 1
    assert len(list(staged[0].glob("*.raw"))) == 24
    for index in range(24):
        assert (staged[0] / f"edited-burst-{index:02d}.raw").read_bytes() == authored_frame(index)


def test_lossless_png_preserves_every_independently_authored_pixel() -> None:
    # A separate decoder verifies all coordinates/channels, not encoder byte structure.
    pixels = raw_pixels(RAW)
    assert pixels == PIXELS and len(RAW) == 819216
    png = encode_png(pixels)
    with Image.open(io.BytesIO(png)) as decoded:
        assert decoded.size == (320, 640) and decoded.mode == "RGBA"
        assert decoded.info["srgb"] == 0
        assert decoded.tobytes() == PIXELS


@pytest.mark.parametrize(
    "value",
    [
        b"",
        RAW[:15],
        struct.pack(">4I", 320, 640, 1, 1) + PIXELS,
        struct.pack("<4I", 640, 320, 1, 1) + PIXELS,
        struct.pack("<4I", 0, 640, 1, 1) + PIXELS,
        struct.pack("<4I", 0xFFFFFFFF, 640, 1, 1) + PIXELS,
        struct.pack("<4I", 320, 640, 5, 1) + PIXELS,  # BGRA
        struct.pack("<4I", 320, 640, 2, 1) + PIXELS,  # RGBX
        struct.pack("<4I", 320, 640, 1, 0) + PIXELS,  # Unknown colorspace
        struct.pack("<4I", 320, 640, 1, 2) + PIXELS,  # Display P3
        RAW[:-1],
        RAW + b"\x00",
        RAW + b"\x00" * 640 * 4,  # Unexpected row padding
        RAW[:19] + b"\x80" + RAW[20:],  # Unverified premultiplied alpha
    ],
    ids=[
        "empty",
        "short-header",
        "endianness",
        "swapped-dimensions",
        "zero-dimension",
        "huge-dimension",
        "bgra",
        "rgbx",
        "unknown-color",
        "p3",
        "short-payload",
        "trailing-byte",
        "stride-padding",
        "nonopaque",
    ],
)
def test_raw_parser_rejects_unverified_layouts_and_boundary_lengths(value: bytes) -> None:
    with pytest.raises(ValueError, match="Unsupported"):
        raw_pixels(value)


@pytest.mark.parametrize("size", [819215, 819217])
def test_manifest_rejects_nonprofile_frame_size_before_transfer(size: int) -> None:
    with pytest.raises(ValueError, match="Unbounded"):
        parse_manifest(manifest().replace("819216", str(size)), TOKEN)


def test_digest_matching_but_unsupported_raw_pixels_never_publish(tmp_path: Path) -> None:
    bad = struct.pack("<4I", 320, 640, 5, 1) + PIXELS
    with pytest.raises(ValueError, match="Unsupported"):
        capture_burst(TransferredGuest(value=bad), tmp_path)
    assert not list(tmp_path.glob("edited-burst-*.png"))
    assert not (tmp_path / "edited-burst-derivation.json").exists()
    staged = list(tmp_path.glob("custom-emoji-burst-*/*.raw"))
    assert len(staged) == 24
    for index, path in enumerate(sorted(staged)):
        assert path.read_bytes() == authored_frame(index, bad)


def test_existing_derivation_metadata_is_preserved(tmp_path: Path) -> None:
    path = tmp_path / "edited-burst-derivation.json"
    path.write_text("prior evidence")
    with pytest.raises(ValueError, match="already exists"):
        capture_burst(TransferredGuest(), tmp_path)
    assert path.read_text() == "prior evidence"
    assert not list(tmp_path.glob("edited-burst-*.png"))
