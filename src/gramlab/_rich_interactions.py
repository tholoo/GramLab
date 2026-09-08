"""Run-owned rich targets, single-use input and client-local effects."""

from __future__ import annotations

import copy
import hashlib
import threading
import uuid
from pathlib import Path
from typing import Any, Protocol

from gramlab._interactions import Interactions
from gramlab._rich_button_journal import Journal, JournalLimitError
from gramlab._rich_buttons import occurrences
from gramlab.world import World


class NativeRichInput(Protocol):
    """Independent semantic contract implemented by the trusted Android host."""

    def observe(self, message: dict[str, Any]) -> str:
        """Open the selected chat and return its actual process-lifetime nonce."""
        ...

    def prepare(self, receipt: dict[str, Any], *, client_nonce: str) -> dict[str, Any]:
        """Validate current lifetime, original bounds and clipboard before any touch."""
        ...

    def dispatch(self, receipt: dict[str, Any], prepared: dict[str, Any]) -> dict[str, Any]:
        """Perform one ordinary touch and return exact effect/evidence or uncertainty."""
        ...

    def abort_prepared(self, receipt: dict[str, Any], prepared: dict[str, Any]) -> None:
        """Disarm this exact prepared operation after failed pre-intent bookkeeping."""
        ...

    def reconcile(self, receipt: dict[str, Any]) -> dict[str, Any] | None:
        """Read retained effects only; never dispatch or restart the application."""
        ...


class RichInteractions:
    def __init__(
        self,
        directory: Path,
        *,
        lock: threading.Lock,
        interactions: Interactions,
        native: NativeRichInput | None = None,
    ) -> None:
        self.directory = directory
        self._input_lock = lock
        self._registry_lock = threading.RLock()
        self._interactions = interactions
        self._native = native
        self.failed = False
        self.failure: str | None = None
        self._targets: dict[str, dict[str, Any]] = {}
        self._receipts: dict[str, dict[str, Any]] = {}
        self._clipboard: dict[int, str | None] = {}
        self._persona: int | None = None
        self._client_nonce = uuid.uuid4().hex
        with World.open(directory) as world:
            self.world_id = world.world_id
        self.journal = Journal(directory.parent, run_id=uuid.uuid4().hex, world_id=self.world_id)

    def close(self) -> None:
        self.journal.close()

    def _fail(self, code: str) -> None:
        self.failed = True
        self.failure = self.failure or code

    def rich_buttons(self, *, chat_id: int, message_id: int) -> dict[str, Any]:
        if any(type(value) is not int or not 0 < value < 2**63 for value in (chat_id, message_id)):
            raise ValueError("Rich observation requires positive integer message identifiers")
        with self._input_lock:
            with World.open(self.directory) as world:
                if world.world_id != self.world_id:
                    raise ValueError("Control world has been replaced")
                chat = world.get_chat(chat_id)
                record = world.rich_button_snapshot(
                    user_id=chat["user_id"], chat_id=chat_id, message_id=message_id
                )
            found = occurrences(record["message"]["rich_message"])
            observation: dict[str, Any] = {
                "chat_id": chat_id,
                "message_id": message_id,
                "message_revision": record["revision"],
                "targets": [{"target_id": uuid.uuid4().hex, **item} for item in found],
            }
            if not found:
                return observation
            self._interactions.check_rich_capacity(len(found))
            self.journal.preflight_allocation(
                observation, user_id=chat["user_id"], client_nonce="0" * 128
            )
            for target in observation["targets"]:
                possible = {
                    "operation_id": "0" * 32,
                    "target": {
                        "chat_id": chat_id,
                        "message_id": message_id,
                        "message_revision": record["revision"],
                        **target,
                    },
                    "status": "rejected_before_dispatch",
                    "dispatch": "not_dispatched",
                    "effect": None,
                    "reason": {"code": "message_revision_changed"},
                    "evidence": self._empty_evidence(),
                }
                self.journal.preflight_receipt(possible, client_nonce="0" * 128)
            if self._native is not None:
                try:
                    nonce = self._native.observe(record)
                    self.journal.preflight_allocation(
                        observation, user_id=chat["user_id"], client_nonce=nonce
                    )
                except Exception:
                    self._fail("rich_button_component_failed")
                    raise RuntimeError("Rich-button client observation failed") from None
            else:
                nonce = self._interactions.select_virtual_persona(chat["user_id"])
                if nonce != self._client_nonce:
                    self._clipboard.clear()
            self._persona = chat["user_id"]
            self._client_nonce = nonce
            with self._registry_lock:
                try:
                    self._interactions.reserve_rich_targets(
                        len(found),
                        lambda: self.journal.allocate(
                            observation, user_id=chat["user_id"], client_nonce=nonce
                        ),
                    )
                except (OSError, RuntimeError):
                    self._fail("rich_button_journal_failed")
                    raise
                for target in observation["targets"]:
                    self._targets[target["target_id"]] = {
                        "target": {
                            "chat_id": chat_id,
                            "message_id": message_id,
                            "message_revision": record["revision"],
                            **copy.deepcopy(target),
                        },
                        "user_id": chat["user_id"],
                        "client_nonce": nonce,
                    }
            return copy.deepcopy(observation)

    def _empty_evidence(self) -> dict[str, Any]:
        value: dict[str, Any] = {
            "mode": "simulation" if self._native is None else "headless-android",
            "world_event_sequences": [],
            "clipboard_observation": None,
        }
        if self._native is not None:
            value["native"] = {"observation": None, "effect": None, "captures": []}
        return value

    def _transition(self, kind: str, receipt: dict[str, Any], entry: dict[str, Any]) -> None:
        existing = self._receipts.get(entry["target"]["target_id"])
        try:
            if (
                kind == "receipt"
                and existing is not None
                and receipt["evidence"] != existing["evidence"]
            ):
                self.journal.evidence(
                    receipt["operation_id"], receipt["evidence"], client_nonce=entry["client_nonce"]
                )
            self.journal.transition(kind, receipt, client_nonce=entry["client_nonce"])
        except (OSError, RuntimeError, ValueError):
            self._fail("rich_button_journal_failed")
            raise RuntimeError("Rich-button journal transition failed") from None
        if existing is None:
            self._receipts[entry["target"]["target_id"]] = copy.deepcopy(receipt)
        else:
            existing.clear()
            existing.update(copy.deepcopy(receipt))

    def tap_rich_button(self, *, target_id: str) -> dict[str, Any]:
        with self._registry_lock:
            if not isinstance(target_id, str) or target_id not in self._targets:
                raise ValueError("Invalid rich target")
            entry = self._targets[target_id]
            previous = self._receipts.get(target_id)
            if previous is not None:
                if previous["status"] != "uncertain" or self._native is None:
                    return copy.deepcopy(previous)
        if previous is not None:
            return self._reconcile(target_id, entry)
        with self._registry_lock:
            # Another HTTP thread can claim between the two registry sections.
            if target_id in self._receipts:
                return copy.deepcopy(self._receipts[target_id])
            receipt: dict[str, Any] = {
                "operation_id": uuid.uuid4().hex,
                "target": copy.deepcopy(entry["target"]),
                "status": "in_progress",
                "dispatch": "not_dispatched",
                "effect": None,
                "reason": None,
                "evidence": self._empty_evidence(),
            }
            self._transition("claim", receipt, entry)
            self._interactions.claim_rich_target(self._receipts[target_id])
        with self._input_lock:
            try:
                self._execute(receipt, entry)
            except Exception:
                self._fail("rich_button_component_failed")
                if receipt["dispatch"] == "not_dispatched":
                    receipt.update(
                        status="rejected_before_dispatch",
                        reason={"code": "component_stopped"},
                        effect=None,
                    )
                else:
                    receipt.update(
                        status="uncertain", reason={"code": "dispatch_unconfirmed"}, effect=None
                    )
            with self._registry_lock:
                self._transition("receipt", receipt, entry)
                return copy.deepcopy(self._receipts[target_id])

    def _reconcile(self, target_id: str, entry: dict[str, Any]) -> dict[str, Any]:
        with self._input_lock:
            with self._registry_lock:
                receipt = copy.deepcopy(self._receipts[target_id])
            if (
                self._native is not None
                and receipt["status"] == "uncertain"
                and receipt["reason"] != {"code": "effect_mismatch"}
                and not entry.get("mismatch", False)
            ):
                try:
                    outcome = self._native.reconcile(copy.deepcopy(receipt))
                    candidate = (
                        None if outcome is None else self._native_outcome(receipt, outcome, entry)
                    )
                except Exception:
                    self._fail("rich_button_component_failed")
                    raise RuntimeError("Rich-button reconciliation failed") from None
                if candidate is not None:
                    with self._registry_lock:
                        if candidate["status"] == "succeeded":
                            self._transition("receipt", candidate, entry)
                        else:
                            # The contract permits one uncertain receipt followed only by
                            # success. Persist changed polling evidence without another
                            # receipt; a known mismatch permanently closes live polling.
                            if candidate["reason"] == {"code": "effect_mismatch"}:
                                entry["mismatch"] = True
                            try:
                                self.journal.evidence(
                                    receipt["operation_id"],
                                    candidate["evidence"],
                                    client_nonce=entry["client_nonce"],
                                )
                            except (OSError, RuntimeError, ValueError):
                                self._fail("rich_button_journal_failed")
                                raise RuntimeError(
                                    "Rich-button evidence transition failed"
                                ) from None
                            self._receipts[target_id]["evidence"] = copy.deepcopy(
                                candidate["evidence"]
                            )
                        receipt = copy.deepcopy(self._receipts[target_id])
            return receipt

    def _native_outcome(
        self, receipt: dict[str, Any], outcome: dict[str, Any], entry: dict[str, Any]
    ) -> dict[str, Any]:
        if (
            not isinstance(outcome, dict)
            or outcome.keys() != {"status", "dispatch", "effect", "reason", "evidence"}
            or outcome["status"] not in {"succeeded", "uncertain"}
        ):
            raise ValueError("Invalid native rich-button outcome")
        candidate = {**copy.deepcopy(receipt), **copy.deepcopy(outcome)}
        self.journal.preflight_receipt(candidate, client_nonce=entry["client_nonce"])
        return candidate

    def _execute(self, receipt: dict[str, Any], entry: dict[str, Any]) -> None:
        if self._native is None and (
            entry["client_nonce"] != self._interactions.virtual_client_nonce
            or entry["user_id"] != self._interactions.virtual_persona
        ):
            receipt.update(status="rejected_before_dispatch", reason={"code": "client_restarted"})
            return
        target = entry["target"]
        try:
            with World.open(self.directory) as world:
                if world.world_id != self.world_id:
                    raise ValueError("access_denied")
                with world.rich_button_transaction(
                    user_id=entry["user_id"],
                    chat_id=target["chat_id"],
                    message_id=target["message_id"],
                    revision=target["message_revision"],
                    path=target["path"],
                    button=target["button"],
                ):
                    if self._native is None:
                        self._virtual_effect(world, receipt, entry)
            if self._native is not None:
                prepared = self._native.prepare(
                    copy.deepcopy(receipt), client_nonce=entry["client_nonce"]
                )
                try:
                    prospective = prepared["receipt_for_size_check"]
                    if any(prospective[key] != receipt[key] for key in ("operation_id", "target")):
                        raise RuntimeError("Invalid native preparation identity")
                    try:
                        self.journal.preflight_receipt(
                            prospective, client_nonce=entry["client_nonce"]
                        )
                    except JournalLimitError:
                        raise ValueError("target_unavailable") from None
                    self._intent(receipt, entry)
                except BaseException:
                    try:
                        self._native.abort_prepared(copy.deepcopy(receipt), prepared)
                    except (OSError, RuntimeError):
                        self._fail("rich_button_component_failed")
                    raise
                outcome = self._native.dispatch(copy.deepcopy(receipt), prepared)
                receipt.update(self._native_outcome(receipt, outcome, entry))
        except ValueError as error:
            if receipt["dispatch"] != "not_dispatched":
                raise
            code = str(error)
            if code not in {
                "access_denied",
                "message_revision_changed",
                "client_restarted",
                "target_unavailable",
            }:
                raise RuntimeError("Rich-button component returned an invalid rejection") from None
            receipt.update(
                status="rejected_before_dispatch",
                reason={"code": code},
            )

    def _intent(self, receipt: dict[str, Any], entry: dict[str, Any]) -> None:
        candidate = copy.deepcopy(receipt)
        candidate["dispatch"] = "intent_recorded"
        with self._registry_lock:
            self._transition("intent", candidate, entry)
        receipt.update(candidate)

    def _virtual_effect(self, world: World, receipt: dict[str, Any], entry: dict[str, Any]) -> None:
        button = entry["target"]["button"]
        persona = entry["user_id"]
        before = self._clipboard.get(persona)
        if (
            "callback_data" not in button
            and before is not None
            and len(before.encode("utf-8")) > 4096
        ):
            raise ValueError("target_unavailable")
        # This candidate measures framing before input, never supplies the reported effect.
        prospective = copy.deepcopy(receipt)
        prospective.update(status="succeeded", dispatch="dispatched")
        if "callback_data" in button:
            future_sequence = 2**63 - 1
            prospective["effect"] = {
                "kind": "callback",
                "callback": {
                    "id": "00000000-0000-4000-8000-000000000000",
                    "user_id": persona,
                    "chat_id": entry["target"]["chat_id"],
                    "message": world.get_message(
                        entry["target"]["chat_id"], entry["target"]["message_id"]
                    ),
                    "data": button["callback_data"],
                    "chat_instance": hashlib.sha256(
                        f"{self.world_id}:{entry['target']['chat_id']}".encode()
                    ).hexdigest(),
                    "answer": None,
                },
                "event_sequence": future_sequence,
            }
            prospective["evidence"]["world_event_sequences"] = [future_sequence]
        else:
            copied = button["copy_text"]["text"] if "copy_text" in button else before
            prospective["effect"] = (
                {"kind": "copy", "text": copied}
                if "copy_text" in button
                else {"kind": "none", "reason": "disabled"}
            )
            prospective["evidence"]["clipboard_observation"] = {"before": before, "after": copied}
        try:
            self.journal.preflight_receipt(prospective, client_nonce=entry["client_nonce"])
        except JournalLimitError:
            raise ValueError("target_unavailable") from None
        self._intent(receipt, entry)
        if "callback_data" in button:
            callback = world._create_callback_locked(
                user_id=persona,
                chat_id=entry["target"]["chat_id"],
                message_id=entry["target"]["message_id"],
                data=button["callback_data"],
                request_id=receipt["operation_id"],
                version=4,
            )
            created = world.events()[-1]
            receipt["effect"] = {
                "kind": "callback",
                "callback": callback,
                "event_sequence": created["sequence"],
            }
            receipt["evidence"]["world_event_sequences"] = [created["sequence"]]
        else:
            if "copy_text" in button:
                self._clipboard[persona] = button["copy_text"]["text"]
                receipt["effect"] = {"kind": "copy", "text": self._clipboard[persona]}
            else:
                receipt["effect"] = {"kind": "none", "reason": "disabled"}
            receipt["evidence"]["clipboard_observation"] = {
                "before": before,
                "after": self._clipboard.get(persona),
            }
        receipt.update(status="succeeded", dispatch="dispatched")
