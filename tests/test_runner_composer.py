"""A private consumer uses one composer scenario in both supported run modes."""

import json
import os
from pathlib import Path

import pytest

from gramlab.runner import run
from gramlab.runtime import RuntimeProfile


def composer_project(directory: Path) -> Path:
    directory.mkdir()
    for name in ("run.toml", "scenario.py", "bot.py"):
        (directory / name).write_bytes((Path("examples/composer") / name).read_bytes())
    return directory / "run.toml"


def test_consumer_composer_runs_with_real_bot_and_retains_semantic_receipts(
    tmp_path: Path, trace_runner
):
    manifest = composer_project(tmp_path / "project")
    output = tmp_path / "run"
    assert (
        run(
            manifest,
            output,
            profile=RuntimeProfile.load(Path(os.environ["GRAMLAB_RUNTIME_PROFILE"])),
        )
        == "passed"
    ), (output / "result.json").read_text()
    recorded = json.loads((output / "result.json").read_text())
    assert len(recorded["histories"]["1"]) == 8
    assert len(recorded["interactions"]) == 4
    assert [row["sends"][0]["position"] for row in recorded["interactions"]] == [1, 3, 5, 7]
    assert all(not row["native"] for row in recorded["interactions"])
    assert [row["label"] for row in recorded["captures"]] == [
        "before-input",
        "first-send",
        "after-input",
    ]
    assert "four bot replies" in recorded["processes"]["scenario"]["stdout"]
    assert "type_message" in (output / "report.html").read_text()


@pytest.mark.android
def test_consumer_composer_uses_original_input_and_matches_simulation(tmp_path: Path):
    manifest_path = os.environ.get("GRAMLAB_ANDROID_RUNTIME_PROFILE")
    apk = os.environ.get("GRAMLAB_ANDROID_PROBE_APK")
    if manifest_path is None or apk is None or not os.access("/dev/kvm", os.R_OK | os.W_OK):
        pytest.skip("Requires the Android profile, APK and accessible KVM")
    profile = RuntimeProfile.load(Path(os.environ["GRAMLAB_RUNTIME_PROFILE"]))
    android_profile = RuntimeProfile.load(Path(manifest_path))
    manifest = composer_project(tmp_path / "project")
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
            profile=profile,
            android_profile=android_profile,
            android_apk=Path(apk),
        )
        recorded = json.loads((output / "result.json").read_text())
        assert outcome == "passed", recorded
        results.append(recorded)
    simulation, android = results
    assert simulation["world"] == android["world"]
    assert simulation["histories"] == android["histories"]
    assert simulation["events"] == android["events"]
    assert len(android["interactions"]) == 4
    for virtual, actual in zip(simulation["interactions"], android["interactions"], strict=True):
        assert not virtual["native"] and actual["native"]
        assert {key: virtual[key] for key in ("operation", "text", "chat_id")} == {
            key: actual[key] for key in ("operation", "text", "chat_id")
        }
        assert virtual["sends"][0]["message"] == actual["sends"][0]["message"]
        assert virtual["sends"][0]["position"] == actual["sends"][0]["position"]
        if actual["operation"] == "start_bot_chat":
            assert actual["android"]["input"]["input"] == "touch"
            assert actual["android"]["input"]["target"]["text"] == "Start Bot"
            assert actual["android"]["input"]["send_actions"] == 1
            assert actual["android"]["launch"] is None  # Same captured first-use screen.
            continue
        assert actual["android"]["input"] == {
            "ok": True,
            "input": "accessibility",
            "text_verified": True,
            "send_actions": 1,
            "uid": 2000,
        }
    assert len(android["captures"]) == 3
    assert all(capture["rendered"] for capture in android["captures"])
    report = (tmp_path / "headless-android" / "report.html").read_text()
    assert report.count("data:image/png;base64,") == 3
    assert "gramlab-client_" not in report and "gramlab-control_" not in report
