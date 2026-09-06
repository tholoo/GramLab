"""Actual upstream rich rendering follows the same real-bot scenario as simulation."""

import json
import os
import shutil
from dataclasses import asdict
from pathlib import Path

import pytest
from test_rich_round_trip import assert_rich_scenario, stage_rich_scenario

from gramlab.reports import Finding, Report, Screenshot, write_report
from gramlab.runtime import RuntimeProfile, Sandbox

pytestmark = pytest.mark.android


def test_real_bot_rich_blocks_render_edit_and_restart(tmp_path: Path) -> None:
    manifest = os.environ.get("GRAMLAB_ANDROID_RUNTIME_PROFILE")
    apk = os.environ.get("GRAMLAB_ANDROID_PROBE_APK")
    if manifest is None or apk is None or not os.access("/dev/kvm", os.R_OK | os.W_OK):
        pytest.skip("Requires the Android profile, rich-message APK and accessible KVM")
    profile = RuntimeProfile.load(Path(manifest))
    core = RuntimeProfile.load(Path(os.environ["GRAMLAB_RUNTIME_PROFILE"]))
    toolchain = json.loads(Path("clients/android/toolchain.json").read_text())
    image_package = (
        f"system-images;android-{toolchain['sdk']['platform']};"
        f"{toolchain['runtime']['imageType']};{toolchain['runtime']['abi']}"
    )
    stage_rich_scenario(tmp_path, core)
    shutil.copy2(apk, tmp_path / "client.apk")
    shutil.copy2(
        "clients/android/fixtures/rich-message.json", tmp_path / "rich-message-catalog.json"
    )
    shutil.copy2(
        "clients/android/fixtures/rich-message-invalid-tables.json",
        tmp_path / "rich-invalid-tables.json",
    )
    (tmp_path / "emulator-profile.json").write_text(json.dumps(asdict(profile)))
    for name in ("emulator_process.py", "android_guest.py", "android_rich_messages.py"):
        shutil.copy2(Path("tests/probes") / name, tmp_path / name)
    result = Sandbox(profile).supervise(
        [
            profile.python,
            "/work/android_rich_messages.py",
            profile.executables["emulator"],
            profile.executables["adb"],
            profile.executables["avdmanager"],
            image_package,
        ],
        data=tmp_path,
        kvm=True,
        timeout=420,
    )
    (tmp_path / "rich-result.json").write_text(result.stdout)
    assert result.returncode == 0, result.stderr
    observed = json.loads(result.stdout)["extra_probe"]
    assert_rich_scenario(observed)
    client = observed["client"]
    scene = json.loads(Path("tests/fixtures/rich-scene.json").read_text())
    for phase in ("initial", "edited"):
        messages = client["codecs"][phase]["messages"]
        assert len(messages) == 2
        rich = messages[0]
        assert rich["id"] == 2 and rich["text"] == ""
        assert rich["rich_message"] == scene[phase]
        assert "rich_message" not in messages[1]
    catalog = client["codecs"]["catalog"]["messages"]
    assert len(catalog) == 1
    assert catalog[0]["id"] == 1 and catalog[0]["text"] == ""
    assert catalog[0]["rich_message"] == json.loads(
        Path("clients/android/fixtures/rich-message.json").read_text()
    )
    assert client["codecs"]["rejections"] == {
        name: {"returncode": 2, "result": {"error": "GRAMLAB_BRIDGE_INVALID_RICH_MESSAGE"}}
        for name in ("later-row-wider-than-first", "expanded-cell-area-over-10000")
    }
    for phase in ("initial", "edited", "restarted"):
        assert "Rich blocks" in client[phase]
        assert "GramLab" in client[phase]
        assert ("۱۲۳" if phase == "initial" else "۴۵۶") in client[phase]
        assert ("Language" if phase == "initial" else "زبان") in client[phase]
        if phase != "initial":
            assert "Rich blocks updated" in client[phase]
            assert "Edited rich message" in client[phase]
        assert (tmp_path / f"{phase}.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert "Accounts: 0" in client["accounts"]
    for launch in client["launches"].values():
        assert "Status: ok" in launch and "LaunchState: COLD" in launch
    events = [
        json.loads(line) for line in (tmp_path / "edited-trace.jsonl").read_text().splitlines()
    ]
    assert any(event["event"] == "events_applied" for event in events)
    write_report(
        tmp_path / "report.html",
        Report(
            run_id="rich-message-send-edit-restart",
            title="Rich messages in the original Android renderer",
            mode="headless-android",
            outcome="passed",
            seed=7,
            profile={
                "Bot API target": "10.3; explicit block subset",
                "Android": "Pinned client, AOSP API 36, software GPU",
                "Display": "320 x 640, 160 dpi; baseline effects profile",
            },
            summary="A real local bot sends structured bilingual blocks and edits them to RTL. "
            "The native serializer retains the complete content; the original chat renders "
            "the send, live edit and cold restart.",
            evidence={
                "Bot replies": {key: observed[key] for key in ("initial", "edited")},
                "Durable history": observed["history"],
                "Native serialized content": client["codecs"],
            },
            timings=client["timings"],
            screenshots=[
                Screenshot(caption=phase, png=(tmp_path / f"{phase}.png").read_bytes())
                for phase in ("initial", "edited", "restarted")
            ],
            findings=[
                Finding(
                    stage="verified",
                    title="Structured rich content reaches Android",
                    detail="Heading, formatted text, bordered table and nested quotation are "
                    "preserved through real Bot API send/edit and native serialization.",
                )
            ],
            limitations=[
                "This scenario covers selected blocks, not all rich-message features.",
                "Input uses blocks with automatic entity detection explicitly disabled.",
                "Media, custom emoji, HTML/Markdown and draft streaming remain unverified.",
                "Baseline graphics settings do not establish full visual-effects fidelity.",
            ],
        ),
    )
