"""Public rich-message consumers retain the same structured evidence in both modes."""

import json
import os
import shutil
from pathlib import Path
from typing import Any

import pytest

from gramlab.runner import run
from gramlab.runtime import RuntimeProfile


def rich_project(directory: Path) -> Path:
    directory.mkdir()
    for name in ("run.toml", "scenario.py", "bot.py", "scene.json"):
        shutil.copy2(Path("examples/rich") / name, directory / name)
    return directory / "run.toml"


def assert_rich_evidence(recorded: dict[str, Any], *, rendered: bool) -> None:
    scene = json.loads(Path("tests/fixtures/rich-scene.json").read_text())
    user = {"id": 1, "chat_id": 1, "sender_id": 2, "date": 1700000000, "text": "Show rich blocks"}
    original = {
        "id": 2,
        "chat_id": 1,
        "sender_id": 1,
        "date": 1700000000,
        "text": "",
        "rich_message": scene["initial"],
    }
    edited = {**original, "edit_date": 1700000005, "rich_message": scene["edited"]}
    command = {**user, "id": 3, "date": 1700000005, "text": "Edit rich blocks"}
    assert recorded["outcome"] == "passed", recorded
    assert recorded["histories"] == {"1": [user, edited, command]}
    captures = recorded["captures"]
    assert [capture["label"] for capture in captures] == ["initial", "edited", "restarted"]
    assert all(capture["chat_id"] == 1 and capture["rendered"] == rendered for capture in captures)
    assert [capture["history"] for capture in captures] == [
        [user, original],
        [user, edited, command],
        [user, edited, command],
    ]
    assert "Structured send and RTL edit" in recorded["processes"]["scenario"]["stdout"]


def test_rich_example_uses_real_bot_and_public_capture_requests(tmp_path: Path) -> None:
    manifest = rich_project(tmp_path / "project")
    output = tmp_path / "run"
    outcome = run(
        manifest,
        output,
        profile=RuntimeProfile.load(Path(os.environ["GRAMLAB_RUNTIME_PROFILE"])),
    )
    recorded = json.loads((output / "result.json").read_text())
    assert outcome == "passed", recorded
    assert_rich_evidence(recorded, rendered=False)
    assert not list(output.glob("captures/*.png"))
    assert "Rich blocks updated" in (output / "report.html").read_text()


@pytest.mark.android
def test_rich_example_renders_original_blocks_and_matches_simulation(tmp_path: Path) -> None:
    android_manifest = os.environ.get("GRAMLAB_ANDROID_RUNTIME_PROFILE")
    apk = os.environ.get("GRAMLAB_ANDROID_PROBE_APK")
    if android_manifest is None or apk is None or not os.access("/dev/kvm", os.R_OK | os.W_OK):
        pytest.skip("Requires the provisioned Android profile, rich-message APK and KVM")
    manifest = rich_project(tmp_path / "project")
    source = manifest.read_text()
    results = []
    for mode in ("simulation-only", "headless-android"):
        manifest.write_text(
            source.replace('mode = "simulation-only"', f'mode = "{mode}"').replace(
                "timeout = 20", "timeout = 300"
            )
        )
        output = tmp_path / mode
        outcome = run(
            manifest,
            output,
            profile=RuntimeProfile.load(Path(os.environ["GRAMLAB_RUNTIME_PROFILE"])),
            android_profile=RuntimeProfile.load(Path(android_manifest)),
            android_apk=Path(apk),
        )
        recorded = json.loads((output / "result.json").read_text())
        assert outcome == "passed", recorded
        assert_rich_evidence(recorded, rendered=mode == "headless-android")
        results.append(recorded)
    simulation, android = results
    for key in ("world", "histories", "events"):
        assert simulation[key] == android[key]
    for capture in android["captures"]:
        native = capture["android"]
        assert "Accounts: 0" in native["accounts"]
        assert "Status: ok" in native["launch"]
        assert ("۱۲۳" if capture["label"] == "initial" else "۴۵۶") in native["ui"]
        assert "GramLab" in native["ui"]
        png = tmp_path / "headless-android" / "captures" / (capture["label"] + ".png")
        assert png.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert android["android"]["network"]["ipv4"] != 0
    assert android["android"]["network"]["ipv6"] != 0
    report = (tmp_path / "headless-android" / "report.html").read_text()
    assert report.count("data:image/png;base64,") == 3
    assert "gramlab-client_" not in report and "gramlab-control_" not in report
