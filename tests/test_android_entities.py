"""Formatting survives the pinned Android serializer and actual renderer."""

import json
import os
import shutil
from dataclasses import asdict
from pathlib import Path

import pytest
from test_entities import assert_formatted_result

from gramlab.runtime import RuntimeProfile, Sandbox

pytestmark = pytest.mark.android


def test_android_serialization_retains_all_supported_formatting_entities(tmp_path: Path) -> None:
    manifest, apk = (
        os.environ.get("GRAMLAB_ANDROID_RUNTIME_PROFILE"),
        os.environ.get("GRAMLAB_ANDROID_PROBE_APK"),
    )
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
    shutil.copy2("tests/fixtures/formatting.json", tmp_path / "formatting.json")
    shutil.copy2("tests/fixtures/echo_bot.py", tmp_path / "echo_bot.py")
    (tmp_path / "component-profile.json").write_text(json.dumps(asdict(core)))
    (tmp_path / "emulator-profile.json").write_text(json.dumps(asdict(profile)))
    for name in (
        "emulator_process.py",
        "component_bot.py",
        "android_guest.py",
        "android_client_bridge.py",
    ):
        shutil.copy2(Path("tests/probes") / name, tmp_path / name)
    result = Sandbox(profile).supervise(
        [
            profile.python,
            "/work/android_client_bridge.py",
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
    assert observed["returncode"] == 0, observed["stdout"]
    messages = json.loads(observed["stdout"])["messages"]
    assert (
        messages[0]["text"]
        == json.loads(Path("tests/fixtures/formatting.json").read_text())["text"]
    )
    assert messages[0]["entities"] == [
        {"kind": "TL_messageEntityBold", "offset": 3, "length": 9},
        {"kind": "TL_messageEntityItalic", "offset": 13, "length": 6},
        {"kind": "TL_messageEntityUnderline", "offset": 20, "length": 9},
        {"kind": "TL_messageEntityStrike", "offset": 30, "length": 6},
        {"kind": "TL_messageEntitySpoiler", "offset": 37, "length": 6},
        {"kind": "TL_messageEntityCode", "offset": 44, "length": 6},
        {"kind": "TL_messageEntityPre", "offset": 51, "length": 11, "language": "python"},
        {"kind": "TL_messageEntityBlockquote", "offset": 63, "length": 10, "collapsed": False},
        {"kind": "TL_messageEntityBlockquote", "offset": 74, "length": 27, "collapsed": True},
    ]
    assert "entities" not in messages[1]


def test_real_bot_formatting_edit_renders_and_survives_android_restart(tmp_path: Path) -> None:
    manifest, apk = (
        os.environ.get("GRAMLAB_ANDROID_RUNTIME_PROFILE"),
        os.environ.get("GRAMLAB_ANDROID_PROBE_APK"),
    )
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
    for name in ("formatting.json", "formatted_bot.py"):
        shutil.copy2(Path("tests/fixtures") / name, tmp_path / name)
    (tmp_path / "component-profile.json").write_text(json.dumps(asdict(core)))
    (tmp_path / "emulator-profile.json").write_text(json.dumps(asdict(profile)))
    for name in (
        "emulator_process.py",
        "component_bot.py",
        "android_guest.py",
        "formatted_round_trip.py",
        "android_formatting.py",
    ):
        shutil.copy2(Path("tests/probes") / name, tmp_path / name)
    result = Sandbox(profile).supervise(
        [
            profile.python,
            "/work/android_formatting.py",
            profile.executables["emulator"],
            profile.executables["adb"],
            profile.executables["avdmanager"],
            image_package,
        ],
        data=tmp_path,
        kvm=True,
        timeout=300,
    )
    assert result.returncode == 0, result.stderr
    observed = json.loads(result.stdout)["extra_probe"]
    assert_formatted_result(
        observed, json.loads(Path("tests/fixtures/formatting.json").read_text())
    )
    client = observed["client"]
    for phase in ("plain", "formatted", "restarted"):
        assert "Bold" in client[phase] and "Show formatting" in client[phase]
        assert (tmp_path / f"{phase}.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    for launch in client["launches"].values():
        assert "Status: ok" in launch and "LaunchState: COLD" in launch
    assert "Accounts: 0" in client["accounts"]
    events = [
        json.loads(line) for line in (tmp_path / "formatted-trace.jsonl").read_text().splitlines()
    ]
    assert any(event["event"] == "events_applied" for event in events)
