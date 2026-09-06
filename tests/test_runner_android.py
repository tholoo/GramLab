"""The same consumer scenario drives semantic and actual upstream-renderer evidence."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from test_runner import project as echo_project

from gramlab.runner import run
from gramlab.runtime import RuntimeProfile

pytestmark = pytest.mark.android


def test_consumer_captures_match_worlds_and_render_both_personas(tmp_path: Path):
    profile = os.environ.get("GRAMLAB_ANDROID_RUNTIME_PROFILE")
    apk = os.environ.get("GRAMLAB_ANDROID_PROBE_APK")
    if profile is None or apk is None or not os.access("/dev/kvm", os.R_OK | os.W_OK):
        pytest.skip("Requires the provisioned Android profile, approved APK and KVM")
    project = tmp_path / "project"
    project.mkdir()
    for name in ("bot.py", "scenario.py"):
        (project / name).write_bytes((Path("examples/echo") / name).read_bytes())
    results = []
    for mode in ("simulation-only", "headless-android"):
        manifest = project / "run.toml"
        manifest.write_text(
            Path("examples/echo/run.toml")
            .read_text()
            .replace('mode = "simulation-only"', f'mode = "{mode}"')
            .replace("timeout = 15", "timeout = 300")
        )
        output = tmp_path / mode
        command = [
            sys.executable,
            "-m",
            "gramlab",
            "run",
            str(manifest),
            "--output",
            str(output),
            "--android-profile",
            profile,
            "--android-apk",
            apk,
        ]
        result = subprocess.run(  # noqa: S603 — public CLI; all consumer execution is contained
            command,
            capture_output=True,
            text=True,
            timeout=420,
        )
        assert result.returncode == 0, result.stderr + (
            (output / "result.json").read_text()
            if (output / "result.json").exists()
            else result.stdout
        )
        results.append(json.loads((output / "result.json").read_text()))
    simulation, android = results
    assert simulation["world"] == android["world"]
    assert simulation["histories"] == android["histories"]
    assert len(android["captures"]) == len(simulation["captures"]) == 2
    for simple, rendered in zip(simulation["captures"], android["captures"], strict=True):
        assert {key: rendered[key] for key in ("chat_id", "label", "history")} == {
            key: simple[key] for key in ("chat_id", "label", "history")
        }
        assert not simple["rendered"] and rendered["rendered"]
        observed = rendered["android"]
        assert "Accounts: 0" in observed["accounts"]
        assert "Status: ok" in observed["launch"]
        assert "Echo: " in observed["ui"]
        png = tmp_path / "headless-android" / "captures" / (rendered["label"] + ".png")
        assert png.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    guest = android["android"]
    assert guest["api"] == "36" and guest["abi"] == "x86_64"
    assert guest["filesystem"] == {
        "world_visible": False,
        "bot_visible": False,
        "scenario_visible": False,
        "private_avd_visible": True,
        "same_pid_namespace": False,
        "same_network": True,
    }
    assert guest["network"]["ipv4"] != 0 and guest["network"]["ipv6"] != 0
    report = (tmp_path / "headless-android" / "report.html").read_text()
    assert report.count("data:image/png;base64,") == 2
    assert "gramlab-client_" not in report and "gramlab-control_" not in report


def test_android_scenario_failure_keeps_original_capture(tmp_path: Path, trace_runner):
    profile = os.environ.get("GRAMLAB_ANDROID_RUNTIME_PROFILE")
    apk = os.environ.get("GRAMLAB_ANDROID_PROBE_APK")
    if profile is None or apk is None or not os.access("/dev/kvm", os.R_OK | os.W_OK):
        pytest.skip("Requires the provisioned Android profile, approved APK and KVM")
    manifest = echo_project(tmp_path / "project")
    manifest.write_text(
        'mode = "headless-android"\n'
        + manifest.read_text().replace("timeout = 10", "timeout = 300")
    )
    with (manifest.parent / "scenario.py").open("a") as script:
        script.write("""lab.capture_chat(
    chat_id=1, label="before-failure", contains=["Echo: سلام hello"],
)
raise RuntimeError("Intentional failure after Android capture")
""")
    output = tmp_path / "run"
    outcome = run(
        manifest,
        output,
        profile=RuntimeProfile.load(Path(os.environ["GRAMLAB_RUNTIME_PROFILE"])),
        android_profile=RuntimeProfile.load(Path(profile)),
        android_apk=Path(apk),
    )
    assert outcome == "failed"
    recorded = json.loads((output / "result.json").read_text())
    assert recorded["failure"] == "process_failed"
    assert len(recorded["captures"]) == 1 and recorded["captures"][0]["rendered"]
    assert (
        "Intentional failure after Android capture" in recorded["processes"]["scenario"]["stderr"]
    )
    assert (
        (output / "captures" / "before-failure.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    )
    assert (output / "report.html").read_text().count("data:image/png;base64,") == 1


def test_android_startup_deadline_retains_failed_run(tmp_path: Path):
    profile = os.environ.get("GRAMLAB_ANDROID_RUNTIME_PROFILE")
    apk = os.environ.get("GRAMLAB_ANDROID_PROBE_APK")
    if profile is None or apk is None or not os.access("/dev/kvm", os.R_OK | os.W_OK):
        pytest.skip("Requires the provisioned Android profile, approved APK and KVM")
    manifest = echo_project(tmp_path / "project")
    manifest.write_text(
        'mode = "headless-android"\n'
        + manifest.read_text().replace("timeout = 10", "timeout = 0.1")
    )
    output = tmp_path / "run"
    outcome = run(
        manifest,
        output,
        profile=RuntimeProfile.load(Path(os.environ["GRAMLAB_RUNTIME_PROFILE"])),
        android_profile=RuntimeProfile.load(Path(profile)),
        android_apk=Path(apk),
    )
    assert outcome == "failed"
    recorded = json.loads((output / "result.json").read_text())
    assert recorded["failure"] == "timeout"
    assert recorded["processes"] == {} and recorded["captures"] == []
    assert (output / "report.html").is_file()


def test_consumer_inline_button_uses_native_input_and_matches_simulation(tmp_path: Path):
    from test_runner_interactions import inline_project

    profile = os.environ.get("GRAMLAB_ANDROID_RUNTIME_PROFILE")
    apk = os.environ.get("GRAMLAB_ANDROID_PROBE_APK")
    if profile is None or apk is None or not os.access("/dev/kvm", os.R_OK | os.W_OK):
        pytest.skip("Requires the provisioned Android profile, approved APK and KVM")
    manifest = inline_project(tmp_path / "project")
    results = []
    for mode in ("simulation-only", "headless-android"):
        manifest.write_text(
            Path("examples/inline/run.toml")
            .read_text()
            .replace('mode = "simulation-only"', f'mode = "{mode}"')
            .replace("timeout = 15", "timeout = 300")
        )
        output = tmp_path / mode
        outcome = run(
            manifest,
            output,
            profile=RuntimeProfile.load(Path(os.environ["GRAMLAB_RUNTIME_PROFILE"])),
            android_profile=RuntimeProfile.load(Path(profile)),
            android_apk=Path(apk),
        )
        recorded = json.loads((output / "result.json").read_text())
        assert outcome == "passed", recorded
        results.append(recorded)
    simulation, android = results
    assert simulation["world"] == android["world"]
    assert simulation["histories"] == android["histories"]
    assert len(simulation["interactions"]) == len(android["interactions"]) == 1
    simple, native = simulation["interactions"][0], android["interactions"][0]
    assert simple["native"] is False and native["native"] is True
    for key in ("chat_id", "message_id", "row", "column"):
        assert simple[key] == native[key]
    for key in ("user_id", "chat_id", "message", "data"):
        assert simple["callback"][key] == native["callback"][key]
    assert native["callback"]["data"] == "confirm"
    assert native["android"]["target"]["class"] == "android.widget.Button"
    assert native["android"]["target"]["text"] == "Confirm"
    created = [event for event in android["events"] if event["type"] == "callback.created"]
    assert len(created) == 1 and created[0]["data"]["id"] == native["callback"]["id"]
    assert [record["label"] for record in android["captures"]] == ["before-tap", "after-edit"]
    assert all(record["rendered"] for record in android["captures"])
    report = (tmp_path / "headless-android/report.html").read_text()
    assert report.count("data:image/png;base64,") == 2


def test_ambiguous_native_target_fails_run_without_a_second_callback(tmp_path: Path):
    from test_runner_interactions import inline_project

    profile = os.environ.get("GRAMLAB_ANDROID_RUNTIME_PROFILE")
    apk = os.environ.get("GRAMLAB_ANDROID_PROBE_APK")
    if profile is None or apk is None or not os.access("/dev/kvm", os.R_OK | os.W_OK):
        pytest.skip("Requires the provisioned Android profile, approved APK and KVM")
    manifest = inline_project(tmp_path / "project")
    manifest.write_text(Path("examples/inline/android.toml").read_text())
    with (manifest.parent / "scenario.py").open("a") as script:
        script.write("""
from gramlab.scenario import ScenarioError
for _ in range(2):
    duplicate = lab.send_message(
        chat_id=chat["id"], sender_id=lab.bots()["inline"], text="Duplicate prompt",
        reply_markup={"inline_keyboard": [[{"text": "Confirm", "callback_data": "duplicate"}]]},
    )
before = lab.events()
try:
    lab.tap_inline_button(chat_id=chat["id"], message_id=duplicate["id"], row=0, column=0)
except ScenarioError as error:
    if error.code != "server_error" or not error.outcome_uncertain:
        raise AssertionError("Native backend failure must expose uncertain outcome")
else:
    raise AssertionError("Ambiguous message accepted")
if lab.events() != before:
    raise AssertionError("Ambiguous target caused a world mutation")
""")
    output = tmp_path / "run"
    outcome = run(
        manifest,
        output,
        profile=RuntimeProfile.load(Path(os.environ["GRAMLAB_RUNTIME_PROFILE"])),
        android_profile=RuntimeProfile.load(Path(profile)),
        android_apk=Path(apk),
    )
    recorded = json.loads((output / "result.json").read_text())
    assert outcome == "failed", recorded
    assert recorded["failure"] == "interaction_failed"
    assert recorded["processes"]["scenario"]["exit_code"] == 0
    assert len(recorded["interactions"]) == 2
    assert recorded["interactions"][1]["failure"] == "RuntimeError"
    assert recorded["android"]["input_failure"] in (
        "Inline message text is ambiguous in this chat",
        "Inline message and complete keyboard must have one accessible match",
    )
    callbacks = [event for event in recorded["events"] if event["type"] == "callback.created"]
    assert len(callbacks) == 1 and callbacks[0]["data"]["data"] == "confirm"
    assert len(recorded["captures"]) == 2
    assert (output / "report.html").read_text().count("data:image/png;base64,") == 2


def test_consumer_recovers_pending_callback_after_bot_crash_in_both_modes(tmp_path: Path):
    from test_runner_lifecycle import recovery_project

    profile = os.environ.get("GRAMLAB_ANDROID_RUNTIME_PROFILE")
    apk = os.environ.get("GRAMLAB_ANDROID_PROBE_APK")
    if profile is None or apk is None or not os.access("/dev/kvm", os.R_OK | os.W_OK):
        pytest.skip("Requires the provisioned Android profile, approved APK and KVM")
    manifest = recovery_project(tmp_path / "project")
    results = []
    for mode in ("simulation-only", "headless-android"):
        manifest.write_text(
            Path("examples/recovery/android.toml")
            .read_text()
            .replace('mode = "headless-android"', f'mode = "{mode}"')
        )
        output = tmp_path / mode
        outcome = run(
            manifest,
            output,
            profile=RuntimeProfile.load(Path(os.environ["GRAMLAB_RUNTIME_PROFILE"])),
            android_profile=RuntimeProfile.load(Path(profile)),
            android_apk=Path(apk),
        )
        recorded = json.loads((output / "result.json").read_text())
        assert outcome == "passed", recorded
        results.append(recorded)
    simulation, android = results
    assert simulation["world"] == android["world"]
    assert simulation["histories"] == android["histories"]
    assert simulation["lifecycle"] == android["lifecycle"]
    assert [event["operation"] for event in android["lifecycle"]] == ["stop_bot", "start_bot"]
    assert len(android["interactions"]) == 1 and android["interactions"][0]["native"]
    assert len([event for event in android["events"] if event["type"] == "callback.created"]) == 1
    assert android["processes"]["bot:recovery"]["stopped_by_scenario"]
    assert android["processes"]["bot:recovery#2"]["generation"] == 2
    assert [capture["label"] for capture in android["captures"]] == [
        "before-crash",
        "after-recovery",
    ]
    assert all(capture["rendered"] for capture in android["captures"])
    report = (tmp_path / "headless-android/report.html").read_text()
    assert report.count("data:image/png;base64,") == 2
