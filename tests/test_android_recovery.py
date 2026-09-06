"""Cold startup must reconcile older cached messages with the authoritative world."""

import json
import os
import shutil
import xml.etree.ElementTree as ET
from dataclasses import asdict
from pathlib import Path

import pytest
from recovery_report import write_recovery_report

from gramlab.runtime import RuntimeProfile, Sandbox

pytestmark = pytest.mark.android


def assert_recovery_result(observed) -> None:
    bot = {"id": 2, "is_bot": True, "first_name": "Echo", "username": "gramlab_echo_bot"}
    chat = {"id": 1, "type": "private", "first_name": "Sara"}
    keyboard = {"inline_keyboard": [[{"text": "Original action", "callback_data": "original"}]]}
    entities = [{"type": "bold", "offset": 7, "length": 9}]
    semantic = dict(observed)
    del semantic["client"]
    assert semantic == {
        "before": [
            {
                "message_id": 2,
                "from": bot,
                "chat": chat,
                "date": 1700000000,
                "text": "سلام — original",
                "reply_markup": keyboard,
            },
            {
                "message_id": 3,
                "from": bot,
                "chat": chat,
                "date": 1700000000,
                "text": "Previously newest",
            },
        ],
        "after": [
            {
                "message_id": 2,
                "from": bot,
                "chat": chat,
                "date": 1700000000,
                "edit_date": 1700000005,
                "text": "سلام — corrected 😀",
                "entities": entities,
            },
            {
                "message_id": 4,
                "from": bot,
                "chat": chat,
                "date": 1700000005,
                "text": "Sent while away",
            },
        ],
        "history": [
            {"id": 1, "chat_id": 1, "sender_id": 1, "date": 1700000000, "text": "Check recovery"},
            {
                "id": 2,
                "chat_id": 1,
                "sender_id": 2,
                "date": 1700000000,
                "edit_date": 1700000005,
                "text": "سلام — corrected 😀",
                "entities": entities,
            },
            {
                "id": 3,
                "chat_id": 1,
                "sender_id": 2,
                "date": 1700000000,
                "text": "Previously newest",
            },
            {"id": 4, "chat_id": 1, "sender_id": 2, "date": 1700000005, "text": "Sent while away"},
        ],
        "pending": [],
    }


def test_android_recovers_older_edits_and_newer_replies_without_duplicates(tmp_path: Path) -> None:
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
    shutil.copy2("tests/fixtures/recovery_bot.py", tmp_path / "recovery_bot.py")
    (tmp_path / "component-profile.json").write_text(json.dumps(asdict(core)))
    (tmp_path / "emulator-profile.json").write_text(json.dumps(asdict(profile)))
    for name in (
        "emulator_process.py",
        "component_bot.py",
        "android_guest.py",
        "recovery_round_trip.py",
        "android_recovery.py",
    ):
        shutil.copy2(Path("tests/probes") / name, tmp_path / name)
    result = Sandbox(profile).supervise(
        [
            profile.python,
            "/work/android_recovery.py",
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
    (tmp_path / "recovery-result.json").write_text(json.dumps(observed))
    assert_recovery_result(observed)
    for phase in ("recovered", "repeated"):
        # Trusted UIAutomator output from the dedicated guest.
        nodes = list(ET.fromstring(observed["client"][phase]).iter("node"))  # noqa: S314
        descriptions = [
            node.get("text", "") + "\n" + node.get("content-desc", "") for node in nodes
        ]
        for text in ("Check recovery", "corrected", "Previously newest", "Sent while away"):
            assert sum(text in description for description in descriptions) == 1
        assert all("original" not in description for description in descriptions)
        assert all("Original action" not in description for description in descriptions)
        assert (tmp_path / f"{phase}.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert "Accounts: 0" in observed["client"]["accounts"]
    for launch in observed["client"]["launches"].values():
        assert "Status: ok" in launch and "LaunchState: COLD" in launch
    report = write_recovery_report(tmp_path, observed, mode="headless-android")
    assert report.read_text().count("data:image/png;base64,") == 3
