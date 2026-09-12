"""Public residual rich-button acceptance at contained and original-client seams."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import runpy
import shutil
import subprocess
import unicodedata
from pathlib import Path
from typing import Any, cast

import pytest
from PIL import Image

from gramlab.runner import run
from gramlab.runtime import RuntimeProfile, Sandbox

FILLERS = [
    {
        "type": "paragraph",
        "text": f"فاصلهٔ مستقل {index} / spacer {index}"
        + ("\ngauge line one\ngauge line two\ngauge line three" if index == 5 else ""),
    }
    for index in range(1, 16)
]
RICH_MESSAGE = {
    "blocks": [
        {"type": "paragraph", "text": "فارسی از ابتدای ردیف آغاز می‌شود / RTL starts here"},
        *FILLERS[:3],
        {
            "type": "buttons",
            "buttons": [
                {
                    "text": "لبهٔ نیمه‌پیدا / clipped edge",
                    "callback_data": "must:not-dispatch",
                }
            ],
        },
        *FILLERS[4:],
        {
            "type": "buttons",
            "buttons": [
                {"text": "تأیید راست‌به‌چپ / RTL confirm", "callback_data": "rtl:confirm"},
                {
                    "text": "کپی مستقل / Copy",
                    "copy_text": {"text": "متن کپی‌شده / copied text"},
                },
            ],
        },
        {
            "type": "paragraph",
            "text": [
                "کنترل تو در تو: ",
                {
                    "type": "bold",
                    "text": {
                        "type": "button",
                        "button": {
                            "text": "پاسخ گم‌شده / Lost reply",
                            "callback_data": "lost:reply",
                        },
                    },
                },
            ],
        },
        {
            "type": "details",
            "summary": "جزئیات بسته / closed details",
            "blocks": [{"type": "paragraph", "text": "No control in this closed body"}],
        },
    ]
}
BOT_USER = {"id": 1, "is_bot": True, "first_name": "residual"}
USER = {"id": 2, "is_bot": False, "first_name": "Sara", "language_code": "fa"}
CHAT = {"id": 1, "type": "private", "user_id": 2, "bot_id": 1}
SNAPSHOT = {
    "schema": 1,
    "seed": 115,
    "now": 1700000000,
    "users": [BOT_USER, USER],
    "chats": [CHAT],
}


def message(identifier: int, sender: int, *, text: str = "") -> dict[str, Any]:
    return {
        "id": identifier,
        "chat_id": 1,
        "sender_id": sender,
        "date": 1700000000,
        "text": text,
    }


PUBLISH_REQUEST = message(1, 2, text="publish residual controls")
PUBLISHED = message(2, 1) | {"rich_message": RICH_MESSAGE}
FINISH_REQUEST = message(3, 2, text="finish residual controls")
TARGET_SPECS: list[tuple[list[str | int], dict[str, Any], str]] = [
    (
        ["blocks", 4, "buttons", 0],
        {"text": "لبهٔ نیمه‌پیدا / clipped edge", "callback_data": "must:not-dispatch"},
        "لبهٔ نیمه‌پیدا / clipped edge",
    ),
    (
        ["blocks", 16, "buttons", 0],
        {"text": "تأیید راست‌به‌چپ / RTL confirm", "callback_data": "rtl:confirm"},
        "تأیید راست‌به‌چپ / RTL confirm",
    ),
    (
        ["blocks", 16, "buttons", 1],
        {"text": "کپی مستقل / Copy", "copy_text": {"text": "متن کپی‌شده / copied text"}},
        "کپی مستقل / Copy",
    ),
    (
        ["blocks", 17, "text", 1, "text", "button"],
        {"text": "پاسخ گم‌شده / Lost reply", "callback_data": "lost:reply"},
        "پاسخ گم‌شده / Lost reply",
    ),
]


def project(directory: Path, *, mode: str) -> Path:
    directory.mkdir()
    (directory / "fixture-mode.json").write_text(json.dumps(mode))
    (directory / "run.toml").write_text(
        f'schema = 1\nmode = "{mode}"\nseed = 115\nnow = 1700000000\n'
        f"timeout = {60 if mode == 'simulation-only' else 900}\n"
        '[scenario]\nentry = "scenario.py"\nfiles = ["scenario.py", "fixture-mode.json"]\n'
        '[bots.residual]\nentry = "bot.py"\nfiles = ["bot.py"]\n'
    )
    shutil.copy2("tests/rich_button_residual_scenario.py", directory / "scenario.py")
    shutil.copy2("tests/fixtures/rich_button_residual_bot.py", directory / "bot.py")
    return directory / "run.toml"


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


def assert_observation(observation: dict[str, Any]) -> dict[tuple[str | int, ...], dict[str, Any]]:
    assert observation.keys() == {"chat_id", "message_id", "message_revision", "targets"}
    assert {key: observation[key] for key in ("chat_id", "message_id", "message_revision")} == {
        "chat_id": 1,
        "message_id": 2,
        "message_revision": 5,
    }
    assert len(observation["targets"]) == 4
    by_path: dict[tuple[str | int, ...], dict[str, Any]] = {}
    for target, (path, button, label) in zip(observation["targets"], TARGET_SPECS, strict=True):
        assert target == {
            "target_id": target["target_id"],
            "path": path,
            "button": button,
            "label": label,
        }
        assert_token(target["target_id"])
        by_path[tuple(path)] = target
    assert len({target["target_id"] for target in observation["targets"]}) == 4
    return by_path


def assert_success_receipt(
    receipt: dict[str, Any], target: dict[str, Any], *, effect: dict[str, Any]
) -> None:
    assert_token(receipt["operation_id"])
    assert receipt == {
        "operation_id": receipt["operation_id"],
        "target": {
            "chat_id": 1,
            "message_id": 2,
            "message_revision": 5,
            **target,
        },
        "status": "succeeded",
        "dispatch": "dispatched",
        "effect": effect,
        "reason": None,
        "evidence": receipt["evidence"],
    }


def api_message(value: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "message_id": value["id"],
        "from": BOT_USER if value["sender_id"] == 1 else USER,
        "chat": {"id": 2, "type": "private", "first_name": "Sara"},
        "date": value["date"],
    }
    result["rich_message" if "rich_message" in value else "text"] = value.get(
        "rich_message", value["text"]
    )
    return result


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

    value = json.loads(raw, object_pairs_hook=unique)
    assert type(value) is dict and value["generation"] == int(match[1])
    return cast(dict[str, Any], value)


def install_native_supervisor(monkeypatch: pytest.MonkeyPatch) -> str:
    bootstrap = Path("tests/probes/rich_button_residual_supervisor.py").read_bytes()
    digest = hashlib.sha256(bootstrap).hexdigest()
    original = Sandbox.supervise

    def instrumented(
        self: Sandbox, command: list[str], *, data: Path, timeout: float = 30, kvm: bool = False
    ) -> subprocess.CompletedProcess[str]:
        assert command == [self.profile.python, "-m", "gramlab._run"]
        (data / "rich_button_residual_supervisor.py").write_bytes(bootstrap)
        return original(
            self,
            [self.profile.python, "/work/rich_button_residual_supervisor.py"],
            data=data,
            timeout=timeout,
            kvm=kvm,
        )

    monkeypatch.setattr(Sandbox, "supervise", instrumented)
    return digest


def test_contained_simulation_specifies_rtl_callback_copy_and_repeat(
    tmp_path: Path,
) -> None:
    recorded, _ = execute(tmp_path / "project", mode="simulation-only")
    scenario = process_json(recorded, "scenario")[-1]
    assert recorded["outcome"] == "passed" and recorded["failure"] is None
    assert scenario.keys() == {"mode", "user", "chat", "actions", "final"}
    assert scenario["mode"] == "simulation-only" and scenario["user"] == USER
    assert scenario["chat"] == CHAT
    assert [action["name"] for action in scenario["actions"]] == [
        "rtl_callback",
        "copy",
        "lost_reply_callback",
    ]
    observation = scenario["actions"][0]["observation"]
    targets = assert_observation(observation)
    assert all(action["observation"] == observation for action in scenario["actions"])
    rtl, copied, lost = scenario["actions"]
    rtl_callback = rtl["receipt"]["effect"]["callback"]
    lost_callback = lost["receipt"]["effect"]["callback"]
    for callback, payload in ((rtl_callback, "rtl:confirm"), (lost_callback, "lost:reply")):
        assert re.fullmatch(r"[0-9a-f-]{36}", callback["id"])
        assert re.fullmatch(r"[0-9a-f]{64}", callback["chat_instance"])
        assert callback == {
            "id": callback["id"],
            "user_id": 2,
            "chat_id": 1,
            "message": PUBLISHED,
            "data": payload,
            "chat_instance": callback["chat_instance"],
            "answer": None,
        }
    rtl_target = targets[("blocks", 16, "buttons", 0)]
    assert_success_receipt(
        rtl["receipt"],
        rtl_target,
        effect={"kind": "callback", "callback": rtl_callback, "event_sequence": 6},
    )
    assert rtl["receipt"]["evidence"] == {
        "mode": "simulation",
        "world_event_sequences": [6],
        "clipboard_observation": None,
    }
    assert rtl["repeat"] is None
    copy_effect = {
        "kind": "copy",
        "text": "متن کپی‌شده / copied text",
    }
    assert_success_receipt(
        copied["receipt"], targets[("blocks", 16, "buttons", 1)], effect=copy_effect
    )
    assert copied["receipt"]["evidence"] == {
        "mode": "simulation",
        "world_event_sequences": [],
        "clipboard_observation": {"before": None, "after": "متن کپی‌شده / copied text"},
    }
    assert copied["repeat"] is None
    assert_success_receipt(
        lost["receipt"],
        targets[("blocks", 17, "text", 1, "text", "button")],
        effect={"kind": "callback", "callback": lost_callback, "event_sequence": 8},
    )
    assert lost["receipt"]["evidence"] == {
        "mode": "simulation",
        "world_event_sequences": [8],
        "clipboard_observation": None,
    }
    assert lost["repeat"] == lost["receipt"]
    for action in scenario["actions"]:
        assert action["target"] in observation["targets"]
        assert action["before"]["snapshot"] == SNAPSHOT
        assert action["after"]["snapshot"] == SNAPSHOT
        assert action["before"]["history"] == [PUBLISH_REQUEST, PUBLISHED]
        assert action["after"]["history"] == [PUBLISH_REQUEST, PUBLISHED]

    callback_events = [
        {key: value for key, value in callback.items() if key != "answer"}
        for callback in (rtl_callback, lost_callback)
    ]
    expected_events = [
        {"sequence": 1, "type": "user.created", "data": BOT_USER},
        {"sequence": 2, "type": "user.created", "data": USER},
        {"sequence": 3, "type": "chat.created", "data": CHAT},
        {"sequence": 4, "type": "message.created", "data": PUBLISH_REQUEST},
        {"sequence": 5, "type": "message.created", "data": PUBLISHED},
        {"sequence": 6, "type": "callback.created", "data": callback_events[0]},
        {
            "sequence": 7,
            "type": "callback.answered",
            "data": {
                "id": rtl_callback["id"],
                "user_id": 2,
                "answer": {"text": "ثبت شد / recorded", "show_alert": False, "cache_time": 0},
            },
        },
        {"sequence": 8, "type": "callback.created", "data": callback_events[1]},
        {
            "sequence": 9,
            "type": "callback.answered",
            "data": {
                "id": lost_callback["id"],
                "user_id": 2,
                "answer": {"text": "ثبت شد / recorded", "show_alert": False, "cache_time": 0},
            },
        },
        {"sequence": 10, "type": "message.created", "data": FINISH_REQUEST},
    ]
    assert scenario["final"] == {
        "snapshot": SNAPSHOT,
        "history": [PUBLISH_REQUEST, PUBLISHED, FINISH_REQUEST],
        "events": expected_events,
    }

    bot = process_json(recorded, "bot:residual")
    assert len(bot) == 2 and bot[0] == {"event": "published", "message": api_message(PUBLISHED)}
    assert bot[1].keys() == {"event", "callbacks", "api"} and bot[1]["event"] == "finished"
    expected_callbacks = [
        {
            "id": callback["id"],
            "from": USER,
            "message": api_message(PUBLISHED),
            "chat_instance": callback["chat_instance"],
            "data": callback["data"],
        }
        for callback in (rtl_callback, lost_callback)
    ]
    assert bot[1]["callbacks"] == expected_callbacks
    writes = [entry for entry in bot[1]["api"] if entry["method"] != "getUpdates"]
    assert writes == [
        {
            "method": "sendRichMessage",
            "parameters": {
                "chat_id": 2,
                "rich_message": RICH_MESSAGE | {"skip_entity_detection": True},
            },
            "status": 200,
            "body": {"ok": True, "result": api_message(PUBLISHED)},
        },
        *[
            {
                "method": "answerCallbackQuery",
                "parameters": {
                    "callback_query_id": callback["id"],
                    "text": "ثبت شد / recorded",
                },
                "status": 200,
                "body": {"ok": True, "result": True},
            }
            for callback in (rtl_callback, lost_callback)
        ],
    ]
    polls = [entry for entry in bot[1]["api"] if entry["method"] == "getUpdates"]
    delivered = [update for poll in polls for update in poll["body"]["result"]]
    assert delivered == [
        {"update_id": 1, "message": api_message(PUBLISH_REQUEST)},
        {"update_id": 2, "callback_query": expected_callbacks[0]},
        {"update_id": 3, "callback_query": expected_callbacks[1]},
        {"update_id": 4, "message": api_message(FINISH_REQUEST)},
    ]
    assert polls[-1]["parameters"] == {"offset": 5}
    assert polls[-1]["body"] == {"ok": True, "result": []}


def test_native_supervisor_is_the_only_staged_entry_and_preserves_original_input_order(
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
    staged = data / "rich_button_residual_supervisor.py"
    assert called == {
        "command": ["python", "/work/rich_button_residual_supervisor.py"],
        "data": data,
        "timeout": 31,
        "kvm": True,
    }
    assert hashlib.sha256(staged.read_bytes()).hexdigest() == digest
    source = staged.read_text()
    assert "original_observe(self, message)" in source
    assert "original_prepare(self, receipt, client_nonce=client_nonce)" in source
    assert "original_dispatch(self, receipt, prepared)" in source
    assert "original_control_init(self, directory" in source
    assert "RequestHandlerClass" in source
    assert 'callback_data") == "lost:reply"' in source
    assert 'result.get("status") == "succeeded"' in source
    assert 'arguments[:3] == ("shell", "input", "tap")' in source
    restart = source.index("restart_started")
    relaunch = source.index("._open_chat(", restart)
    prepared = source.index("original_prepare(self, receipt", relaunch)
    assert restart < relaunch < prepared
    confirmed = source.index("original_reply = handler_class.reply")
    dropped = source.index("control_reply_dropped", confirmed)
    assert confirmed < dropped
    assert 'shell", "input", "swipe' not in source
    assert "capture_chat" not in source


def test_supervisor_drops_only_one_completed_selected_control_reply(tmp_path: Path) -> None:
    source = Path(__file__).resolve().parent / "probes/rich_button_residual_supervisor.py"
    namespace = runpy.run_path(source.as_posix())
    forwarded: list[tuple[int, dict[str, Any]]] = []

    class Handler:
        connection: Any
        close_connection: bool

        def reply(self, status: int, value: dict[str, Any]) -> None:
            forwarded.append((status, value))

    class Server:
        RequestHandlerClass = Handler

    def fake_init(self: Any, directory: Path, **keywords: Any) -> None:
        assert directory == tmp_path / "world" and keywords == {"bots": {"residual": 1}}
        self._server = Server()

    persisted: list[dict[str, Any]] = []
    semantic = {
        "snapshot": SNAPSHOT,
        "histories": {"1": [PUBLISH_REQUEST, PUBLISHED]},
        "events": [],
    }
    control_init = namespace["control_init"]
    control_init.__globals__.update(
        original_control_init=fake_init,
        semantic_state=lambda: semantic,
        persist=lambda: persisted.append(json.loads(json.dumps(namespace["record"]))),
    )
    control = type("Control", (), {})()
    control_init(control, tmp_path / "world", bots={"residual": 1})

    class Connection:
        def __init__(self) -> None:
            self.shutdowns: list[int] = []
            self.closed = False

        def shutdown(self, direction: int) -> None:
            self.shutdowns.append(direction)

        def close(self) -> None:
            self.closed = True

    def handler() -> Any:
        value = Handler()
        value.connection = Connection()
        value.close_connection = False
        return value

    target = {
        "target_id": "a" * 32,
        "chat_id": 1,
        "message_id": 2,
        "message_revision": 5,
        "path": ["blocks", 17, "text", 1, "text", "button"],
        "button": {"text": "پاسخ گم‌شده / Lost reply", "callback_data": "lost:reply"},
        "label": "پاسخ گم‌شده / Lost reply",
    }
    terminal = {
        "operation_id": "b" * 32,
        "target": target,
        "status": "succeeded",
        "dispatch": "dispatched",
        "effect": {"kind": "callback"},
        "reason": None,
        "evidence": {"mode": "headless-android"},
    }
    progress = terminal | {"status": "in_progress", "dispatch": "intent_recorded"}
    first = handler()
    first.reply(200, {"schema": 1, "world_id": "world", "result": progress})
    assert forwarded == [(200, {"schema": 1, "world_id": "world", "result": progress})]
    assert first.connection.shutdowns == [] and not first.connection.closed

    dropped = handler()
    dropped.reply(200, {"schema": 1, "world_id": "world", "result": terminal})
    assert dropped.close_connection is True
    assert dropped.connection.shutdowns == [2] and dropped.connection.closed is True
    assert len(persisted) == 1
    assert persisted[0]["control_reply"] == {
        "control_reply_dropped": True,
        "status": 200,
        "receipt": terminal,
        "input_taps": [],
        "semantic_state": semantic,
    }

    repeated = handler()
    repeated.reply(200, {"schema": 1, "world_id": "world", "result": terminal})
    assert forwarded[-1] == (200, {"schema": 1, "world_id": "world", "result": terminal})
    assert repeated.connection.shutdowns == [] and not repeated.connection.closed
    assert len(persisted) == 1


def test_supervisor_evidence_is_bounded_and_redacts_capabilities(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = Path(__file__).resolve().parent / "probes/rich_button_residual_supervisor.py"
    monkeypatch.chdir(tmp_path)
    namespace = runpy.run_path(source.as_posix())
    secret = "gramlab-client_" + "q" * 43
    namespace["record"]["control_reply"] = {
        "control_reply_dropped": True,
        "receipt": {"diagnostic": secret},
    }
    namespace["persist"]([secret])
    retained = Path("rich-button-residual-supervisor.json").read_bytes()
    assert len(retained) <= 1024 * 1024 and secret.encode() not in retained
    assert json.loads(retained)["control_reply"]["receipt"] == {"diagnostic": "[REDACTED]"}


def assert_native_rejection(receipt: dict[str, Any], target: dict[str, Any], *, code: str) -> None:
    assert_token(receipt["operation_id"])
    assert receipt == {
        "operation_id": receipt["operation_id"],
        "target": {
            "chat_id": 1,
            "message_id": 2,
            "message_revision": 5,
            **target,
        },
        "status": "rejected_before_dispatch",
        "dispatch": "not_dispatched",
        "effect": None,
        "reason": {"code": code},
        "evidence": {
            "mode": "headless-android",
            "world_event_sequences": [],
            "clipboard_observation": None,
            "native": {"observation": None, "effect": None, "captures": []},
        },
    }


def assert_native_success_files(
    output: Path,
    receipt: dict[str, Any],
    *,
    expected_path: list[str | int],
    expected_action: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    operation = receipt["operation_id"]
    evidence = receipt["evidence"]
    assert evidence["mode"] == "headless-android"
    native = evidence["native"]
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
    assert observation["schema"] == 1 and effect["schema"] == 1
    assert [observation[key] for key in ("user_id", "chat_id", "message_id", "revision")] == [
        2,
        1,
        2,
        5,
    ]
    assert observation["available"] is True and observation["reason"] is None
    assert effect["operation_id"] == operation and effect["path"] == expected_path
    assert effect["state"] == "complete" and effect["reason"] is None
    assert effect["action"] == expected_action
    touch = effect["touch"]
    assert touch["path"] == expected_path
    assert type(touch["down_uptime_ms"]) is int and touch["down_uptime_ms"] > 0
    assert type(touch["up_uptime_ms"]) is int and touch["up_uptime_ms"] >= touch["down_uptime_ms"]
    capture = native_file(output, native["captures"][0], operation)
    with Image.open(capture) as image:
        image.verify()
        assert image.format == "PNG" and image.size == (320, 640)
    return observation, effect


@pytest.mark.android
def test_original_android_rejects_clipping_restarts_and_recovers_one_lost_reply(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    recorded, output = execute(
        tmp_path / "project", mode="headless-android", monkeypatch=monkeypatch
    )
    assert recorded["outcome"] == "passed" and recorded["failure"] is None
    scenario = process_json(recorded, "scenario")[-1]
    assert scenario.keys() == {"mode", "user", "chat", "actions", "final"}
    assert scenario["mode"] == "headless-android"
    assert scenario["user"] == USER and scenario["chat"] == CHAT
    assert [action["name"] for action in scenario["actions"]] == [
        "clipped",
        "rtl_callback",
        "restart_old_copy",
        "restart_fresh_copy",
        "lost_reply_callback",
    ]
    clipped, rtl, old_copy, fresh_copy, lost = scenario["actions"]
    observations = [
        clipped["observation"],
        old_copy["observation"],
        fresh_copy["observation"],
        lost["observation"],
    ]
    assert rtl["observation"] == observations[0]
    target_maps = [assert_observation(observation) for observation in observations]
    target_ids = [
        target["target_id"] for observation in observations for target in observation["targets"]
    ]
    assert len(target_ids) == len(set(target_ids)) == 16

    clipped_target = target_maps[0][("blocks", 4, "buttons", 0)]
    assert_native_rejection(clipped["receipt"], clipped_target, code="target_unavailable")
    assert clipped["repeat"] == clipped["receipt"]
    rtl_target = target_maps[0][("blocks", 16, "buttons", 0)]
    rtl_callback = rtl["receipt"]["effect"]["callback"]
    assert_success_receipt(
        rtl["receipt"],
        rtl_target,
        effect={"kind": "callback", "callback": rtl_callback, "event_sequence": 6},
    )
    assert rtl["repeat"] == rtl["receipt"]
    assert rtl_callback == {
        "id": rtl_callback["id"],
        "user_id": 2,
        "chat_id": 1,
        "message": PUBLISHED,
        "data": "rtl:confirm",
        "chat_instance": rtl_callback["chat_instance"],
        "answer": None,
    }
    assert re.fullmatch(r"[0-9a-f-]{36}", rtl_callback["id"])
    assert re.fullmatch(r"[0-9a-f]{64}", rtl_callback["chat_instance"])
    _rtl_observation, rtl_effect = assert_native_success_files(
        output,
        rtl["receipt"],
        expected_path=["blocks", 16, "buttons", 0],
        expected_action="callback",
    )
    assert len(rtl_effect["requests"]) == 1
    assert rtl_effect["requests"][0]["callback_id"] == rtl_callback["id"]
    assert rtl_effect["requests"][0]["message_revision"] == 5

    old_target = target_maps[1][("blocks", 16, "buttons", 1)]
    assert_native_rejection(old_copy["receipt"], old_target, code="client_restarted")
    assert old_copy["repeat"] == old_copy["receipt"]
    fresh_target = target_maps[2][("blocks", 16, "buttons", 1)]
    copy_effect = {"kind": "copy", "text": "متن کپی‌شده / copied text"}
    assert_success_receipt(fresh_copy["receipt"], fresh_target, effect=copy_effect)
    assert fresh_copy["repeat"] == fresh_copy["receipt"]
    _, copy_native_effect = assert_native_success_files(
        output,
        fresh_copy["receipt"],
        expected_path=["blocks", 16, "buttons", 1],
        expected_action="copy",
    )
    assert copy_native_effect["requests"] == []
    assert copy_native_effect["clipboard"] == {
        "before": copy_native_effect["clipboard"]["before"],
        "after": "متن کپی‌شده / copied text",
    }
    assert (
        fresh_copy["receipt"]["evidence"]["clipboard_observation"]
        == copy_native_effect["clipboard"]
    )

    assert lost["transport_failure"] == {
        "operation": "tap_rich_button",
        "code": "transport_error",
        "outcome_uncertain": True,
        "status": None,
    }
    lost_target = target_maps[3][("blocks", 17, "text", 1, "text", "button")]
    lost_callback = lost["receipt"]["effect"]["callback"]
    assert_success_receipt(
        lost["receipt"],
        lost_target,
        effect={"kind": "callback", "callback": lost_callback, "event_sequence": 8},
    )
    assert lost["repeat"] == lost["receipt"]
    assert lost_callback == {
        "id": lost_callback["id"],
        "user_id": 2,
        "chat_id": 1,
        "message": PUBLISHED,
        "data": "lost:reply",
        "chat_instance": lost_callback["chat_instance"],
        "answer": None,
    }
    _, lost_native_effect = assert_native_success_files(
        output,
        lost["receipt"],
        expected_path=["blocks", 17, "text", 1, "text", "button"],
        expected_action="callback",
    )
    assert len(lost_native_effect["requests"]) == 1
    assert lost_native_effect["requests"][0]["callback_id"] == lost_callback["id"]
    assert lost_native_effect["requests"][0]["message_revision"] == 5

    for action, before_events, after_events in zip(
        scenario["actions"], (5, 5, 7, 7, 7), (5, 7, 7, 7, 9), strict=True
    ):
        assert action["before"]["snapshot"] == SNAPSHOT
        assert action["after"]["snapshot"] == SNAPSHOT
        assert action["before"]["history"] == [PUBLISH_REQUEST, PUBLISHED]
        assert action["after"]["history"] == [PUBLISH_REQUEST, PUBLISHED]
        assert len(action["before"]["events"]) == before_events
        assert len(action["after"]["events"]) == after_events
    callback_data = [
        event["data"]["data"]
        for event in scenario["final"]["events"]
        if event["type"] == "callback.created"
    ]
    assert callback_data == ["rtl:confirm", "lost:reply"]
    assert scenario["final"]["snapshot"] == SNAPSHOT
    assert scenario["final"]["history"] == [PUBLISH_REQUEST, PUBLISHED, FINISH_REQUEST]
    assert [event["type"] for event in scenario["final"]["events"]] == [
        "user.created",
        "user.created",
        "chat.created",
        "message.created",
        "message.created",
        "callback.created",
        "callback.answered",
        "callback.created",
        "callback.answered",
        "message.created",
    ]

    supervisor = json.loads((output / "rich-button-residual-supervisor.json").read_text())
    assert supervisor.keys() == {
        "schema",
        "bootstrap_sha256",
        "observations",
        "preparations",
        "dispatches",
        "restart",
        "control_reply",
        "input_taps",
    }
    assert supervisor["schema"] == 1
    assert (
        supervisor["bootstrap_sha256"]
        == hashlib.sha256(
            Path("tests/probes/rich_button_residual_supervisor.py").read_bytes()
        ).hexdigest()
    )
    native_observations = supervisor["observations"]
    assert len(native_observations) == 4
    assert [item["index"] for item in native_observations] == [0, 1, 2, 3]
    assert all(item["accounts"] == "Accounts: 0" for item in native_observations)
    assert all(item["world_id"] == recorded["run_id"] for item in native_observations)
    assert all(
        [item[key] for key in ("user_id", "chat_id", "message_id", "revision")] == [2, 1, 2, 5]
        for item in native_observations
    )
    assert len({item["pid"] for item in native_observations}) == 4
    assert len({item["client_nonce"] for item in native_observations}) == 4
    assert len({item["activation_nonce"] for item in native_observations}) == 4
    first_targets = {tuple(target["path"]): target for target in native_observations[0]["targets"]}
    native_clipped = first_targets[("blocks", 4, "buttons", 0)]
    assert native_clipped["available"] is False and native_clipped["reason"] == "clipped"
    bounds = native_clipped["screen_bounds"]
    assert len(bounds) == 4 and bounds[0] < bounds[2] and bounds[1] < bounds[3]
    assert all(type(value) in (int, float) and math.isfinite(value) for value in bounds)
    assert bounds[2] > 0 and bounds[0] < 320 and bounds[3] > 0 and bounds[1] < 640
    row_rtl = first_targets[("blocks", 16, "buttons", 0)]
    row_copy = first_targets[("blocks", 16, "buttons", 1)]
    assert row_rtl["available"] is True and row_rtl["reason"] is None
    assert row_copy["available"] is True and row_copy["reason"] is None
    assert unicodedata.bidirectional(row_rtl["label"][0]) == "AL"
    assert row_rtl["screen_bounds"][0] > row_copy["screen_bounds"][0]
    nested = first_targets[("blocks", 17, "text", 1, "text", "button")]
    assert nested["available"] is True and nested["reason"] is None
    rtl_capture = native_observations[0]["rtl_capture"]
    rtl_png = output / rtl_capture["path"]
    raw = rtl_png.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == rtl_capture["sha256"]
    assert len(raw) == rtl_capture["bytes"]
    with Image.open(rtl_png) as image:
        image.verify()
        assert image.format == "PNG" and image.size == (320, 640)

    restart = supervisor["restart"]
    assert restart["restart_started"] is True and restart["restart_complete"] is True
    assert restart["path"] == ["blocks", 16, "buttons", 1]
    assert restart["before"]["pid"] != restart["after"]["pid"]
    assert restart["before"]["client_nonce"] != restart["after"]["client_nonce"]
    assert restart["before"]["activation_nonce"] == restart["after"]["activation_nonce"]
    assert restart["semantic_before"] == restart["semantic_after"]
    assert restart["before"]["pid"] == native_observations[1]["pid"]
    assert restart["before"]["client_nonce"] == native_observations[1]["client_nonce"]
    assert restart["after"]["pid"] != native_observations[2]["pid"]
    assert restart["after"]["client_nonce"] != native_observations[2]["client_nonce"]

    preparations = supervisor["preparations"]
    assert [(item["path"], item["status"], item.get("reason")) for item in preparations] == [
        (["blocks", 4, "buttons", 0], "rejected", "target_unavailable"),
        (["blocks", 16, "buttons", 0], "prepared", None),
        (["blocks", 16, "buttons", 1], "rejected", "client_restarted"),
        (["blocks", 16, "buttons", 1], "prepared", None),
        (["blocks", 17, "text", 1, "text", "button"], "prepared", None),
    ]
    assert all(item["input_taps_before"] == item["input_taps_after"] for item in preparations)
    dispatches = supervisor["dispatches"]
    assert [item["path"] for item in dispatches] == [
        ["blocks", 16, "buttons", 0],
        ["blocks", 16, "buttons", 1],
        ["blocks", 17, "text", 1, "text", "button"],
    ]
    assert all(item["result"]["status"] == "succeeded" for item in dispatches)
    assert all(item["input_taps_after"] == item["input_taps_before"] + 1 for item in dispatches)
    assert len(supervisor["input_taps"]) == 3
    control_reply = supervisor["control_reply"]
    assert control_reply["control_reply_dropped"] is True and control_reply["status"] == 200
    assert control_reply["receipt"] == lost["receipt"]
    assert len(control_reply["input_taps"]) == 3
    assert dispatches[-1]["result"] == {
        key: lost["receipt"][key] for key in ("status", "dispatch", "effect", "reason", "evidence")
    }
    assert not any(
        callback["data"] == "must:not-dispatch"
        for callback in process_json(recorded, "bot:residual")[-1]["callbacks"]
    )
    assert recorded["android"]["network"] == {"ipv4": 1, "ipv6": 1}
    assert recorded["android"]["filesystem"] == {
        "world_visible": False,
        "bot_visible": False,
        "scenario_visible": False,
        "private_avd_visible": True,
        "same_pid_namespace": False,
        "same_network": True,
    }
