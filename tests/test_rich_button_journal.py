"""Durable rich-button journals preserve single-use operation evidence."""

import copy
import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from gramlab._rich_button_journal import Journal, JournalLimitError, recover_journal
from gramlab.world import World

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
                "reason": {"code": "component_stopped"},
            },
        ],
        "unclaimed_target_ids": ["target_4"],
    }


def test_intent_only_uncertainty_does_not_invent_a_backend_handoff(tmp_path: Path) -> None:
    observed = observation("target_1")
    journal = Journal(tmp_path, run_id=RUN_ID, world_id=WORLD_ID)
    journal.allocate(observed, user_id=2, client_nonce=CLIENT)
    claimed = receipt(observed, 0, "operation_1")
    journal.transition("claim", claimed, client_nonce=CLIENT)
    intent = claimed | {"dispatch": "intent_recorded"}
    journal.transition("intent", intent, client_nonce=CLIENT)
    uncertain = intent | {
        "status": "uncertain",
        "reason": {"code": "dispatch_unconfirmed"},
    }
    journal.transition("receipt", uncertain, client_nonce=CLIENT)
    journal.close()
    assert recover_journal(tmp_path / "rich-button-journal.jsonl")["receipts"] == [uncertain]


def test_known_mismatch_cannot_be_replaced_by_later_success(tmp_path: Path) -> None:
    observed = observation("target_1")
    journal = Journal(tmp_path, run_id=RUN_ID, world_id=WORLD_ID)
    journal.allocate(observed, user_id=2, client_nonce=CLIENT)
    claimed = receipt(observed, 0, "operation_1")
    journal.transition("claim", claimed, client_nonce=CLIENT)
    journal.transition("intent", claimed | {"dispatch": "intent_recorded"}, client_nonce=CLIENT)
    mismatch = claimed | {
        "status": "uncertain",
        "dispatch": "dispatched",
        "reason": {"code": "effect_mismatch"},
    }
    journal.transition("receipt", mismatch, client_nonce=CLIENT)
    evidence = EVIDENCE | {"clipboard_observation": {"before": None, "after": None}}
    journal.evidence("operation_1", evidence, client_nonce=CLIENT)
    with pytest.raises(ValueError, match="mismatch"):
        journal.transition(
            "receipt",
            mismatch
            | {
                "status": "succeeded",
                "reason": None,
                "effect": {"kind": "none", "reason": "disabled"},
                "evidence": evidence,
            },
            client_nonce=CLIENT,
        )
    journal.close()


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

    evidence = EVIDENCE | {"clipboard_observation": {"before": None, "after": None}}
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
    journal.preflight_allocation(observation("preflight"), user_id=2, client_nonce="0" * 128)
    assert path.read_bytes() == initial
    with pytest.raises(ValueError, match="Duplicate rich-button target"):
        journal.preflight_allocation(observation("same", "same"), user_id=2, client_nonce="0" * 128)
    with pytest.raises(ValueError, match="64"):
        journal.allocate(
            observation(*(f"target_{index}" for index in range(65))),
            user_id=2,
            client_nonce=CLIENT,
        )
    oversized = observation("large")
    oversized["targets"][0]["label"] = "x" * (128 * 1024)
    with pytest.raises(JournalLimitError, match="128 KiB"):
        journal.preflight_allocation(oversized, user_id=2, client_nonce="0" * 128)
    assert path.read_bytes() == initial
    journal.allocate(
        observation(*(f"target_{index}" for index in range(64))),
        user_id=2,
        client_nonce=CLIENT,
    )
    with pytest.raises(ValueError, match="64"):
        journal.preflight_allocation(observation("extra"), user_id=2, client_nonce="0" * 128)
    assert len(path.read_bytes()) > len(initial)
    journal.close()


def test_preflight_uses_final_record_encoding_without_mutating_the_journal(tmp_path: Path) -> None:
    observed = observation("target_1")
    journal = Journal(tmp_path, run_id=RUN_ID, world_id=WORLD_ID)
    path = tmp_path / "rich-button-journal.jsonl"
    before_allocation = path.read_bytes()
    arbitrary = receipt(observed, 0, "0" * 32) | {
        "status": "rejected_before_dispatch",
        "reason": {"code": "message_revision_changed"},
    }
    journal.preflight_receipt(arbitrary, client_nonce="0" * 128)
    assert path.read_bytes() == before_allocation

    journal.allocate(observed, user_id=2, client_nonce=CLIENT)
    claimed = receipt(observed, 0, "operation_1")
    journal.transition("claim", claimed, client_nonce=CLIENT)
    before = path.read_bytes()

    prospective = claimed | {
        "status": "succeeded",
        "dispatch": "dispatched",
        "effect": {"kind": "none", "reason": "disabled"},
    }
    journal.preflight_receipt(prospective, client_nonce=CLIENT)
    assert path.read_bytes() == before
    large_observed = observation("large_target")
    large_observed["targets"][0]["button"] = {"text": "Large", "callback_data": "large"}
    large_observed["targets"][0]["label"] = "Large"
    large_observed["targets"][0]["path"] = ["blocks", 1, "buttons", 0]
    oversized = receipt(large_observed, 0, "large_operation") | {
        "status": "succeeded",
        "dispatch": "dispatched",
        "effect": {
            "kind": "callback",
            "callback": {
                "id": "00000000-0000-4000-8000-000000000001",
                "user_id": 2,
                "chat_id": 3,
                "message": {
                    "id": 5,
                    "chat_id": 3,
                    "sender_id": 2,
                    "date": 1,
                    "text": "",
                    "rich_message": {
                        "blocks": [
                            {"type": "paragraph", "text": "x" * (128 * 1024)},
                            {
                                "type": "buttons",
                                "buttons": [{"text": "Large", "callback_data": "large"}],
                            },
                        ]
                    },
                },
                "data": "large",
                "chat_instance": "0" * 64,
                "answer": None,
            },
            "event_sequence": 1,
        },
    }
    with pytest.raises(JournalLimitError, match="128 KiB"):
        journal.preflight_receipt(oversized, client_nonce="0" * 128)
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

    bounded = tmp_path / "oversized-tail.jsonl"
    bounded.write_bytes(path.read_bytes().splitlines(keepends=True)[0] + b"x" * (128 * 1024 + 1))
    with pytest.raises(ValueError, match="128 KiB"):
        recover_journal(bounded)


def test_evidence_advances_monotonically_for_actions_and_native_artifacts(tmp_path: Path) -> None:
    observed = observation("copy", "disabled", "callback", "native")
    observed["targets"][0]["button"] = {"text": "Copy", "copy_text": {"text": "copied"}}
    observed["targets"][2]["button"] = {"text": "Callback", "callback_data": "payload"}
    observed["targets"][3]["button"] = {"text": "Copy", "copy_text": {"text": "copied"}}
    journal = Journal(tmp_path, run_id=RUN_ID, world_id=WORLD_ID)
    journal.allocate(observed, user_id=2, client_nonce=CLIENT)

    copied = receipt(observed, 0, "copy_operation")
    journal.transition("claim", copied, client_nonce=CLIENT)
    journal.transition("intent", copied | {"dispatch": "intent_recorded"}, client_nonce=CLIENT)
    baseline = EVIDENCE | {"clipboard_observation": {"before": "old", "after": "old"}}
    journal.evidence("copy_operation", baseline, client_nonce=CLIENT)
    for invalid in (
        EVIDENCE,
        baseline | {"world_event_sequences": [1]},
        baseline | {"clipboard_observation": {"before": "changed", "after": "copied"}},
        baseline | {"clipboard_observation": {"before": "old", "after": "unrelated"}},
    ):
        with pytest.raises(ValueError):
            journal.evidence("copy_operation", invalid, client_nonce=CLIENT)
    confirmed = baseline | {"clipboard_observation": {"before": "old", "after": "copied"}}
    journal.evidence("copy_operation", confirmed, client_nonce=CLIENT)
    with pytest.raises(ValueError, match="immutable"):
        journal.evidence("copy_operation", baseline, client_nonce=CLIENT)

    disabled = receipt(observed, 1, "disabled_operation")
    journal.transition("claim", disabled, client_nonce=CLIENT)
    journal.transition("intent", disabled | {"dispatch": "intent_recorded"}, client_nonce=CLIENT)
    disabled_pair = EVIDENCE | {"clipboard_observation": {"before": "same", "after": "same"}}
    journal.evidence("disabled_operation", disabled_pair, client_nonce=CLIENT)
    with pytest.raises(ValueError, match="immutable"):
        journal.evidence(
            "disabled_operation",
            EVIDENCE | {"clipboard_observation": {"before": "same", "after": "changed"}},
            client_nonce=CLIENT,
        )

    callback = receipt(observed, 2, "callback_operation")
    journal.transition("claim", callback, client_nonce=CLIENT)
    journal.transition("intent", callback | {"dispatch": "intent_recorded"}, client_nonce=CLIENT)
    with pytest.raises(ValueError, match="clipboard"):
        journal.evidence(
            "callback_operation",
            EVIDENCE | {"clipboard_observation": {"before": None, "after": None}},
            client_nonce=CLIENT,
        )

    native_empty = {
        **EVIDENCE,
        "mode": "headless-android",
        "native": {"observation": None, "effect": None, "captures": []},
    }
    native = receipt(observed, 3, "native_operation", evidence=native_empty)
    journal.transition("claim", native, client_nonce=CLIENT)
    journal.transition("intent", native | {"dispatch": "intent_recorded"}, client_nonce=CLIENT)
    observed_native = copy.deepcopy(native_empty)
    observed_native["native"] = {
        "observation": "observation.json",
        "effect": None,
        "captures": ["before.png"],
    }
    journal.evidence("native_operation", observed_native, client_nonce=CLIENT)
    invalid_natives: tuple[dict[str, Any], ...] = (
        {"observation": "changed.json", "effect": None, "captures": ["before.png"]},
        {"observation": "observation.json", "effect": None, "captures": []},
    )
    for invalid_native in invalid_natives:
        invalid = copy.deepcopy(observed_native)
        invalid["native"] = invalid_native
        with pytest.raises(ValueError):
            journal.evidence("native_operation", invalid, client_nonce=CLIENT)
    first_effect = copy.deepcopy(observed_native)
    first_effect["native"]["effect"] = "effect-1.json"
    journal.evidence("native_operation", first_effect, client_nonce=CLIENT)
    replacement = copy.deepcopy(first_effect)
    replacement["native"]["effect"] = "effect-2.json"
    journal.evidence("native_operation", replacement, client_nonce=CLIENT)
    dropped = copy.deepcopy(replacement)
    dropped["native"]["effect"] = None
    with pytest.raises(ValueError, match="dropped"):
        journal.evidence("native_operation", dropped, client_nonce=CLIENT)
    journal.close()


def test_callback_effect_binds_complete_actual_world_callback_and_target(tmp_path: Path) -> None:
    world_directory = tmp_path / "world"
    with World.create(world_directory, seed=71, now=100) as world:
        actual_world_id = world.world_id
        user = world.create_user(first_name="Human")
        bot = world.create_user(first_name="Bot", is_bot=True)
        chat = world.open_private_chat(user_id=user["id"], bot_id=bot["id"])
        message = world.send_rich_message(
            chat_id=chat["id"],
            sender_id=bot["id"],
            rich_message={
                "blocks": [
                    {
                        "type": "buttons",
                        "buttons": [{"text": "Actual", "callback_data": "actual:payload"}],
                    }
                ],
                "skip_entity_detection": True,
            },
        )
        callback = world.create_callback(
            user_id=user["id"],
            chat_id=chat["id"],
            message_id=message["id"],
            data="actual:payload",
            request_id="operation_actual",
            version=4,
        )
        event_sequence = world.events()[-1]["sequence"]

    observed = {
        "chat_id": chat["id"],
        "message_id": message["id"],
        "message_revision": 1,
        "targets": [
            {
                "target_id": "actual_target",
                "path": ["blocks", 0, "buttons", 0],
                "button": {"text": "Actual", "callback_data": "actual:payload"},
                "label": "Actual",
            }
        ],
    }
    journal_directory = tmp_path / "journal"
    journal_directory.mkdir()
    journal = Journal(journal_directory, run_id=RUN_ID, world_id=actual_world_id)
    journal.allocate(observed, user_id=user["id"], client_nonce=CLIENT)
    claimed = receipt(observed, 0, "operation_actual")
    journal.transition("claim", claimed, client_nonce=CLIENT)
    intent = claimed | {"dispatch": "intent_recorded"}
    journal.transition("intent", intent, client_nonce=CLIENT)
    evidence = EVIDENCE | {"world_event_sequences": [event_sequence]}
    journal.evidence("operation_actual", evidence, client_nonce=CLIENT)
    effect = {"kind": "callback", "callback": callback, "event_sequence": event_sequence}
    succeeded = intent | {
        "status": "succeeded",
        "dispatch": "dispatched",
        "effect": effect,
        "evidence": evidence,
    }

    wrong_action = succeeded | {"effect": {"kind": "copy", "text": "actual:payload"}}
    before_preflight = (journal_directory / "rich-button-journal.jsonl").read_bytes()
    journal.preflight_receipt(wrong_action, client_nonce=CLIENT)
    assert (journal_directory / "rich-button-journal.jsonl").read_bytes() == before_preflight
    with pytest.raises(ValueError, match="target"):
        journal.transition("receipt", wrong_action, client_nonce=CLIENT)
    for field, changed in (
        ("data", "wrong"),
        ("answer", {"text": "too late"}),
        ("user_id", user["id"] + 1),
        ("chat_instance", "f" * 64),
    ):
        malformed = copy.deepcopy(succeeded)
        malformed["effect"]["callback"][field] = changed
        with pytest.raises(ValueError):
            journal.transition("receipt", malformed, client_nonce=CLIENT)
    actual_message = succeeded["effect"]["callback"]["message"]
    malformed_messages: list[dict[str, Any]] = []
    missing = copy.deepcopy(actual_message)
    missing.pop("sender_id")
    malformed_messages.append(missing)
    unknown = copy.deepcopy(actual_message)
    unknown["unexpected"] = True
    malformed_messages.append(unknown)
    bad_date = copy.deepcopy(actual_message)
    bad_date["date"] = True
    malformed_messages.append(bad_date)
    bad_text = copy.deepcopy(actual_message)
    bad_text["text"] = "not a rich message"
    malformed_messages.append(bad_text)
    bad_edit = copy.deepcopy(actual_message)
    bad_edit["edit_date"] = -1
    malformed_messages.append(bad_edit)
    bad_markup = copy.deepcopy(actual_message)
    bad_markup["reply_markup"] = []
    malformed_messages.append(bad_markup)
    for malformed_message in malformed_messages:
        malformed = copy.deepcopy(succeeded)
        malformed["effect"]["callback"]["message"] = malformed_message
        with pytest.raises(ValueError):
            journal.transition("receipt", malformed, client_nonce=CLIENT)
    wrong_occurrence = copy.deepcopy(succeeded)
    wrong_occurrence["effect"]["callback"]["message"]["rich_message"]["blocks"][0]["buttons"][0][
        "callback_data"
    ] = "different"
    with pytest.raises(ValueError, match="occurrence"):
        journal.transition("receipt", wrong_occurrence, client_nonce=CLIENT)

    journal.transition("receipt", succeeded, client_nonce=CLIENT)
    journal.close()
    assert recover_journal(journal_directory / "rich-button-journal.jsonl")["receipts"] == [
        succeeded
    ]

    overflow = tmp_path / "overflow.jsonl"
    lines = (journal_directory / "rich-button-journal.jsonl").read_text().splitlines()
    lines[-1] = lines[-1].replace('"message":{', '"message":{"overflow":1e400,', 1)
    overflow.write_text("\n".join(lines) + "\n")
    with pytest.raises(ValueError, match="non-finite"):
        recover_journal(overflow)


@pytest.mark.parametrize(
    "damage",
    [
        "duplicate",
        "identity",
        "sequence",
        "schema-bool",
        "sequence-float",
        "unknown-target",
        "crlf",
    ],
)
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
        elif damage == "schema-bool":
            record["schema"] = True
        elif damage == "sequence-float":
            record["sequence"] = 1.0
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
