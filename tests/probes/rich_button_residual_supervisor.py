"""Test-only residual native barriers around the frozen public rich-button seams."""

from __future__ import annotations

import copy
import hashlib
import json
import runpy
import socket
import threading
import time
from pathlib import Path
from typing import Any, cast

from gramlab._android_rich_buttons import AndroidRichInput
from gramlab._control import WorldControl
from gramlab.reports import _Redactor
from gramlab.world import World

PACKAGE = "org.gramlab.android"
CLIPPED_PATH = ["blocks", 4, "buttons", 0]
COPY_PATH = ["blocks", 16, "buttons", 1]
LOST_PATH = ["blocks", 17, "text", 1, "text", "button"]
LIMIT = 1024 * 1024

original_observe = AndroidRichInput.observe
original_prepare = AndroidRichInput.prepare
original_dispatch = AndroidRichInput.dispatch
original_control_init = WorldControl.__init__
record_lock = threading.Lock()
active_secrets: list[str] = []
restart_done = False
control_reply_dropped = False
guest_calls = 0
input_taps: list[dict[str, Any]] = []
record: dict[str, Any] = {
    "schema": 1,
    "bootstrap_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    "observations": [],
    "preparations": [],
    "dispatches": [],
    "restart": None,
    "control_reply": None,
    "input_taps": input_taps,
}


def persist(secrets: list[str] | None = None) -> None:
    redactor = _Redactor(active_secrets if secrets is None else secrets)
    body = json.dumps(redactor.clean(record), ensure_ascii=True, indent=2).encode()
    if len(body) > LIMIT:
        raise RuntimeError("Residual supervisor evidence exceeds bound")
    with record_lock:
        temporary = Path("rich-button-residual-supervisor.json.tmp")
        temporary.write_bytes(body)
        temporary.replace("rich-button-residual-supervisor.json")


def semantic_state() -> dict[str, Any]:
    with World.open(Path("world")) as world:
        snapshot = world.snapshot()
        return {
            "snapshot": snapshot,
            "histories": {str(chat["id"]): world.history(chat["id"]) for chat in snapshot["chats"]},
            "events": world.events(),
        }


def counted_adb(self: Any, *arguments: str, **keywords: Any) -> Any:
    global guest_calls
    guest_calls += 1
    if len(arguments) == 5 and arguments[:3] == ("shell", "input", "tap"):
        input_taps.append({"guest_call": guest_calls, "arguments": list(arguments)})
    return self.__class__._residual_original_adb(self, *arguments, **keywords)


def _pid(self: AndroidRichInput) -> int:
    values = self.android._adb("shell", "pidof", PACKAGE).stdout.split()
    if len(values) != 1 or not values[0].isdecimal():
        raise RuntimeError("Residual proof requires one original app process")
    return int(values[0])


def observe(self: AndroidRichInput, message: dict[str, Any]) -> str:
    global active_secrets
    nonce = original_observe(self, message)
    active_secrets = self.android.secrets
    sample = self._observation(self._read("rich-button-observation.json"), nonce=nonce)
    targets = [
        {
            key: copy.deepcopy(target[key])
            for key in (
                "path",
                "button",
                "label",
                "available",
                "reason",
                "local_bounds",
                "origin",
                "screen_bounds",
            )
            if key in target
        }
        for target in sample["targets"]
    ]
    accounts = self.android._adb("shell", "dumpsys", "account").stdout
    if "Accounts: 0" not in accounts:
        raise RuntimeError("Dedicated guest must have zero Android accounts")
    observation = {
        "index": len(record["observations"]),
        "world_id": sample["world_id"],
        "user_id": sample["user_id"],
        "chat_id": sample["chat_id"],
        "message_id": sample["message_id"],
        "revision": sample["revision"],
        "activation_nonce": sample["nonce"],
        "client_nonce": sample["client_nonce"],
        "pid": sample["pid"],
        "generation": sample["generation"],
        "drawn_uptime_ms": sample["drawn_uptime_ms"],
        "available": sample["available"],
        "reason": sample["reason"],
        "targets": targets,
        "accounts": "Accounts: 0",
        "guest_calls": guest_calls,
    }
    if not record["observations"]:
        screenshot = Path("rich-button-residual-rtl.png")
        self._capture_original(screenshot)
        raw = screenshot.read_bytes()
        observation["rtl_capture"] = {
            "path": screenshot.as_posix(),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw),
        }
    record["observations"].append(observation)
    persist(self.android.secrets)
    return nonce


def _restart_before_prepare(
    self: AndroidRichInput, receipt: dict[str, Any], *, client_nonce: str
) -> None:
    global restart_done
    before_sample = self._observation(
        self._read("rich-button-observation.json"), nonce=client_nonce
    )
    before_state = semantic_state()
    proof: dict[str, Any] = {
        "restart_started": True,
        "target_id": receipt["target"]["target_id"],
        "path": copy.deepcopy(receipt["target"]["path"]),
        "before": {
            "pid": _pid(self),
            "client_nonce": before_sample["client_nonce"],
            "activation_nonce": before_sample["nonce"],
            "generation": before_sample["generation"],
        },
        "semantic_before": before_state,
    }
    record["restart"] = proof
    persist(self.android.secrets)
    if self._record is None:
        raise RuntimeError("Residual restart has no selected original message")
    self.android._open_chat(
        self._record["chat"],
        before_launch=lambda: self._write("rich-button-observe.json", self._activation or {}),
    )
    deadline = min(self.android.deadline, time.monotonic() + 10)
    while True:
        sample = self._observation(self._read("rich-button-observation.json"))
        pid = _pid(self)
        if sample["client_nonce"] != client_nonce and pid != proof["before"]["pid"]:
            break
        if time.monotonic() >= deadline:
            raise RuntimeError("Original app process did not establish a fresh lifetime")
        time.sleep(0.05)
    after_state = semantic_state()
    if after_state != before_state:
        raise RuntimeError("Original app restart changed authoritative semantic state")
    proof.update(
        restart_complete=True,
        after={
            "pid": pid,
            "client_nonce": sample["client_nonce"],
            "activation_nonce": sample["nonce"],
            "generation": sample["generation"],
        },
        semantic_after=after_state,
    )
    restart_done = True
    persist(self.android.secrets)


def prepare(
    self: AndroidRichInput, receipt: dict[str, Any], *, client_nonce: str
) -> dict[str, Any]:
    target = receipt.get("target", {})
    path = target.get("path")
    if path == COPY_PATH and not restart_done:
        _restart_before_prepare(self, receipt, client_nonce=client_nonce)
    before_taps = len(input_taps)
    try:
        prepared = original_prepare(self, receipt, client_nonce=client_nonce)
    except BaseException as error:
        record["preparations"].append(
            {
                "target_id": target.get("target_id"),
                "path": copy.deepcopy(path),
                "client_nonce": client_nonce,
                "status": "rejected",
                "reason": str(error),
                "exception_class": type(error).__name__,
                "input_taps_before": before_taps,
                "input_taps_after": len(input_taps),
                "semantic_state": semantic_state(),
            }
        )
        persist(self.android.secrets)
        raise
    context = prepared["context"]
    record["preparations"].append(
        {
            "target_id": target["target_id"],
            "path": copy.deepcopy(path),
            "client_nonce": client_nonce,
            "status": "prepared",
            "pid": context["pid"],
            "activation_nonce": context["arm"]["nonce"],
            "observation_generation": context["arm"]["observation_generation"],
            "geometry": copy.deepcopy(context["geometry"]),
            "input_taps_before": before_taps,
            "input_taps_after": len(input_taps),
        }
    )
    persist(self.android.secrets)
    return prepared


def dispatch(
    self: AndroidRichInput, receipt: dict[str, Any], prepared: dict[str, Any]
) -> dict[str, Any]:
    before_taps = len(input_taps)
    before_state = semantic_state()
    result = original_dispatch(self, receipt, prepared)
    record["dispatches"].append(
        {
            "operation_id": receipt["operation_id"],
            "target_id": receipt["target"]["target_id"],
            "path": copy.deepcopy(receipt["target"]["path"]),
            "button": copy.deepcopy(receipt["target"]["button"]),
            "client_nonce": prepared["context"]["arm"]["client_nonce"],
            "pid": prepared["context"]["pid"],
            "result": copy.deepcopy(result),
            "input_taps_before": before_taps,
            "input_taps_after": len(input_taps),
            "semantic_before": before_state,
            "semantic_after": semantic_state(),
        }
    )
    persist(self.android.secrets)
    return result


def control_init(self: WorldControl, directory: Path, **keywords: Any) -> None:
    original_control_init(self, directory, **keywords)
    handler_class = cast(Any, self._server.RequestHandlerClass)
    original_reply = handler_class.reply

    def reply(handler: Any, status: int, value: dict[str, Any]) -> None:
        global control_reply_dropped
        result = value.get("result")
        button = result.get("target", {}).get("button", {}) if isinstance(result, dict) else {}
        if (
            not control_reply_dropped
            and status == 200
            and isinstance(result, dict)
            and result.get("status") == "succeeded"
            and button.get("callback_data") == "lost:reply"
        ):
            control_reply_dropped = True
            record["control_reply"] = {
                "control_reply_dropped": True,
                "status": status,
                "receipt": copy.deepcopy(result),
                "input_taps": copy.deepcopy(input_taps),
                "semantic_state": semantic_state(),
            }
            persist()
            handler.close_connection = True
            try:
                handler.connection.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            handler.connection.close()
            return
        original_reply(handler, status, value)

    handler_class.reply = reply


def install() -> None:
    from gramlab._android import Android

    Android._residual_original_adb = Android._adb  # type: ignore[attr-defined]
    Android._adb = counted_adb  # type: ignore[method-assign]
    AndroidRichInput.observe = observe  # type: ignore[assignment,method-assign]
    AndroidRichInput.prepare = prepare  # type: ignore[method-assign]
    AndroidRichInput.dispatch = dispatch  # type: ignore[method-assign]
    WorldControl.__init__ = control_init  # type: ignore[method-assign]


if __name__ == "__main__":
    install()
    runpy.run_module("gramlab._run", run_name="__main__")
