"""Real upstream activity and rendered synthetic bot conversation."""

import json
import os
import shutil
from dataclasses import asdict
from pathlib import Path

import pytest

from gramlab.runtime import RuntimeProfile, Sandbox

pytestmark = pytest.mark.android


def test_synthetic_world_opens_the_real_client_chat(tmp_path: Path) -> None:
    manifest = os.environ.get("GRAMLAB_ANDROID_RUNTIME_PROFILE")
    apk = os.environ.get("GRAMLAB_ANDROID_PROBE_APK")
    if manifest is None or apk is None:
        pytest.skip("Requires the Android profile and built client APK")
    if not os.access("/dev/kvm", os.R_OK | os.W_OK):
        pytest.skip("Requires an accessible KVM device")
    profile = RuntimeProfile.load(Path(manifest))
    toolchain = json.loads(Path("clients/android/toolchain.json").read_text())
    image_package = (
        f"system-images;android-{toolchain['sdk']['platform']};"
        f"{toolchain['runtime']['imageType']};{toolchain['runtime']['abi']}"
    )
    shutil.copy2(apk, tmp_path / "client.apk")
    shutil.copytree(
        "src/gramlab", tmp_path / "gramlab", ignore=shutil.ignore_patterns("__pycache__")
    )
    component_profile = RuntimeProfile.load(Path(os.environ["GRAMLAB_RUNTIME_PROFILE"]))
    (tmp_path / "component-profile.json").write_text(json.dumps(asdict(component_profile)))
    shutil.copy2("tests/probes/component_bot.py", tmp_path / "component_bot.py")
    shutil.copy2("tests/fixtures/echo_bot.py", tmp_path / "echo_bot.py")
    for name in ("android_guest.py", "android_application.py"):
        shutil.copy2(Path("tests/probes") / name, tmp_path / name)
    result = Sandbox(profile).supervise(
        [
            profile.python,
            "/work/android_application.py",
            profile.executables["emulator"],
            profile.executables["adb"],
            profile.executables["avdmanager"],
            image_package,
        ],
        data=tmp_path,
        kvm=True,
        timeout=420,
    )
    assert result.returncode == 0, result.stderr
    observed = json.loads(result.stdout)["extra_probe"]
    for phase, artifact in (
        ("initial", "ui"),
        ("restarted", "restarted"),
        ("recovered", "recovered"),
    ):
        assert "Status: ok" in observed[phase]["launch"], observed[phase]["launch"]
        assert "LaunchState: COLD" in observed[phase]["launch"]
        assert observed[phase]["ui"].count('text="سلام hello') == 1
        assert observed[phase]["ui"].count('text="Echo: سلام hello') == 1
        assert "Start Bot" not in observed[phase]["ui"]
        assert "Accounts: 0" in observed[phase]["accounts"]
        assert (tmp_path / f"{artifact}.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    for phase, reason in (
        ("missing", "configuration_missing"),
        ("wrong_world", "world_binding_mismatch"),
    ):
        rejected = [json.loads(line) for line in observed[phase]["trace"].splitlines()]
        assert rejected, f"{phase} startup rejection has no diagnostic trace"
        assert rejected[-1]["event"] == "startup_rejected"
        assert rejected[-1]["method"] == reason
        assert "FATAL EXCEPTION: main" in observed[phase]["logcat"]
        assert "GRAMLAB_STARTUP_REJECTED_" + reason in observed[phase]["logcat"]
    assert observed["history"] == [
        {"id": 1, "chat_id": 1, "sender_id": 1, "date": 1700000000, "text": "سلام hello"},
        {"id": 2, "chat_id": 1, "sender_id": 2, "date": 1700000000, "text": "Echo: سلام hello"},
    ]
