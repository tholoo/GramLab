"""Real bot HTTP to Android-side TL projection, before application activation."""

import json
import os
import shutil
from dataclasses import asdict
from pathlib import Path

import pytest

from gramlab.runtime import RuntimeProfile, Sandbox

pytestmark = pytest.mark.android


def test_real_bot_reply_becomes_the_personas_android_dialog_and_history(tmp_path: Path) -> None:
    manifest = os.environ.get("GRAMLAB_ANDROID_RUNTIME_PROFILE")
    apk = os.environ.get("GRAMLAB_ANDROID_PROBE_APK")
    if manifest is None or apk is None:
        pytest.skip("Requires the Android profile and built bridge probe APK")
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
    for name in ("android_guest.py", "android_client_bridge.py"):
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
    assert observed["returncode"] == 0, observed
    assert observed["pending"] == []
    for name, error in {
        "persona": "GRAMLAB_BRIDGE_INVALID_DATA",
        "world": "GRAMLAB_BRIDGE_INVALID_DATA",
        "capability": "GRAMLAB_BRIDGE_HTTP_401",
        "external": "GRAMLAB_BRIDGE_INVALID_DATA",
        "redirect": "GRAMLAB_BRIDGE_HTTP_302",
    }.items():
        rejected = observed["rejections"][name]
        assert rejected["returncode"] == 2, rejected
        assert json.loads(rejected["stdout"]) == {"error": error}
    assert json.loads(observed["stdout"]) == {
        "persona": 1,
        "cursor": 8,
        "now": 1700000000,
        "users": [
            {
                "id": 1,
                "first_name": "Sara",
                "self": True,
                "bot": False,
                "username": None,
                "language_code": "fa",
                "phone": None,
            },
            {
                "id": 2,
                "first_name": "Echo",
                "self": False,
                "bot": True,
                "username": "gramlab_echo_bot",
                "language_code": None,
                "phone": None,
            },
        ],
        "dialogs": [{"peer_id": 2, "top_message": 2}],
        "dialog_message_count": 1,
        "messages": [
            {
                "id": 2,
                "sender_id": 2,
                "recipient_id": 1,
                "out": False,
                "date": 1700000000,
                "text": "Echo: سلام hello",
            },
            {
                "id": 1,
                "sender_id": 1,
                "recipient_id": 2,
                "out": True,
                "date": 1700000000,
                "text": "سلام hello",
            },
        ],
    }
