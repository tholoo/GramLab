"""Original Android custom-emoji lifecycle and immutable cache acceptance."""

import hashlib
import importlib
import json
import os
import re
import shutil
import struct
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pytest
from custom_emoji_visual import (
    capture_intervals,
    locate_animation,
    locate_animation_sequence,
    locate_static,
    require_complete_cycle,
    require_distinct_carriers,
)
from PIL import Image
from test_android_quoted_code import assert_isolation

from gramlab.reports import Report, Screenshot, write_report
from gramlab.runtime import RuntimeProfile, Sandbox

pytestmark = pytest.mark.android

STATIC = Path("tests/assets/custom-emoji/emoji-static.webp")
ANIMATED = Path("tests/assets/custom-emoji/emoji-animated.webm")
THUMBNAIL = Path("tests/assets/custom-emoji/emoji-thumbnail.webp")


def test_original_custom_emoji_edit_animation_and_cold_cache(tmp_path: Path) -> None:
    manifest = os.environ.get("GRAMLAB_ANDROID_RUNTIME_PROFILE")
    apk = os.environ.get("GRAMLAB_ANDROID_PROBE_APK")
    if manifest is None or apk is None or not os.access("/dev/kvm", os.R_OK | os.W_OK):
        pytest.skip("Requires the Android profile, reviewed custom emoji APK and accessible KVM")
    profile = RuntimeProfile.load(Path(manifest))
    core = RuntimeProfile.load(Path(os.environ["GRAMLAB_RUNTIME_PROFILE"]))
    helper = importlib.import_module("test_custom_emoji_round_trip")
    helper.stage_scenario(tmp_path, core)
    shutil.copy2(apk, tmp_path / "client.apk")
    (tmp_path / "emulator-profile.json").write_text(json.dumps(asdict(profile)))
    for name in (
        "emulator_process.py",
        "android_guest.py",
        "android_custom_emoji.py",
        "guest_screenshot_burst.py",
        "native_asset_proxy.py",
    ):
        shutil.copy2(Path("tests/probes") / name, tmp_path / name)
    toolchain = json.loads(Path("clients/android/toolchain.json").read_text())
    image = (
        f"system-images;android-{toolchain['sdk']['platform']};"
        f"{toolchain['runtime']['imageType']};{toolchain['runtime']['abi']}"
    )
    result = Sandbox(profile).supervise(
        [
            profile.python,
            "/work/android_custom_emoji.py",
            profile.executables["emulator"],
            profile.executables["adb"],
            profile.executables["avdmanager"],
            image,
        ],
        data=tmp_path,
        kvm=True,
        timeout=480,
    )
    (tmp_path / "custom-emoji-native-result.json").write_text(result.stdout)
    (tmp_path / "custom-emoji-native-stderr.log").write_text(result.stderr)
    assert result.returncode == 0, result.stderr
    full = json.loads(result.stdout)
    assert_isolation(full)
    helper.assert_scenario(full["extra_probe"])
    assert_native_lifecycle(tmp_path, full["extra_probe"], apk)


def assert_burst_derivation(directory: Path, starts: list[int], ends: list[int]) -> dict[str, Any]:
    """Independently decode every native PNG and compare it to retained original pixels."""
    metadata: dict[str, Any] = json.loads((directory / "edited-burst-derivation.json").read_text())
    assert metadata["schema"] == 1
    assert metadata["input_format"] == "android-screencap-raw"
    assert metadata["raw_header_le_uint32"] == [320, 640, 1, 1]
    assert metadata["opaque"] is True and metadata["derivation"] == "lossless-png-rgba8"
    assert metadata["manifest_path"] == "edited-burst-manifest.txt"
    assert (
        hashlib.sha256((directory / metadata["manifest_path"]).read_bytes()).hexdigest()
        == (metadata["manifest_sha256"])
    )
    frames = metadata["frames"]
    assert len(frames) == len(starts) == len(ends) == 24
    raw_directories = set()
    for index, (frame, start, end) in enumerate(zip(frames, starts, ends, strict=True)):
        assert re.fullmatch(
            rf"custom-emoji-burst-[a-f0-9]{{32}}/edited-burst-{index:02d}\.raw", frame["raw_path"]
        )
        assert frame["png_path"] == f"edited-burst-{index:02d}.png"
        raw_directories.add(Path(frame["raw_path"]).parent)
        raw = (directory / frame["raw_path"]).read_bytes()
        assert len(raw) == frame["raw_size"] == 16 + 320 * 640 * 4
        assert struct.unpack("<4I", raw[:16]) == (320, 640, 1, 1)
        assert hashlib.sha256(raw).hexdigest() == frame["raw_sha256"]
        rgba = raw[16:]
        assert rgba[3::4] == bytes([255]) * (320 * 640)
        assert hashlib.sha256(rgba).hexdigest() == frame["rgba_sha256"]
        png = (directory / frame["png_path"]).read_bytes()
        assert len(png) == frame["png_size"]
        assert hashlib.sha256(png).hexdigest() == frame["png_sha256"]
        with Image.open(directory / frame["png_path"]) as image:
            assert image.format == "PNG" and image.mode == "RGBA" and image.size == (320, 640)
            assert image.tobytes() == rgba
        assert (frame["start_ns"], frame["end_ns"]) == (start, end)
    assert len(raw_directories) == 1
    return metadata


def assert_native_lifecycle(tmp_path: Path, observed: dict[str, Any], apk: str) -> None:
    client = observed["client"]["observed"]
    assert set(client["captures"]) == {"initial", "edited", "restarted"}
    for phase in client["captures"]:
        assert (tmp_path / f"{phase}.xml").read_text() == client["captures"][phase]
        assert (tmp_path / f"{phase}.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert set(client["launches"]) == {"initial", "animation-enabled", "restarted"}
    assert all(
        "Status: ok" in value and "LaunchState: COLD" in value
        for value in client["launches"].values()
    )
    assert client["taps"] == {
        "initial": {
            "label": "Animate / متحرک",
            "bounds": client["taps"]["initial"]["bounds"],
        }
    }
    assert "Accounts: 0" in client["accounts"]
    profile = client["animation_profile"]
    assert profile["checked"] == {"Autoplay in keyboard": "true", "Autoplay in chat": "true"}
    assert int(profile["after"]["lite_mode6"]["value"]) & (16384 | 4096) == 16384 | 4096
    assert "level:" in profile["battery"]
    requests = client["native_requests"]
    assert all(row["status"] == 200 and row["error"] is None for row in requests)
    assert not any(row["asset_id"] == 1 for row in requests)
    phases = Counter((row["phase"], row["asset_id"]) for row in requests)
    assert phases[("initial", 2)] >= 1
    assert phases[("edited", 3)] >= 1
    assert not any(row["phase"] == "restarted" for row in requests)
    documents = client["document_requests"]
    assert any(row["phase"] == "initial" and "1" in row["custom_emoji_ids"] for row in documents)
    assert any(row["phase"] == "edited" and "1109" in row["custom_emoji_ids"] for row in documents)
    assert all(row["status"] == 200 and row["error"] is None for row in documents)
    with Image.open(tmp_path / "initial.png") as opened:
        initial = opened.convert("RGB")
    initial_boxes = client["carrier_bounds"]["initial"]
    required_carriers = {"incoming", "ordinary", "rich", "button"}
    for phase in ("initial", "edited", "restarted"):
        require_distinct_carriers(
            {name: tuple(box) for name, box in client["carrier_bounds"][phase].items()},
            required_carriers,
        )
    assert all(locate_static(initial, tuple(raw_box)) for raw_box in initial_boxes.values())
    burst = []
    timestamps = client["burst_timestamps_ns"]
    assert len(timestamps) == 24
    derivation = assert_burst_derivation(tmp_path, timestamps, client["burst_end_timestamps_ns"])
    intervals = capture_intervals(timestamps, client["burst_end_timestamps_ns"])
    for index in range(24):
        with Image.open(tmp_path / f"edited-burst-{index:02d}.png") as opened:
            burst.append(opened.copy())
    complete = 0
    edited_boxes = client["carrier_bounds"]["edited"]
    carrier_states: dict[str, list[int]] = {}
    timing_windows: dict[str, dict[str, int | list[int]]] = {}
    for carrier in ("ordinary", "rich", "button"):
        raw_box = edited_boxes[carrier]
        try:
            located = locate_animation_sequence(burst, [tuple(raw_box)] * len(burst))
            states = [frame.state for frame in located[: len(intervals)]]
            timing = require_complete_cycle(states, intervals_ns=intervals)
            assert timing is not None
            carrier_states[carrier] = states
            timing_windows[carrier] = {
                "capture_indexes": list(timing.capture_indexes),
                "capture_count": timing.capture_count,
                "capture_times_ns": list(timing.capture_times_ns),
                "capture_span_ns": timing.capture_span_ns,
                "phase_bounds_ns": list(timing.phase_bounds_ns),
            }
        except AssertionError:
            continue
        complete += 1
    assert complete == 3, "All three edited bot carriers must show the authored animation"
    assert len({tuple(states) for states in carrier_states.values()}) == 1, (
        "All three edited bot carriers must remain synchronized in every capture"
    )
    for phase in ("edited", "restarted"):
        with Image.open(tmp_path / f"{phase}.png") as opened:
            frame = opened.convert("RGB")
        boxes = client["carrier_bounds"][phase]
        assert locate_static(frame, tuple(boxes["incoming"]))
        assert all(
            locate_animation(frame, tuple(boxes[carrier])) is not None
            for carrier in ("ordinary", "rich", "button")
        )
    expected = {
        "2_2.jpg": (THUMBNAIL.stat().st_size, hashlib.sha256(THUMBNAIL.read_bytes()).hexdigest()),
        "-1_1109.webm": (
            ANIMATED.stat().st_size,
            hashlib.sha256(ANIMATED.read_bytes()).hexdigest(),
        ),
    }
    for phase, record in client["cache"].items():
        assert record["partials"] == []
        for filename, (size, digest) in expected.items():
            copies = record["files"][filename]
            if phase == "initial" and filename == "-1_1109.webm":
                assert copies == []
                continue
            assert copies
            assert all(copy["size"] == size and copy["sha256"] == digest for copy in copies)
    assert (tmp_path / "client.apk").read_bytes() == Path(apk).read_bytes()
    write_report(
        tmp_path / "report.html",
        Report(
            run_id="custom-emoji-native-lifecycle",
            title="Original custom emoji lifecycle",
            mode="headless-android",
            outcome="passed",
            seed=31,
            profile={"APK SHA-256": hashlib.sha256(Path(apk).read_bytes()).hexdigest()},
            summary="Original static and animated custom emoji survive an edit and cold restart.",
            evidence={
                "Assets": requests,
                "Documents": documents,
                "Cache": client["cache"],
                "Animation capture derivation": derivation,
                "Animation timing windows": timing_windows,
            },
            limitations=(
                "Synthetic local catalog evidence does not establish production entitlement.",
                "Broader resolver fault and cancellation coverage remains separate.",
                "Animation burst PNGs are lossless copies of retained original raw screen pixels.",
            ),
            screenshots=tuple(
                Screenshot(caption=phase, png=(tmp_path / f"{phase}.png").read_bytes())
                for phase in ("initial", "edited", "restarted")
            ),
        ),
    )
