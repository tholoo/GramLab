"""Host contracts with a real World; guest files/input are explicitly substituted.

These independently authored private observations are not native acceptance evidence.
"""

from __future__ import annotations

import copy
import json
import time
from pathlib import Path
from typing import Any

import pytest

from gramlab._android import Android
from gramlab._android_rich_buttons import AndroidRichInput
from gramlab.runtime import RuntimeProfile
from gramlab.world import World


class ExternalGuest(AndroidRichInput):
    """Substitute only the external guest observation/input boundary."""

    def __init__(self, android: Android, record: dict[str, Any], world_id: str) -> None:
        super().__init__(android)
        self.record = record
        block = record["message"]["rich_message"]["blocks"][0]
        self.selected_path = (
            ["blocks", 0, "buttons", 0]
            if block["type"] == "buttons"
            else ["blocks", 0, "text", 0, "button"]
        )
        self.selected_button = (
            block["buttons"][0] if block["type"] == "buttons" else block["text"][0]["button"]
        )
        self.world_id = world_id
        self.files: dict[str, dict[str, Any]] = {}
        self.writes: list[str] = []
        self.touches = 0
        self.pid = 321
        self.now = 10000
        self.after_touch: Any = None
        self.capture_hook: Any = None
        self.baseline: str | None = None

    def launch(self, chat: dict[str, Any], *, before_launch: Any = None) -> str:
        assert chat == self.record["chat"]
        self.android._persona = chat["user_id"]
        self.android._active_chat = chat["id"]
        assert before_launch is not None
        before_launch()
        return "substituted external launch"

    def _read(self, name: str) -> dict[str, Any]:
        return copy.deepcopy(self.files[name])

    def _write(self, name: str, value: dict[str, Any]) -> None:
        self.writes.append(name)
        self.files[name] = copy.deepcopy(value)
        if name == "rich-button-observe.json":
            button = self.selected_button
            self.files["rich-button-observation.json"] = value | {
                "client_nonce": "process-original",
                "pid": self.pid,
                "generation": 5,
                "drawn_uptime_ms": 9990,
                "available": True,
                "reason": None,
                "targets": [
                    {
                        "path": self.selected_path,
                        "button": button,
                        "label": "Same",
                        "available": True,
                        "reason": None,
                        "local_bounds": [10.5, 1.25, 90.5, 31.25],
                        "origin": [0, 0],
                        "screen_bounds": [10.5, 101.25, 90.5, 131.25],
                    }
                ],
            }
        if name == "rich-button-arm.json":
            self.files["rich-button-effect.json"] = {
                key: val for key, val in value.items() if key != "observation_generation"
            } | {
                "generation": 6,
                "uptime_ms": 10000,
                "state": "armed",
                "reason": None,
                "touch": None,
                "action": None,
                "requests": [],
                "clipboard": (
                    None
                    if "callback_data" in self.selected_button
                    else {"before": self.baseline, "after": self.baseline}
                ),
            }

    def _guest_state(self) -> tuple[int, int]:
        return self.pid, self.now

    def _capture_original(self, path: Path) -> None:
        # No invented PNG is created or offered as a native capture.
        if self.capture_hook is not None:
            self.capture_hook()

    def touch(self, *args: str, **kwargs: Any) -> Any:
        assert args[:3] == ("shell", "input", "tap")
        self.touches += 1
        assert self.touches == 1
        effect = self.files["rich-button-effect.json"]
        effect.update(
            generation=7,
            uptime_ms=10001,
            state="complete",
            touch={"down_uptime_ms": 10000, "up_uptime_ms": 10001, "path": effect["path"]},
        )
        button = self.selected_button
        if "callback_data" in button:
            with World.open(Path("world")) as world:
                callback = world.create_callback(
                    user_id=effect["user_id"],
                    chat_id=effect["chat_id"],
                    message_id=effect["message_id"],
                    data=button["callback_data"],
                    request_id="http-exact",
                    version=4,
                )
            effect.update(
                action="callback",
                clipboard=None,
                requests=[
                    {
                        "native_request_token": 19,
                        "request_id": "http-exact",
                        "callback_id": callback["id"],
                        "message_revision": effect["revision"],
                    }
                ],
            )
        elif "copy_text" in button:
            effect.update(
                action="copy",
                clipboard={"before": self.baseline, "after": button["copy_text"]["text"]},
            )
        else:
            effect.update(
                action="disabled_suppressed",
                touch={"down_uptime_ms": 10000, "up_uptime_ms": None, "path": effect["path"]},
            )
        self.now = 10010
        if self.after_touch is not None:
            self.after_touch(effect)
        return None


@pytest.fixture
def staged(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
    def make(
        kind: str = "callback", *, inline: bool = False
    ) -> tuple[ExternalGuest, dict[str, Any]]:
        with World.create(tmp_path / "world", seed=7, now=100) as world:
            user = world.create_user(first_name="Sara")
            bot = world.create_user(first_name="Bot", is_bot=True)
            chat = world.open_private_chat(user_id=user["id"], bot_id=bot["id"])
            action: dict[str, Any] = (
                {"callback_data": "same"}
                if kind == "callback"
                else (
                    {"copy_text": {"text": "برداشت / copy"}} if kind == "copy" else {"disabled": {}}
                )
            )
            message = world.send_rich_message(
                chat_id=chat["id"],
                sender_id=bot["id"],
                rich_message={
                    "skip_entity_detection": True,
                    "blocks": (
                        [
                            {
                                "type": "paragraph",
                                "text": [{"type": "button", "button": {"text": "Same", **action}}],
                            }
                        ]
                        if inline
                        else [{"type": "buttons", "buttons": [{"text": "Same", **action}]}]
                    ),
                },
            )
            revision = world.client_snapshot(user["id"], version=4)["message_revisions"][0][
                "revision"
            ]
            record = {"chat": chat, "message": message, "revision": revision}
            world_id = world.world_id
        android = Android(
            RuntimeProfile(bubblewrap="", python="", store_paths=()),
            deadline=time.monotonic() + 5,
            secrets=[],
            bridge_version=4,
        )
        guest = ExternalGuest(android, record, world_id)
        monkeypatch.setattr(android, "_open_chat", guest.launch)
        monkeypatch.setattr(android, "_adb", guest.touch)
        nonce = guest.observe(record)
        receipt: dict[str, Any] = {
            "operation_id": "operation-one",
            "target": {
                "target_id": "target-one",
                "chat_id": chat["id"],
                "message_id": message["id"],
                "message_revision": revision,
                "path": copy.deepcopy(guest.selected_path),
                "button": guest.selected_button,
                "label": "Same",
            },
            "status": "in_progress",
            "dispatch": "not_dispatched",
            "effect": None,
            "reason": None,
            "evidence": {
                "mode": "headless-android",
                "world_event_sequences": [],
                "clipboard_observation": None,
                "native": {"observation": None, "effect": None, "captures": []},
            },
        }
        assert nonce == "process-original"
        return guest, receipt

    monkeypatch.chdir(tmp_path)
    return make


def test_exact_original_callback_and_frozen_world_message(staged: Any) -> None:
    guest, receipt = staged()
    original = copy.deepcopy(receipt)
    prepared = guest.prepare(receipt, client_nonce="process-original")
    assert guest.touches == 0
    assert set(prepared) == {"context", "receipt_for_size_check"}
    result = guest.dispatch(receipt, prepared)
    with World.open(Path("world")) as world:
        creation = world.events()[-1]
    assert result["status"] == "succeeded"
    assert result["effect"] == {
        "kind": "callback",
        "callback": creation["data"] | {"answer": None},
        "event_sequence": creation["sequence"],
    }
    assert result["evidence"]["world_event_sequences"] == [creation["sequence"]]
    assert set(result) == {"status", "dispatch", "effect", "reason", "evidence"}
    assert guest.reconcile(receipt) == result
    assert guest.dispatch(receipt, prepared) == result
    assert guest.touches == 1
    assert guest.writes.count("rich-button-arm.json") == 1
    assert receipt == original


@pytest.mark.parametrize("kind", ["copy", "disabled"])
def test_original_local_effect_and_readonly_reconciliation(staged: Any, kind: str) -> None:
    guest, receipt = staged(kind)
    guest.baseline = "برداشت / copy" if kind == "copy" else "unchanged"
    with World.open(Path("world")) as world:
        before = world.events()
    prepared = guest.prepare(receipt, client_nonce="process-original")
    result = guest.dispatch(receipt, prepared)
    assert result["status"] == "succeeded"
    assert result["effect"] == (
        {"kind": "copy", "text": guest.baseline}
        if kind == "copy"
        else {"kind": "none", "reason": "disabled"}
    )
    assert result["evidence"]["clipboard_observation"] == {
        "before": guest.baseline,
        "after": guest.baseline,
    }
    with World.open(Path("world")) as world:
        assert world.events() == before
    writes = list(guest.writes)
    assert guest.reconcile(receipt) == result
    assert guest.writes == writes
    assert guest.touches == 1


@pytest.mark.parametrize(
    "field,value,reason",
    [
        ("client_nonce", "another-process", "client_restarted"),
        ("pid", 999, "client_restarted"),
        ("revision", 999, "message_revision_changed"),
        ("drawn_uptime_ms", 0, "target_unavailable"),
        ("generation", True, "target_unavailable"),
        ("available", False, "target_unavailable"),
    ],
)
def test_unusable_observation_rejects_without_touch(
    staged: Any, field: str, value: Any, reason: str
) -> None:
    guest, receipt = staged()
    guest.files["rich-button-observation.json"][field] = value
    with pytest.raises(ValueError, match=reason):
        guest.prepare(receipt, client_nonce="process-original")
    assert guest.touches == 0


def test_screenshot_precedes_final_revision_and_lifetime_checks(staged: Any) -> None:
    guest, receipt = staged()
    guest.capture_hook = lambda: setattr(guest, "pid", 999)
    with pytest.raises(ValueError, match="client_restarted"):
        guest.prepare(receipt, client_nonce="process-original")
    assert guest.touches == 0


@pytest.mark.parametrize(
    "field,value",
    [
        ("action", None),
        ("requests", []),
        (
            "requests",
            [
                {
                    "native_request_token": 19,
                    "request_id": "http-exact",
                    "callback_id": "wrong-id",
                    "message_revision": 4,
                }
            ],
        ),
        ("client_nonce", "another-process"),
    ],
)
def test_missing_or_wrong_native_chain_never_becomes_success(
    staged: Any, field: str, value: Any
) -> None:
    guest, receipt = staged()
    prepared = guest.prepare(receipt, client_nonce="process-original")
    guest.after_touch = lambda effect: effect.update({field: value})
    result = guest.dispatch(receipt, prepared)
    assert result["status"] == "uncertain"
    assert result["effect"] is None
    assert guest.touches == 1
    assert guest.reconcile(receipt) is None


def test_client_restarts_during_touch_never_confirms_old_evidence(staged: Any) -> None:
    guest, receipt = staged()
    prepared = guest.prepare(receipt, client_nonce="process-original")
    guest.after_touch = lambda effect: setattr(guest, "pid", 999)
    result = guest.dispatch(receipt, prepared)
    assert result["status"] == "uncertain"
    assert result["reason"] == {"code": "effect_mismatch"}
    assert guest.reconcile(receipt) is None


def test_lost_input_reply_can_reconcile_exact_effect_without_touch_or_arm(staged: Any) -> None:
    guest, receipt = staged()
    prepared = guest.prepare(receipt, client_nonce="process-original")

    def lost_reply(effect: dict[str, Any]) -> None:
        raise RuntimeError("external ADB reply lost after the ordinary touch")

    guest.after_touch = lost_reply
    result = guest.dispatch(receipt, prepared)
    assert result["status"] == "uncertain"
    writes = list(guest.writes)
    recovered = guest.reconcile(receipt)
    assert recovered is not None and recovered["status"] == "succeeded"
    assert guest.writes == [*writes, "rich-button-disarm.json"]
    assert guest.touches == 1


def test_immediate_bot_answer_does_not_mutate_creation_receipt(staged: Any) -> None:
    guest, receipt = staged()
    prepared = guest.prepare(receipt, client_nonce="process-original")

    def answer(effect: dict[str, Any]) -> None:
        with World.open(Path("world")) as world:
            world.answer_callback(
                bot_id=guest.record["chat"]["bot_id"],
                callback_id=effect["requests"][0]["callback_id"],
                text="answered",
            )

    guest.after_touch = answer
    result = guest.dispatch(receipt, prepared)
    assert result["status"] == "succeeded"
    assert result["effect"]["callback"]["answer"] is None


@pytest.mark.parametrize(
    "bounds",
    [
        [10, 100, 10, 120],
        [-1, 100, 40, 120],
        [10, 100, 321, 120],
        [10, 100, True, 120],
        [10, 100, float("nan"), 120],
    ],
)
def test_unusable_original_bounds_reject(staged: Any, bounds: list[Any]) -> None:
    guest, receipt = staged()
    guest.files["rich-button-observation.json"]["targets"][0]["screen_bounds"] = bounds
    with pytest.raises(ValueError, match="target_unavailable"):
        guest.prepare(receipt, client_nonce="process-original")
    assert guest.touches == 0


def test_boolean_target_path_is_not_integer_zero(staged: Any) -> None:
    guest, receipt = staged()
    receipt["target"]["path"][1] = False
    with pytest.raises(ValueError, match="target_unavailable"):
        guest.prepare(receipt, client_nonce="process-original")
    assert guest.touches == 0


@pytest.mark.parametrize(
    "clipboard",
    [
        None,
        {"before": None, "after": "changed"},
        {"before": "x" * 4097, "after": "x" * 4097},
        {"before": {"uri": "guest"}, "after": None},
    ],
)
def test_copy_requires_bounded_actual_clipboard_before_touch(staged: Any, clipboard: Any) -> None:
    guest, receipt = staged("copy")
    write = guest._write

    def boundary(name: str, value: dict[str, Any]) -> None:
        write(name, value)
        if name == "rich-button-arm.json":
            guest.files["rich-button-effect.json"]["clipboard"] = clipboard

    guest._write = boundary
    with pytest.raises(ValueError, match="target_unavailable"):
        guest.prepare(receipt, client_nonce="process-original")
    assert guest.touches == 0
    assert guest.writes[-1] == "rich-button-disarm.json"


@pytest.mark.parametrize("kind", ["copy", "disabled"])
def test_clipboard_equality_without_original_action_is_not_confirmation(
    staged: Any, kind: str
) -> None:
    guest, receipt = staged(kind)
    prepared = guest.prepare(receipt, client_nonce="process-original")
    guest.after_touch = lambda effect: effect.update(action=None)
    result = guest.dispatch(receipt, prepared)
    assert result["status"] == "uncertain" and result["effect"] is None


@pytest.mark.parametrize(
    "raw",
    [
        b'{"schema":1,"schema":1}',
        b'{"x":NaN}',
        b'{"x":Infinity}',
        b'{"x":"\xff"}',
        b'{"x":"\\ud800"}',
        b"[]",
        b"{} trailing",
        b'{"x":' + b"1" * (1024 * 1024) + b"}",
    ],
)
def test_guest_framing_is_strict_utf8_json(monkeypatch: pytest.MonkeyPatch, raw: bytes) -> None:
    import base64
    import subprocess

    android = Android(
        RuntimeProfile(bubblewrap="", python="", store_paths=()),
        deadline=time.monotonic() + 5,
        secrets=[],
        bridge_version=4,
    )

    def boundary(*args: str, **kwargs: Any) -> Any:
        return subprocess.CompletedProcess(args, 0, stdout=base64.b64encode(raw).decode())

    monkeypatch.setattr(android, "_adb", boundary)
    host = AndroidRichInput(android)
    with pytest.raises(ValueError, match="target_unavailable"):
        host._read("rich-button-observation.json")


def test_arm_waits_for_actual_ack_without_rewriting_or_touch(staged: Any) -> None:
    guest, receipt = staged()
    read = guest._read
    attempts = 0

    def boundary(name: str) -> dict[str, Any]:
        nonlocal attempts
        if name == "rich-button-effect.json":
            attempts += 1
            if attempts == 1:
                raise FileNotFoundError("external guest has not published acknowledgement")
            if attempts == 2:
                return dict(read(name)) | {"operation_id": "previous-operation"}
        return dict(read(name))

    guest._read = boundary
    prepared = guest.prepare(receipt, client_nonce="process-original")
    assert attempts == 3
    assert guest.touches == 0
    assert guest.writes.count("rich-button-arm.json") == 1
    guest.abort_prepared(receipt, prepared)
    writes = list(guest.writes)
    guest.abort_prepared(receipt, prepared)
    assert guest.writes == writes
    assert guest.reconcile(receipt) is None
    with pytest.raises(ValueError):
        guest.dispatch(receipt, prepared)
    assert guest.touches == 0


@pytest.mark.parametrize("aba", [False, True])
def test_same_clock_and_aba_edits_reject_after_original_capture(staged: Any, aba: bool) -> None:
    guest, receipt = staged()

    def edit() -> None:
        with World.open(Path("world")) as world:
            world.edit_message(
                chat_id=guest.record["chat"]["id"],
                message_id=guest.record["message"]["id"],
                bot_id=guest.record["chat"]["bot_id"],
                rich_message={
                    "skip_entity_detection": True,
                    "blocks": [
                        {
                            "type": "buttons",
                            "buttons": [{"text": "Changed", "callback_data": "same"}],
                        }
                    ],
                },
            )
            if aba:
                world.edit_message(
                    chat_id=guest.record["chat"]["id"],
                    message_id=guest.record["message"]["id"],
                    bot_id=guest.record["chat"]["bot_id"],
                    rich_message={
                        "skip_entity_detection": True,
                        **guest.record["message"]["rich_message"],
                    },
                )

    guest.capture_hook = edit
    with pytest.raises(ValueError, match="message_revision_changed"):
        guest.prepare(receipt, client_nonce="process-original")
    assert guest.touches == 0
    assert "rich-button-arm.json" not in guest.writes


def test_retained_effect_files_never_overwrite_previous_generations(staged: Any) -> None:
    guest, receipt = staged()
    prepared = guest.prepare(receipt, client_nonce="process-original")
    candidate = prepared["receipt_for_size_check"]
    prior = {p: p.read_bytes() for p in Path("rich-buttons").rglob("*.json")}
    result = guest.dispatch(receipt, prepared)
    assert result["status"] == "succeeded"
    assert all(path.read_bytes() == data for path, data in prior.items())
    assert len(json.dumps(candidate).encode()) >= len(json.dumps(receipt | result).encode())
    assert (
        json.loads(Path(result["evidence"]["native"]["effect"]).read_bytes())["state"] == "complete"
    )


def test_late_callback_revision_race_cannot_use_equal_payload(staged: Any) -> None:
    guest, receipt = staged()
    prepared = guest.prepare(receipt, client_nonce="process-original")

    def race(effect: dict[str, Any]) -> None:
        with World.open(Path("world")) as world:
            world.edit_message(
                chat_id=guest.record["chat"]["id"],
                message_id=guest.record["message"]["id"],
                bot_id=guest.record["chat"]["bot_id"],
                rich_message={
                    "skip_entity_detection": True,
                    "blocks": [
                        {
                            "type": "buttons",
                            "buttons": [{"text": "Different occurrence", "callback_data": "same"}],
                        }
                    ],
                },
            )
            callback = world.create_callback(
                user_id=effect["user_id"],
                chat_id=effect["chat_id"],
                message_id=effect["message_id"],
                data="same",
                request_id="actual-raced-request",
                version=4,
            )
            revision = world.callback_dependencies(effect["user_id"], callback, version=4)[
                "message_revision"
            ]
        effect["requests"][0].update(
            request_id="actual-raced-request", callback_id=callback["id"], message_revision=revision
        )

    guest.after_touch = race
    result = guest.dispatch(receipt, prepared)
    assert result["status"] == "uncertain" and result["reason"] == {"code": "effect_mismatch"}
    assert guest.touches == 1


def test_valid_effect_with_wrong_identity_is_retained_as_mismatch(staged: Any) -> None:
    guest, receipt = staged()
    prepared = guest.prepare(receipt, client_nonce="process-original")
    guest.after_touch = lambda effect: effect.update(client_nonce="wrong-process")
    result = guest.dispatch(receipt, prepared)
    assert result["status"] == "uncertain"
    retained = json.loads(Path(result["evidence"]["native"]["effect"]).read_bytes())
    assert retained["client_nonce"] == "wrong-process"
    retained["client_nonce"] = "process-original"
    retained["generation"] += 1
    guest.files["rich-button-effect.json"] = retained
    assert guest.reconcile(receipt) is None


def test_launch_hook_runs_after_persona_clear_and_configuration_before_start(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import subprocess
    from types import SimpleNamespace

    monkeypatch.chdir(tmp_path)
    with World.create(Path("world"), seed=7, now=100) as world:
        user = world.create_user(first_name="Sara")
        bot = world.create_user(first_name="Bot", is_bot=True)
        chat = world.open_private_chat(user_id=user["id"], bot_id=bot["id"])
    android = Android(
        RuntimeProfile(bubblewrap="", python="", store_paths=()),
        deadline=time.monotonic() + 5,
        secrets=[],
        bridge_version=4,
    )
    calls: list[tuple[str, ...]] = []

    def boundary(*args: str, **kwargs: Any) -> Any:
        calls.append(args)
        return subprocess.CompletedProcess(
            args, 0, stdout="Success" if args[:3] == ("shell", "pm", "clear") else "Status: ok"
        )

    monkeypatch.setattr(android, "_adb", boundary)
    monkeypatch.setattr(android, "_guest", SimpleNamespace(poll=lambda: None))
    monkeypatch.setattr(android, "_bridge", SimpleNamespace(base_url="http://127.0.0.1:12345"))

    def activate() -> None:
        assert calls[0][:3] == ("shell", "am", "force-stop")
        assert calls[1][:3] == ("shell", "pm", "clear")
        assert "config.json" in calls[-1][-1]
        calls.append(("activate-private-observer",))

    android._open_chat(chat, before_launch=activate)
    assert calls[-2] == ("activate-private-observer",)
    assert calls[-1][:3] == ("shell", "am", "start")
    calls.clear()
    android._open_chat(chat)
    assert calls[0][:3] == ("shell", "am", "force-stop")
    assert calls[-1][:3] == ("shell", "am", "start")
    assert not any(call == ("activate-private-observer",) for call in calls)


def test_disarm_failure_keeps_confirmed_effect_and_blocks_another_input(staged: Any) -> None:
    guest, receipt = staged()
    prepared = guest.prepare(receipt, client_nonce="process-original")
    write = guest._write

    def boundary(name: str, value: dict[str, Any]) -> None:
        if name == "rich-button-disarm.json":
            raise RuntimeError("external cleanup response unavailable")
        write(name, value)

    guest._write = boundary
    result = guest.dispatch(receipt, prepared)
    assert result["status"] == "succeeded"
    assert guest.reconcile(receipt) == result
    with pytest.raises(ValueError):
        guest.observe(guest.record)
    assert guest.touches == 1
    assert guest.android.observations["rich_button_disarm_pending"] == "operation-one"


def test_oversized_post_touch_clipboard_is_bounded_uncertainty_with_diagnostic(staged: Any) -> None:
    guest, receipt = staged("copy")
    prepared = guest.prepare(receipt, client_nonce="process-original")
    guest.after_touch = lambda effect: effect.update(
        clipboard={"before": None, "after": "x" * 4097}
    )
    result = guest.dispatch(receipt, prepared)
    assert result["status"] == "uncertain" and result["effect"] is None
    diagnostic = guest.android.observations["rich_button_diagnostics"]["operation-one"]
    assert json.loads(Path(diagnostic).read_bytes())["clipboard"]["after"] == "x" * 4097
    assert guest.touches == 1


@pytest.mark.parametrize("kind", ["callback", "copy", "disabled"])
def test_inline_original_object_paths_support_each_effect(staged: Any, kind: str) -> None:
    guest, receipt = staged(kind, inline=True)
    assert receipt["target"]["path"] == ["blocks", 0, "text", 0, "button"]
    prepared = guest.prepare(receipt, client_nonce="process-original")
    result = guest.dispatch(receipt, prepared)
    assert result["status"] == "succeeded"
    assert guest.touches == 1


def test_offscreen_duplicate_does_not_disable_visible_occurrence(staged: Any) -> None:
    guest, receipt = staged()
    with World.open(Path("world")) as world:
        message = world.edit_message(
            chat_id=guest.record["chat"]["id"],
            message_id=guest.record["message"]["id"],
            bot_id=guest.record["chat"]["bot_id"],
            rich_message={
                "skip_entity_detection": True,
                "blocks": [
                    {"type": "buttons", "buttons": [{"text": "Same", "callback_data": "same"}] * 2}
                ],
            },
        )
        revision = world.client_snapshot(guest.record["chat"]["user_id"], version=4)[
            "message_revisions"
        ][0]["revision"]
    guest.record = {"chat": guest.record["chat"], "message": message, "revision": revision}
    write = guest._write

    def boundary(name: str, value: dict[str, Any]) -> None:
        write(name, value)
        if name == "rich-button-observe.json":
            guest.files["rich-button-observation.json"]["targets"].append(
                {
                    "path": ["blocks", 0, "buttons", 1],
                    "button": {"text": "Same", "callback_data": "same"},
                    "label": "Same",
                    "available": False,
                    "reason": "offscreen",
                }
            )

    guest._write = boundary
    guest.observe(guest.record)
    receipt["target"]["message_revision"] = revision
    prepared = guest.prepare(receipt, client_nonce="process-original")
    assert guest.dispatch(receipt, prepared)["status"] == "succeeded"
    second = copy.deepcopy(receipt)
    second["operation_id"] = "operation-two"
    second["target"]["target_id"] = "target-two"
    second["target"]["path"][-1] = 1
    with pytest.raises(ValueError, match="target_unavailable"):
        guest.prepare(second, client_nonce="process-original")
    assert guest.touches == 1


def test_edit_during_journal_preflight_leaves_intent_uncertain_without_input(staged: Any) -> None:
    guest, receipt = staged()
    prepared = guest.prepare(receipt, client_nonce="process-original")
    with World.open(Path("world")) as world:
        world.edit_message(
            chat_id=guest.record["chat"]["id"],
            message_id=guest.record["message"]["id"],
            bot_id=guest.record["chat"]["bot_id"],
            rich_message={
                "skip_entity_detection": True,
                "blocks": [
                    {
                        "type": "buttons",
                        "buttons": [{"text": "After intent", "callback_data": "same"}],
                    }
                ],
            },
        )
        before = world.events()
    result = guest.dispatch(receipt, prepared)
    assert result["status"] == "uncertain"
    assert result["dispatch"] == "intent_recorded"
    assert result["effect"] is None
    assert guest.touches == 0
    assert guest.reconcile(receipt) is None
    assert guest.dispatch(receipt, prepared) == result
    assert guest.writes[-1] == "rich-button-disarm.json"
    with World.open(Path("world")) as world:
        assert world.events() == before


@pytest.mark.parametrize(
    "change", ["uptime", "geometry", "pid", "nonce", "arm_command", "consumed", "down"]
)
def test_post_intent_client_or_arm_change_never_sends_input(staged: Any, change: str) -> None:
    guest, receipt = staged()
    prepared = guest.prepare(receipt, client_nonce="process-original")
    if change == "uptime":
        guest.now = 16000
    elif change == "geometry":
        guest.files["rich-button-observation.json"]["targets"][0]["screen_bounds"][0] += 1
    elif change == "pid":
        guest.pid += 1
    elif change == "nonce":
        guest.files["rich-button-observation.json"]["client_nonce"] = "new-process"
    elif change == "arm_command":
        guest.files["rich-button-arm.json"]["operation_id"] = "different-operation"
    elif change == "consumed":
        guest.files["rich-button-effect.json"].update(state="consumed", generation=7)
    else:
        guest.files["rich-button-effect.json"].update(
            generation=7,
            touch={
                "down_uptime_ms": 10000,
                "up_uptime_ms": None,
                "path": receipt["target"]["path"],
            },
        )
    result = guest.dispatch(receipt, prepared)
    assert result["status"] == "uncertain"
    assert result["dispatch"] == "intent_recorded"
    assert result["effect"] is None
    assert guest.touches == 0
    assert guest.reconcile(receipt) is None
    assert guest.writes[-1] == "rich-button-disarm.json"


@pytest.mark.parametrize("kind", ["callback", "copy", "disabled"])
def test_prospective_receipt_passes_real_journal_preflight(staged: Any, kind: str) -> None:
    from gramlab._rich_button_journal import Journal

    guest, receipt = staged(kind)
    prepared = guest.prepare(receipt, client_nonce="process-original")
    directory = Path("journal")
    directory.mkdir()
    journal = Journal(directory, run_id="host-preflight", world_id=guest.world_id)
    try:
        target = receipt["target"]
        journal.allocate(
            {
                "chat_id": target["chat_id"],
                "message_id": target["message_id"],
                "message_revision": target["message_revision"],
                "targets": [{key: target[key] for key in ("target_id", "path", "button", "label")}],
            },
            user_id=guest.record["chat"]["user_id"],
            client_nonce="process-original",
        )
        journal.transition("claim", receipt, client_nonce="process-original")
        before = journal.path.read_bytes()
        journal.preflight_receipt(
            prepared["receipt_for_size_check"], client_nonce="process-original"
        )
        assert journal.path.read_bytes() == before
        assert guest.touches == 0
    finally:
        journal.close()
        guest.abort_prepared(receipt, prepared)


@pytest.mark.parametrize(
    "change", ["schema", "extra", "world", "chat", "revision", "mapping", "uptime"]
)
def test_post_input_observation_must_remain_strict_and_bound(staged: Any, change: str) -> None:
    guest, receipt = staged()
    prepared = guest.prepare(receipt, client_nonce="process-original")

    def alter(_effect: dict[str, Any]) -> None:
        observation = guest.files["rich-button-observation.json"]
        if change == "schema":
            observation["schema"] = True
        elif change == "extra":
            observation["extra"] = None
        elif change == "world":
            observation["world_id"] = "unrelated-world"
        elif change == "chat":
            observation["chat_id"] += 1
        elif change == "revision":
            observation["revision"] += 1
        elif change == "mapping":
            observation["targets"][0]["button"]["callback_data"] = "unrelated"
        else:
            observation["drawn_uptime_ms"] = 0

    guest.after_touch = alter
    result = guest.dispatch(receipt, prepared)
    assert result["status"] == "uncertain"
    assert result["effect"] is None
    assert guest.touches == 1
    assert guest.reconcile(receipt) is None


def test_actual_callback_survives_legitimate_bot_edit_before_confirmation(staged: Any) -> None:
    guest, receipt = staged()
    prepared = guest.prepare(receipt, client_nonce="process-original")
    frozen = copy.deepcopy(guest.record["message"])

    def edit_after_acceptance(_effect: dict[str, Any]) -> None:
        with World.open(Path("world")) as world:
            world.edit_message(
                chat_id=guest.record["chat"]["id"],
                message_id=guest.record["message"]["id"],
                bot_id=guest.record["chat"]["bot_id"],
                text="Bot has already handled the exact callback",
            )
        # The activation still denotes the consumed original revision; the current
        # client reports that it is no longer applied instead of mapping new content.
        guest.files["rich-button-observation.json"].update(
            generation=8,
            drawn_uptime_ms=10005,
            available=False,
            reason="message_not_applied",
            targets=[],
        )

    guest.after_touch = edit_after_acceptance
    result = guest.dispatch(receipt, prepared)
    assert result["status"] == "succeeded"
    assert result["effect"]["callback"]["message"] == frozen


def _delayed_callback(
    guest: ExternalGuest, receipt: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> Any:
    """External input returns before transport accepts; complete only when asked."""

    def touch(*args: str, **_kwargs: Any) -> None:
        assert args[:3] == ("shell", "input", "tap")
        guest.touches += 1
        guest.files["rich-button-effect.json"].update(
            generation=7,
            uptime_ms=10001,
            state="consumed",
            action="callback",
            touch={
                "down_uptime_ms": 10000,
                "up_uptime_ms": 10001,
                "path": receipt["target"]["path"],
            },
            requests=[
                {
                    "native_request_token": 19,
                    "request_id": "http-late",
                    "callback_id": None,
                    "message_revision": None,
                }
            ],
            clipboard=None,
        )
        guest.now = 10010
        # End only the host's first bounded wait, without pretending transport completed.
        guest.android.deadline = time.monotonic() - 1

    monkeypatch.setattr(guest.android, "_adb", touch)

    def complete() -> None:
        assert "rich-button-disarm.json" not in guest.writes, (
            "native live-arm guard would reject late completion"
        )
        with World.open(Path("world")) as world:
            callback = world.create_callback(
                user_id=guest.record["chat"]["user_id"],
                chat_id=guest.record["chat"]["id"],
                message_id=guest.record["message"]["id"],
                data="same",
                request_id="http-late",
                version=4,
            )
        effect = guest.files["rich-button-effect.json"]
        effect.update(generation=8, uptime_ms=10020, state="complete")
        effect["requests"][0].update(
            callback_id=callback["id"], message_revision=guest.record["revision"]
        )
        guest.now = 10030
        guest.android.deadline = time.monotonic() + 5

    return complete


def test_completion_after_uncertain_receipt_reconciles_and_only_then_disarms(
    staged: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    guest, receipt = staged()
    prepared = guest.prepare(receipt, client_nonce="process-original")
    complete = _delayed_callback(guest, receipt, monkeypatch)
    result = guest.dispatch(receipt, prepared)
    assert result["status"] == "uncertain"
    assert result["reason"] == {"code": "effect_timeout"}
    assert "rich-button-disarm.json" not in guest.writes
    second = copy.deepcopy(receipt)
    second["operation_id"] = "another-operation"
    second["target"]["target_id"] = "another-target"
    with pytest.raises(ValueError):
        guest.prepare(second, client_nonce="process-original")
    assert guest.reconcile(receipt) is None
    complete()
    confirmed = guest.reconcile(receipt)
    assert confirmed is not None and confirmed["status"] == "succeeded"
    assert guest.writes[-1] == "rich-button-disarm.json"
    assert guest.writes.count("rich-button-arm.json") == 1
    assert guest.touches == 1
    writes = list(guest.writes)
    assert guest.reconcile(receipt) == confirmed
    assert guest.writes == writes


def test_new_observation_abandons_unresolved_arm_before_restart(
    staged: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    guest, receipt = staged()
    prepared = guest.prepare(receipt, client_nonce="process-original")
    _delayed_callback(guest, receipt, monkeypatch)
    result = guest.dispatch(receipt, prepared)
    assert result["status"] == "uncertain"
    assert "rich-button-disarm.json" not in guest.writes
    guest.android.deadline = time.monotonic() + 5
    guest.observe(guest.record)
    assert guest.writes[-2:] == ["rich-button-disarm.json", "rich-button-observe.json"]
    assert guest.reconcile(receipt) is None
    assert guest.dispatch(receipt, prepared) == result
    assert guest.touches == 1


@pytest.mark.parametrize("terminal", ["complete", "unavailable", "uncertain"])
def test_native_terminal_effect_state_cannot_switch_to_another_terminal(
    staged: Any, terminal: str
) -> None:
    guest, receipt = staged("copy")
    prepared = guest.prepare(receipt, client_nonce="process-original")
    original = copy.deepcopy(guest.files["rich-button-effect.json"])
    first = original | {"generation": 7, "state": terminal}
    second = original | {
        "generation": 8,
        "state": "complete" if terminal != "complete" else "uncertain",
    }
    state = prepared["context"]
    # Feed independently authored protocol publications through the validator; their
    # complete semantic effect is deliberately not claimed by these transition checks.
    guest._effect(state, first)
    with pytest.raises(ValueError):
        guest._effect(state, second)
    guest.abort_prepared(receipt, prepared)


def test_consumed_copy_effect_cannot_remove_established_clipboard(staged: Any) -> None:
    guest, receipt = staged("copy")
    prepared = guest.prepare(receipt, client_nonce="process-original")
    current = copy.deepcopy(guest.files["rich-button-effect.json"])
    with pytest.raises(ValueError):
        guest._effect(
            prepared["context"], current | {"generation": 7, "state": "consumed", "clipboard": None}
        )
    guest.abort_prepared(receipt, prepared)


@pytest.mark.parametrize(
    "clipboard",
    [
        {"before": "mutated baseline", "after": None},
        {"before": None, "after": "unrelated observed content"},
    ],
)
def test_consumed_copy_cannot_mutate_established_baseline(staged: Any, clipboard: Any) -> None:
    guest, receipt = staged("copy")
    prepared = guest.prepare(receipt, client_nonce="process-original")
    current = copy.deepcopy(guest.files["rich-button-effect.json"])
    with pytest.raises(ValueError):
        guest._effect(
            prepared["context"],
            current | {"generation": 7, "state": "consumed", "clipboard": clipboard},
        )
    guest.abort_prepared(receipt, prepared)


def test_known_mismatch_on_late_poll_disarms_and_stays_unrecoverable(
    staged: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    guest, receipt = staged()
    prepared = guest.prepare(receipt, client_nonce="process-original")
    complete = _delayed_callback(guest, receipt, monkeypatch)
    assert guest.dispatch(receipt, prepared)["status"] == "uncertain"
    complete()
    exact = copy.deepcopy(guest.files["rich-button-effect.json"])
    guest.files["rich-button-effect.json"]["requests"][0]["request_id"] = "unrelated-request"
    assert guest.reconcile(receipt) is None
    assert guest.writes[-1] == "rich-button-disarm.json"
    guest.files["rich-button-effect.json"] = exact | {"generation": 9}
    assert guest.reconcile(receipt) is None
    assert guest.touches == 1


def test_consumed_copy_retains_baseline_until_original_handler_evidence(
    staged: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    guest, receipt = staged("copy")
    guest.baseline = "initial plain text"
    prepared = guest.prepare(receipt, client_nonce="process-original")
    original_touch = guest.touch
    original_read = guest._read
    pending: dict[str, Any] | None = None

    def touch(*args: str, **kwargs: Any) -> Any:
        nonlocal pending
        result = original_touch(*args, **kwargs)
        pending = copy.deepcopy(guest.files["rich-button-effect.json"])
        guest.files["rich-button-effect.json"].update(
            state="consumed", clipboard={"before": guest.baseline, "after": guest.baseline}
        )
        return result

    def read(name: str) -> dict[str, Any]:
        nonlocal pending
        result: dict[str, Any] = original_read(name)
        if name == "rich-button-effect.json" and result["state"] == "consumed":
            assert pending is not None
            guest.files[name] = pending | {"generation": 8}
            pending = None
        return result

    monkeypatch.setattr(guest.android, "_adb", touch)
    guest._read = read
    result = guest.dispatch(receipt, prepared)
    assert result["status"] == "succeeded"
    assert result["evidence"]["clipboard_observation"] == {
        "before": guest.baseline,
        "after": "برداشت / copy",
    }
    assert guest.touches == 1
