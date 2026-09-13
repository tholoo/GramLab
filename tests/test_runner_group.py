"""The generic group example exercises a real contained Bot API consumer."""

import json
import os
import shutil
from pathlib import Path

import pytest

from gramlab.runner import run
from gramlab.runtime import RuntimeProfile


def group_project(directory: Path) -> Path:
    directory.mkdir()
    for name in ("run.toml", "scenario.py", "bot.py"):
        shutil.copy2(Path("examples/group") / name, directory / name)
    return directory / "run.toml"


def test_group_example_proves_membership_delivery_callback_and_edit(tmp_path: Path) -> None:
    output = tmp_path / "run"
    assert (
        run(
            Path("examples/group/run.toml"),
            output,
            profile=RuntimeProfile.load(Path(os.environ["GRAMLAB_RUNTIME_PROFILE"])),
        )
        == "passed"
    ), (output / "result.json").read_text()
    result = json.loads((output / "result.json").read_text())
    group = result["world"]["chats"][0]
    assert group == {
        "id": -1,
        "type": "supergroup",
        "title": "Study group",
        "members": [
            {"user_id": 1, "status": "member"},
            {"user_id": 2, "status": "creator"},
            {"user_id": 3, "status": "member"},
        ],
    }
    assert [message["text"] for message in result["histories"]["-1"]] == [
        "/game",
        "Continued for the group",
        "after restart",
        "Ready for the group",
    ]
    assert result["interactions"][0]["callback"]["user_id"] == 3
    assert [record["operation"] for record in result["lifecycle"]] == [
        "stop_bot",
        "start_bot",
    ]
    assert [capture["label"] for capture in result["captures"]] == [
        "group-before",
        "group-after",
        "group-restarted",
    ]


@pytest.mark.android
def test_group_example_renders_callback_edit_and_restarts_in_original_android(
    tmp_path: Path,
) -> None:
    android_manifest = os.environ.get("GRAMLAB_ANDROID_RUNTIME_PROFILE")
    apk = os.environ.get("GRAMLAB_ANDROID_PROBE_APK")
    if android_manifest is None or apk is None or not os.access("/dev/kvm", os.R_OK | os.W_OK):
        pytest.skip("Requires the Android profile, group-capable APK and KVM")
    manifest = group_project(tmp_path / "project")
    manifest.write_text(
        manifest.read_text()
        .replace('mode = "simulation-only"', 'mode = "headless-android"')
        .replace("timeout = 15", "timeout = 300")
    )
    output = tmp_path / "run"

    outcome = run(
        manifest,
        output,
        profile=RuntimeProfile.load(Path(os.environ["GRAMLAB_RUNTIME_PROFILE"])),
        android_profile=RuntimeProfile.load(Path(android_manifest)),
        android_apk=Path(apk),
        bridge_version=6,
    )
    result = json.loads((output / "result.json").read_text())

    assert outcome == "passed", result
    assert [message["text"] for message in result["histories"]["-1"]] == [
        "/game",
        "Continued for the group",
        "after restart",
        "Ready for the group",
    ]
    assert result["interactions"][0]["native"] is True
    assert result["interactions"][0]["callback"]["user_id"] == 3
    assert result["interactions"][1]["operation"] == "type_message"
    assert result["interactions"][1]["native"] is True
    expected = {
        "group-before": ["Study group", "/game", "Ready for the group"],
        "group-after": ["Study group", "/game", "Continued for the group"],
        "group-restarted": ["Study group", "after restart", "Ready for the group"],
    }
    for capture in result["captures"]:
        assert capture["rendered"] is True
        assert "Accounts: 0" in capture["android"]["accounts"]
        assert "Status: ok" in capture["android"]["launch"]
        assert all(text in capture["android"]["ui"] for text in expected[capture["label"]])
        assert "admin tag:" not in capture["android"]["ui"]
        screenshot = output / "captures" / f"{capture['label']}.png"
        assert screenshot.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    callback_events = [
        event["data"] for event in result["events"] if event["type"] == "callback.created"
    ]
    assert len(callback_events) == 1
    assert callback_events[0]["chat_id"] == -1
    assert result["android"]["network"]["ipv4"] != 0
    assert result["android"]["network"]["ipv6"] != 0
