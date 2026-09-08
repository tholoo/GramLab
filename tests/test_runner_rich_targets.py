"""Public real-bot acceptance for frozen rich-button targeting."""

from __future__ import annotations

import json
import os
import re
import shutil
from itertools import pairwise
from pathlib import Path
from typing import Any, cast

import pytest

from gramlab.runner import run
from gramlab.runtime import RuntimeProfile

FILLER = [{"type": "paragraph", "text": f"Filler {index} / فاصله {index}"} for index in range(15)]
EXPECTED_PRIMARY = {
    "blocks": [
        {
            "type": "buttons",
            "buttons": [
                {"text": "Same / همان", "callback_data": "same:payload"},
                {"text": ["Copy / ", "کپی"], "copy_text": {"text": "row copied / ردیف"}},
                {"text": "Disabled / غیرفعال", "disabled": {}},
            ],
        },
        {
            "type": "paragraph",
            "text": [
                "Nested / تو در تو ",
                {
                    "type": "bold",
                    "text": [
                        {
                            "type": "button",
                            "button": {
                                "text": "Same / همان",
                                "callback_data": "same:payload",
                            },
                        },
                        " | ",
                        {
                            "type": "button",
                            "button": {
                                "text": ["Copy / ", "کپی"],
                                "copy_text": {"text": "inline copied / درون"},
                            },
                        },
                    ],
                },
                {
                    "type": "button",
                    "button": {"text": "Disabled inline / غیرفعال", "disabled": {}},
                },
            ],
        },
        {
            "type": "details",
            "summary": "Hidden / پنهان",
            "blocks": [
                {
                    "type": "paragraph",
                    "text": {
                        "type": "button",
                        "button": {
                            "text": "Hidden callback / پنهان",
                            "callback_data": "hidden",
                        },
                    },
                }
            ],
        },
        *FILLER,
        {
            "type": "paragraph",
            "text": {
                "type": "button",
                "button": {
                    "text": "Offscreen callback / دور",
                    "callback_data": "offscreen",
                },
            },
        },
    ]
}
EXPECTED_TARGETS = [
    (
        ["blocks", 0, "buttons", 0],
        {"text": "Same / همان", "callback_data": "same:payload"},
        "Same / همان",
    ),
    (
        ["blocks", 0, "buttons", 1],
        {"text": ["Copy / ", "کپی"], "copy_text": {"text": "row copied / ردیف"}},
        "Copy / کپی",
    ),
    (
        ["blocks", 0, "buttons", 2],
        {"text": "Disabled / غیرفعال", "disabled": {}},
        "Disabled / غیرفعال",
    ),
    (
        ["blocks", 1, "text", 1, "text", 0, "button"],
        {"text": "Same / همان", "callback_data": "same:payload"},
        "Same / همان",
    ),
    (
        ["blocks", 1, "text", 1, "text", 2, "button"],
        {"text": ["Copy / ", "کپی"], "copy_text": {"text": "inline copied / درون"}},
        "Copy / کپی",
    ),
    (
        ["blocks", 1, "text", 2, "button"],
        {"text": "Disabled inline / غیرفعال", "disabled": {}},
        "Disabled inline / غیرفعال",
    ),
    (
        ["blocks", 2, "blocks", 0, "text", "button"],
        {"text": "Hidden callback / پنهان", "callback_data": "hidden"},
        "Hidden callback / پنهان",
    ),
    (
        ["blocks", 18, "text", "button"],
        {"text": "Offscreen callback / دور", "callback_data": "offscreen"},
        "Offscreen callback / دور",
    ),
]


def project(directory: Path, *, mode: str) -> Path:
    directory.mkdir()
    timeout = 60 if mode == "simulation-only" else 900
    manifest = directory / "run.toml"
    manifest.write_text(
        f'schema = 1\nmode = "{mode}"\nseed = 41\nnow = 1700000000\ntimeout = {timeout}\n'
        '[scenario]\nentry = "scenario.py"\nfiles = ["scenario.py"]\n'
        '[bots.targets]\nentry = "bot.py"\nfiles = ["bot.py"]\n'
    )
    shutil.copy2("tests/rich_targets_scenario.py", directory / "scenario.py")
    shutil.copy2("tests/fixtures/rich_targets_bot.py", directory / "bot.py")
    return manifest


def execute(directory: Path, *, mode: str) -> dict[str, Any]:
    arguments: dict[str, Any] = {}
    if mode == "headless-android":
        android_profile = os.environ.get("GRAMLAB_ANDROID_RUNTIME_PROFILE")
        apk = os.environ.get("GRAMLAB_ANDROID_PROBE_APK")
        if android_profile is None or apk is None or not os.access("/dev/kvm", os.R_OK | os.W_OK):
            pytest.skip("Requires the Android profile, reviewed rich-target APK and accessible KVM")
        arguments = {
            "android_profile": RuntimeProfile.load(Path(android_profile)),
            "android_apk": Path(apk),
            "bridge_version": 4,
        }
    output = directory.parent / (mode + "-run")
    outcome = run(
        project(directory, mode=mode),
        output,
        profile=RuntimeProfile.load(Path(os.environ["GRAMLAB_RUNTIME_PROFILE"])),
        **arguments,
    )
    recorded = json.loads((output / "result.json").read_text())
    assert outcome == "passed", recorded
    return cast(dict[str, Any], recorded)


def process_json(recorded: dict[str, Any], process: str) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in recorded["processes"][process]["stdout"].splitlines()
        if line.strip()
    ]


def assert_observation(observation: dict[str, Any], *, revision: int) -> None:
    assert observation.keys() == {"chat_id", "message_id", "message_revision", "targets"}
    assert {key: observation[key] for key in ("chat_id", "message_id", "message_revision")} == {
        "chat_id": 1,
        "message_id": 2,
        "message_revision": revision,
    }
    assert len(observation["targets"]) == len(EXPECTED_TARGETS)
    target_ids = []
    for actual, (path, button, label) in zip(observation["targets"], EXPECTED_TARGETS, strict=True):
        assert actual == {
            "target_id": actual["target_id"],
            "path": path,
            "button": button,
            "label": label,
        }
        assert re.fullmatch(r"[A-Za-z0-9_-]{1,128}", actual["target_id"])
        target_ids.append(actual["target_id"])
    assert len(set(target_ids)) == 8


def expected_receipt_target(observation_target: dict[str, Any], revision: int) -> dict[str, Any]:
    return {
        "target_id": observation_target["target_id"],
        "chat_id": 1,
        "message_id": 2,
        "message_revision": revision,
        "path": observation_target["path"],
        "button": observation_target["button"],
        "label": observation_target["label"],
    }


def assert_callback_receipt(
    receipt: dict[str, Any],
    target: dict[str, Any],
    message: dict[str, Any],
    payload: str,
    event_sequence: int,
) -> None:
    callback = receipt["effect"]["callback"]
    assert re.fullmatch(
        r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}",
        callback["id"],
    )
    assert callback == {
        "id": callback["id"],
        "user_id": 2,
        "chat_id": 1,
        "message": message,
        "data": payload,
        "chat_instance": callback["chat_instance"],
        "answer": None,
    }
    assert re.fullmatch(r"[0-9a-f]{64}", callback["chat_instance"])
    assert receipt == {
        "operation_id": receipt["operation_id"],
        "target": target,
        "status": "succeeded",
        "dispatch": "dispatched",
        "effect": {
            "kind": "callback",
            "callback": callback,
            "event_sequence": event_sequence,
        },
        "reason": None,
        "evidence": {
            "mode": "simulation",
            "world_event_sequences": [event_sequence],
            "clipboard_observation": None,
        },
    }
    assert re.fullmatch(r"[A-Za-z0-9_-]{1,128}", receipt["operation_id"])


def test_real_bot_public_rich_targets_preserve_effects_staleness_and_quiet_state(
    tmp_path: Path, trace_runner: Any
) -> None:
    recorded = execute(tmp_path / "project", mode="simulation-only")
    scenario = process_json(recorded, "scenario")[-1]
    observation = scenario["observation"]
    assert_observation(observation, revision=5)

    initial_message = {
        "id": 2,
        "chat_id": 1,
        "sender_id": 1,
        "date": 1700000000,
        "text": "",
        "rich_message": EXPECTED_PRIMARY,
    }
    receipts = scenario["receipts"]
    targets = observation["targets"]
    for name, index, payload, sequence in (
        ("row_callback", 0, "same:payload", 7),
        ("inline_callback", 3, "same:payload", 8),
        ("hidden", 6, "hidden", 9),
        ("offscreen", 7, "offscreen", 10),
    ):
        assert_callback_receipt(
            receipts[name],
            expected_receipt_target(targets[index], 5),
            initial_message,
            payload,
            sequence,
        )
    assert receipts["row_callback_repeat"] == receipts["row_callback"]

    assert receipts["row_copy"] == {
        "operation_id": receipts["row_copy"]["operation_id"],
        "target": expected_receipt_target(targets[1], 5),
        "status": "succeeded",
        "dispatch": "dispatched",
        "effect": {"kind": "copy", "text": "row copied / ردیف"},
        "reason": None,
        "evidence": {
            "mode": "simulation",
            "world_event_sequences": [],
            "clipboard_observation": {"before": None, "after": "row copied / ردیف"},
        },
    }
    assert receipts["row_disabled"] == {
        "operation_id": receipts["row_disabled"]["operation_id"],
        "target": expected_receipt_target(targets[2], 5),
        "status": "succeeded",
        "dispatch": "dispatched",
        "effect": {"kind": "none", "reason": "disabled"},
        "reason": None,
        "evidence": {
            "mode": "simulation",
            "world_event_sequences": [],
            "clipboard_observation": {
                "before": "row copied / ردیف",
                "after": "row copied / ردیف",
            },
        },
    }
    assert receipts["inline_copy"] == {
        "operation_id": receipts["inline_copy"]["operation_id"],
        "target": expected_receipt_target(targets[4], 5),
        "status": "succeeded",
        "dispatch": "dispatched",
        "effect": {"kind": "copy", "text": "inline copied / درون"},
        "reason": None,
        "evidence": {
            "mode": "simulation",
            "world_event_sequences": [],
            "clipboard_observation": {
                "before": "row copied / ردیف",
                "after": "inline copied / درون",
            },
        },
    }
    assert receipts["inline_disabled"] == {
        "operation_id": receipts["inline_disabled"]["operation_id"],
        "target": expected_receipt_target(targets[5], 5),
        "status": "succeeded",
        "dispatch": "dispatched",
        "effect": {"kind": "none", "reason": "disabled"},
        "reason": None,
        "evidence": {
            "mode": "simulation",
            "world_event_sequences": [],
            "clipboard_observation": {
                "before": "inline copied / درون",
                "after": "inline copied / درون",
            },
        },
    }
    for name in ("row_copy", "row_disabled", "inline_copy", "inline_disabled"):
        assert scenario["states"][name]["before"] == scenario["states"][name]["after"]
    assert len({receipt["operation_id"] for receipt in receipts.values()}) == 8

    stale_observation = scenario["stale_observation"]
    assert_observation(stale_observation, revision=5)
    stale_target = expected_receipt_target(stale_observation["targets"][0], 5)
    assert scenario["stale"] == {
        "operation_id": scenario["stale"]["operation_id"],
        "target": stale_target,
        "status": "rejected_before_dispatch",
        "dispatch": "not_dispatched",
        "effect": None,
        "reason": {"code": "message_revision_changed"},
        "evidence": {
            "mode": "simulation",
            "world_event_sequences": [],
            "clipboard_observation": None,
        },
    }
    assert scenario["stale_repeat"] == scenario["stale"]
    assert scenario["stale_before"] == scenario["stale_after"]
    assert re.fullmatch(r"[A-Za-z0-9_-]{1,128}", scenario["stale"]["operation_id"])

    unrelated_observation = scenario["unrelated_observation"]
    assert_observation(unrelated_observation, revision=13)
    target_sets = [
        {target["target_id"] for target in current["targets"]}
        for current in (observation, stale_observation, unrelated_observation)
    ]
    assert all(left.isdisjoint(right) for left, right in pairwise(target_sets))
    edited_primary = initial_message | {"edit_date": 1700000000}
    assert_callback_receipt(
        scenario["unrelated"],
        expected_receipt_target(unrelated_observation["targets"][0], 13),
        edited_primary,
        "same:payload",
        18,
    )
    assert scenario["unrelated_repeat"] == scenario["unrelated"]

    expected_history = [
        {"id": 1, "chat_id": 1, "sender_id": 2, "date": 1700000000, "text": "publish rich targets"},
        edited_primary,
        {
            "id": 3,
            "chat_id": 1,
            "sender_id": 1,
            "date": 1700000000,
            "edit_date": 1700000000,
            "text": "",
            "rich_message": {"blocks": [{"type": "paragraph", "text": "Unrelated B"}]},
        },
        {"id": 4, "chat_id": 1, "sender_id": 2, "date": 1700000000, "text": "same-clock ABA"},
        {"id": 5, "chat_id": 1, "sender_id": 1, "date": 1700000000, "text": "ABA complete"},
        {"id": 6, "chat_id": 1, "sender_id": 2, "date": 1700000000, "text": "edit unrelated"},
        {
            "id": 7,
            "chat_id": 1,
            "sender_id": 1,
            "date": 1700000000,
            "text": "Unrelated edit complete",
        },
        {"id": 8, "chat_id": 1, "sender_id": 2, "date": 1700000000, "text": "finish rich targets"},
    ]
    assert recorded["histories"] == {"1": expected_history}
    assert scenario["history"] == expected_history

    bot = process_json(recorded, "bot:targets")
    assert [entry["event"] for entry in bot] == ["published", "finished"]
    assert [callback["data"] for callback in bot[-1]["callbacks"]] == [
        "same:payload",
        "same:payload",
        "hidden",
        "offscreen",
        "same:payload",
    ]
    callback_events = [event for event in scenario["events"] if event["type"] == "callback.created"]
    answer_events = [event for event in scenario["events"] if event["type"] == "callback.answered"]
    assert len(callback_events) == len(answer_events) == 5
    callback_snapshots = [
        receipts["row_callback"]["effect"]["callback"],
        receipts["inline_callback"]["effect"]["callback"],
        receipts["hidden"]["effect"]["callback"],
        receipts["offscreen"]["effect"]["callback"],
        scenario["unrelated"]["effect"]["callback"],
    ]
    assert all(callback["answer"] is None for callback in callback_snapshots)
    assert [event["data"] for event in callback_events] == [
        {key: value for key, value in callback.items() if key != "answer"}
        for callback in callback_snapshots
    ]
    assert all(
        event["data"]["answer"]
        == {"text": "Observed / مشاهده شد", "show_alert": False, "cache_time": 0}
        for event in answer_events
    )


@pytest.mark.android
def test_public_rich_targets_prepare_original_effect_and_unavailability_evidence(
    tmp_path: Path,
) -> None:
    recorded = execute(tmp_path / "project", mode="headless-android")
    scenario = process_json(recorded, "scenario")[-1]
    assert_observation(scenario["observation"], revision=5)
    for name in (
        "row_callback",
        "row_copy",
        "row_disabled",
        "inline_callback",
        "inline_copy",
        "inline_disabled",
    ):
        receipt = scenario["receipts"][name]
        assert receipt["status"] == "succeeded" and receipt["dispatch"] == "dispatched"
        assert receipt["evidence"]["mode"] == "headless-android"
        assert receipt["evidence"]["native"].keys() == {"observation", "effect", "captures"}
    for name in ("hidden", "offscreen"):
        receipt = scenario["receipts"][name]
        assert receipt["status"] == "rejected_before_dispatch"
        assert receipt["dispatch"] == "not_dispatched"
        assert receipt["reason"] == {"code": "target_unavailable"}
    assert scenario["receipts"]["row_callback_repeat"] == scenario["receipts"]["row_callback"]
    assert scenario["stale_repeat"] == scenario["stale"]
    assert scenario["unrelated_repeat"] == scenario["unrelated"]
