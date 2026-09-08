"""Trusted host consumption of app-private original rich-button observations.

The registry owns authorization, serialization and durable dispatch intent. This adapter
never synthesizes actions: the only input is one ordinary guest touch per operation.
"""

from __future__ import annotations

import base64
import copy
import hashlib
import json
import math
import re
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any

from gramlab._android import Android
from gramlab.reports import _png, _Redactor
from gramlab.world import World

_PACKAGE = "org.gramlab.android"
_LIMIT = 1024 * 1024
_ID = re.compile(r"[A-Za-z0-9_-]{1,128}")
_ACTIVATION = {"schema", "nonce", "world_id", "user_id", "chat_id", "message_id", "revision"}
_IDENTITY = _ACTIVATION | {"client_nonce", "operation_id", "path"}
_UNAVAILABLE = {
    "not_bound",
    "message_not_applied",
    "message_not_drawn",
    "offscreen",
    "clipped",
    "window_unfocused",
    "unsupported_layout",
    "unmapped_object",
    "ambiguous_object",
    "stale_activation",
}
_EFFECT_REASONS = {
    "wrong_identity",
    "revision_changed",
    "unavailable_target",
    "arm_conflict",
    "unmapped_dispatch",
    "multiple_dispatches",
    "request_mismatch",
    "clipboard_unavailable",
    "component_stopped",
}
_FILES = {
    "rich-button-observe.json",
    "rich-button-observation.json",
    "rich-button-arm.json",
    "rich-button-effect.json",
    "rich-button-disarm.json",
}


def _require(condition: bool, code: str = "target_unavailable") -> None:
    if not condition:
        raise ValueError(code)


def _fields(value: Any, keys: set[str]) -> None:
    _require(type(value) is dict and value.keys() == keys)


def _integer(value: Any, minimum: int = 0) -> bool:
    return type(value) is int and minimum <= value < 2**63


def _token(value: Any) -> bool:
    return type(value) is str and _ID.fullmatch(value) is not None


def _path(value: Any) -> bool:
    return (
        type(value) is list
        and bool(value)
        and all((type(part) is str and bool(part)) or _integer(part) for part in value)
    )


def _encoded(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode(
        "utf-8"
    )


def _strict_json(raw: bytes) -> dict[str, Any]:
    _require(0 < len(raw) <= _LIMIT)

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            _require(key not in result)
            result[key] = value
        return result

    def invalid(_value: str) -> Any:
        raise ValueError("target_unavailable")

    try:
        result = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=invalid)
        _require(type(result) is dict)
        _encoded(result)  # Reject escaped unpaired surrogates too.
    except (UnicodeError, RecursionError, json.JSONDecodeError) as error:
        raise ValueError("target_unavailable") from error
    return dict(result)


def _label(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "".join(_label(item) for item in value)
    _require(isinstance(value, dict) and isinstance(value.get("alternative_text"), str))
    return str(value["alternative_text"])


def _occurrences(rich: dict[str, Any]) -> list[dict[str, Any]]:
    """Independent semantic mapping check; never used to reconstruct native placement."""
    result: list[dict[str, Any]] = []

    def visit(value: Any, path: list[str | int]) -> None:
        if isinstance(value, list):
            for index, child in enumerate(value):
                visit(child, [*path, index])
        elif isinstance(value, dict):
            if "button" in value:
                button = value["button"]
                result.append(
                    {"path": [*path, "button"], "button": button, "label": _label(button["text"])}
                )
            if "buttons" in value:
                for index, button in enumerate(value["buttons"]):
                    result.append(
                        {
                            "path": [*path, "buttons", index],
                            "button": button,
                            "label": _label(button["text"]),
                        }
                    )
            # All admitted action-bearing containers, in canonical document order.
            for key in ("summary", "blocks", "text", "caption", "items", "cells", "credit"):
                if key in value:
                    visit(value[key], [*path, key])

    visit(rich, [])
    return result


def _clipboard(value: Any) -> None:
    _fields(value, {"before", "after"})
    for text in value.values():
        _require(text is None or (type(text) is str and len(text.encode("utf-8")) <= 4096))


class AndroidRichInput:
    def __init__(self, android: Android) -> None:
        self.android = android
        self._record: dict[str, Any] | None = None
        self._activation: dict[str, Any] | None = None
        self._nonce: str | None = None
        self._operations: dict[str, dict[str, Any]] = {}
        self._live: str | None = None

    def _read(self, name: str) -> dict[str, Any]:
        _require(name in _FILES)
        # Shell v2 preserves remote exit status and separates stderr; exec-out
        # escapes the quoted script again and cannot report the missing-file status.
        # Base64 preserves strict original UTF-8 despite Android._adb's text decoder.
        result = self.android._adb(
            "shell",
            "-T",
            "run-as",
            _PACKAGE,
            "sh",
            "-c",
            f"'if [ -f files/gramlab/{name} ]; then "
            f"head -c {_LIMIT + 1} files/gramlab/{name} | base64; else exit 44; fi'",
            check=False,
        )
        if result.returncode == 44:
            raise FileNotFoundError(name)
        if result.returncode:
            raise RuntimeError("Private guest observation read failed")
        try:
            raw = base64.b64decode("".join(result.stdout.split()), validate=True)
        except ValueError as error:
            raise ValueError("target_unavailable") from error
        try:
            return _strict_json(raw)
        except ValueError:
            if self._live is not None:
                state = self._operations[self._live]
                state["candidate"] = {
                    "diagnostic": "invalid_private_json_framing",
                    "source": name,
                    "bytes_read": len(raw),
                    "exceeds_limit": len(raw) > _LIMIT,
                    "sha256_of_read_prefix": hashlib.sha256(raw).hexdigest(),
                }
                self._diagnostic(state)
            raise

    def _write(self, name: str, value: dict[str, Any]) -> None:
        _require(name in _FILES)
        raw = _encoded(value)
        _require(len(raw) <= _LIMIT)
        self.android._adb(
            "shell",
            "-T",
            "run-as",
            _PACKAGE,
            "sh",
            "-c",
            f"'mkdir -p files/gramlab && cat > files/gramlab/{name}.tmp && "
            f"mv files/gramlab/{name}.tmp files/gramlab/{name}'",
            input=raw.decode("utf-8"),
        )

    def _guest_state(self) -> tuple[int, int]:
        pids = self.android._adb("shell", "pidof", _PACKAGE).stdout.split()
        _require(len(pids) == 1 and pids[0].isdecimal(), "client_restarted")
        uptime = self.android._adb("shell", "cat", "/proc/uptime").stdout.split()
        _require(bool(uptime))
        seconds = float(uptime[0])
        _require(math.isfinite(seconds) and seconds >= 0)
        windows = self.android._adb("shell", "dumpsys", "window", "displays").stdout
        focused = re.findall(r"mCurrentFocus=Window\{[^\n]*\bu\d+ ([^\s}]+)", windows)
        _require(len(focused) == 1 and focused[0].startswith(_PACKAGE + "/"))
        return int(pids[0]), int(seconds * 1000)

    def _capture_original(self, path: Path) -> None:
        screenshot = subprocess.run(  # noqa: S603 — dedicated serial, original unmodified PNG
            [
                self.android.profile.executables["adb"],
                "-s",
                "emulator-5554",
                "exec-out",
                "screencap",
                "-p",
            ],
            capture_output=True,
            timeout=self.android._remaining(15),
            check=True,
        ).stdout
        _png(screenshot, _Redactor(self.android.secrets))
        with path.open("xb") as output:
            output.write(screenshot)

    def _current(self, record: dict[str, Any]) -> dict[str, Any]:
        _fields(record, {"chat", "message", "revision"})
        chat, message = record["chat"], record["message"]
        _require(isinstance(chat, dict) and isinstance(message, dict), "access_denied")
        _require(_integer(record["revision"], 1), "message_revision_changed")
        with World.open(Path("world")) as world:
            snapshot = world.client_snapshot(chat["user_id"], version=4)
        _require(chat in snapshot["chats"], "access_denied")
        _require(
            message["sender_id"] == chat["bot_id"] and message["chat_id"] == chat["id"],
            "access_denied",
        )
        revisions = [
            r
            for r in snapshot["message_revisions"]
            if r["chat_id"] == chat["id"] and r["message_id"] == message["id"]
        ]
        _require(
            revisions
            == [
                {"chat_id": chat["id"], "message_id": message["id"], "revision": record["revision"]}
            ]
            and message in snapshot["messages"],
            "message_revision_changed",
        )
        return snapshot

    def _observation(self, sample: dict[str, Any], *, nonce: str | None = None) -> dict[str, Any]:
        _fields(
            sample,
            _ACTIVATION
            | {
                "client_nonce",
                "pid",
                "generation",
                "drawn_uptime_ms",
                "available",
                "reason",
                "targets",
            },
        )
        _require(type(sample["schema"]) is int and sample["schema"] == 1)
        for field in ("user_id", "chat_id", "message_id", "revision", "pid"):
            _require(_integer(sample[field], 1))
        _require(_token(sample["nonce"]) and _token(sample["client_nonce"]))
        _require(_integer(sample["generation"]) and _integer(sample["drawn_uptime_ms"]))
        if self._activation is None or self._record is None:
            raise ValueError("client_restarted")
        _require(sample["revision"] == self._activation["revision"], "message_revision_changed")
        _require(all(sample[key] == value for key, value in self._activation.items()))
        if nonce is not None:
            _require(sample["client_nonce"] == nonce, "client_restarted")
        _require(type(sample["available"]) is bool)
        _require(
            sample["reason"] is None
            if sample["available"]
            else type(sample["reason"]) is str and sample["reason"] in _UNAVAILABLE
        )
        _require(type(sample["targets"]) is list)
        expected = _occurrences(self._record["message"]["rich_message"])
        mapped: list[dict[str, Any]] = []
        for target in sample["targets"]:
            base = {"path", "button", "label", "available", "reason"}
            geometry = {"local_bounds", "origin", "screen_bounds"}
            _require(type(target) is dict and target.keys() in (base, base | geometry))
            _require(_path(target["path"]) and type(target["available"]) is bool)
            _require(
                target["reason"] is None
                if target["available"]
                else type(target["reason"]) is str and target["reason"] in _UNAVAILABLE
            )
            _require(not target["available"] or geometry <= target.keys())
            for key, length in (("local_bounds", 4), ("origin", 2), ("screen_bounds", 4)):
                if key in target:
                    numbers = target[key]
                    _require(type(numbers) is list and len(numbers) == length)
                    _require(
                        all(
                            type(n) in (int, float) and abs(n) <= 1000000 and math.isfinite(n)
                            for n in numbers
                        )
                    )
                    if length == 4:
                        _require(numbers[0] < numbers[2] and numbers[1] < numbers[3])
            mapped.append({key: target[key] for key in ("path", "button", "label")})
        _require(mapped == expected if sample["available"] else not mapped or mapped == expected)
        return sample

    def observe(self, record: dict[str, Any]) -> str:
        _require(self.android._bridge_version == 4)
        snapshot = self._current(record)
        if self._live is not None:
            previous = self._operations[self._live]
            _require(previous["dispatched"] and previous["result"] is not None)
            _require(previous["result"]["status"] == "uncertain" and not previous["mismatch"])
            # A deliberate observation already authorizes a cold launch. Abandon
            # this unresolved lifetime before disarming it; never recover its input.
            previous["abandoned"] = True
            self.android.observations.setdefault("rich_button_abandoned", {})[
                previous["arm"]["operation_id"]
            ] = {"reason": "new_observation"}
            self._disarm(previous)
        self._record = copy.deepcopy(record)
        self._activation = {
            "schema": 1,
            "nonce": uuid.uuid4().hex,
            "world_id": snapshot["world_id"],
            "user_id": record["chat"]["user_id"],
            "chat_id": record["chat"]["id"],
            "message_id": record["message"]["id"],
            "revision": record["revision"],
        }
        self.android._open_chat(
            record["chat"],
            before_launch=lambda: self._write("rich-button-observe.json", self._activation or {}),
        )
        end = min(self.android.deadline, time.monotonic() + 10)
        while True:
            try:
                sample = self._observation(self._read("rich-button-observation.json"))
                pid, now = self._guest_state()
                _require(pid == sample["pid"], "client_restarted")
                _require(0 <= now - sample["drawn_uptime_ms"] <= 5000)
                # WindowManager can already report this app while its retained
                # draw still predates focus. Wait for native focus publication;
                # genuinely hidden/offscreen targets remain explicitly unavailable.
                _require(sample["reason"] != "window_unfocused")
                _require(all(t["reason"] != "window_unfocused" for t in sample["targets"]))
                self._current(record)
                self._nonce = str(sample["client_nonce"])
                return self._nonce
            except (ValueError, RuntimeError, FileNotFoundError):
                if time.monotonic() >= end:
                    raise
                time.sleep(0.05)

    def _fresh(self, state: dict[str, Any]) -> dict[str, Any]:
        snapshot = self._current(state["record"])
        _require(snapshot["world_id"] == state["arm"]["world_id"], "client_restarted")
        _require(
            self.android._persona == state["arm"]["user_id"]
            and self.android._active_chat == state["arm"]["chat_id"],
            "client_restarted",
        )
        _require(self._read("rich-button-observe.json") == self._activation, "client_restarted")
        sample = self._observation(
            self._read("rich-button-observation.json"), nonce=state["arm"]["client_nonce"]
        )
        pid, now = self._guest_state()
        _require(pid == sample["pid"] == state["pid"], "client_restarted")
        _require(sample["generation"] >= state["observation"]["generation"])
        _require(0 <= now - sample["drawn_uptime_ms"] <= 5000)
        _require(sample["available"])
        found = [
            target for target in sample["targets"] if target["path"] == state["target"]["path"]
        ]
        _require(len(found) == 1 and found[0]["available"])
        target = found[0]
        _require(all(target[key] == state["target"][key] for key in ("path", "button", "label")))
        if "geometry" in state:
            _require(
                {key: target[key] for key in ("local_bounds", "origin", "screen_bounds")}
                == state["geometry"]
            )
        left, top, right, bottom = target["screen_bounds"]
        _require(0 <= left < right <= 320 and 0 <= top < bottom <= 640)
        state["now"] = now
        return sample

    def _retain(self, state: dict[str, Any], kind: str, sample: dict[str, Any]) -> str:
        raw = _encoded(sample)
        digest = hashlib.sha256(raw).hexdigest()[:16]
        path: Path = state["directory"] / f"{kind}-{sample['generation']}-{digest}.json"
        _require(len(raw) <= _LIMIT)
        if path.exists():
            _require(path.read_bytes() == raw)
        else:
            with path.open("xb") as output:
                output.write(raw)
        _require(len(path.as_posix().encode("utf-8")) <= 256)
        state["evidence"]["native"][kind] = path.as_posix()
        return path.as_posix()

    def prepare(self, receipt: dict[str, Any], *, client_nonce: str) -> dict[str, Any]:
        _require(_token(receipt["operation_id"]) and _token(client_nonce))
        _require(receipt["operation_id"] not in self._operations and self._live is None)
        _require(client_nonce == self._nonce and self._record is not None, "client_restarted")
        if self._record is None or self._activation is None:
            raise ValueError("client_restarted")
        target = receipt["target"]
        _fields(
            target,
            {"target_id", "chat_id", "message_id", "message_revision", "path", "button", "label"},
        )
        _require(_token(target["target_id"]) and _path(target["path"]))
        for field in ("chat_id", "message_id", "message_revision"):
            _require(_integer(target[field], 1))
        record = self._record
        _require(
            target["chat_id"] == record["chat"]["id"]
            and target["message_id"] == record["message"]["id"],
            "access_denied",
        )
        _require(target["message_revision"] == record["revision"], "message_revision_changed")
        sample = self._observation(self._read("rich-button-observation.json"), nonce=client_nonce)
        directory = Path("rich-buttons") / receipt["operation_id"]
        directory.mkdir(parents=True, mode=0o700)
        arm = self._activation | {
            "client_nonce": client_nonce,
            "operation_id": receipt["operation_id"],
            "path": target["path"],
            "observation_generation": sample["generation"],
        }
        state: dict[str, Any] = {
            "arm": arm,
            "target": copy.deepcopy(target),
            "record": copy.deepcopy(record),
            "pid": sample["pid"],
            "observation": sample,
            "directory": directory,
            "evidence": {
                "mode": "headless-android",
                "world_event_sequences": [],
                "clipboard_observation": None,
                "native": {"observation": None, "effect": None, "captures": []},
            },
            "dispatched": False,
            "mismatch": False,
            "result": None,
            "effect": None,
            "quiet_since": None,
        }
        sample = self._fresh(state)
        state["observation"] = sample
        arm["observation_generation"] = sample["generation"]
        selected = next(t for t in sample["targets"] if t["path"] == target["path"])
        state["geometry"] = {
            key: selected[key] for key in ("local_bounds", "origin", "screen_bounds")
        }
        self._retain(state, "observation", sample)
        capture = directory / "before.png"
        self._capture_original(capture)
        state["evidence"]["native"]["captures"].append(capture.as_posix())
        self._fresh(state)
        self._operations[receipt["operation_id"]] = state
        self._live = receipt["operation_id"]
        try:
            self._write("rich-button-arm.json", arm)
            end = min(self.android.deadline, time.monotonic() + 5)
            while True:
                try:
                    pending = self._read("rich-button-effect.json")
                except FileNotFoundError:
                    pending = None
                # The serialized guest writer may still expose an older operation's
                # immutable result until the new arm is acknowledged on its UI thread.
                if pending is None or pending.get("operation_id") != arm["operation_id"]:
                    _require(time.monotonic() < end)
                    time.sleep(0.05)
                    continue
                effect = self._effect(state, pending)
                self._ready(state, effect)
                if effect["generation"] >= arm["observation_generation"]:
                    break
                _require(time.monotonic() < end)
                time.sleep(0.05)
            state["baseline"] = effect["clipboard"]
            state["observation"] = self._fresh(state)
            with World.open(Path("world")) as world:
                state["world_before"] = world.client_snapshot(arm["user_id"], version=4)
            # A prospective receipt is only a conservative journal-size reservation.
            prospective = copy.deepcopy(receipt)
            prospective.update(
                status="succeeded",
                dispatch="dispatched",
                reason=None,
                evidence=copy.deepcopy(state["evidence"]),
            )
            if "callback_data" in target["button"]:
                callback = {
                    "id": "x" * 128,
                    "user_id": arm["user_id"],
                    "chat_id": arm["chat_id"],
                    "message": record["message"],
                    "data": target["button"]["callback_data"],
                    "chat_instance": "0" * 64,
                    "answer": None,
                }
                prospective["effect"] = {
                    "kind": "callback",
                    "callback": callback,
                    "event_sequence": 2**63 - 1,
                }
                prospective["evidence"]["world_event_sequences"] = [2**63 - 1]
            else:
                prospective["effect"] = (
                    {"kind": "copy", "text": target["button"]["copy_text"]["text"]}
                    if "copy_text" in target["button"]
                    else {"kind": "none", "reason": "disabled"}
                )
                prospective["evidence"]["clipboard_observation"] = {
                    "before": "\x00" * 4096,
                    "after": "\x00" * 4096,
                }
            prospective["evidence"]["native"] = {
                "observation": "x" * 256,
                "effect": "x" * 256,
                "captures": ["x" * 256] * 2,
            }
            return {"context": state, "receipt_for_size_check": prospective}
        except Exception:
            self._disarm(state)
            raise

    def abort_prepared(self, receipt: dict[str, Any], prepared: dict[str, Any]) -> None:
        """Release only this exact arm after registry preflight/intent failure."""
        state = self._operations[receipt["operation_id"]]
        _require(prepared["context"] is state and receipt["target"] == state["target"])
        _require(not state["dispatched"])
        state["aborted"] = True
        self._disarm(state)

    def _ready(self, state: dict[str, Any], effect: dict[str, Any]) -> None:
        _require(effect["state"] == "armed" and effect["reason"] is None)
        _require(effect["action"] is None and not effect["requests"])
        touch = effect["touch"]
        _require(
            touch is None or (touch["down_uptime_ms"] is None and touch["up_uptime_ms"] is None)
        )
        if "callback_data" not in state["target"]["button"]:
            _clipboard(effect["clipboard"])
            _require(effect["clipboard"]["before"] == effect["clipboard"]["after"])
            if "baseline" in state:
                _require(effect["clipboard"] == state["baseline"])

    def _effect(self, state: dict[str, Any], value: dict[str, Any]) -> dict[str, Any]:
        state["candidate"] = copy.deepcopy(value)
        _fields(
            value,
            _IDENTITY
            | {
                "generation",
                "uptime_ms",
                "state",
                "reason",
                "touch",
                "action",
                "requests",
                "clipboard",
            },
        )
        _require(type(value["schema"]) is int and value["schema"] == 1)
        for field in ("user_id", "chat_id", "message_id", "revision"):
            _require(_integer(value[field], 1))
        for field in ("nonce", "client_nonce", "operation_id"):
            _require(_token(value[field]))
        _require(_path(value["path"]))
        _require(_integer(value["generation"]) and _integer(value["uptime_ms"]))
        _require(value["state"] in ("armed", "consumed", "complete", "unavailable", "uncertain"))
        _require(
            value["reason"] is None
            or (type(value["reason"]) is str and value["reason"] in _EFFECT_REASONS)
        )
        _require(value["action"] in (None, "callback", "copy", "disabled_suppressed"))
        touch = value["touch"]
        if touch is not None:
            _fields(touch, {"down_uptime_ms", "up_uptime_ms", "path"})
            _require(_path(touch["path"]) and touch["path"] == state["arm"]["path"])
            for key in ("down_uptime_ms", "up_uptime_ms"):
                _require(
                    touch[key] is None
                    or (_integer(touch[key]) and touch[key] <= value["uptime_ms"])
                )
            _require(
                touch["up_uptime_ms"] is None
                or (
                    touch["down_uptime_ms"] is not None
                    and touch["down_uptime_ms"] <= touch["up_uptime_ms"]
                )
            )
        _require(type(value["requests"]) is list and len(value["requests"]) <= 2)
        for request in value["requests"]:
            _fields(
                request, {"native_request_token", "request_id", "callback_id", "message_revision"}
            )
            for key in ("native_request_token", "message_revision"):
                _require(request[key] is None or _integer(request[key], 1))
            for key in ("request_id", "callback_id"):
                _require(request[key] is None or _token(request[key]))
        if value["clipboard"] is not None:
            _clipboard(value["clipboard"])
        self._retain(state, "effect", value)
        _require(all(value[key] == state["arm"][key] for key in _IDENTITY))
        previous = state["effect"]
        if previous is not None:
            if previous["clipboard"] is not None:
                _require(value["clipboard"] is not None)
                _require(previous["clipboard"]["before"] == value["clipboard"]["before"])
                if previous["clipboard"]["after"] != value["clipboard"]["after"]:
                    button = state["target"]["button"]
                    _require(previous["clipboard"]["after"] == previous["clipboard"]["before"])
                    _require("copy_text" in button and value["action"] == "copy")
                    _require(value["clipboard"]["after"] == button["copy_text"]["text"])
                    _require(touch is not None and touch["up_uptime_ms"] is not None)
                if previous["state"] in ("complete", "unavailable", "uncertain"):
                    _require(previous["clipboard"] == value["clipboard"])
            _require(value["generation"] >= previous["generation"])
            _require(value["uptime_ms"] >= previous["uptime_ms"])
            _require(value["generation"] != previous["generation"] or value == previous)
            if previous["state"] in ("complete", "unavailable", "uncertain"):
                _require(value["state"] == previous["state"])
            elif previous["state"] == "consumed":
                _require(value["state"] != "armed")
            _require(previous["reason"] is None or value["reason"] == previous["reason"])
            if previous["touch"] is not None:
                _require(touch is not None)
                for key in ("down_uptime_ms", "up_uptime_ms"):
                    _require(previous["touch"][key] is None or touch[key] == previous["touch"][key])
            _require(previous["action"] is None or previous["action"] == value["action"])
            _require(len(value["requests"]) >= len(previous["requests"]))
            for old, new in zip(previous["requests"], value["requests"], strict=False):
                _require(all(val is None or new[key] == val for key, val in old.items()))
        state["effect"] = copy.deepcopy(value)
        return value

    def _disarm(self, state: dict[str, Any]) -> None:
        if state.get("disarmed"):
            return
        self._write(
            "rich-button-disarm.json",
            {key: state["arm"][key] for key in ("schema", "nonce", "client_nonce", "operation_id")},
        )
        state["disarmed"] = True
        if self._live == state["arm"]["operation_id"]:
            self._live = None

    def _finish(self, state: dict[str, Any]) -> None:
        try:
            self._disarm(state)
        except (OSError, RuntimeError, subprocess.SubprocessError):
            # Keep the known effect and the outstanding arm; another input cannot
            # start while cleanup remains unconfirmed.
            self.android.observations["rich_button_disarm_pending"] = state["arm"]["operation_id"]

    def _diagnostic(self, state: dict[str, Any]) -> None:
        value = state.get("candidate")
        if value is None:
            return
        raw = _encoded(value)
        if len(raw) > _LIMIT:
            return
        digest = hashlib.sha256(raw).hexdigest()[:16]
        path: Path = state["directory"] / f"unvalidated-effect-{digest}.json"
        if not path.exists():
            path.write_bytes(raw)
        self.android.observations.setdefault("rich_button_diagnostics", {})[
            state["arm"]["operation_id"]
        ] = path.as_posix()

    def _outcome(
        self, state: dict[str, Any], effect: dict[str, Any] | None, reason: str | None = None
    ) -> dict[str, Any]:
        return {
            "status": "succeeded" if effect is not None else "uncertain",
            "dispatch": "dispatched" if state["dispatched"] else "intent_recorded",
            "effect": effect,
            "reason": {"code": reason} if reason else None,
            "evidence": copy.deepcopy(state["evidence"]),
        }

    def _confirm(self, state: dict[str, Any]) -> dict[str, Any] | None:
        value = self._effect(state, self._read("rich-button-effect.json"))
        # Validate the accompanying private observation against this operation's
        # activation and frozen mapping. A bot edit may make that old revision
        # unavailable; the accepted callback's frozen World revision is authoritative.
        observed = self._read("rich-button-observation.json")
        state["candidate"] = {"source": "rich-button-observation.json", "observation": observed}
        observed = self._observation(observed, nonce=state["arm"]["client_nonce"])
        pid, now = self._guest_state()
        _require(pid == observed["pid"] == state["pid"])
        _require(self.android._persona == state["arm"]["user_id"])
        _require(self.android._active_chat == state["arm"]["chat_id"])
        _require(
            self._read("rich-button-observe.json")
            == {key: state["arm"][key] for key in _ACTIVATION}
        )
        previous = state.get("post_observation", state["observation"])
        _require(observed["generation"] >= previous["generation"])
        _require(observed["drawn_uptime_ms"] >= previous["drawn_uptime_ms"])
        _require(observed["generation"] != previous["generation"] or observed == previous)
        _require(0 <= now - observed["drawn_uptime_ms"] <= 5000)
        state["post_observation"] = copy.deepcopy(observed)
        state["candidate"] = value
        _require(value["uptime_ms"] <= now)
        _require(value["reason"] is None)
        _require(len(value["requests"]) <= 1)
        if value["state"] != "complete":
            return None
        target, arm = state["target"], state["arm"]
        touch = value["touch"]
        _require(touch is not None and touch["down_uptime_ms"] is not None)
        _require(touch["down_uptime_ms"] >= state["armed_uptime"])
        with World.open(Path("world")) as world:
            _require(world.world_id == arm["world_id"])
            _require(world.get_chat(arm["chat_id"]) == state["record"]["chat"])
            events = world.events(after=state["world_before"]["cursor"])
            if "callback_data" in target["button"]:
                _require(
                    value["action"] == "callback"
                    and touch["up_uptime_ms"] is not None
                    and len(value["requests"]) == 1
                )
                chain = value["requests"][0]
                if any(part is None for part in chain.values()):
                    return None
                callback = world.get_callback(
                    user_id=arm["user_id"], callback_id=chain["callback_id"]
                )
                dependencies = world.callback_dependencies(arm["user_id"], callback, version=4)
                _require(
                    dependencies["message_revision"] == chain["message_revision"] == arm["revision"]
                )
                _require(
                    callback["message"] == state["record"]["message"]
                    and callback["data"] == target["button"]["callback_data"]
                )
                _require(
                    callback["chat_id"] == arm["chat_id"] and callback["user_id"] == arm["user_id"]
                )
                frozen = callback | {"answer": None}
                matching = [
                    event
                    for event in events
                    if event["type"] == "callback.created"
                    and event["data"] | {"answer": None} == frozen
                ]
                _require(len(matching) == 1)
                sequence = matching[0]["sequence"]
                state["evidence"]["world_event_sequences"] = [sequence]
                return self._outcome(
                    state, {"kind": "callback", "callback": frozen, "event_sequence": sequence}
                )
            _require(not value["requests"])
            _clipboard(value["clipboard"])
            _require(value["clipboard"]["before"] == state["baseline"]["before"])
            current = world.client_snapshot(arm["user_id"], version=4)
            _require(current == state["world_before"] and not events)
        if "copy_text" in target["button"]:
            _require(value["action"] == "copy" and touch["up_uptime_ms"] is not None)
            _require(value["clipboard"]["after"] == target["button"]["copy_text"]["text"])
            effect = {"kind": "copy", "text": value["clipboard"]["after"]}
        else:
            _require(value["action"] == "disabled_suppressed")
            _require(value["clipboard"]["before"] == value["clipboard"]["after"])
            effect = {"kind": "none", "reason": "disabled"}
        if state["quiet_since"] is None:
            state["quiet_since"] = time.monotonic()
        if time.monotonic() - state["quiet_since"] < 0.25:
            return None
        state["evidence"]["clipboard_observation"] = copy.deepcopy(value["clipboard"])
        return self._outcome(state, effect)

    def dispatch(self, receipt: dict[str, Any], prepared: dict[str, Any]) -> dict[str, Any]:
        state = self._operations[receipt["operation_id"]]
        _require(prepared["context"] is state and receipt["target"] == state["target"])
        _require(not state.get("aborted"))
        if state["result"] is not None:
            return dict(copy.deepcopy(state["result"]))
        if state["dispatched"]:
            return self._outcome(state, None, "dispatch_unconfirmed")
        # The caller has recorded durable intent. Its receipt preflight and fsync
        # can take time; validate the exact arm and repeat freshness after that gap.
        # A failed check is uncertainty with intent_recorded, never a rejection.
        try:
            armed = self._read("rich-button-arm.json")
            _fields(armed, set(state["arm"]))
            for field in ("schema", "user_id", "chat_id", "message_id", "revision"):
                _require(_integer(armed[field], 1))
            _require(_path(armed["path"]) and _integer(armed["observation_generation"]))
            _require(armed == state["arm"])
            effect = self._effect(state, self._read("rich-button-effect.json"))
            self._ready(state, effect)
            _require(effect["generation"] >= armed["observation_generation"])
            state["observation"] = self._fresh(state)
            _require(effect["uptime_ms"] <= state["now"])
            state["armed_uptime"] = effect["uptime_ms"]
            left, top, right, bottom = state["geometry"]["screen_bounds"]
            # Mark handoff immediately before the sole ordinary input command.
            state["dispatched"] = True
            self.android._adb(
                "shell", "input", "tap", str((left + right) / 2), str((top + bottom) / 2)
            )
            end = min(self.android.deadline, time.monotonic() + 10)
            while True:
                result = self._confirm(state)
                if result is not None:
                    state["result"] = result
                    self._finish(state)
                    return copy.deepcopy(result)
                if time.monotonic() >= end:
                    break
                time.sleep(0.05)
            result = self._outcome(state, None, "effect_timeout")
        except (ValueError, KeyError, TypeError, UnicodeError) as error:
            state["mismatch"] = True
            self._diagnostic(state)
            result = self._outcome(state, None, "effect_mismatch")
            self.android.observations["rich_button_failure"] = type(error).__name__
        except (OSError, RuntimeError, subprocess.SubprocessError):
            result = self._outcome(state, None, "dispatch_unconfirmed")
        state["result"] = result
        if not state["dispatched"] or state["mismatch"]:
            self._finish(state)
        return copy.deepcopy(result)

    def reconcile(self, receipt: dict[str, Any]) -> dict[str, Any] | None:
        state = self._operations.get(receipt["operation_id"])
        if state is None or state["mismatch"] or state.get("abandoned") or not state["dispatched"]:
            return None
        if state["result"] is not None and state["result"]["status"] == "succeeded":
            return dict(copy.deepcopy(state["result"]))
        try:
            result = self._confirm(state)
        except (ValueError, KeyError, TypeError, UnicodeError):
            state["mismatch"] = True
            self._diagnostic(state)
            self._finish(state)
            return None
        except (OSError, RuntimeError, subprocess.SubprocessError):
            return None
        if result is not None:
            state["result"] = result
            self._finish(state)
        return copy.deepcopy(result)
