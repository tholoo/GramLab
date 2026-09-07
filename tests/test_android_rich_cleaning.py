"""Cleaned bot messages retain complete native semantics, live RTL edits and cold restart."""

# Intentional Persian text exercises Unicode preservation.
# ruff: noqa: RUF001

import hashlib
import json
import os
import shutil
import xml.etree.ElementTree as ET
from dataclasses import asdict
from pathlib import Path

import pytest
from test_rich_cleaning_round_trip import (
    EXPECTED_SCENE,
    assert_cleaning_scenario,
    stage_cleaning_scenario,
)

from gramlab.reports import Report, Screenshot, write_report
from gramlab.runtime import RuntimeProfile, Sandbox

pytestmark = pytest.mark.android


def test_cleaned_rich_content_renders_live_rtl_edit_and_cold_restart(tmp_path: Path) -> None:
    manifest = os.environ.get("GRAMLAB_ANDROID_RUNTIME_PROFILE")
    apk = os.environ.get("GRAMLAB_ANDROID_PROBE_APK")
    if manifest is None or apk is None or not os.access("/dev/kvm", os.R_OK | os.W_OK):
        pytest.skip("Requires the provisioned Android profile, rich-message APK and KVM")
    profile = RuntimeProfile.load(Path(manifest))
    core = RuntimeProfile.load(Path(os.environ["GRAMLAB_RUNTIME_PROFILE"]))
    toolchain = json.loads(Path("clients/android/toolchain.json").read_text())
    image_package = (
        f"system-images;android-{toolchain['sdk']['platform']};"
        f"{toolchain['runtime']['imageType']};{toolchain['runtime']['abi']}"
    )
    stage_cleaning_scenario(tmp_path, core)
    shutil.copy2(apk, tmp_path / "client.apk")
    (tmp_path / "emulator-profile.json").write_text(json.dumps(asdict(profile)))
    for name in (
        "emulator_process.py",
        "android_guest.py",
        "android_rich_messages.py",
        "android_rich_cleaning.py",
    ):
        shutil.copy2(Path("tests/probes") / name, tmp_path / name)
    result = Sandbox(profile).supervise(
        [
            profile.python,
            "/work/android_rich_cleaning.py",
            profile.executables["emulator"],
            profile.executables["adb"],
            profile.executables["avdmanager"],
            image_package,
        ],
        data=tmp_path,
        kvm=True,
        timeout=300,
    )
    (tmp_path / "cleaning-native-result.json").write_text(result.stdout)
    (tmp_path / "cleaning-native-stderr.log").write_text(result.stderr)
    assert result.returncode == 0, result.stderr
    full = json.loads(result.stdout)
    assert full["host_interfaces"] == [[1, "lo"]]
    assert "Accounts: 0" in full["accounts"]
    assert full["emulator_filesystem"] == {
        "world_visible": False,
        "bot_visible": False,
        "private_avd_visible": True,
        "same_pid_namespace": False,
        "same_network": True,
    }
    assert full["network"]["local"] == "gramlab-local-reply\n"
    assert full["network"]["local_error"] == ""
    for family in ("ipv4", "ipv6"):
        assert full["network"][family] == {
            "returncode": 1,
            "stdout": "",
            "stderr": "nc: connect: Network is unreachable\n",
        }
    observed = full["extra_probe"]
    assert_cleaning_scenario(observed)
    client = observed["client"]
    assert set(client["codecs"]) == {"initial", "edited"}
    for phase in ("initial", "edited"):
        assert client["codecs"][phase]["messages"] == [
            {
                "id": 2,
                "sender_id": 2,
                "recipient_id": 1,
                "out": False,
                "date": 1700000000,
                "text": "",
                "rich_message": EXPECTED_SCENE[phase],
            },
            {
                "id": 1,
                "sender_id": 1,
                "recipient_id": 2,
                "out": True,
                "date": 1700000000,
                "text": "Show rich blocks",
            },
        ]
    assert set(client["launches"]) == {"initial", "restarted"}
    for launch in client["launches"].values():
        assert "Status: ok" in launch and "LaunchState: COLD" in launch
    for phase in ("initial", "edited", "restarted"):
        assert (tmp_path / f"{phase}.xml").read_text() == client[phase]
        tree = ET.fromstring(client[phase])  # noqa: S314 — dedicated guest UIAutomator XML
        text = "\n".join(node.get("text", "") for node in tree.iter("node"))
        expected = (
            ["Clean start", "Amber 42", "ABCD", "print 1", "Value 7"]
            if phase == "initial"
            else ["متن پاک", "EFGH", "note 2", "جدول پاک", "عدد ۸"]
        )
        assert all(fragment in text for fragment in [*expected, "فارسی می\u200cماند"])
        assert (tmp_path / f"{phase}.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert "Accounts: 0" in client["accounts"]
    events = [
        json.loads(line) for line in (tmp_path / "edited-trace.jsonl").read_text().splitlines()
    ]
    assert any(event["event"] == "events_applied" for event in events)
    write_report(
        tmp_path / "report.html",
        Report(
            run_id="rich-cleaning-send-edit-restart",
            title="Cleaned rich text in the original Android renderer",
            mode="headless-android",
            outcome="passed",
            seed=7,
            profile={
                "Android": "Pinned client; AOSP API 36; 320 x 640 at 160 dpi",
                "APK SHA-256": hashlib.sha256(Path(apk).read_bytes()).hexdigest(),
            },
            summary="A real local bot sends dirty rich text and edits it to RTL. Complete replies, "
            "history and native serialization retain the independently specified cleaned content. "
            "The original chat supplies initial, live-edit and cold-restart captures.",
            evidence={
                "Raw input": json.loads((tmp_path / "rich-scene.json").read_text()),
                "Expected canonical content": EXPECTED_SCENE,
                "Bot and native observations": observed,
                "Network isolation": full["network"],
                "Emulator filesystem": full["emulator_filesystem"],
            },
            timings={
                name.removesuffix("_seconds"): value * 1000
                for name, value in client["timings"].items()
            },
            screenshots=[
                Screenshot(caption=phase, png=(tmp_path / f"{phase}.png").read_bytes())
                for phase in ("initial", "edited", "restarted")
            ],
            limitations=[
                "Source-derived canonical expectations do not establish live server acceptance.",
                "This short scene omits long truncation boundaries and unsupported rich actions.",
                "Screenshots require visual inspection in addition to semantic verification.",
            ],
        ),
    )
