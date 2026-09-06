"""A real Android inline tap drives the same callback/edit world as simulation-only mode."""

import json
import os
import shutil
import signal
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from gramlab.runtime import RuntimeProfile, Sandbox

pytestmark = pytest.mark.android


def test_real_android_tap_replays_after_bot_kill_and_renders_the_edit_after_client_restart(
    tmp_path: Path,
) -> None:
    manifest, apk = (
        os.environ.get("GRAMLAB_ANDROID_RUNTIME_PROFILE"),
        os.environ.get("GRAMLAB_ANDROID_PROBE_APK"),
    )
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
    shutil.copy2("tests/fixtures/callback_bot.py", tmp_path / "callback_bot.py")
    for name in ("android_guest.py", "android_callbacks.py", "callback_round_trip.py"):
        shutil.copy2(Path("tests/probes") / name, tmp_path / name)
    result = Sandbox(profile).run(
        [
            profile.python,
            "/work/android_callbacks.py",
            profile.executables["emulator"],
            profile.executables["adb"],
            profile.executables["avdmanager"],
            image_package,
        ],
        data=tmp_path,
        kvm=True,
        timeout=360,
    )
    assert result.returncode == 0, result.stderr
    guest = json.loads(result.stdout)
    assert "ANGLE" in guest["graphics"] and "SwiftShader" in guest["graphics"]
    observed = guest["extra_probe"]
    assert observed["killed"] == -signal.SIGKILL
    assert observed["before"]["callback"]["data"] == "confirm"
    assert observed["before"]["callback"]["answer"] is None
    assert observed["after"]["callback"]["answer"] == {
        "text": "انجام شد ✓",
        "show_alert": False,
        "cache_time": 0,
    }
    assert observed["history"] == [
        {"id": 1, "chat_id": 1, "sender_id": 1, "date": 1700000000, "text": "سلام hello"},
        {
            "id": 2,
            "chat_id": 1,
            "sender_id": 2,
            "date": 1700000000,
            "edit_date": 1700000005,
            "text": "تأیید شد ✓",
        },
    ]
    assert observed["pending"] == []
    client = observed["client"]
    assert "تأیید ✓" in client["before"]
    for phase in ("edited", "restarted"):
        assert client[phase].count('text="تأیید شد ✓') == 1
        assert "سلام hello — choose" not in client[phase]
        assert "تأیید ✓" not in client[phase]
    for phase in ("before", "edited", "restarted"):
        assert (
            sum(
                node.get("text", "").startswith("سلام hello\n")
                for node in ET.fromstring(client[phase]).iter("node")  # noqa: S314 — dedicated guest XML
            )
            == 1
        )
    assert (
        "LaunchState: COLD" in client["launch"] and "LaunchState: COLD" in client["restart_launch"]
    )
    assert "Accounts: 0" in client["accounts"]
    for name in ("before-tap", "after-edit", "after-restart"):
        assert (tmp_path / f"{name}.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    trace = [
        json.loads(line) for line in (tmp_path / "after-edit-trace.jsonl").read_text().splitlines()
    ]
    assert any(
        record["event"] == "response" and record["method"] == "TL_messages_getBotCallbackAnswer"
        for record in trace
    )
    assert any(record["event"] == "events_applied" for record in trace)
