"""Real shell framing and explicit external screenshot-transfer boundary controls.

Authored PNG fixtures substitute screencap output; these are not native animation evidence.
"""

from __future__ import annotations

import hashlib
import os
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
from custom_emoji_visual import capture_intervals
from probes.guest_screenshot_burst import capture_burst, capture_command, parse_manifest

TOKEN = "0123456789abcdef0123456789abcdef"  # noqa: S105 - public test correlation nonce
PNG = Path("tests/assets/rich-media/photo-square-16x16.png")


def manifest(token: str = TOKEN) -> str:
    value = PNG.read_bytes()
    digest = hashlib.sha256(value).hexdigest()
    lines = [f"GRAMLAB_SCREENSHOT_BURST 1 {token} 24"]
    for index in range(24):
        tick = 12345 + index * 20
        start = f"{tick // 100}.{tick % 100:02d}"
        end = f"{(tick + 7) // 100}.{(tick + 7) % 100:02d}"
        lines.append(f"FRAME {index:02d} {start} {end} {len(value)} {digest}")
    return "\n".join([*lines, "END 24", ""])


def test_guest_centiseconds_bound_acquisition_without_host_clock_or_transfer_time() -> None:
    frames = parse_manifest(manifest(), TOKEN)
    assert len(frames) == 24
    assert frames[0].start_ns == 123_450_000_000
    assert frames[0].end_ns == 123_530_000_000
    assert frames[-1].start_ns == 128_050_000_000
    assert frames[-1].end_ns == 128_130_000_000
    assert [frame.name for frame in frames] == [f"edited-burst-{i:02d}.png" for i in range(24)]
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
    # Only the external screencap command is substituted with an authored PNG copy.
    # Real sh, /proc/uptime, sleep, wc and sha256sum execute the production loop.
    capture = commands / "screencap"
    capture.write_text(
        "#!/bin/sh\nset -eu\n"
        'case "$2" in *-03.png)\n'
        + ({"command": "exit 7\n", "missing": "exit 0\n"}.get(failure or "", ":\n"))
        + ';; esac\ncp "$BURST_FIXTURE" "$2"\n'
    )
    capture.chmod(0o755)
    toybox = commands / "toybox"
    toybox.write_text('#!/bin/sh\nexec "$@"\n')
    toybox.chmod(0o755)
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
            "BURST_FIXTURE": str(PNG.resolve()),
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
        assert all((directory / frame.name).read_bytes() == PNG.read_bytes() for frame in frames)
        assert all(frame.end_ns > frame.start_ns for frame in frames)
        # Twenty-three inter-frame sleeps alone account for at least 1.84 seconds.
        assert frames[-1].start_ns - frames[0].start_ns >= 1_830_000_000


class TransferredGuest:
    """Independently supplied records/PNG files at the external guest boundary."""

    def __init__(self, fault: str | None = None) -> None:
        self.fault = fault
        self.calls: list[tuple[str, ...]] = []

    def __call__(self, *arguments: str, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        self.calls.append(arguments)
        assert kwargs == {"timeout": 60}
        if arguments[0] == "shell":
            # The command is quoted once for ADB, whose remote shell invokes sh -c.
            script = shlex.split(arguments[-1])[0]
            prefix = "printf 'GRAMLAB_SCREENSHOT_BURST 1 "
            token = script.split(prefix)[1].split(" ")[0]
            return subprocess.CompletedProcess(
                arguments, 9 if self.fault == "capture" else 0, manifest(token), ""
            )
        assert arguments[0] == "pull" and len(arguments) == 3
        directory = Path(arguments[2])
        directory.mkdir()
        for index in range(24):
            shutil.copyfile(PNG, directory / f"edited-burst-{index:02d}.png")
        first = directory / "edited-burst-00.png"
        if self.fault == "missing":
            first.unlink()
        elif self.fault == "extra":
            (directory / "extra.png").write_bytes(PNG.read_bytes())
        elif self.fault == "symlink":
            first.unlink()
            first.symlink_to(PNG.resolve())
        elif self.fault == "changed":
            data = bytearray(first.read_bytes())
            data[-1] ^= 1
            first.write_bytes(data)
        return subprocess.CompletedProcess(arguments, 1 if self.fault == "pull" else 0, "", "")


def test_one_guest_capture_session_then_one_transfer_retains_original_bytes(tmp_path: Path) -> None:
    guest = TransferredGuest()
    starts, ends = capture_burst(guest, tmp_path)
    assert starts == [123_450_000_000 + index * 200_000_000 for index in range(24)]
    assert ends == [123_530_000_000 + index * 200_000_000 for index in range(24)]
    assert [command[0] for command in guest.calls] == ["shell", "pull"]
    assert len(list(tmp_path.glob("edited-burst-*.png"))) == 24
    assert all(path.read_bytes() == PNG.read_bytes() for path in tmp_path.glob("*.png"))
    assert (tmp_path / "edited-burst-manifest.txt").is_file()
    assert (tmp_path / "edited-burst-stderr.txt").read_text() == ""


@pytest.mark.parametrize("fault", ["capture", "pull", "missing", "extra", "symlink", "changed"])
def test_failed_capture_or_transfer_never_publishes_a_successful_subset(
    tmp_path: Path, fault: str
) -> None:
    guest = TransferredGuest(fault)
    with pytest.raises((ValueError, RuntimeError)):
        capture_burst(guest, tmp_path)
    assert not list(tmp_path.glob("edited-burst-*.png"))
    assert len(guest.calls) == (1 if fault == "capture" else 2)
    assert (tmp_path / "edited-burst-manifest.txt").is_file()


def test_capture_does_not_overwrite_an_existing_original_frame(tmp_path: Path) -> None:
    existing = tmp_path / "edited-burst-13.png"
    existing.write_bytes(b"retained prior evidence")
    with pytest.raises(ValueError, match="already exists"):
        capture_burst(TransferredGuest(), tmp_path)
    assert existing.read_bytes() == b"retained prior evidence"
    assert len(list(tmp_path.glob("edited-burst-*.png"))) == 1


def test_publication_failure_removes_only_its_new_links_and_keeps_transferred_originals(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    actual = Path.hardlink_to

    def interrupted(path: Path, target: str | Path) -> None:
        if path.name == "edited-burst-13.png":
            raise OSError("injected link failure")
        actual(path, target)

    monkeypatch.setattr(Path, "hardlink_to", interrupted)
    with pytest.raises(OSError, match="injected link failure"):
        capture_burst(TransferredGuest(), tmp_path)
    assert not list(tmp_path.glob("edited-burst-*.png"))
    staged = list(tmp_path.glob("custom-emoji-burst-*"))
    assert len(staged) == 1
    assert len(list(staged[0].glob("*.png"))) == 24
    assert all(path.read_bytes() == PNG.read_bytes() for path in staged[0].glob("*.png"))
