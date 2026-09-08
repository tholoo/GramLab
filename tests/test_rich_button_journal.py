"""Durable rich-button journals preserve single-use operation evidence."""

import copy
import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from gramlab._rich_button_journal import Journal, recover_journal

RUN_ID = "00000000-0000-4000-8000-000000000071"
WORLD_ID = "00000000-0000-4000-8000-000000000070"
CLIENT = "client_lifetime_1"
EVIDENCE: dict[str, Any] = {
    "mode": "simulation",
    "world_event_sequences": [],
    "clipboard_observation": None,
}


def observation(*target_ids: str) -> dict[str, Any]:
    return {
        "chat_id": 3,
        "message_id": 5,
        "message_revision": 11,
        "targets": [
            {
                "target_id": target_id,
                "path": ["blocks", 0, "buttons", index],
                "button": {"text": f"Button {index}", "disabled": {}},
                "label": f"Button {index}",
            }
            for index, target_id in enumerate(target_ids)
        ],
    }


def receipt(
    observed: dict[str, Any],
    target: int,
    operation_id: str,
    *,
    status: str = "in_progress",
    dispatch: str = "not_dispatched",
    effect: dict[str, Any] | None = None,
    reason: dict[str, str] | None = None,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    selected = observed["targets"][target]
    return {
        "operation_id": operation_id,
        "target": {
            **copy.deepcopy(selected),
            "chat_id": observed["chat_id"],
            "message_id": observed["message_id"],
            "message_revision": observed["message_revision"],
        },
        "status": status,
        "dispatch": dispatch,
        "effect": copy.deepcopy(effect),
        "reason": copy.deepcopy(reason),
        "evidence": copy.deepcopy(EVIDENCE if evidence is None else evidence),
    }


def test_journal_transitions_and_recovers_complete_and_interrupted_operations(
    tmp_path: Path,
) -> None:
    observed = observation("target_1", "target_2", "target_3", "target_4")
    observed["targets"][0]["button"] = {
        "text": "Button 0",
        "copy_text": {"text": "copied"},
    }
    journal = Journal(tmp_path, run_id=RUN_ID, world_id=WORLD_ID)
    path = tmp_path / "rich-button-journal.jsonl"
    assert path.stat().st_mode & 0o777 == 0o600
    start_size = path.stat().st_size
    journal.allocate(observation(), user_id=2, client_nonce=CLIENT)
    assert path.stat().st_size == start_size
    journal.allocate(observed, user_id=2, client_nonce=CLIENT)

    first = receipt(observed, 0, "operation_1")
    journal.transition("claim", first, client_nonce=CLIENT)
    intent = first | {"dispatch": "intent_recorded"}
    journal.transition("intent", intent, client_nonce=CLIENT)
    copied = {
        "mode": "simulation",
        "world_event_sequences": [],
        "clipboard_observation": {"before": None, "after": None},
    }
    journal.evidence("operation_1", copied, client_nonce=CLIENT)
    uncertain = intent | {
        "status": "uncertain",
        "dispatch": "dispatched",
        "reason": {"code": "effect_timeout"},
        "evidence": copied,
    }
    journal.transition("receipt", uncertain, client_nonce=CLIENT)
    confirmed = copied | {"clipboard_observation": {"before": None, "after": "copied"}}
    journal.evidence("operation_1", confirmed, client_nonce=CLIENT)
    succeeded = uncertain | {
        "status": "succeeded",
        "effect": {"kind": "copy", "text": "copied"},
        "reason": None,
        "evidence": confirmed,
    }
    journal.transition("receipt", succeeded, client_nonce=CLIENT)

    second = receipt(observed, 1, "operation_2")
    journal.transition("claim", second, client_nonce=CLIENT)
    third = receipt(observed, 2, "operation_3")
    journal.transition("claim", third, client_nonce=CLIENT)
    third_intent = third | {"dispatch": "intent_recorded"}
    journal.transition("intent", third_intent, client_nonce=CLIENT)
    journal.close()

    assert recover_journal(path) == {
        "schema": 1,
        "run_id": RUN_ID,
        "world_id": WORLD_ID,
        "incomplete_tail": False,
        "receipts": [
            succeeded,
            second
            | {
                "status": "rejected_before_dispatch",
                "reason": {"code": "component_stopped"},
            },
            third_intent
            | {
                "status": "uncertain",
                "dispatch": "dispatched",
                "reason": {"code": "component_stopped"},
            },
        ],
        "unclaimed_target_ids": ["target_4"],
    }


def test_journal_rejects_invalid_identity_order_and_terminal_mutation(tmp_path: Path) -> None:
    observed = observation("target_1", "target_2")
    journal = Journal(tmp_path, run_id=RUN_ID, world_id=WORLD_ID)
    journal.allocate(observed, user_id=2, client_nonce=CLIENT)
    first = receipt(observed, 0, "operation_1")

    with pytest.raises(ValueError, match="Unknown rich-button operation"):
        journal.evidence("missing", EVIDENCE, client_nonce=CLIENT)
    with pytest.raises(ValueError, match="client lifetime"):
        journal.transition("claim", first, client_nonce="wrong_client")
    with pytest.raises(ValueError, match="claim"):
        journal.transition("intent", first | {"dispatch": "intent_recorded"}, client_nonce=CLIENT)
    journal.transition("claim", first, client_nonce=CLIENT)
    with pytest.raises(ValueError, match="already claimed"):
        journal.transition("claim", first, client_nonce=CLIENT)
    with pytest.raises(ValueError, match="operation identifier"):
        journal.transition("claim", receipt(observed, 1, "operation_1"), client_nonce=CLIENT)
    with pytest.raises(ValueError, match="intent"):
        journal.evidence("operation_1", EVIDENCE, client_nonce=CLIENT)

    rejected = first | {
        "status": "rejected_before_dispatch",
        "reason": {"code": "message_revision_changed"},
    }
    journal.transition("receipt", rejected, client_nonce=CLIENT)
    with pytest.raises(ValueError, match="terminal"):
        journal.transition("intent", first | {"dispatch": "intent_recorded"}, client_nonce=CLIENT)
    journal.close()


def test_journal_writes_only_changed_evidence_and_enforces_record_progression(
    tmp_path: Path,
) -> None:
    observed = observation("target_1")
    journal = Journal(tmp_path, run_id=RUN_ID, world_id=WORLD_ID)
    journal.allocate(observed, user_id=2, client_nonce=CLIENT)
    claimed = receipt(observed, 0, "operation_1")
    journal.transition("claim", claimed, client_nonce=CLIENT)
    intent = claimed | {"dispatch": "intent_recorded"}
    journal.transition("intent", intent, client_nonce=CLIENT)
    path = tmp_path / "rich-button-journal.jsonl"
    before = path.stat().st_size
    journal.evidence("operation_1", EVIDENCE, client_nonce=CLIENT)
    assert path.stat().st_size == before

    evidence = EVIDENCE | {"world_event_sequences": [12]}
    journal.evidence("operation_1", evidence, client_nonce=CLIENT)
    uncertain = intent | {
        "status": "uncertain",
        "dispatch": "dispatched",
        "reason": {"code": "dispatch_unconfirmed"},
        "evidence": evidence,
    }
    journal.transition("receipt", uncertain, client_nonce=CLIENT)
    with pytest.raises(ValueError, match="changed evidence"):
        journal.transition(
            "receipt",
            uncertain
            | {
                "status": "succeeded",
                "reason": None,
                "effect": {"kind": "none", "reason": "disabled"},
            },
            client_nonce=CLIENT,
        )
    journal.close()


def test_allocation_is_atomic_and_bounded(tmp_path: Path) -> None:
    journal = Journal(tmp_path, run_id=RUN_ID, world_id=WORLD_ID)
    path = tmp_path / "rich-button-journal.jsonl"
    initial = path.read_bytes()
    with pytest.raises(ValueError, match="Duplicate rich-button target"):
        journal.allocate(observation("same", "same"), user_id=2, client_nonce=CLIENT)
    with pytest.raises(ValueError, match="64"):
        journal.allocate(
            observation(*(f"target_{index}" for index in range(65))),
            user_id=2,
            client_nonce=CLIENT,
        )
    oversized = observation("large")
    oversized["targets"][0]["label"] = "x" * (128 * 1024)
    with pytest.raises(ValueError, match="128 KiB"):
        journal.allocate(oversized, user_id=2, client_nonce=CLIENT)
    assert path.read_bytes() == initial
    journal.allocate(
        observation(*(f"target_{index}" for index in range(64))),
        user_id=2,
        client_nonce=CLIENT,
    )
    with pytest.raises(ValueError, match="64"):
        journal.allocate(observation("extra"), user_id=2, client_nonce=CLIENT)
    journal.close()


def test_preflight_uses_final_record_encoding_without_mutating_the_journal(tmp_path: Path) -> None:
    observed = observation("target_1")
    journal = Journal(tmp_path, run_id=RUN_ID, world_id=WORLD_ID)
    journal.allocate(observed, user_id=2, client_nonce=CLIENT)
    claimed = receipt(observed, 0, "operation_1")
    journal.transition("claim", claimed, client_nonce=CLIENT)
    path = tmp_path / "rich-button-journal.jsonl"
    before = path.read_bytes()

    prospective = claimed | {
        "status": "succeeded",
        "dispatch": "dispatched",
        "effect": {"kind": "none", "reason": "disabled"},
    }
    journal.preflight_receipt(prospective, client_nonce=CLIENT)
    assert path.read_bytes() == before
    oversized = prospective | {
        "effect": {
            "kind": "callback",
            "callback": {"retained": "x" * (128 * 1024)},
            "event_sequence": 1,
        }
    }
    with pytest.raises(ValueError, match="128 KiB"):
        journal.preflight_receipt(oversized, client_nonce=CLIENT)
    assert path.read_bytes() == before

    journal.transition("intent", claimed | {"dispatch": "intent_recorded"}, client_nonce=CLIENT)
    journal.close()


def test_recovery_accepts_only_an_incomplete_final_record(tmp_path: Path) -> None:
    journal = Journal(tmp_path, run_id=RUN_ID, world_id=WORLD_ID)
    journal.allocate(observation("target_1"), user_id=2, client_nonce=CLIENT)
    journal.close()
    path = tmp_path / "rich-button-journal.jsonl"
    with path.open("ab") as stream:
        stream.write(b'{"schema":1')
    recovered = recover_journal(path)
    assert recovered["incomplete_tail"] is True
    assert recovered["unclaimed_target_ids"] == ["target_1"]

    with path.open("ab") as stream:
        stream.write(b"\n")
    with pytest.raises(ValueError, match="corrupt"):
        recover_journal(path)


@pytest.mark.parametrize("damage", ["duplicate", "identity", "sequence", "unknown-target", "crlf"])
def test_recovery_rejects_complete_corruption(tmp_path: Path, damage: str) -> None:
    journal = Journal(tmp_path, run_id=RUN_ID, world_id=WORLD_ID)
    observed = observation("target_1")
    journal.allocate(observed, user_id=2, client_nonce=CLIENT)
    journal.close()
    path = tmp_path / "rich-button-journal.jsonl"
    lines = path.read_text().splitlines()
    if damage == "crlf":
        path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n", 1))
    elif damage == "duplicate":
        lines[1] = lines[1][:-1] + ',"schema":1}'
    else:
        record = json.loads(lines[1])
        if damage == "identity":
            record["world_id"] = "00000000-0000-4000-8000-000000000099"
        elif damage == "sequence":
            record["sequence"] = 9
        else:
            record["kind"] = "evidence"
            record["payload"] = {
                "operation_id": "missing",
                "client_nonce": CLIENT,
                "evidence": EVIDENCE,
            }
        lines[1] = json.dumps(record, separators=(",", ":"), sort_keys=True)
    if damage != "crlf":
        path.write_text("\n".join(lines) + "\n")
    with pytest.raises(ValueError, match="corrupt"):
        recover_journal(path)


def test_journal_is_exclusive_and_poisoned_after_io_failure(tmp_path: Path) -> None:
    journal = Journal(tmp_path, run_id=RUN_ID, world_id=WORLD_ID)
    with pytest.raises(FileExistsError):
        Journal(tmp_path, run_id=RUN_ID, world_id=WORLD_ID)
    observed = observation("target_1")
    with patch("os.fsync", side_effect=OSError("injected fsync failure")):
        with pytest.raises(OSError, match="injected fsync failure"):
            journal.allocate(observed, user_id=2, client_nonce=CLIENT)
    with pytest.raises(RuntimeError, match="poisoned"):
        journal.allocate(observed, user_id=2, client_nonce=CLIENT)
    journal.close()

    other = tmp_path / "other"
    other.mkdir()
    second = Journal(other, run_id=RUN_ID, world_id=WORLD_ID)
    with patch("os.write", side_effect=OSError("injected write failure")):
        with pytest.raises(OSError, match="injected write failure"):
            second.allocate(observed, user_id=2, client_nonce=CLIENT)
    with pytest.raises(RuntimeError, match="poisoned"):
        second.allocate(observed, user_id=2, client_nonce=CLIENT)
    second.close()
