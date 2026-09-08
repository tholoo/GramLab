"""An unrelated native edit preserves an already observed public rich target."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import runpy
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


def api_message(value: dict[str, Any]) -> dict[str, Any]:
    chat = SNAPSHOT["chats"][value["chat_id"] - 1]
    peer = SNAPSHOT["users"][chat["user_id"] - 1]
    result = {
        "message_id": value["id"],
        "from": SNAPSHOT["users"][value["sender_id"] - 1],
        "chat": {"id": peer["id"], "type": "private", "first_name": peer["first_name"]},
        "date": value["date"],
    }
    field = "rich_message" if "rich_message" in value else "text"
    result[field] = value[field]
    if "edit_date" in value:
        result["edit_date"] = value["edit_date"]
    return result


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


def api_write(method: str, parameters: dict[str, Any], result: Any) -> dict[str, Any]:
    return {
        "method": method,
        "parameters": parameters,
        "status": 200,
        "body": {"ok": True, "result": result},
    }


def assert_bot_exchange(
    api: list[dict[str, Any]], updates: list[dict[str, Any]], writes: list[list[dict[str, Any]]]
) -> None:
    """Preserve causal phases while allowing only empty long-poll races."""

    def poll(parameters: dict[str, int], batch: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "method": "getUpdates",
            "parameters": parameters,
            "status": 200,
            "body": {"ok": True, "result": batch},
        }

    assert api[0] == poll({"timeout": 10}, [updates[0]])
    position = 1

    def consume(expected: list[dict[str, Any]]) -> None:
        nonlocal position
        assert api[position : position + len(expected)] == expected
        position += len(expected)

    consume(writes[0])
    offset = 2
    for update, phase_writes in zip(updates[1:], writes[1:], strict=True):
        while True:
            assert position < len(api)
            entry = api[position]
            position += 1
            batch = entry.get("body", {}).get("result")
            assert type(batch) is list
            assert entry == poll({"offset": offset, "timeout": 10}, batch)
            assert batch in ([], [update])
            if batch:
                offset = update["update_id"] + 1
                consume(phase_writes)
                break
    consume([poll({"offset": offset}, [])])
    assert position == len(api)


def assert_complete_bot(recorded: dict[str, Any], callback: dict[str, Any]) -> None:
    bot = process_json(recorded, "bot:unrelated")
    assert len(bot) == 2
    assert bot[0] == {
        "event": "published",
        "target": api_message(INITIAL_TARGET),
        "unrelated": api_message(INITIAL_UNRELATED),
    }
    api_callback = {
        "id": callback["id"],
        "from": SNAPSHOT["users"][1],
        "message": api_message(INITIAL_TARGET),
        "chat_instance": callback["chat_instance"],
        "data": "stable:confirm",
    }
    assert bot[1].keys() == {"event", "callbacks", "api"}
    assert bot[1]["event"] == "finished" and bot[1]["callbacks"] == [api_callback]
    updates = [
        {"update_id": 1, "message": api_message(message(1, 1, 2, "publish stable target"))},
        {"update_id": 2, "message": api_message(message(2, 1, 3, "edit unrelated"))},
        {"update_id": 3, "callback_query": api_callback},
        {"update_id": 4, "message": api_message(message(2, 3, 3, "edit target"))},
        {"update_id": 5, "message": api_message(message(2, 5, 3, "finish proof"))},
    ]
    writes = [
        [
            api_write(
                "sendRichMessage",
                {"chat_id": 2, "rich_message": TARGET | {"skip_entity_detection": True}},
                api_message(INITIAL_TARGET),
            ),
            api_write(
                "sendRichMessage",
                {
                    "chat_id": 2,
                    "rich_message": UNRELATED_ALPHA | {"skip_entity_detection": True},
                },
                api_message(INITIAL_UNRELATED),
            ),
        ],
        [
            api_write(
                "editMessageText",
                {
                    "chat_id": 2,
                    "message_id": 3,
                    "rich_message": UNRELATED_BRAVO | {"skip_entity_detection": True},
                },
                api_message(EDITED_UNRELATED),
            ),
            api_write(
                "sendMessage",
                {"chat_id": 3, "text": "unrelated edit acknowledged"},
                api_message(message(2, 2, 1, "unrelated edit acknowledged")),
            ),
        ],
        [
            api_write(
                "answerCallbackQuery",
                {"callback_query_id": callback["id"], "text": "Confirmed / تأیید شد"},
                True,
            )
        ],
        [
            api_write(
                "editMessageText",
                {
                    "chat_id": 2,
                    "message_id": 2,
                    "rich_message": CHANGED_TARGET | {"skip_entity_detection": True},
                },
                api_message(EDITED_TARGET),
            ),
            api_write(
                "sendMessage",
                {"chat_id": 3, "text": "target edit acknowledged"},
                api_message(message(2, 4, 1, "target edit acknowledged")),
            ),
        ],
        [],
    ]
    assert_bot_exchange(bot[1]["api"], updates, writes)


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


def assert_counter(value: Any, *, minimum: int = 0) -> None:
    assert type(value) is int and minimum <= value <= 2**63 - 1


def native_file(root: Path, relative: str, operation: str) -> Path:
    path = Path(relative)
    assert not path.is_absolute() and path.parts[:2] == ("rich-buttons", operation)
    assert len(path.parts) == 3 and path.name not in (".", "..")
    resolved = root / path
    assert not any((root / Path(*path.parts[:index])).is_symlink() for index in range(1, 4))
    assert resolved.is_file()
    return resolved


def read_native_json(root: Path, relative: str, operation: str, kind: str) -> dict[str, Any]:
    path = native_file(root, relative, operation)
    match = re.fullmatch(rf"{kind}-([0-9]+)-([0-9a-f]{{16}})\.json", path.name)
    assert match is not None and path.stat().st_size <= 1024 * 1024
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest()[:16] == match[2]

    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        assert len({key for key, _ in pairs}) == len(pairs)
        return dict(pairs)

    record = json.loads(raw, object_pairs_hook=unique)
    assert type(record) is dict and record["generation"] == int(match[1])
    return cast(dict[str, Any], record)


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
    assert recorded["outcome"] == "passed" and recorded["failure"] is None
    scenario = process_json(recorded, "scenario")[-1]
    assert scenario.keys() == {
        "initial_rendered",
        "observation",
        "original_target_id",
        "success",
        "success_repeat",
        "before_success",
        "after_success",
        "related_observation",
        "rejected",
        "rejected_repeat",
        "before_rejection",
        "after_rejection",
        "rendered_history",
        "control_history",
        "events",
    }
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
    assert_complete_bot(recorded, callback)
    return scenario, callback


def test_public_target_survives_unrelated_real_bot_edit_in_simulation(
    tmp_path: Path, trace_runner: Any
) -> None:
    recorded, _ = execute(tmp_path / "project", mode="simulation-only")
    scenario, callback = assert_scenario(recorded, mode="simulation")
    assert len([event for event in scenario["events"] if event["type"] == "callback.created"]) == 1
    assert callback["answer"] is None


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
    assert "screencap" not in source
    assert "hashlib.sha256(Path(__file__).read_bytes()).hexdigest()" in source
    assert 'arguments[:3] == ("shell", "input", "tap")' in source
    accounts = source.index('._adb("shell", "dumpsys", "account")')
    observed = source.index("observation_complete")
    barrier = source.index("ui_barrier_before_prepare")
    persisted = source.index("persist(self.android.secrets)", barrier)
    prepared = source.index("original_prepare(")
    assert accounts < observed < barrier < persisted < prepared
    assert source.index("prepare_complete") < source.index("dispatch_started")
    fresh = source[source.index("def fresh(") : source.index("def counted_adb(")]
    assert "error.__traceback__" in fresh and "original_fresh(self, state)" in fresh
    assert all(
        value not in fresh for value in ("._adb(", "._read(", "World.open(", "sleep(", "time.")
    )
    scenario = Path("tests/unrelated_target_scenario.py").read_text()
    unrelated = scenario.index('text="edit unrelated"')
    success = scenario.index("success = rich_lab.tap_rich_button")
    assert "rich_lab.rich_buttons" not in scenario[unrelated:success]
    assert "capture_chat" not in scenario[unrelated:success]
    failed = scenario.index('"event": "original_target_failed"')
    retained = scenario.index('"receipt": success')
    raised = scenario.index("raise RuntimeError", success)
    repeated = scenario.index("success_repeat = rich_lab.tap_rich_button")
    callback_wait = scenario.index('"callback answer"')
    assert success < failed < retained < raised < repeated < callback_wait


def test_fresh_failure_retains_original_frame_without_another_guest_call(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = Path(__file__).resolve().parent / "probes/unrelated_target_supervisor.py"
    monkeypatch.chdir(tmp_path)
    namespace = runpy.run_path(source.as_posix())
    failure = ValueError("original freshness failure")
    secret = "gramlab-client_" + "q" * 43
    calls = 0

    def failing_fresh(self: Any, state: dict[str, Any]) -> dict[str, Any]:
        nonlocal calls
        del self
        calls += 1
        sample: dict[str, Any] = {
            "generation": 4,
            "drawn_uptime_ms": 105399,
            "targets": [{"path": ["blocks", 1], "label": secret}],
        }
        pid, now = 2390, 110401
        assert state["pid"] == pid and now - sample["drawn_uptime_ms"] > 5000
        raise failure

    class FakeAndroid:
        def __init__(self) -> None:
            self.secrets = [secret]

    class FakeHost:
        android = FakeAndroid()

    fresh = namespace["fresh"]
    fresh.__globals__["original_fresh"] = failing_fresh
    state: dict[str, Any] = {
        "arm": {"operation_id": "d" * 32, "chat_id": 1, "message_id": 2},
        "target": {"path": ["blocks", 1], "label": secret},
        "pid": 2390,
    }
    with pytest.raises(ValueError) as caught:
        fresh(FakeHost(), state)
    assert caught.value is failure and calls == 1
    retained = Path("unrelated-target-barrier.json").read_bytes()
    assert len(retained) <= 128 * 1024 and secret.encode() not in retained
    barrier = json.loads(retained)
    assert barrier["bootstrap_sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert [event["kind"] for event in barrier["events"]] == ["fresh_failed"]
    event = barrier["events"][0]
    assert event["operation_id"] == "d" * 32 and event["exception_class"] == "ValueError"
    assert event["frame_present"] is True and event["missing_locals"] == []
    assert event["locals"] == {
        "pid": 2390,
        "now": 110401,
        "sample": {
            "generation": 4,
            "drawn_uptime_ms": 105399,
            "targets": [{"path": ["blocks", 1], "label": "[REDACTED]"}],
        },
    }
    traceback = caught.value.__traceback__
    while traceback is not None and traceback.tb_frame.f_code is not failing_fresh.__code__:
        traceback = traceback.tb_next
    assert traceback is not None and event["line"] == traceback.tb_lineno
    assert event["source"] == {
        "file": Path(failing_fresh.__code__.co_filename).name,
        "sha256": hashlib.sha256(Path(failing_fresh.__code__.co_filename).read_bytes()).hexdigest(),
    }
    assert event["state"]["target"]["label"] == "[REDACTED]"


@pytest.mark.android
def test_native_target_survives_applied_unrelated_edit_without_lifetime_renewal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    recorded, output = execute(
        tmp_path / "project", mode="headless-android", monkeypatch=monkeypatch
    )
    scenario, callback = assert_scenario(recorded, mode="headless-android")
    barrier = json.loads((output / "unrelated-target-barrier.json").read_text())
    assert barrier.keys() == {"schema", "bootstrap_sha256", "events"}
    assert barrier["schema"] == 1 and type(barrier["schema"]) is int
    assert (
        barrier["bootstrap_sha256"]
        == hashlib.sha256(
            Path("tests/probes/unrelated_target_supervisor.py").read_bytes()
        ).hexdigest()
    )
    assert [event["kind"] for event in barrier["events"]] == [
        "observation_complete",
        "ui_barrier_before_prepare",
        "prepare_complete",
        "dispatch_started",
        "dispatch_complete",
    ]
    observed, ui, prepared, dispatched, complete = barrier["events"]
    assert observed.keys() == {
        "kind",
        "world_id",
        "persona",
        "chat_id",
        "message_id",
        "revision",
        "activation_nonce",
        "client_nonce",
        "pid",
        "generation",
        "drawn_uptime_ms",
        "geometry",
        "accounts",
        "guest_calls",
    }
    assert ui.keys() == {
        "kind",
        "persona",
        "chat_id",
        "target_id",
        "world_id",
        "client_nonce",
        "pid",
        "generation",
        "xml_sha256",
        "xml_bytes",
        "guest_calls",
    }
    prepared_fields = {
        "kind",
        "target_id",
        "world_id",
        "persona",
        "chat_id",
        "message_id",
        "revision",
        "activation_nonce",
        "client_nonce",
        "pid",
        "geometry",
        "observation_generation",
        "guest_calls",
    }
    assert prepared.keys() == prepared_fields | {
        "drawn_uptime_ms",
        "ui_xml_sha256",
        "before_png",
        "before_png_sha256",
        "before_png_bytes",
    }
    assert dispatched.keys() == prepared_fields
    assert (
        ui["target_id"]
        == prepared["target_id"]
        == dispatched["target_id"]
        == scenario["original_target_id"]
    )
    assert ui["client_nonce"] == prepared["client_nonce"] == dispatched["client_nonce"]
    assert observed["client_nonce"] == ui["client_nonce"]
    assert_token(observed["activation_nonce"])
    assert_token(observed["client_nonce"])
    assert (
        observed["activation_nonce"]
        == prepared["activation_nonce"]
        == dispatched["activation_nonce"]
    )
    assert observed["pid"] == prepared["pid"] == dispatched["pid"]
    assert observed["geometry"] == prepared["geometry"] == dispatched["geometry"]
    assert observed["persona"] == 2 and observed["chat_id"] == 1
    assert observed["message_id"] == 2 and observed["revision"] == 7
    assert (
        observed["world_id"]
        == ui["world_id"]
        == prepared["world_id"]
        == dispatched["world_id"]
        == recorded["run_id"]
    )
    assert [prepared[key] for key in ("persona", "chat_id", "message_id", "revision")] == [
        2,
        1,
        2,
        7,
    ]
    assert [dispatched[key] for key in ("persona", "chat_id", "message_id", "revision")] == [
        2,
        1,
        2,
        7,
    ]
    assert_counter(observed["pid"], minimum=1)
    assert_counter(observed["generation"], minimum=1)
    assert_counter(observed["drawn_uptime_ms"], minimum=1)
    assert ui["generation"] == observed["generation"]
    assert_counter(prepared["observation_generation"], minimum=observed["generation"])
    assert_counter(dispatched["observation_generation"], minimum=observed["generation"])
    assert dispatched["observation_generation"] <= prepared["observation_generation"]
    assert_counter(prepared["drawn_uptime_ms"], minimum=observed["drawn_uptime_ms"])
    assert prepared["guest_calls"] == dispatched["guest_calls"]
    assert_counter(prepared["guest_calls"], minimum=ui["guest_calls"])
    assert prepared["ui_xml_sha256"] == ui["xml_sha256"]
    left, top, right, bottom = prepared["geometry"]["screen_bounds"]
    tap = {
        "guest_call": complete["input_taps"][0]["guest_call"],
        "arguments": [
            "shell",
            "input",
            "tap",
            str((left + right) / 2),
            str((top + bottom) / 2),
        ],
    }
    assert complete == {
        "kind": "dispatch_complete",
        "status": "succeeded",
        "dispatch": "dispatched",
        "input_taps": [tap],
    }
    assert_counter(tap["guest_call"], minimum=dispatched["guest_calls"] + 1)
    assert ui["persona"] == 2 and ui["chat_id"] == 1
    assert observed["accounts"] == "Accounts: 0"
    xml = (output / "unrelated-target-ui.xml").read_text()
    assert "Unrelated bravo / حالت ب" in xml
    assert hashlib.sha256(xml.encode()).hexdigest() == ui["xml_sha256"]
    assert len(xml.encode()) == ui["xml_bytes"]
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
    assert native.keys() == {"observation", "effect", "captures"}
    assert native["captures"] == [f"rich-buttons/{operation}/before.png"]
    observation = read_native_json(output, native["observation"], operation, "observation")
    effect = read_native_json(output, native["effect"], operation, "effect")
    common = {
        "schema",
        "nonce",
        "client_nonce",
        "world_id",
        "user_id",
        "chat_id",
        "message_id",
        "revision",
    }
    assert observation.keys() == common | {
        "pid",
        "generation",
        "drawn_uptime_ms",
        "available",
        "reason",
        "targets",
    }
    assert observation["schema"] == 1 and type(observation["schema"]) is int
    assert observation["world_id"] == recorded["run_id"]
    assert [observation[key] for key in ("user_id", "chat_id", "message_id", "revision")] == [
        2,
        1,
        2,
        7,
    ]
    for key in ("user_id", "chat_id", "message_id", "revision", "pid"):
        assert_counter(observation[key], minimum=1)
    assert_token(observation["nonce"])
    assert_token(observation["client_nonce"])
    assert observation["nonce"] == observed["activation_nonce"]
    assert observation["client_nonce"] == ui["client_nonce"]
    assert observation["pid"] == prepared["pid"]
    assert_counter(observation["generation"], minimum=observed["generation"])
    assert_counter(observation["drawn_uptime_ms"], minimum=observed["drawn_uptime_ms"])
    assert observation["generation"] <= prepared["observation_generation"]
    assert observation["available"] is True and observation["reason"] is None
    assert type(observation["targets"]) is list and len(observation["targets"]) == 1
    selected = observation["targets"][0]
    assert selected.keys() == {
        "path",
        "button",
        "label",
        "available",
        "reason",
        "local_bounds",
        "origin",
        "screen_bounds",
    }
    assert {key: selected[key] for key in ("path", "button", "label")} == {
        "path": ["blocks", 1, "buttons", 0],
        "button": {"text": "Confirm / تأیید", "callback_data": "stable:confirm"},
        "label": "Confirm / تأیید",
    }
    assert selected["available"] is True and selected["reason"] is None
    assert {key: selected[key] for key in ("local_bounds", "origin", "screen_bounds")} == prepared[
        "geometry"
    ]
    for field, size in (("local_bounds", 4), ("origin", 2), ("screen_bounds", 4)):
        assert type(selected[field]) is list and len(selected[field]) == size
        assert all(
            type(number) in (int, float) and math.isfinite(number) and abs(number) <= 1_000_000
            for number in selected[field]
        )
    assert 0 <= left < right <= 320 and 0 <= top < bottom <= 640
    assert effect.keys() == common | {
        "operation_id",
        "path",
        "generation",
        "uptime_ms",
        "state",
        "reason",
        "touch",
        "action",
        "requests",
        "clipboard",
    }
    assert {key: effect[key] for key in common} == {key: observation[key] for key in common}
    assert effect["operation_id"] == operation
    assert effect["path"] == ["blocks", 1, "buttons", 0]
    assert_counter(effect["generation"], minimum=observation["generation"])
    assert_counter(effect["uptime_ms"], minimum=observation["drawn_uptime_ms"])
    assert effect["state"] == "complete" and effect["reason"] is None
    assert effect["action"] == "callback" and effect["clipboard"] is None
    touch = effect["touch"]
    assert touch.keys() == {"down_uptime_ms", "up_uptime_ms", "path"}
    assert touch["path"] == effect["path"]
    assert_counter(touch["down_uptime_ms"], minimum=observation["drawn_uptime_ms"])
    assert_counter(touch["up_uptime_ms"], minimum=touch["down_uptime_ms"])
    assert touch["up_uptime_ms"] <= effect["uptime_ms"]
    assert len(effect["requests"]) == 1
    request = effect["requests"][0]
    assert request.keys() == {
        "native_request_token",
        "request_id",
        "callback_id",
        "message_revision",
    }
    assert_counter(request["native_request_token"], minimum=1)
    assert_token(request["request_id"])
    assert request["callback_id"] == callback["id"] and request["message_revision"] == 7
    capture = native_file(output, native["captures"][0], operation)
    capture_bytes = capture.read_bytes()
    assert prepared["before_png"] == native["captures"][0]
    assert prepared["before_png_sha256"] == hashlib.sha256(capture_bytes).hexdigest()
    assert prepared["before_png_bytes"] == len(capture_bytes)
    with Image.open(capture) as image:
        assert image.format == "PNG" and image.size == (320, 640)
        image.verify()
    database = sqlite3.connect((output / "world/world.sqlite3").as_uri() + "?mode=ro", uri=True)
    try:
        rows = database.execute(
            "SELECT user_id,bot_id,request_id,request_body,body,answer FROM callbacks WHERE id=?",
            (callback["id"],),
        ).fetchall()
    finally:
        database.close()
    assert len(rows) == 1 and rows[0][:3] == (2, 1, request["request_id"])
    assert json.loads(rows[0][3]) == {
        "chat_id": 1,
        "data": "stable:confirm",
        "message_id": 2,
    }
    assert json.loads(rows[0][4]) == {
        key: value for key, value in callback.items() if key != "answer"
    }
    assert json.loads(rows[0][5]) == {
        "text": "Confirmed / تأیید شد",
        "show_alert": False,
        "cache_time": 0,
    }
