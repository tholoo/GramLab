"""Public rich-message buttons use real callbacks and conservative native identity."""

import json
import os
import re
import shutil
from pathlib import Path
from typing import Any

import pytest

from gramlab.runner import run
from gramlab.runtime import RuntimeProfile


def project(directory: Path) -> Path:
    directory.mkdir()
    for name in ("run.toml", "bot.py", "scenario.py"):
        shutil.copy2(Path("examples/rich_inline") / name, directory / name)
    return directory / "run.toml"


def verify(result: dict[str, Any], *, native: bool) -> None:
    initial = {
        "id": 2,
        "chat_id": 1,
        "sender_id": 1,
        "date": 1700000000,
        "text": "",
        "rich_message": {
            "blocks": [
                {"type": "heading", "size": 2, "text": "Rich choice"},
                {
                    "type": "table",
                    "cells": [
                        [
                            {"text": "زبان", "align": "left", "valign": "middle"},
                            {"text": "English", "align": "left", "valign": "middle"},
                        ]
                    ],
                    "is_bordered": True,
                },
                {
                    "type": "paragraph",
                    "text": ["Choose ", {"type": "bold", "text": "an option"}, " — تأیید"],
                },
            ]
        },
        "reply_markup": {
            "inline_keyboard": [
                [
                    {"text": "Cancel", "callback_data": "cancel"},
                    {"text": "Confirm", "callback_data": "wrong"},
                ],
                [{"text": "Confirm", "callback_data": "confirm"}],
            ]
        },
    }
    edited = {key: value for key, value in initial.items() if key != "reply_markup"}
    edited.update(
        edit_date=1700000000,
        rich_message={
            "blocks": [{"type": "paragraph", "text": "Selected: confirm ✓ — انجام شد"}],
            "is_rtl": True,
        },
    )
    assert result["outcome"] == "passed", result
    assert result["histories"] == {
        "1": [
            {"id": 1, "chat_id": 1, "sender_id": 2, "date": 1700000000, "text": "سلام hello"},
            edited,
        ]
    }
    assert [capture["history"][1] for capture in result["captures"]] == [initial, edited]
    assert len(result["interactions"]) == 1
    interaction = result["interactions"][0]
    assert interaction["native"] is native
    assert interaction["row"] == 1 and interaction["column"] == 0
    callback = interaction["callback"]
    assert callback["message"] == initial and callback["data"] == "confirm"
    assert callback["user_id"] == 2 and callback["chat_id"] == 1
    events = [event for event in result["events"] if event["type"] == "callback.created"]
    assert len(events) == 1 and events[0]["data"]["message"] == initial
    answers = [event for event in result["events"] if event["type"] == "callback.answered"]
    assert len(answers) == 1
    assert answers[0]["data"] == {
        "id": callback["id"],
        "user_id": 2,
        "answer": {"text": "Done", "show_alert": False, "cache_time": 0},
    }
    assert re.fullmatch(r"[0-9a-f]{64}", callback["chat_instance"])
    if native:
        assert interaction["android"]["target"]["text"] == "Confirm"
        assert interaction["android"]["target"]["class"] == "android.widget.Button"


def execute(manifest: Path, output: Path, *, native: bool) -> dict[str, Any]:
    source = manifest.read_text()
    if native:
        source = source.replace('mode = "simulation-only"', 'mode = "headless-android"').replace(
            "timeout = 15", "timeout = 300"
        )
    manifest.write_text(source)
    run(
        manifest,
        output,
        profile=RuntimeProfile.load(Path(os.environ["GRAMLAB_RUNTIME_PROFILE"])),
        android_profile=RuntimeProfile.load(Path(os.environ["GRAMLAB_ANDROID_RUNTIME_PROFILE"]))
        if native
        else None,
        android_apk=Path(os.environ["GRAMLAB_ANDROID_PROBE_APK"]) if native else None,
    )
    recorded: dict[str, Any] = json.loads((output / "result.json").read_text())
    return recorded


def test_rich_inline_real_bot_callback_and_edit(tmp_path: Path) -> None:
    manifest = project(tmp_path / "project")
    verify(execute(manifest, tmp_path / "run", native=False), native=False)


@pytest.mark.android
def test_rich_inline_native_callback_matches_simulation(tmp_path: Path) -> None:
    manifest = project(tmp_path / "project")
    simulation = execute(manifest, tmp_path / "simulation", native=False)
    verify(simulation, native=False)
    android = execute(manifest, tmp_path / "android", native=True)
    verify(android, native=True)
    for key in ("world", "histories"):
        assert simulation[key] == android[key]
    normalized_events = []
    for recorded in (simulation, android):
        events = json.loads(json.dumps(recorded["events"]))
        for event in events:
            if event["type"].startswith("callback."):
                event["data"]["id"] = "<callback>"
                if "chat_instance" in event["data"]:
                    event["data"]["chat_instance"] = "<world-scoped-chat>"
        normalized_events.append(events)
    assert normalized_events[0] == normalized_events[1]
    for capture in android["captures"]:
        assert "Accounts: 0" in capture["android"]["accounts"]
        assert (
            (tmp_path / "android/captures" / (capture["label"] + ".png"))
            .read_bytes()
            .startswith(b"\x89PNG\r\n\x1a\n")
        )
    assert (tmp_path / "android/report.html").read_text().count("data:image/png;base64,") == 2


@pytest.mark.android
def test_offscreen_rich_duplicate_rejects_before_input(tmp_path: Path) -> None:
    manifest = project(tmp_path / "project")
    # The second response changes rich styling but keeps the accessible content identical.
    bot = manifest.parent / "bot.py"
    bot.write_text(
        bot.read_text().replace(
            '"type": "bold", "text": "an option"',
            '"type": "italic" if message["text"] == "Second duplicate" else "bold", '
            '"text": "an option"',
        )
    )
    scenario = manifest.parent / "scenario.py"
    with scenario.open("a") as script:
        script.write("""
from gramlab.scenario import ScenarioError
lab.send_message(chat_id=chat["id"], sender_id=user["id"], text="First duplicate")
deadline = time.monotonic() + 10
while len(lab.history(chat["id"])) != 4:
    expect(time.monotonic() < deadline, "First duplicate missing")
    time.sleep(0.05)
for index in range(30):
    lab.send_message(chat_id=chat["id"], sender_id=lab.bots()["inline"], text=f"Spacer {index}")
lab.send_message(chat_id=chat["id"], sender_id=user["id"], text="Second duplicate")
deadline = time.monotonic() + 10
while len(lab.history(chat["id"])) != 36:
    expect(time.monotonic() < deadline, "Second duplicate missing")
    time.sleep(0.05)
duplicate = lab.history(chat["id"])[-1]
lab.capture_chat(chat_id=chat["id"], label="before-ambiguous", contains=["Rich choice"])
before = lab.events()
try:
    lab.tap_inline_button(chat_id=chat["id"], message_id=duplicate["id"], row=1, column=0)
except ScenarioError as error:
    expect(error.code == "server_error" and error.outcome_uncertain, "Wrong native failure")
else:
    raise AssertionError("Indistinguishable off-screen rich message accepted")
expect(lab.events() == before, "Ambiguous input caused a world mutation")
""")
    result = execute(manifest, tmp_path / "android", native=True)
    assert result["outcome"] == "failed" and result["failure"] == "interaction_failed", result
    assert result["processes"]["scenario"]["exit_code"] == 0
    assert result["android"]["input_failure"] == "Inline message text is ambiguous in this chat"
    assert len(result["interactions"]) == 2
    assert result["interactions"][1]["failure"] == "RuntimeError"
    callbacks = [event for event in result["events"] if event["type"] == "callback.created"]
    assert len(callbacks) == 1 and callbacks[0]["data"]["data"] == "confirm"
    history = result["histories"]["1"]
    assert history[3]["rich_message"]["blocks"][-1]["text"][1]["type"] == "bold"
    assert history[-1]["rich_message"]["blocks"][-1]["text"][1]["type"] == "italic"
    assert len(result["captures"]) == 3
    assert result["captures"][-1]["android"]["ui"].count("Heading 2, Rich choice") == 1
    assert (tmp_path / "android/report.html").read_text().count("data:image/png;base64,") == 3
