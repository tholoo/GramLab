"""An unrelated native edit preserves an already observed public rich target."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
from pathlib import Path
from typing import Any, cast

import pytest
from PIL import Image

from gramlab.runner import run
from gramlab.runtime import RuntimeProfile, Sandbox

TARGET = {
    "blocks": [
        {"type": "paragraph", "text": "Stable target / هدف ثابت"},
        {
            "type": "buttons",
            "buttons": [{"text": "Confirm / تأیید", "callback_data": "stable:confirm"}],
        },
    ]
}
CHANGED_TARGET = {
    "blocks": [
        {"type": "paragraph", "text": "Changed target / هدف تغییرکرده"},
        {
            "type": "buttons",
            "buttons": [{"text": "Changed / تغییر", "callback_data": "changed:confirm"}],
        },
    ]
}
UNRELATED_ALPHA = {"blocks": [{"type": "paragraph", "text": "Unrelated alpha / حالت الف"}]}
UNRELATED_BRAVO = {"blocks": [{"type": "paragraph", "text": "Unrelated bravo / حالت ب"}]}
SNAPSHOT: dict[str, Any] = {
    "schema": 1,
    "seed": 95,
    "now": 1700000000,
    "users": [
        {"id": 1, "is_bot": True, "first_name": "unrelated"},
        {"id": 2, "is_bot": False, "first_name": "Sara", "language_code": "fa"},
        {"id": 3, "is_bot": False, "first_name": "Controller"},
    ],
    "chats": [
        {"id": 1, "type": "private", "user_id": 2, "bot_id": 1},
        {"id": 2, "type": "private", "user_id": 3, "bot_id": 1},
    ],
}


def message(chat: int, identifier: int, sender: int, text: str) -> dict[str, Any]:
    return {
        "id": identifier,
        "chat_id": chat,
        "sender_id": sender,
        "date": 1700000000,
        "text": text,
    }


INITIAL_TARGET = {
    "id": 2,
    "chat_id": 1,
    "sender_id": 1,
    "date": 1700000000,
    "text": "",
    "rich_message": TARGET,
}
EDITED_TARGET = INITIAL_TARGET | {"edit_date": 1700000000, "rich_message": CHANGED_TARGET}
INITIAL_UNRELATED = {
    "id": 3,
    "chat_id": 1,
    "sender_id": 1,
    "date": 1700000000,
    "text": "",
    "rich_message": UNRELATED_ALPHA,
}
EDITED_UNRELATED = INITIAL_UNRELATED | {
    "edit_date": 1700000000,
    "rich_message": UNRELATED_BRAVO,
}


def project(directory: Path, *, mode: str) -> Path:
    directory.mkdir()
    (directory / "run.toml").write_text(
        f'schema = 1\nmode = "{mode}"\nseed = 95\nnow = 1700000000\n'
        f"timeout = {60 if mode == 'simulation-only' else 900}\n"
        '[scenario]\nentry = "scenario.py"\nfiles = ["scenario.py"]\n'
        '[bots.unrelated]\nentry = "bot.py"\nfiles = ["bot.py"]\n'
    )
    shutil.copy2("tests/unrelated_target_scenario.py", directory / "scenario.py")
    shutil.copy2("tests/fixtures/unrelated_target_bot.py", directory / "bot.py")
    return directory / "run.toml"


def install_native_supervisor(monkeypatch: pytest.MonkeyPatch) -> str:
    bootstrap = Path("tests/probes/unrelated_target_supervisor.py").read_bytes()
    digest = hashlib.sha256(bootstrap).hexdigest()
    original = Sandbox.supervise

    def instrumented(
        self: Sandbox, command: list[str], *, data: Path, timeout: float = 30, kvm: bool = False
    ) -> subprocess.CompletedProcess[str]:
        assert command == [self.profile.python, "-m", "gramlab._run"]
        (data / "unrelated_target_supervisor.py").write_bytes(bootstrap)
        return original(
            self,
            [self.profile.python, "/work/unrelated_target_supervisor.py"],
            data=data,
            timeout=timeout,
            kvm=kvm,
        )

    monkeypatch.setattr(Sandbox, "supervise", instrumented)
    return digest


def execute(
    directory: Path, *, mode: str, monkeypatch: pytest.MonkeyPatch | None = None
) -> tuple[dict[str, Any], Path]:
    arguments: dict[str, Any] = {}
    if mode == "headless-android":
        profile = os.environ.get("GRAMLAB_ANDROID_RUNTIME_PROFILE")
        apk = os.environ.get("GRAMLAB_ANDROID_PROBE_APK")
        if profile is None or apk is None or not os.access("/dev/kvm", os.R_OK | os.W_OK):
            pytest.skip("Requires the Android profile, reviewed rich-target APK and accessible KVM")
        assert monkeypatch is not None
        install_native_supervisor(monkeypatch)
        arguments = {
            "android_profile": RuntimeProfile.load(Path(profile)),
            "android_apk": Path(apk),
            "bridge_version": 4,
        }
    output = directory.parent / f"{mode}-run"
    outcome = run(
        project(directory, mode=mode),
        output,
        profile=RuntimeProfile.load(Path(os.environ["GRAMLAB_RUNTIME_PROFILE"])),
        **arguments,
    )
    recorded = json.loads((output / "result.json").read_text())
    assert outcome == "passed", recorded
    return cast(dict[str, Any], recorded), output


def process_json(recorded: dict[str, Any], process: str) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in recorded["processes"][process]["stdout"].splitlines()
        if line.strip()
    ]


def assert_token(value: Any) -> None:
    assert type(value) is str and re.fullmatch(r"[A-Za-z0-9_-]{1,128}", value)


def expected_target(observation: dict[str, Any]) -> dict[str, Any]:
    target = observation["targets"][0]
    assert observation == {
        "chat_id": 1,
        "message_id": 2,
        "message_revision": 7,
        "targets": [
            {
                "target_id": target["target_id"],
                "path": ["blocks", 1, "buttons", 0],
                "button": {"text": "Confirm / تأیید", "callback_data": "stable:confirm"},
                "label": "Confirm / تأیید",
            }
        ],
    }
    assert_token(target["target_id"])
    return {
        "target_id": target["target_id"],
        "chat_id": 1,
        "message_id": 2,
        "message_revision": 7,
        "path": ["blocks", 1, "buttons", 0],
        "button": {"text": "Confirm / تأیید", "callback_data": "stable:confirm"},
        "label": "Confirm / تأیید",
    }


def base_events() -> list[dict[str, Any]]:
    values = [
        ("user.created", SNAPSHOT["users"][0]),
        ("user.created", SNAPSHOT["users"][1]),
        ("user.created", SNAPSHOT["users"][2]),
        ("chat.created", SNAPSHOT["chats"][0]),
        ("chat.created", SNAPSHOT["chats"][1]),
        ("message.created", message(1, 1, 2, "publish stable target")),
        ("message.created", INITIAL_TARGET),
        ("message.created", INITIAL_UNRELATED),
        ("message.created", message(2, 1, 3, "edit unrelated")),
        ("message.edited", EDITED_UNRELATED),
        ("message.created", message(2, 2, 1, "unrelated edit acknowledged")),
    ]
    return [
        {"sequence": sequence, "type": kind, "data": data}
        for sequence, (kind, data) in enumerate(values, 1)
    ]


def assert_scenario(
    recorded: dict[str, Any], *, mode: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    scenario = process_json(recorded, "scenario")[-1]
    target = expected_target(scenario["observation"])
    callback = scenario["success"]["effect"]["callback"]
    assert_token(scenario["success"]["operation_id"])
    assert re.fullmatch(r"[0-9a-f-]{36}", callback["id"])
    assert re.fullmatch(r"[0-9a-f]{64}", callback["chat_instance"])
    assert callback == {
        "id": callback["id"],
        "user_id": 2,
        "chat_id": 1,
        "message": INITIAL_TARGET,
        "data": "stable:confirm",
        "chat_instance": callback["chat_instance"],
        "answer": None,
    }
    evidence: dict[str, Any] = {
        "mode": mode,
        "world_event_sequences": [12],
        "clipboard_observation": None,
    }
    if mode == "headless-android":
        evidence["native"] = scenario["success"]["evidence"]["native"]
    assert scenario["success"] == {
        "operation_id": scenario["success"]["operation_id"],
        "target": target,
        "status": "succeeded",
        "dispatch": "dispatched",
        "effect": {"kind": "callback", "callback": callback, "event_sequence": 12},
        "reason": None,
        "evidence": evidence,
    }
    assert scenario["original_target_id"] == target["target_id"]
    assert scenario["success_repeat"] == scenario["success"]
    events = base_events()
    assert scenario["before_success"] == {"snapshot": SNAPSHOT, "events": events}
    events.extend(
        [
            {
                "sequence": 12,
                "type": "callback.created",
                "data": {key: value for key, value in callback.items() if key != "answer"},
            },
            {
                "sequence": 13,
                "type": "callback.answered",
                "data": {
                    "id": callback["id"],
                    "user_id": 2,
                    "answer": {
                        "text": "Confirmed / تأیید شد",
                        "show_alert": False,
                        "cache_time": 0,
                    },
                },
            },
        ]
    )
    assert scenario["after_success"] == {"snapshot": SNAPSHOT, "events": events}
    related = expected_target(scenario["related_observation"])
    assert related["target_id"] != target["target_id"]
    events.extend(
        [
            {"sequence": 14, "type": "message.created", "data": message(2, 3, 3, "edit target")},
            {"sequence": 15, "type": "message.edited", "data": EDITED_TARGET},
            {
                "sequence": 16,
                "type": "message.created",
                "data": message(2, 4, 1, "target edit acknowledged"),
            },
        ]
    )
    empty_evidence: dict[str, Any] = {
        "mode": mode,
        "world_event_sequences": [],
        "clipboard_observation": None,
    }
    if mode == "headless-android":
        empty_evidence["native"] = {"observation": None, "effect": None, "captures": []}
    rejected = scenario["rejected"]
    assert_token(rejected["operation_id"])
    assert rejected == {
        "operation_id": rejected["operation_id"],
        "target": related,
        "status": "rejected_before_dispatch",
        "dispatch": "not_dispatched",
        "effect": None,
        "reason": {"code": "message_revision_changed"},
        "evidence": empty_evidence,
    }
    assert scenario["rejected_repeat"] == rejected
    assert (
        scenario["before_rejection"]
        == scenario["after_rejection"]
        == {
            "snapshot": SNAPSHOT,
            "events": events,
        }
    )
    rendered = [message(1, 1, 2, "publish stable target"), EDITED_TARGET, EDITED_UNRELATED]
    control = [
        message(2, 1, 3, "edit unrelated"),
        message(2, 2, 1, "unrelated edit acknowledged"),
        message(2, 3, 3, "edit target"),
        message(2, 4, 1, "target edit acknowledged"),
        message(2, 5, 3, "finish proof"),
    ]
    events.append({"sequence": 17, "type": "message.created", "data": control[-1]})
    assert scenario["initial_rendered"] == [
        message(1, 1, 2, "publish stable target"),
        INITIAL_TARGET,
        INITIAL_UNRELATED,
    ]
    assert scenario["rendered_history"] == rendered
    assert scenario["control_history"] == control
    assert scenario["events"] == recorded["events"] == events
    assert recorded["histories"] == {"1": rendered, "2": control}
    assert recorded["world"] == SNAPSHOT
    return scenario, callback


def test_public_target_survives_unrelated_real_bot_edit_in_simulation(
    tmp_path: Path, trace_runner: Any
) -> None:
    recorded, _ = execute(tmp_path / "project", mode="simulation-only")
    scenario, callback = assert_scenario(recorded, mode="simulation")
    bot = process_json(recorded, "bot:unrelated")
    assert [entry["event"] for entry in bot] == ["published", "finished"]
    assert bot[-1]["callbacks"] == [
        {
            "id": callback["id"],
            "from": SNAPSHOT["users"][1],
            "message": {
                "message_id": 2,
                "from": SNAPSHOT["users"][0],
                "chat": {"id": 2, "type": "private", "first_name": "Sara"},
                "date": 1700000000,
                "rich_message": TARGET,
            },
            "chat_instance": callback["chat_instance"],
            "data": "stable:confirm",
        }
    ]
    assert len([event for event in scenario["events"] if event["type"] == "callback.created"]) == 1


def test_supervisor_source_is_staged_as_the_only_native_entry_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    called: dict[str, Any] = {}

    def fake(
        self: Sandbox, command: list[str], *, data: Path, timeout: float = 30, kvm: bool = False
    ) -> subprocess.CompletedProcess[str]:
        del self
        called.update(command=command, data=data, timeout=timeout, kvm=kvm)
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(Sandbox, "supervise", fake)
    digest = install_native_supervisor(monkeypatch)
    data = tmp_path / "run"
    data.mkdir()
    profile = RuntimeProfile(bubblewrap="bwrap", python="python", store_paths=())
    Sandbox(profile).supervise(["python", "-m", "gramlab._run"], data=data, timeout=31, kvm=True)
    staged = data / "unrelated_target_supervisor.py"
    assert called == {
        "command": ["python", "/work/unrelated_target_supervisor.py"],
        "data": data,
        "timeout": 31,
        "kvm": True,
    }
    assert hashlib.sha256(staged.read_bytes()).hexdigest() == digest
    source = staged.read_text()
    assert '._wait_ui(["Unrelated bravo / حالت ب"])' in source
    assert "._open_chat(" not in source and "._capture(" not in source
    assert source.index("observation_complete") < source.index("ui_barrier_before_prepare")
    assert source.index("ui_barrier_before_prepare") < source.index("original_prepare(")
    assert source.index("prepare_complete") < source.index("dispatch_started")
    scenario = Path("tests/unrelated_target_scenario.py").read_text()
    unrelated = scenario.index('text="edit unrelated"')
    success = scenario.index("success = rich_lab.tap_rich_button")
    assert "rich_lab.rich_buttons" not in scenario[unrelated:success]
    assert "capture_chat" not in scenario[unrelated:success]


@pytest.mark.android
def test_native_target_survives_applied_unrelated_edit_without_lifetime_renewal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    recorded, output = execute(
        tmp_path / "project", mode="headless-android", monkeypatch=monkeypatch
    )
    scenario, callback = assert_scenario(recorded, mode="headless-android")
    barrier = json.loads((output / "unrelated-target-barrier.json").read_text())
    assert [event["kind"] for event in barrier["events"]] == [
        "observation_complete",
        "ui_barrier_before_prepare",
        "prepare_complete",
        "dispatch_started",
        "dispatch_complete",
    ]
    observed, ui, prepared, dispatched, complete = barrier["events"]
    assert (
        ui["target_id"]
        == prepared["target_id"]
        == dispatched["target_id"]
        == scenario["original_target_id"]
    )
    assert ui["client_nonce"] == prepared["client_nonce"] == dispatched["client_nonce"]
    assert observed["client_nonce"] == ui["client_nonce"]
    assert observed["pid"] == prepared["pid"] == dispatched["pid"]
    assert observed["geometry"] == prepared["geometry"] == dispatched["geometry"]
    assert observed["persona"] == 2 and observed["chat_id"] == 1
    assert observed["message_id"] == 2 and observed["revision"] == 7
    assert observed["world_id"] == recorded["run_id"]
    assert prepared["guest_calls"] == dispatched["guest_calls"]
    assert complete == {
        "kind": "dispatch_complete",
        "status": "succeeded",
        "dispatch": "dispatched",
    }
    assert ui["persona"] == 2 and ui["chat_id"] == 1 and ui["accounts"] == "Accounts: 0"
    xml = (output / "unrelated-target-ui.xml").read_text()
    png = output / "unrelated-target-ui.png"
    assert "Unrelated bravo / حالت ب" in xml
    assert hashlib.sha256(xml.encode()).hexdigest() == ui["xml_sha256"]
    assert hashlib.sha256(png.read_bytes()).hexdigest() == ui["png_sha256"]
    with Image.open(png) as image:
        assert image.format == "PNG" and image.size == (320, 640)
        image.verify()
    assert recorded["android"]["network"] == {"ipv4": 1, "ipv6": 1}
    assert recorded["android"]["filesystem"] == {
        "world_visible": False,
        "bot_visible": False,
        "scenario_visible": False,
        "private_avd_visible": True,
        "same_pid_namespace": False,
        "same_network": True,
    }
    native = scenario["success"]["evidence"]["native"]
    operation = scenario["success"]["operation_id"]
    assert native["captures"] == [f"rich-buttons/{operation}/before.png"]
    observation = json.loads((output / native["observation"]).read_text())
    effect = json.loads((output / native["effect"]).read_text())
    assert observation["world_id"] == recorded["run_id"]
    assert [observation[key] for key in ("user_id", "chat_id", "message_id", "revision")] == [
        2,
        1,
        2,
        7,
    ]
    assert observation["client_nonce"] == ui["client_nonce"]
    assert observation["pid"] == prepared["pid"]
    selected = next(
        item for item in observation["targets"] if item["path"] == ["blocks", 1, "buttons", 0]
    )
    assert {key: selected[key] for key in ("local_bounds", "origin", "screen_bounds")} == prepared[
        "geometry"
    ]
    assert effect["operation_id"] == operation and effect["state"] == "complete"
    assert effect["action"] == "callback" and effect["touch"]["up_uptime_ms"] is not None
    assert len(effect["requests"]) == 1 and effect["requests"][0]["callback_id"] == callback["id"]
    database = sqlite3.connect((output / "world/world.sqlite3").as_uri() + "?mode=ro", uri=True)
    try:
        row = database.execute(
            "SELECT user_id,bot_id,body,answer FROM callbacks WHERE id=?", (callback["id"],)
        ).fetchone()
    finally:
        database.close()
    assert row[:2] == (2, 1)
    assert json.loads(row[2]) == {key: value for key, value in callback.items() if key != "answer"}
    assert json.loads(row[3]) == {
        "text": "Confirmed / تأیید شد",
        "show_alert": False,
        "cache_time": 0,
    }
