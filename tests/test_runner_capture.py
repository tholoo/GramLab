"""Scenario captures use the authoritative world and remain meaningful without Android."""

import json
import os
from pathlib import Path

import pytest
from test_runner import invoke, project

from gramlab.runner import run
from gramlab.runtime import RuntimeProfile


def test_scenario_capture_retains_the_complete_requested_chat(tmp_path: Path):
    manifest = project(tmp_path / "project")
    with (manifest.parent / "scenario.py").open("a") as script:
        script.write("""captured = lab.capture_chat(
    chat_id=chat["id"], label="reply", contains=["Echo: سلام hello"],
)
assert captured == {
    "chat_id": 1, "label": "reply", "history": lab.history(1), "rendered": False,
}
""")
    output = tmp_path / "run"
    result = invoke(manifest, output)
    assert result.returncode == 0, (output / "result.json").read_text()
    recorded = json.loads((output / "result.json").read_text())
    assert recorded["captures"] == [
        {
            "chat_id": 1,
            "label": "reply",
            "history": recorded["histories"]["1"],
            "rendered": False,
        }
    ]
    assert not list(output.glob("captures/*.png"))
    assert "reply" in (output / "report.html").read_text()


def test_capture_rejections_do_not_overwrite_existing_evidence(tmp_path: Path):
    manifest = project(tmp_path / "project")
    with (manifest.parent / "scenario.py").open("a") as script:
        script.write("""from gramlab.scenario import ScenarioError
first = lab.capture_chat(chat_id=1, label="reply", contains=["Echo: سلام hello"])
for arguments in (
    {"chat_id": 1, "label": "reply", "contains": ["Echo: سلام hello"]},
    {"chat_id": 1, "label": "missing", "contains": ["not in this chat"]},
    {"chat_id": 2, "label": "other", "contains": ["Echo: سلام hello"]},
    {"chat_id": 1, "label": "../escaped", "contains": ["Echo: سلام hello"]},
    {"chat_id": 1, "label": "empty", "contains": []},
):
    try:
        lab.capture_chat(**arguments)
    except ScenarioError as error:
        assert error.code == "invalid_request" and not error.outcome_uncertain
    else:
        raise AssertionError("Invalid capture accepted")
""")
    output = tmp_path / "run"
    result = invoke(manifest, output)
    assert result.returncode == 0, (output / "result.json").read_text()
    recorded = json.loads((output / "result.json").read_text())
    assert len(recorded["captures"]) == 1
    assert recorded["captures"][0]["label"] == "reply"
    assert not (tmp_path / "escaped.png").exists()


@pytest.mark.parametrize("fail_after_capture", [False, True])
def test_python_runner_api_keeps_captures_on_pass_and_failure(
    tmp_path: Path,
    trace_runner,
    fail_after_capture: bool,
):
    manifest = project(tmp_path / "project")
    with (manifest.parent / "scenario.py").open("a") as script:
        script.write('lab.capture_chat(chat_id=1, label="reply", contains=["Echo: سلام hello"])\n')
        if fail_after_capture:
            script.write('raise RuntimeError("Failed after capture")\n')
    output = tmp_path / "run"
    outcome = run(
        manifest,
        output,
        profile=RuntimeProfile.load(Path(os.environ["GRAMLAB_RUNTIME_PROFILE"])),
    )
    assert outcome == ("failed" if fail_after_capture else "passed")
    recorded = json.loads((output / "result.json").read_text())
    assert recorded["captures"] == [
        {
            "chat_id": 1,
            "label": "reply",
            "rendered": False,
            "history": [
                {"id": 1, "chat_id": 1, "sender_id": 2, "date": 1700000000, "text": "سلام hello"},
                {
                    "id": 2,
                    "chat_id": 1,
                    "sender_id": 1,
                    "date": 1700000000,
                    "text": "Echo: سلام hello",
                },
            ],
        }
    ]
    assert recorded["outcome"] == outcome
    assert (output / "report.html").is_file()


def test_capture_limit_and_credential_shaped_labels_are_rejected(tmp_path: Path):
    manifest = project(tmp_path / "project")
    with (manifest.parent / "scenario.py").open("a") as script:
        script.write("""from gramlab.scenario import ScenarioError
try:
    lab.capture_chat(chat_id=1, label="gramlab-control_" + "a" * 43, contains=["hello"])
except ScenarioError as error:
    assert error.code == "invalid_request"
else:
    raise AssertionError("Credential-shaped artifact label accepted")
for index in range(8):
    lab.capture_chat(chat_id=1, label="capture-" + str(index), contains=["Echo: سلام hello"])
try:
    lab.capture_chat(chat_id=1, label="ninth", contains=["hello"])
except ScenarioError as error:
    assert error.code == "invalid_request" and not error.outcome_uncertain
else:
    raise AssertionError("Capture limit was ignored")
""")
    output = tmp_path / "run"
    result = invoke(manifest, output)
    assert result.returncode == 0, (output / "result.json").read_text()
    records = json.loads((output / "result.json").read_text())["captures"]
    assert [record["label"] for record in records] == [f"capture-{index}" for index in range(8)]


def test_headless_mode_requires_provisioning_before_output(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("GRAMLAB_ANDROID_RUNTIME_PROFILE", raising=False)
    monkeypatch.delenv("GRAMLAB_ANDROID_APK", raising=False)
    manifest = project(tmp_path / "project")
    manifest.write_text('mode = "headless-android"\n' + manifest.read_text())
    output = tmp_path / "run"
    result = invoke(manifest, output)
    assert result.returncode == 2
    assert "requires a trusted Android profile" in result.stderr
    assert not output.exists()
