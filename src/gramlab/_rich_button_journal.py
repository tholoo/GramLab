"""Durable, bounded evidence journal for single-use rich-button operations."""

from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import re
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any

from gramlab._rich_buttons import occurrences

_SCHEMA = 1
_NAME = "rich-button-journal.jsonl"
_MAX_TARGETS = 64
_MAX_RECORD = 128 * 1024
_TARGET_RESERVATION = 1024 * 1024
_MAX_JOURNAL = 80 * 1024 * 1024
# Every record consumes at least one byte, so the byte cap is also a conservative
# upper bound for every future sequence value and its encoded width.
_MAX_SEQUENCE = _MAX_JOURNAL
_ID = re.compile(r"[A-Za-z0-9_-]{1,128}\Z")
_PRE_REASONS = frozenset(
    {
        "message_revision_changed",
        "access_denied",
        "client_restarted",
        "target_unavailable",
        "component_stopped",
    }
)
_UNCERTAIN_REASONS = frozenset(
    {"dispatch_unconfirmed", "effect_timeout", "effect_mismatch", "component_stopped"}
)


class JournalLimitError(ValueError):
    """A prospective record or allocation cannot fit its fixed byte reservation."""


def _object(value: Any, keys: set[str], context: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError(f"Invalid rich-button {context}")
    return value


def _identifier(value: Any, context: str) -> str:
    if not isinstance(value, str) or _ID.fullmatch(value) is None:
        raise ValueError(f"Invalid rich-button {context}")
    return value


def _positive(value: Any, context: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 < value < 2**63:
        raise ValueError(f"Invalid rich-button {context}")
    return int(value)


def _timestamp(value: Any, context: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value < 2**63:
        raise ValueError(f"Invalid rich-button {context}")
    return int(value)


def _bounded_text(value: Any, context: str, limit: int = 4096) -> str:
    if not isinstance(value, str) or len(value.encode("utf-8")) > limit:
        raise ValueError(f"Invalid rich-button {context}")
    return value


def _path(value: Any) -> list[str | int]:
    if not isinstance(value, list) or not value:
        raise ValueError("Invalid rich-button path")
    result: list[str | int] = []
    for component in value:
        if isinstance(component, bool) or not isinstance(component, (str, int)):
            raise ValueError("Invalid rich-button path")
        if isinstance(component, int) and component < 0:
            raise ValueError("Invalid rich-button path")
        result.append(component)
    return result


def _button_text(value: Any) -> None:
    if isinstance(value, str):
        return
    if isinstance(value, list):
        if not value:
            raise ValueError("Invalid rich-button button text")
        for child in value:
            _button_text(child)
        return
    item = _object(
        value,
        {"type", "custom_emoji_id", "alternative_text"},
        "button text",
    )
    if item["type"] != "custom_emoji":
        raise ValueError("Invalid rich-button button text")
    _identifier(item["custom_emoji_id"], "custom emoji identifier")
    if not isinstance(item["alternative_text"], str):
        raise ValueError("Invalid rich-button button text")


def _button(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or "text" not in value:
        raise ValueError("Invalid rich-button button")
    allowed = {"text", "style", "callback_data", "copy_text", "disabled"}
    if set(value) - allowed:
        raise ValueError("Invalid rich-button button")
    actions = set(value) & {"callback_data", "copy_text", "disabled"}
    if len(actions) != 1:
        raise ValueError("Invalid rich-button button")
    _button_text(value["text"])
    if "style" in value and not isinstance(value["style"], str):
        raise ValueError("Invalid rich-button button")
    action = next(iter(actions))
    if action == "callback_data" and not isinstance(value[action], str):
        raise ValueError("Invalid rich-button button")
    if action == "copy_text":
        copied = _object(value[action], {"text"}, "copy action")
        _bounded_text(copied["text"], "copy text")
    if action == "disabled" and value[action] != {}:
        raise ValueError("Invalid rich-button button")
    return copy.deepcopy(value)


def _target(value: Any, *, complete: bool) -> dict[str, Any]:
    keys = {"target_id", "path", "button", "label"}
    if complete:
        keys |= {"chat_id", "message_id", "message_revision"}
    item = _object(value, keys, "target")
    result: dict[str, Any] = {
        "target_id": _identifier(item["target_id"], "target identifier"),
        "path": _path(item["path"]),
        "button": _button(item["button"]),
        "label": _bounded_text(item["label"], "label", 128 * 1024),
    }
    if complete:
        result.update(
            {
                "chat_id": _positive(item["chat_id"], "chat identifier"),
                "message_id": _positive(item["message_id"], "message identifier"),
                "message_revision": _positive(item["message_revision"], "message revision"),
            }
        )
    return result


def _observation(value: Any) -> dict[str, Any]:
    item = _object(value, {"chat_id", "message_id", "message_revision", "targets"}, "observation")
    chat_id = _positive(item["chat_id"], "chat identifier")
    message_id = _positive(item["message_id"], "message identifier")
    revision = _positive(item["message_revision"], "message revision")
    if not isinstance(item["targets"], list):
        raise ValueError("Invalid rich-button observation targets")
    targets = [_target(value_target, complete=False) for value_target in item["targets"]]
    return {
        "chat_id": chat_id,
        "message_id": message_id,
        "message_revision": revision,
        "targets": targets,
    }


def _clipboard_value(value: Any) -> str | None:
    if value is None:
        return None
    return _bounded_text(value, "clipboard text")


def _artifact_path(value: Any) -> str:
    path = _bounded_text(value, "native artifact path", 256)
    parsed = PurePosixPath(path)
    if not path or parsed.is_absolute() or ".." in parsed.parts:
        raise ValueError("Invalid rich-button native artifact path")
    return path


def _evidence(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("Invalid rich-button evidence")
    mode = value.get("mode")
    keys = {"mode", "world_event_sequences", "clipboard_observation"}
    if mode == "headless-android":
        keys.add("native")
    item = _object(value, keys, "evidence")
    sequences = item["world_event_sequences"]
    if not isinstance(sequences, list):
        raise ValueError("Invalid rich-button evidence event sequences")
    clean_sequences = [_positive(sequence, "event sequence") for sequence in sequences]
    clipboard = item["clipboard_observation"]
    clean_clipboard: dict[str, str | None] | None
    if clipboard is None:
        clean_clipboard = None
    else:
        observed = _object(clipboard, {"before", "after"}, "clipboard observation")
        clean_clipboard = {
            "before": _clipboard_value(observed["before"]),
            "after": _clipboard_value(observed["after"]),
        }
    result: dict[str, Any] = {
        "mode": mode,
        "world_event_sequences": clean_sequences,
        "clipboard_observation": clean_clipboard,
    }
    if mode == "simulation":
        return result
    if mode != "headless-android":
        raise ValueError("Invalid rich-button evidence mode")
    native = _object(item["native"], {"observation", "effect", "captures"}, "native evidence")
    captures = native["captures"]
    if not isinstance(captures, list) or len(captures) > 2:
        raise ValueError("Invalid rich-button native captures")
    result["native"] = {
        "observation": None
        if native["observation"] is None
        else _artifact_path(native["observation"]),
        "effect": None if native["effect"] is None else _artifact_path(native["effect"]),
        "captures": [_artifact_path(path) for path in captures],
    }
    return result


def _prefix(previous: list[Any], current: list[Any], context: str) -> None:
    if len(current) < len(previous) or current[: len(previous)] != previous:
        raise ValueError(f"Rich-button {context} must advance by prefix append only")


def _evidence_progress(
    previous: dict[str, Any], current: dict[str, Any], button: dict[str, Any]
) -> None:
    if current["mode"] != previous["mode"]:
        raise ValueError("Rich-button evidence mode is immutable")
    _prefix(
        previous["world_event_sequences"],
        current["world_event_sequences"],
        "event sequences",
    )
    old_clipboard = previous["clipboard_observation"]
    new_clipboard = current["clipboard_observation"]
    if "callback_data" in button:
        if new_clipboard is not None:
            raise ValueError("Rich-button callback clipboard evidence must remain null")
    else:
        if current["world_event_sequences"]:
            raise ValueError("Rich-button copy/disabled evidence cannot add World events")
        if old_clipboard is not None and new_clipboard is None:
            raise ValueError("Rich-button clipboard evidence cannot be dropped")
        if "disabled" in button and old_clipboard is not None and new_clipboard != old_clipboard:
            raise ValueError("Rich-button disabled clipboard evidence is immutable")
        if "copy_text" in button and new_clipboard is not None:
            copied = button["copy_text"]["text"]
            if new_clipboard["after"] not in {new_clipboard["before"], copied}:
                raise ValueError("Rich-button copy evidence has an unrelated clipboard value")
            if old_clipboard is not None:
                if new_clipboard["before"] != old_clipboard["before"]:
                    raise ValueError("Rich-button clipboard before value is immutable")
                if old_clipboard["after"] == copied and new_clipboard["after"] != copied:
                    raise ValueError("Rich-button confirmed copy evidence is immutable")
                if (
                    new_clipboard["after"] != old_clipboard["after"]
                    and new_clipboard["after"] != copied
                ):
                    raise ValueError("Rich-button copy evidence may advance only to target text")
    if current["mode"] != "headless-android":
        return
    old_native = previous["native"]
    new_native = current["native"]
    if old_native["observation"] is not None and (
        new_native["observation"] != old_native["observation"]
    ):
        raise ValueError("Rich-button native observation evidence is immutable")
    _prefix(old_native["captures"], new_native["captures"], "native captures")
    if old_native["effect"] is not None and new_native["effect"] is None:
        raise ValueError("Rich-button native effect evidence cannot be dropped")


def _initial_evidence(evidence: dict[str, Any], button: dict[str, Any]) -> None:
    empty: dict[str, Any] = {
        "mode": evidence["mode"],
        "world_event_sequences": [],
        "clipboard_observation": None,
    }
    if evidence["mode"] == "headless-android":
        empty["native"] = {"observation": None, "effect": None, "captures": []}
    _evidence_progress(empty, evidence, button)


def _reason(value: Any, allowed: frozenset[str]) -> dict[str, str]:
    item = _object(value, {"code"}, "receipt reason")
    if item["code"] not in allowed:
        raise ValueError("Invalid rich-button receipt reason")
    return {"code": item["code"]}


def _callback(value: Any) -> dict[str, Any]:
    callback = _object(
        value,
        {"id", "user_id", "chat_id", "message", "data", "chat_instance", "answer"},
        "callback",
    )
    callback_id = _identifier(callback["id"], "callback identifier")
    user_id = _positive(callback["user_id"], "callback user identifier")
    chat_id = _positive(callback["chat_id"], "callback chat identifier")
    if callback["answer"] is not None:
        raise ValueError("Rich-button callback must retain its creation-time null answer")
    if (
        not isinstance(callback["chat_instance"], str)
        or re.fullmatch(r"[0-9a-f]{64}", callback["chat_instance"]) is None
    ):
        raise ValueError("Invalid rich-button callback chat instance")
    data = _bounded_text(callback["data"], "callback data", 64)
    if not data:
        raise ValueError("Invalid rich-button callback data")
    message = callback["message"]
    if not isinstance(message, dict):
        raise ValueError("Invalid rich-button callback message")
    required = {"id", "chat_id", "sender_id", "date", "text", "rich_message"}
    allowed = required | {"edit_date", "reply_markup"}
    if required - set(message) or set(message) - allowed:
        raise ValueError("Invalid rich-button callback message fields")
    _positive(message["id"], "callback message identifier")
    message_chat = _positive(message["chat_id"], "callback message chat")
    _positive(message["sender_id"], "callback message sender")
    message_date = _timestamp(message["date"], "callback message date")
    if message_chat != chat_id or message["text"] != "":
        raise ValueError("Invalid rich-button callback message identity")
    if not isinstance(message.get("rich_message"), dict):
        raise ValueError("Invalid rich-button callback message")
    if "edit_date" in message:
        if _timestamp(message["edit_date"], "callback message edit date") < message_date:
            raise ValueError("Invalid rich-button callback message edit date")
    if "reply_markup" in message and not isinstance(message["reply_markup"], dict):
        raise ValueError("Invalid rich-button callback reply markup")
    return {
        "id": callback_id,
        "user_id": user_id,
        "chat_id": chat_id,
        "message": copy.deepcopy(message),
        "data": data,
        "chat_instance": callback["chat_instance"],
        "answer": None,
    }


def _effect(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("Invalid rich-button effect")
    kind = value.get("kind")
    if kind == "copy":
        item = _object(value, {"kind", "text"}, "copy effect")
        return {"kind": "copy", "text": _bounded_text(item["text"], "copy effect text")}
    if kind == "none":
        item = _object(value, {"kind", "reason"}, "disabled effect")
        if item["reason"] != "disabled":
            raise ValueError("Invalid rich-button disabled effect")
        return {"kind": "none", "reason": "disabled"}
    if kind == "callback":
        item = _object(value, {"kind", "callback", "event_sequence"}, "callback effect")
        return {
            "kind": "callback",
            "callback": _callback(item["callback"]),
            "event_sequence": _positive(item["event_sequence"], "callback event sequence"),
        }
    raise ValueError("Invalid rich-button effect")


def _receipt(value: Any) -> dict[str, Any]:
    item = _object(
        value,
        {"operation_id", "target", "status", "dispatch", "effect", "reason", "evidence"},
        "receipt",
    )
    status = item["status"]
    dispatch = item["dispatch"]
    if status not in {
        "in_progress",
        "rejected_before_dispatch",
        "succeeded",
        "uncertain",
    } or dispatch not in {"not_dispatched", "intent_recorded", "dispatched"}:
        raise ValueError("Invalid rich-button receipt state")
    target = _target(item["target"], complete=True)
    effect = None if item["effect"] is None else _effect(item["effect"])
    reason: dict[str, str] | None = None
    if status == "in_progress":
        if dispatch not in {"not_dispatched", "intent_recorded"} or effect is not None:
            raise ValueError("Invalid rich-button receipt state")
        if item["reason"] is not None:
            raise ValueError("Invalid rich-button receipt reason")
    elif status == "rejected_before_dispatch":
        if dispatch != "not_dispatched" or effect is not None:
            raise ValueError("Invalid rich-button receipt state")
        reason = _reason(item["reason"], _PRE_REASONS)
    elif status == "uncertain":
        if dispatch not in {"intent_recorded", "dispatched"} or effect is not None:
            raise ValueError("Invalid rich-button receipt state")
        reason = _reason(item["reason"], _UNCERTAIN_REASONS)
    else:
        if dispatch != "dispatched" or effect is None or item["reason"] is not None:
            raise ValueError("Invalid rich-button receipt state")
    return {
        "operation_id": _identifier(item["operation_id"], "operation identifier"),
        "target": target,
        "status": status,
        "dispatch": dispatch,
        "effect": effect,
        "reason": reason,
        "evidence": _evidence(item["evidence"]),
    }


@dataclass
class _TargetState:
    target: dict[str, Any]
    client_nonce: str
    user_id: int
    operation_id: str | None = None


@dataclass
class _OperationState:
    target_id: str
    client_nonce: str
    current: dict[str, Any]
    intent: bool = False
    evidence_count: int = 0
    receipt_count: int = 0
    evidence_at_receipt: dict[str, Any] | None = None
    terminal: bool = False


def _receipt_semantics(receipt: dict[str, Any], target: _TargetState, *, world_id: str) -> None:
    effect = receipt["effect"]
    if effect is None:
        return
    button = target.target["button"]
    if "copy_text" in button:
        if effect != {"kind": "copy", "text": button["copy_text"]["text"]}:
            raise ValueError("Rich-button copy effect does not match target")
        clipboard = receipt["evidence"]["clipboard_observation"]
        if clipboard is None or clipboard["after"] != effect["text"]:
            raise ValueError("Rich-button copy effect does not match evidence")
        return
    if "disabled" in button:
        if effect != {"kind": "none", "reason": "disabled"}:
            raise ValueError("Rich-button disabled effect does not match target")
        clipboard = receipt["evidence"]["clipboard_observation"]
        if clipboard is None or clipboard["before"] != clipboard["after"]:
            raise ValueError("Rich-button disabled effect does not match evidence")
        return
    if effect["kind"] != "callback":
        raise ValueError("Rich-button callback effect does not match target")
    callback = effect["callback"]
    if (
        callback["user_id"] != target.user_id
        or callback["chat_id"] != target.target["chat_id"]
        or callback["data"] != button["callback_data"]
    ):
        raise ValueError("Rich-button callback identity does not match target")
    expected_instance = hashlib.sha256(
        f"{world_id}:{target.target['chat_id']}".encode()
    ).hexdigest()
    if callback["chat_instance"] != expected_instance:
        raise ValueError("Rich-button callback chat instance does not match World")
    if effect["event_sequence"] not in receipt["evidence"]["world_event_sequences"]:
        raise ValueError("Rich-button callback effect does not match evidence")
    message = callback["message"]
    if (
        message["id"] != target.target["message_id"]
        or message["chat_id"] != target.target["chat_id"]
    ):
        raise ValueError("Rich-button callback message does not match target")
    found = occurrences(message["rich_message"])
    if not any(
        item["path"] == target.target["path"]
        and item["button"] == button
        and item["label"] == target.target["label"]
        for item in found
    ):
        raise ValueError("Rich-button callback occurrence does not match target")


@dataclass
class _Ledger:
    world_id: str = ""
    targets: dict[str, _TargetState] = field(default_factory=dict)
    target_order: list[str] = field(default_factory=list)
    operations: dict[str, _OperationState] = field(default_factory=dict)
    operation_order: list[str] = field(default_factory=list)

    def allocate(self, value: Any, *, user_id: Any, client_nonce: Any) -> list[str]:
        actor = _positive(user_id, "user identifier")
        nonce = _identifier(client_nonce, "client lifetime")
        observed = _observation(value)
        ids = [target["target_id"] for target in observed["targets"]]
        if len(ids) != len(set(ids)) or any(target_id in self.targets for target_id in ids):
            raise ValueError("Duplicate rich-button target identifier")
        if len(self.targets) + len(ids) > _MAX_TARGETS:
            raise ValueError("Rich-button journal exceeds 64 issued targets")
        for target in observed["targets"]:
            complete = {
                **copy.deepcopy(target),
                "chat_id": observed["chat_id"],
                "message_id": observed["message_id"],
                "message_revision": observed["message_revision"],
            }
            target_id = target["target_id"]
            self.targets[target_id] = _TargetState(complete, nonce, actor)
            self.target_order.append(target_id)
        return ids

    def transition(self, kind: str, value: Any, *, client_nonce: Any) -> tuple[str, bool]:
        if kind not in {"claim", "intent", "receipt"}:
            raise ValueError("Invalid rich-button transition kind")
        nonce = _identifier(client_nonce, "client lifetime")
        current = _receipt(value)
        operation_id = current["operation_id"]
        target_id = current["target"]["target_id"]
        target = self.targets.get(target_id)
        if target is None:
            raise ValueError("Unknown rich-button target")
        if nonce != target.client_nonce:
            raise ValueError("Rich-button client lifetime does not match allocation")
        if current["target"] != target.target:
            raise ValueError("Rich-button target identity does not match allocation")
        _receipt_semantics(current, target, world_id=self.world_id)
        operation = self.operations.get(operation_id)
        if kind == "claim":
            if operation is not None:
                if operation.target_id != target_id:
                    raise ValueError(
                        "Rich-button operation identifier already names another target"
                    )
                raise ValueError("Rich-button target is already claimed")
            if target.operation_id is not None:
                raise ValueError("Rich-button target is already claimed")
            if current["status"] != "in_progress" or current["dispatch"] != "not_dispatched":
                raise ValueError("Invalid rich-button claim receipt")
            _initial_evidence(current["evidence"], target.target["button"])
            target.operation_id = operation_id
            self.operations[operation_id] = _OperationState(target_id, nonce, current)
            self.operation_order.append(operation_id)
            return target_id, False
        if operation is None:
            raise ValueError("Rich-button transition requires a claim")
        if operation.target_id != target_id:
            raise ValueError("Rich-button operation identifier already names another target")
        if nonce != operation.client_nonce:
            raise ValueError("Rich-button client lifetime does not match claim")
        if operation.terminal:
            raise ValueError("Rich-button operation is terminal")
        if current["evidence"] != operation.current["evidence"]:
            raise ValueError("Rich-button receipt does not contain current evidence")
        if kind == "intent":
            if operation.intent or operation.receipt_count:
                raise ValueError("Rich-button operation already has an intent")
            if current["status"] != "in_progress" or current["dispatch"] != "intent_recorded":
                raise ValueError("Invalid rich-button intent receipt")
            operation.intent = True
            operation.current = current
            return target_id, False
        if not operation.intent:
            if current["status"] != "rejected_before_dispatch":
                raise ValueError("Rich-button receipt requires an intent")
        elif current["status"] not in {"uncertain", "succeeded"}:
            raise ValueError("Invalid rich-button post-intent receipt")
        if operation.receipt_count >= 2:
            raise ValueError("Rich-button operation exceeds two receipts")
        if operation.receipt_count == 1:
            if operation.current["status"] != "uncertain" or current["status"] != "succeeded":
                raise ValueError("Rich-button receipt progression is invalid")
            if operation.current["reason"] == {"code": "effect_mismatch"}:
                raise ValueError("Rich-button effect mismatch cannot resolve to success")
            if operation.evidence_at_receipt == operation.current["evidence"]:
                raise ValueError("Rich-button success after uncertainty requires changed evidence")
        operation.receipt_count += 1
        operation.current = current
        operation.evidence_at_receipt = copy.deepcopy(current["evidence"])
        operation.terminal = current["status"] in {"rejected_before_dispatch", "succeeded"}
        return target_id, operation.terminal

    def evidence(self, operation_id: Any, value: Any, *, client_nonce: Any) -> tuple[str, bool]:
        identifier = _identifier(operation_id, "operation identifier")
        nonce = _identifier(client_nonce, "client lifetime")
        operation = self.operations.get(identifier)
        if operation is None:
            raise ValueError("Unknown rich-button operation")
        if nonce != operation.client_nonce:
            raise ValueError("Rich-button client lifetime does not match claim")
        if operation.terminal:
            raise ValueError("Rich-button operation is terminal")
        if not operation.intent:
            raise ValueError("Rich-button evidence requires an intent")
        clean = _evidence(value)
        if clean == operation.current["evidence"]:
            return operation.target_id, False
        target = self.targets[operation.target_id]
        _evidence_progress(operation.current["evidence"], clean, target.target["button"])
        if operation.evidence_count >= 4:
            raise ValueError("Rich-button operation exceeds four changed evidence records")
        operation.evidence_count += 1
        operation.current["evidence"] = clean
        return operation.target_id, True


def _encode(record: dict[str, Any]) -> bytes:
    try:
        encoded = (
            json.dumps(
                record, ensure_ascii=False, allow_nan=False, separators=(",", ":"), sort_keys=True
            ).encode("utf-8")
            + b"\n"
        )
    except (TypeError, ValueError) as error:
        raise ValueError("Invalid rich-button journal value") from error
    if len(encoded) > _MAX_RECORD:
        raise JournalLimitError("Rich-button journal record exceeds 128 KiB including newline")
    return encoded


class Journal:
    """Own one fresh serialized journal writer for a scenario run."""

    def __init__(self, directory: Path, *, run_id: str, world_id: str) -> None:
        self._run_id = _identifier(run_id, "run identifier")
        self._world_id = _identifier(world_id, "World identifier")
        self._sequence = 0
        self._ledger = _Ledger(world_id=self._world_id)
        self._reservations: dict[str, int] = {}
        self._size = 0
        self._poisoned = False
        self._closed = False
        self._directory = directory
        self.path = directory / _NAME
        self._fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_APPEND, 0o600)
        try:
            self._write_record("start", {})
            directory_fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        except BaseException:
            self._poisoned = True
            os.close(self._fd)
            self._closed = True
            raise

    def _record(self, kind: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._record_at_sequence(kind, payload, self._sequence)

    def _record_at_sequence(
        self, kind: str, payload: dict[str, Any], sequence: int
    ) -> dict[str, Any]:
        return {
            "schema": _SCHEMA,
            "sequence": sequence,
            "run_id": self._run_id,
            "world_id": self._world_id,
            "kind": kind,
            "payload": payload,
        }

    def _ensure_live(self) -> None:
        if self._poisoned:
            raise RuntimeError("Rich-button journal writer is poisoned")
        if self._closed:
            raise RuntimeError("Rich-button journal writer is closed")

    def _write(self, encoded: bytes) -> None:
        self._ensure_live()
        try:
            offset = 0
            while offset < len(encoded):
                written = os.write(self._fd, encoded[offset:])
                if written <= 0:
                    raise OSError("Rich-button journal write made no progress")
                offset += written
            os.fsync(self._fd)
        except OSError:
            self._poisoned = True
            raise
        self._size += len(encoded)
        self._sequence += 1

    def _write_record(self, kind: str, payload: dict[str, Any]) -> int:
        encoded = _encode(self._record(kind, payload))
        self._write(encoded)
        return len(encoded)

    def _prepare_allocation(
        self,
        observation: dict[str, Any],
        *,
        user_id: int,
        client_nonce: str,
        sequence: int,
    ) -> tuple[_Ledger, list[str], bytes | None]:
        candidate = copy.deepcopy(self._ledger)
        target_ids = candidate.allocate(observation, user_id=user_id, client_nonce=client_nonce)
        if not target_ids:
            return candidate, target_ids, None
        payload = {
            "observation": copy.deepcopy(observation),
            "user_id": user_id,
            "client_nonce": client_nonce,
        }
        encoded = _encode(self._record_at_sequence("observation", payload, sequence))
        projected = self._size + sum(self._reservations.values()) + len(encoded)
        projected += len(target_ids) * _TARGET_RESERVATION
        if projected > _MAX_JOURNAL:
            raise JournalLimitError("Rich-button journal exceeds its 80 MiB capacity")
        return candidate, target_ids, encoded

    def preflight_allocation(
        self, observation: dict[str, Any], *, user_id: int, client_nonce: str
    ) -> None:
        """Validate a prospective whole allocation without changing journal or state."""

        self._ensure_live()
        self._prepare_allocation(
            observation,
            user_id=user_id,
            client_nonce=client_nonce,
            sequence=_MAX_SEQUENCE,
        )

    def allocate(self, observation: dict[str, Any], *, user_id: int, client_nonce: str) -> None:
        self._ensure_live()
        candidate, target_ids, encoded = self._prepare_allocation(
            observation,
            user_id=user_id,
            client_nonce=client_nonce,
            sequence=self._sequence,
        )
        if encoded is None:
            return
        self._write(encoded)
        self._ledger = candidate
        for target_id in target_ids:
            self._reservations[target_id] = _TARGET_RESERVATION

    def transition(self, kind: str, receipt: dict[str, Any], *, client_nonce: str) -> None:
        self._ensure_live()
        candidate = copy.deepcopy(self._ledger)
        target_id, terminal = candidate.transition(kind, receipt, client_nonce=client_nonce)
        payload = {"receipt": copy.deepcopy(receipt), "client_nonce": client_nonce}
        encoded = _encode(self._record(kind, payload))
        if len(encoded) > self._reservations[target_id]:
            raise JournalLimitError("Rich-button target exceeds its reserved journal capacity")
        self._write(encoded)
        self._ledger = candidate
        self._reservations[target_id] -= len(encoded)
        if terminal:
            del self._reservations[target_id]

    def evidence(self, operation_id: str, evidence: dict[str, Any], *, client_nonce: str) -> None:
        self._ensure_live()
        candidate = copy.deepcopy(self._ledger)
        target_id, changed = candidate.evidence(operation_id, evidence, client_nonce=client_nonce)
        if not changed:
            return
        payload = {
            "operation_id": operation_id,
            "client_nonce": client_nonce,
            "evidence": copy.deepcopy(evidence),
        }
        encoded = _encode(self._record("evidence", payload))
        if len(encoded) > self._reservations[target_id]:
            raise JournalLimitError("Rich-button target exceeds its reserved journal capacity")
        self._write(encoded)
        self._ledger = candidate
        self._reservations[target_id] -= len(encoded)

    def preflight_receipt(self, receipt: dict[str, Any], *, client_nonce: str) -> None:
        """Check a prospective receipt's identity and worst-case encoded record size."""

        self._ensure_live()
        nonce = _identifier(client_nonce, "client lifetime")
        clean = _receipt(receipt)
        target_id = clean["target"]["target_id"]
        target = self._ledger.targets.get(target_id)
        operation = self._ledger.operations.get(clean["operation_id"])
        if target is not None:
            if nonce != target.client_nonce:
                raise ValueError("Rich-button client lifetime does not match allocation")
            if clean["target"] != target.target:
                raise ValueError("Rich-button target identity does not match allocation")
            if target.operation_id is not None:
                if target.operation_id != clean["operation_id"]:
                    raise ValueError("Rich-button operation identifier does not match claim")
                claimed = self._ledger.operations[target.operation_id]
                if claimed.terminal:
                    raise ValueError("Rich-button operation is terminal")
        if operation is not None:
            if operation.target_id != target_id or nonce != operation.client_nonce:
                raise ValueError("Rich-button operation identifier does not match target")
            if operation.terminal:
                raise ValueError("Rich-button operation is terminal")
        payload = {"receipt": copy.deepcopy(receipt), "client_nonce": client_nonce}
        encoded = _encode(self._record_at_sequence("receipt", payload, _MAX_SEQUENCE))
        if target is not None and len(encoded) > self._reservations[target_id]:
            raise JournalLimitError("Rich-button target exceeds its reserved journal capacity")

    def close(self) -> None:
        if self._closed:
            return
        os.close(self._fd)
        self._closed = True


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-finite number {value}")


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate member {key}")
        result[key] = value
    return result


def _parse(line: bytes) -> dict[str, Any]:
    try:
        value = json.loads(
            line.decode("utf-8"), object_pairs_hook=_pairs, parse_constant=_reject_constant
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise ValueError("Journal is corrupt: invalid JSON record") from error
    if not isinstance(value, dict):
        raise ValueError("Journal is corrupt: record is not an object")
    _finite(value)
    return value


def _finite(value: Any) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("Journal is corrupt: non-finite number")
    if isinstance(value, dict):
        for child in value.values():
            _finite(child)
    elif isinstance(value, list):
        for child in value:
            _finite(child)


def _payload(record: dict[str, Any], expected: set[str]) -> dict[str, Any]:
    value = record["payload"]
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError("invalid record payload")
    return value


def recover_journal(path: Path) -> dict[str, Any]:
    """Validate a terminated journal and derive its bounded offline recovery report."""

    try:
        with path.open("rb") as stream:
            data = stream.read(_MAX_JOURNAL + 1)
        if len(data) > _MAX_JOURNAL:
            raise ValueError("journal exceeds 80 MiB")
        incomplete = bool(data) and not data.endswith(b"\n")
        lines = data.splitlines(keepends=True)
        if incomplete:
            if len(lines[-1]) > _MAX_RECORD:
                raise ValueError("incomplete journal tail exceeds 128 KiB")
            lines = lines[:-1]
        if not lines:
            raise ValueError("journal has no complete start record")
        ledger = _Ledger()
        run_id = ""
        world_id = ""
        for sequence, framed in enumerate(lines):
            if not framed.endswith(b"\n") or framed.endswith(b"\r\n") or len(framed) > _MAX_RECORD:
                raise ValueError("invalid record framing")
            record = _parse(framed[:-1])
            if set(record) != {"schema", "sequence", "run_id", "world_id", "kind", "payload"}:
                raise ValueError("invalid record members")
            if (
                type(record["schema"]) is not int
                or record["schema"] != _SCHEMA
                or type(record["sequence"]) is not int
                or record["sequence"] != sequence
            ):
                raise ValueError("invalid record schema or sequence")
            record_run = _identifier(record["run_id"], "run identifier")
            record_world = _identifier(record["world_id"], "World identifier")
            if sequence == 0:
                run_id, world_id = record_run, record_world
                ledger.world_id = world_id
                if record["kind"] != "start" or record["payload"] != {}:
                    raise ValueError("invalid start record")
                continue
            if record_run != run_id or record_world != world_id:
                raise ValueError("wrong journal identity")
            kind = record["kind"]
            if kind == "observation":
                payload = _payload(record, {"observation", "user_id", "client_nonce"})
                ledger.allocate(
                    payload["observation"],
                    user_id=payload["user_id"],
                    client_nonce=payload["client_nonce"],
                )
            elif kind in {"claim", "intent", "receipt"}:
                payload = _payload(record, {"receipt", "client_nonce"})
                ledger.transition(kind, payload["receipt"], client_nonce=payload["client_nonce"])
            elif kind == "evidence":
                payload = _payload(record, {"operation_id", "client_nonce", "evidence"})
                _, changed = ledger.evidence(
                    payload["operation_id"],
                    payload["evidence"],
                    client_nonce=payload["client_nonce"],
                )
                if not changed:
                    raise ValueError("unchanged evidence record")
            else:
                raise ValueError("unknown record kind")
        receipts: list[dict[str, Any]] = []
        for operation_id in ledger.operation_order:
            operation = ledger.operations[operation_id]
            current = copy.deepcopy(operation.current)
            if current["status"] in {"succeeded", "rejected_before_dispatch", "uncertain"}:
                receipts.append(current)
            elif operation.intent:
                current.update(
                    {
                        "status": "uncertain",
                        "reason": {"code": "component_stopped"},
                    }
                )
                receipts.append(current)
            else:
                current.update(
                    {
                        "status": "rejected_before_dispatch",
                        "reason": {"code": "component_stopped"},
                    }
                )
                receipts.append(current)
        unclaimed = [
            target_id
            for target_id in ledger.target_order
            if ledger.targets[target_id].operation_id is None
        ]
        return {
            "schema": _SCHEMA,
            "run_id": run_id,
            "world_id": world_id,
            "incomplete_tail": incomplete,
            "receipts": receipts,
            "unclaimed_target_ids": unclaimed,
        }
    except (OSError, ValueError, KeyError, TypeError) as error:
        if isinstance(error, OSError):
            raise
        if isinstance(error, ValueError) and str(error).startswith("Journal is corrupt"):
            raise
        raise ValueError(f"Journal is corrupt: {error}") from error
