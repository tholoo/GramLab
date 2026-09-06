"""Source-derived text fixtures must match the original composer before simulation use."""

import json
import os
import shutil
from dataclasses import asdict
from pathlib import Path

import pytest

from gramlab.runtime import RuntimeProfile, Sandbox

pytestmark = pytest.mark.android


def test_original_composer_trims_and_extracts_utf16_entities(tmp_path: Path) -> None:
    manifest = os.environ.get("GRAMLAB_ANDROID_RUNTIME_PROFILE")
    apk = os.environ.get("GRAMLAB_ANDROID_PROBE_APK")
    if manifest is None or apk is None or not os.access("/dev/kvm", os.R_OK | os.W_OK):
        pytest.skip("Requires the Android profile, APK and accessible KVM")
    profile = RuntimeProfile.load(Path(manifest))
    core = RuntimeProfile.load(Path(os.environ["GRAMLAB_RUNTIME_PROFILE"]))
    toolchain = json.loads(Path("clients/android/toolchain.json").read_text())
    image_package = (
        f"system-images;android-{toolchain['sdk']['platform']};"
        f"{toolchain['runtime']['imageType']};{toolchain['runtime']['abi']}"
    )
    shutil.copytree(
        "src/gramlab", tmp_path / "gramlab", ignore=shutil.ignore_patterns("__pycache__")
    )
    shutil.copy2(apk, tmp_path / "client.apk")
    shutil.copy2("tests/fixtures/composer-text.json", tmp_path / "composer-text.json")
    (tmp_path / "component-profile.json").write_text(json.dumps(asdict(core)))
    (tmp_path / "emulator-profile.json").write_text(json.dumps(asdict(profile)))
    for name in ("emulator_process.py", "android_guest.py", "android_composer_text.py"):
        shutil.copy2(Path("tests/probes") / name, tmp_path / name)
    result = Sandbox(profile).supervise(
        [
            profile.python,
            "/work/android_composer_text.py",
            profile.executables["emulator"],
            profile.executables["adb"],
            profile.executables["avdmanager"],
            image_package,
        ],
        data=tmp_path,
        kvm=True,
        timeout=240,
    )
    assert result.returncode == 0, result.stderr
    observed = json.loads(result.stdout)["extra_probe"]
    cases = json.loads(Path("tests/fixtures/composer-text.json").read_text())
    expected = [
        {"id": index + 2, "chat_id": 1, "sender_id": 1, "date": 1700000000, **case["message"]}
        for index, case in enumerate(cases)
    ]
    assert observed["history"] == [
        {
            "id": 1,
            "chat_id": 1,
            "sender_id": 2,
            "date": 1700000000,
            "text": "Composer text contract",
        },
        *expected,
    ]
    assert [row["send"]["message"] for row in observed["cases"]] == expected
    assert [row["send"]["position"] for row in observed["cases"]] == list(range(2, 9))
    assert [row["message"] for row in observed["updates"]] == expected
    assert [row["name"] for row in observed["cases"]] == [case["name"] for case in cases]
    assert all(row["input"]["send_actions"] == 1 for row in observed["cases"])
