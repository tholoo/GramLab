"""Original Android custom-emoji lifecycle and immutable cache acceptance."""

import hashlib
import importlib
import json
import os
import shutil
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pytest
from custom_emoji_visual import animation_states, require_complete_cycle
from PIL import Image

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
    helper.assert_scenario(full["extra_probe"])
    assert_native_lifecycle(tmp_path, full["extra_probe"], apk)


def assert_native_lifecycle(tmp_path: Path, observed: dict[str, Any], apk: str) -> None:
    client = observed["client"]["observed"]
    assert set(client["captures"]) == {"initial", "edited", "restarted"}
    for phase in client["captures"]:
        assert (tmp_path / f"{phase}.xml").read_text() == client["captures"][phase]
        assert (tmp_path / f"{phase}.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert set(client["launches"]) == {"initial", "restarted"}
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
    blue_carriers = 0
    for raw_box in client["carrier_bounds"]["initial"]:
        raw_pixels = initial.crop(tuple(raw_box)).tobytes()
        pixels = zip(raw_pixels[::3], raw_pixels[1::3], raw_pixels[2::3], strict=True)
        if any(
            abs(pixel[0] - 88) <= 45 and abs(pixel[1] - 104) <= 45 and abs(pixel[2] - 240) <= 45
            for pixel in pixels
        ):
            blue_carriers += 1
    assert blue_carriers >= 3
    burst = []
    for index in range(24):
        with Image.open(tmp_path / f"edited-burst-{index:02d}.png") as opened:
            burst.append(opened.copy())
    complete = 0
    for raw_box in client["carrier_bounds"]["edited"]:
        states = animation_states(burst, [tuple(raw_box)] * len(burst))
        try:
            require_complete_cycle(states)
        except AssertionError:
            continue
        complete += 1
    assert complete >= 2, "Ordinary and rich/button carriers must show the authored animation"
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
    assert hashlib.sha256(Path(apk).read_bytes()).hexdigest()
