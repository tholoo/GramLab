"""Public real-bot acceptance for frozen rich-button targeting."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shutil
import sqlite3
from itertools import pairwise
from pathlib import Path
from typing import Any, cast

import pytest
from PIL import Image

from gramlab.runner import run
from gramlab.runtime import RuntimeProfile

FILLER = [{"type": "paragraph", "text": f"Filler {index} / فاصله {index}"} for index in range(15)]
EXPECTED_PRIMARY = {
    "blocks": [
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
        *FILLER,
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
    ]
}
EXPECTED_TARGETS = [
    (
        ["blocks", 0, "text", "button"],
        {"text": "Offscreen callback / دور", "callback_data": "offscreen"},
        "Offscreen callback / دور",
    ),
    (
        ["blocks", 16, "buttons", 0],
        {"text": "Same / همان", "callback_data": "same:payload"},
        "Same / همان",
    ),
    (
        ["blocks", 16, "buttons", 1],
        {"text": ["Copy / ", "کپی"], "copy_text": {"text": "row copied / ردیف"}},
        "Copy / کپی",
    ),
    (
        ["blocks", 16, "buttons", 2],
        {"text": "Disabled / غیرفعال", "disabled": {}},
        "Disabled / غیرفعال",
    ),
    (
        ["blocks", 17, "text", 1, "text", 0, "button"],
        {"text": "Same / همان", "callback_data": "same:payload"},
        "Same / همان",
    ),
    (
        ["blocks", 17, "text", 1, "text", 2, "button"],
        {"text": ["Copy / ", "کپی"], "copy_text": {"text": "inline copied / درون"}},
        "Copy / کپی",
    ),
    (
        ["blocks", 17, "text", 2, "button"],
        {"text": "Disabled inline / غیرفعال", "disabled": {}},
        "Disabled inline / غیرفعال",
    ),
    (
        ["blocks", 18, "blocks", 0, "text", "button"],
        {"text": "Hidden callback / پنهان", "callback_data": "hidden"},
        "Hidden callback / پنهان",
    ),
]


def project(directory: Path, *, mode: str, variant: str | None = None) -> Path:
    directory.mkdir()
    timeout = 60 if mode == "simulation-only" else 900
    if variant is None:
        variant = "native-visible-aba" if mode == "headless-android" else "full"
    (directory / "fixture-variant.json").write_text(json.dumps(variant))
    manifest = directory / "run.toml"
    manifest.write_text(
        f'schema = 1\nmode = "{mode}"\nseed = 41\nnow = 1700000000\ntimeout = {timeout}\n'
        '[scenario]\nentry = "scenario.py"\nfiles = ["scenario.py", "fixture-variant.json"]\n'
        '[bots.targets]\nentry = "bot.py"\nfiles = ["bot.py"]\n'
    )
    shutil.copy2("tests/rich_targets_scenario.py", directory / "scenario.py")
    shutil.copy2("tests/fixtures/rich_targets_bot.py", directory / "bot.py")
    return manifest


def execute(directory: Path, *, mode: str, variant: str | None = None) -> dict[str, Any]:
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
        project(directory, mode=mode, variant=variant),
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
        ("row_callback", 1, "same:payload", 7),
        ("inline_callback", 4, "same:payload", 8),
        ("hidden", 7, "hidden", 9),
        ("offscreen", 0, "offscreen", 10),
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
        "target": expected_receipt_target(targets[2], 5),
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
        "target": expected_receipt_target(targets[3], 5),
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
    assert receipts["inline_copy"] == {
        "operation_id": receipts["inline_copy"]["operation_id"],
        "target": expected_receipt_target(targets[5], 5),
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
        "target": expected_receipt_target(targets[6], 5),
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
    stale_target = expected_receipt_target(stale_observation["targets"][1], 5)
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
        expected_receipt_target(unrelated_observation["targets"][1], 13),
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
    callbacks, events = assert_native_prefix(scenario, tmp_path / "headless-android-run")
    assert_complete_endpoint(recorded, scenario, callbacks, events)


def test_native_fixture_endpoint_stops_after_aba_in_real_contained_simulation(
    tmp_path: Path, trace_runner: Any
) -> None:
    recorded = execute(tmp_path / "project", mode="simulation-only", variant="native-visible-aba")
    scenario = process_json(recorded, "scenario")[-1]
    assert_observation(scenario["observation"], revision=5)
    assert_observation(scenario["stale_observation"], revision=5)
    callbacks = []
    events = initial_events()
    for name, index, payload in (
        ("row_callback", 1, "same:payload"),
        ("inline_callback", 4, "same:payload"),
        ("hidden", 7, "hidden"),
        ("offscreen", 0, "offscreen"),
    ):
        receipt = scenario["receipts"][name]
        assert_callback_receipt(
            receipt,
            expected_receipt_target(scenario["observation"]["targets"][index], 5),
            PRIMARY_MESSAGE,
            payload,
            len(events) + 1,
        )
        callback = receipt["effect"]["callback"]
        callbacks.append(callback)
        events.append(
            {
                "sequence": len(events) + 1,
                "type": "callback.created",
                "data": {key: value for key, value in callback.items() if key != "answer"},
            }
        )
    for kind, message in (
        ("message.created", ordinary_message(4, 2, "same-clock ABA")),
        ("message.edited", PRIMARY_MESSAGE | {"edit_date": 1700000000, "rich_message": ALTERNATE}),
        ("message.edited", PRIMARY_MESSAGE | {"edit_date": 1700000000}),
        ("message.created", ordinary_message(5, 1, "ABA complete")),
    ):
        events.append({"sequence": len(events) + 1, "type": kind, "data": message})
    assert (
        scenario["stale_before"]
        == scenario["stale_after"]
        == {"snapshot": EXPECTED_SNAPSHOT, "events": events}
    )
    stale = scenario["stale"]
    assert stale == {
        "operation_id": stale["operation_id"],
        "target": expected_receipt_target(scenario["stale_observation"]["targets"][1], 5),
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
    assert scenario["stale_repeat"] == stale
    assert_complete_endpoint(recorded, scenario, callbacks, events)


EXPECTED_SNAPSHOT: dict[str, Any] = {
    "schema": 1,
    "seed": 41,
    "now": 1700000000,
    "users": [
        {"id": 1, "is_bot": True, "first_name": "targets"},
        {"id": 2, "is_bot": False, "first_name": "Sara", "language_code": "fa"},
    ],
    "chats": [{"id": 1, "type": "private", "user_id": 2, "bot_id": 1}],
}
PRIMARY_MESSAGE: dict[str, Any] = {
    "id": 2,
    "chat_id": 1,
    "sender_id": 1,
    "date": 1700000000,
    "text": "",
    "rich_message": EXPECTED_PRIMARY,
}
UNRELATED_MESSAGE: dict[str, Any] = {
    "id": 3,
    "chat_id": 1,
    "sender_id": 1,
    "date": 1700000000,
    "text": "",
    "rich_message": {"blocks": [{"type": "paragraph", "text": "Unrelated A"}]},
}
ALTERNATE = {
    "blocks": [
        {"type": "buttons", "buttons": [{"text": "Temporary", "callback_data": "temporary"}]}
    ]
}
ANSWER = {"text": "Observed / مشاهده شد", "show_alert": False, "cache_time": 0}
ACTIONS = {
    "row_callback": 1,
    "row_copy": 2,
    "inline_callback": 4,
    "inline_copy": 5,
    "inline_disabled": 6,
    "hidden": 7,
    "offscreen": 0,
    "row_disabled": 3,
}


def ordinary_message(identifier: int, sender: int, text: str) -> dict[str, Any]:
    return {"id": identifier, "chat_id": 1, "sender_id": sender, "date": 1700000000, "text": text}


def initial_history() -> list[dict[str, Any]]:
    return [ordinary_message(1, 2, "publish rich targets"), PRIMARY_MESSAGE, UNRELATED_MESSAGE]


def aba_history() -> list[dict[str, Any]]:
    return [
        ordinary_message(1, 2, "publish rich targets"),
        PRIMARY_MESSAGE | {"edit_date": 1700000000},
        UNRELATED_MESSAGE,
        ordinary_message(4, 2, "same-clock ABA"),
        ordinary_message(5, 1, "ABA complete"),
    ]


def initial_events() -> list[dict[str, Any]]:
    return [
        {"sequence": 1, "type": "user.created", "data": EXPECTED_SNAPSHOT["users"][0]},
        {"sequence": 2, "type": "user.created", "data": EXPECTED_SNAPSHOT["users"][1]},
        {"sequence": 3, "type": "chat.created", "data": EXPECTED_SNAPSHOT["chats"][0]},
        *[
            {"sequence": index + 4, "type": "message.created", "data": message}
            for index, message in enumerate(initial_history())
        ],
    ]


def token(value: Any) -> None:
    assert type(value) is str and re.fullmatch(r"[A-Za-z0-9_-]{1,128}", value)


def counter(value: Any, *, minimum: int = 0) -> None:
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


def assert_native_evidence(
    root: Path, receipt: dict[str, Any], *, clipboard: dict[str, Any] | None
) -> tuple[str, str, str, int]:
    evidence = receipt["evidence"]
    assert evidence.keys() == {"mode", "world_event_sequences", "clipboard_observation", "native"}
    assert evidence["mode"] == "headless-android" and evidence["clipboard_observation"] == clipboard
    native = evidence["native"]
    assert native.keys() == {"observation", "effect", "captures"}
    operation = receipt["operation_id"]
    observation = read_native_json(root, native["observation"], operation, "observation")
    effect = read_native_json(root, native["effect"], operation, "effect")
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
    assert [observation[key] for key in ("user_id", "chat_id", "message_id", "revision")] == [
        2,
        1,
        2,
        5,
    ]
    for key in ("user_id", "chat_id", "message_id", "revision", "pid"):
        counter(observation[key], minimum=1)
    for key in ("nonce", "client_nonce"):
        token(observation[key])
    assert re.fullmatch(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", observation["world_id"])
    counter(observation["generation"])
    counter(observation["drawn_uptime_ms"])
    assert observation["available"] is True and observation["reason"] is None
    assert len(observation["targets"]) == 8
    for actual, (path, button, label) in zip(observation["targets"], EXPECTED_TARGETS, strict=True):
        assert {key: actual[key] for key in ("path", "button", "label")} == {
            "path": path,
            "button": button,
            "label": label,
        }
        base = {"path", "button", "label", "available", "reason"}
        geometry = {"local_bounds", "origin", "screen_bounds"}
        assert actual.keys() in (base, base | geometry) and type(actual["available"]) is bool
        if actual["available"]:
            assert actual["reason"] is None and geometry <= actual.keys()
        else:
            assert actual["reason"] in {
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
        for field, size in (("local_bounds", 4), ("origin", 2), ("screen_bounds", 4)):
            if field in actual:
                assert type(actual[field]) is list and len(actual[field]) == size
                assert all(
                    type(n) in (int, float) and math.isfinite(n) and abs(n) <= 1_000_000
                    for n in actual[field]
                )
    selected = next(t for t in observation["targets"] if t["path"] == receipt["target"]["path"])
    assert selected["available"] is True
    left, top, right, bottom = selected["screen_bounds"]
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
    for key in ("schema", "user_id", "chat_id", "message_id", "revision"):
        counter(effect[key], minimum=1)
    assert effect["operation_id"] == operation and effect["path"] == receipt["target"]["path"]
    counter(effect["generation"], minimum=observation["generation"])
    counter(effect["uptime_ms"], minimum=observation["drawn_uptime_ms"])
    assert effect["state"] == "complete" and effect["reason"] is None
    touch = effect["touch"]
    assert touch.keys() == {"down_uptime_ms", "up_uptime_ms", "path"}
    assert touch["path"] == effect["path"]
    counter(touch["down_uptime_ms"], minimum=observation["drawn_uptime_ms"])
    assert touch["down_uptime_ms"] <= effect["uptime_ms"]
    if touch["up_uptime_ms"] is not None:
        counter(touch["up_uptime_ms"], minimum=touch["down_uptime_ms"])
        assert touch["up_uptime_ms"] <= effect["uptime_ms"]
    kind = receipt["effect"]["kind"]
    assert (
        effect["action"]
        == {"callback": "callback", "copy": "copy", "none": "disabled_suppressed"}[kind]
    )
    assert effect["clipboard"] == clipboard
    if kind == "callback":
        assert touch["up_uptime_ms"] is not None and len(effect["requests"]) == 1
        request = effect["requests"][0]
        assert request.keys() == {
            "native_request_token",
            "request_id",
            "callback_id",
            "message_revision",
        }
        counter(request["native_request_token"], minimum=1)
        token(request["request_id"])
        assert request["callback_id"] == receipt["effect"]["callback"]["id"]
        assert type(request["message_revision"]) is int and request["message_revision"] == 5
        # Independently cross-bind the native request to the retained authoritative row.
        database = sqlite3.connect((root / "world/world.sqlite3").as_uri() + "?mode=ro", uri=True)
        try:
            assert database.execute("SELECT world_id FROM configuration").fetchone() == (
                observation["world_id"],
            )
            rows = database.execute(
                "SELECT user_id,bot_id,request_id,request_body,body,answer "
                "FROM callbacks WHERE id=?",
                (request["callback_id"],),
            ).fetchall()
        finally:
            database.close()
        assert len(rows) == 1 and rows[0][:3] == (2, 1, request["request_id"])
        assert json.loads(rows[0][3]) == {"chat_id": 1, "data": "same:payload", "message_id": 2}
        assert json.loads(rows[0][4]) == {
            key: value for key, value in receipt["effect"]["callback"].items() if key != "answer"
        }
        assert json.loads(rows[0][5]) == ANSWER

    else:
        assert effect["requests"] == []
    assert native["captures"] == [f"rich-buttons/{operation}/before.png"]
    capture = native_file(root, native["captures"][0], operation)
    with Image.open(capture) as image:
        assert image.format == "PNG" and image.size == (320, 640)
        image.verify()
    return (
        observation["world_id"],
        observation["nonce"],
        observation["client_nonce"],
        observation["pid"],
    )


def assert_native_prefix(
    scenario: dict[str, Any], root: Path
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Validate the unchanged visible/ABA prefix; also usable on preserved native13 evidence."""
    observation = scenario["observation"]
    assert_observation(observation, revision=5)
    assert_observation(scenario["stale_observation"], revision=5)
    assert {t["target_id"] for t in observation["targets"]}.isdisjoint(
        {t["target_id"] for t in scenario["stale_observation"]["targets"]}
    )
    receipts = scenario["receipts"]
    assert receipts.keys() == set(ACTIONS) | {"row_callback_repeat"}
    assert scenario["states"].keys() == ACTIONS.keys()
    events = initial_events()
    callbacks: list[dict[str, Any]] = []
    identities = set()
    operations = set()
    clipboard: str | None = None  # This gate starts a new dedicated guest with an empty clipboard.
    for name, index in ACTIONS.items():
        receipt = receipts[name]
        token(receipt["operation_id"])
        assert receipt["operation_id"] not in operations
        operations.add(receipt["operation_id"])
        target = expected_receipt_target(observation["targets"][index], 5)
        before = {"snapshot": EXPECTED_SNAPSHOT, "events": list(events)}
        if name in ("hidden", "offscreen"):
            assert receipt == {
                "operation_id": receipt["operation_id"],
                "target": target,
                "status": "rejected_before_dispatch",
                "dispatch": "not_dispatched",
                "effect": None,
                "reason": {"code": "target_unavailable"},
                "evidence": {
                    "mode": "headless-android",
                    "world_event_sequences": [],
                    "clipboard_observation": None,
                    "native": {"observation": None, "effect": None, "captures": []},
                },
            }
        else:
            assert receipt.keys() == {
                "operation_id",
                "target",
                "status",
                "dispatch",
                "effect",
                "reason",
                "evidence",
            }
            assert receipt["target"] == target and receipt["status"] == "succeeded"
            assert receipt["dispatch"] == "dispatched" and receipt["reason"] is None
            pair = None
            if name.endswith("callback"):
                callback = receipt["effect"]["callback"]
                # Share the complete literal callback oracle; native evidence is checked below.
                semantic = receipt | {
                    "evidence": {
                        "mode": "simulation",
                        "world_event_sequences": [len(events) + 1],
                        "clipboard_observation": None,
                    }
                }
                assert_callback_receipt(
                    semantic, target, PRIMARY_MESSAGE, "same:payload", len(events) + 1
                )
                assert receipt["evidence"]["world_event_sequences"] == [len(events) + 1]
                assert callback["id"] not in {item["id"] for item in callbacks}
                callbacks.append(callback)
                events.append(
                    {
                        "sequence": len(events) + 1,
                        "type": "callback.created",
                        "data": {key: value for key, value in callback.items() if key != "answer"},
                    }
                )
            else:
                text = "row copied / ردیف" if name == "row_copy" else "inline copied / درون"
                copied = name.endswith("copy")
                assert receipt["effect"] == (
                    {"kind": "copy", "text": text}
                    if copied
                    else {"kind": "none", "reason": "disabled"}
                )
                pair = {"before": clipboard, "after": text if copied else clipboard}
                clipboard = pair["after"]
                assert receipt["evidence"]["world_event_sequences"] == []
            identities.add(assert_native_evidence(root, receipt, clipboard=pair))
        assert scenario["states"][name] == {
            "before": before,
            "after": {"snapshot": EXPECTED_SNAPSHOT, "events": list(events)},
        }
    assert len(identities) == 1 and len(callbacks) == 2
    assert callbacks[0]["chat_instance"] == callbacks[1]["chat_instance"]
    assert receipts["row_callback_repeat"] == receipts["row_callback"]
    for kind, message in (
        ("message.created", ordinary_message(4, 2, "same-clock ABA")),
        ("message.edited", PRIMARY_MESSAGE | {"edit_date": 1700000000, "rich_message": ALTERNATE}),
        ("message.edited", PRIMARY_MESSAGE | {"edit_date": 1700000000}),
        ("message.created", ordinary_message(5, 1, "ABA complete")),
    ):
        events.append({"sequence": len(events) + 1, "type": kind, "data": message})
    stale = scenario["stale"]
    token(stale["operation_id"])
    assert stale["operation_id"] not in operations
    assert stale == {
        "operation_id": stale["operation_id"],
        "target": expected_receipt_target(scenario["stale_observation"]["targets"][1], 5),
        "status": "rejected_before_dispatch",
        "dispatch": "not_dispatched",
        "effect": None,
        "reason": {"code": "message_revision_changed"},
        "evidence": {
            "mode": "headless-android",
            "world_event_sequences": [],
            "clipboard_observation": None,
            "native": {"observation": None, "effect": None, "captures": []},
        },
    }
    assert scenario["stale_repeat"] == stale
    assert (
        scenario["stale_before"]
        == scenario["stale_after"]
        == {"snapshot": EXPECTED_SNAPSHOT, "events": events}
    )
    return callbacks, events


def api_message(message: dict[str, Any]) -> dict[str, Any]:
    """Bot API fixture projection from independently authored canonical messages only."""
    result = {
        "message_id": message["id"],
        "from": EXPECTED_SNAPSHOT["users"][message["sender_id"] - 1],
        "chat": {"id": 2, "type": "private", "first_name": "Sara"},
        "date": 1700000000,
    }
    field = "rich_message" if "rich_message" in message else "text"
    result[field] = message[field]
    if "edit_date" in message:
        result["edit_date"] = 1700000000
    return result


def assert_complete_endpoint(
    recorded: dict[str, Any],
    scenario: dict[str, Any],
    callbacks: list[dict[str, Any]],
    prefix_events: list[dict[str, Any]],
) -> None:
    """Complete expected new endpoint; never normalize old native13's extra traffic away."""
    assert scenario.keys() == {
        "variant",
        "observation",
        "receipts",
        "states",
        "phase_histories",
        "stale_observation",
        "stale",
        "stale_repeat",
        "stale_before",
        "stale_after",
        "history",
        "events",
    }
    assert scenario["variant"] == "native-visible-aba"
    history = [*aba_history(), ordinary_message(6, 2, "finish rich targets")]
    assert recorded["outcome"] == "passed" and recorded["failure"] is None
    assert scenario["history"] == history and recorded["histories"] == {"1": history}
    assert recorded["world"] == EXPECTED_SNAPSHOT
    expected_histories = {
        name: {"before": initial_history(), "after": initial_history()} for name in ACTIONS
    }
    expected_histories["stale"] = {"before": aba_history(), "after": aba_history()}
    assert scenario["phase_histories"] == expected_histories
    events = [
        *prefix_events,
        {"sequence": len(prefix_events) + 1, "type": "message.created", "data": history[-1]},
    ]
    for callback in callbacks:
        events.append(
            {
                "sequence": len(events) + 1,
                "type": "callback.answered",
                "data": {"id": callback["id"], "user_id": 2, "answer": ANSWER},
            }
        )
    assert scenario["events"] == recorded["events"] == events

    bot = process_json(recorded, "bot:targets")
    assert len(bot) == 2
    assert bot[0] == {
        "event": "published",
        "primary": api_message(PRIMARY_MESSAGE),
        "unrelated": api_message(UNRELATED_MESSAGE),
    }
    expected_callbacks = [
        {
            "id": callback["id"],
            "from": EXPECTED_SNAPSHOT["users"][1],
            "message": api_message(PRIMARY_MESSAGE),
            "chat_instance": callback["chat_instance"],
            "data": callback["data"],
        }
        for callback in callbacks
    ]
    assert bot[1].keys() == {"event", "callbacks", "api"}
    assert bot[1]["event"] == "finished" and bot[1]["callbacks"] == expected_callbacks
    expected_updates = [
        {"update_id": 1, "message": api_message(initial_history()[0])},
        *[
            {"update_id": index + 2, "callback_query": callback}
            for index, callback in enumerate(expected_callbacks)
        ],
        {"update_id": len(callbacks) + 2, "message": api_message(history[3])},
        {"update_id": len(callbacks) + 3, "message": api_message(history[5])},
    ]
    expected_writes = []
    for method, parameters, result in (
        (
            "sendRichMessage",
            {"chat_id": 2, "rich_message": EXPECTED_PRIMARY | {"skip_entity_detection": True}},
            api_message(PRIMARY_MESSAGE),
        ),
        (
            "sendRichMessage",
            {
                "chat_id": 2,
                "rich_message": UNRELATED_MESSAGE["rich_message"] | {"skip_entity_detection": True},
            },
            api_message(UNRELATED_MESSAGE),
        ),
        (
            "editMessageText",
            {
                "chat_id": 2,
                "message_id": 2,
                "rich_message": ALTERNATE | {"skip_entity_detection": True},
            },
            api_message(PRIMARY_MESSAGE | {"rich_message": ALTERNATE, "edit_date": 1700000000}),
        ),
        (
            "editMessageText",
            {
                "chat_id": 2,
                "message_id": 2,
                "rich_message": EXPECTED_PRIMARY | {"skip_entity_detection": True},
            },
            api_message(PRIMARY_MESSAGE | {"edit_date": 1700000000}),
        ),
        ("sendMessage", {"chat_id": 2, "text": "ABA complete"}, api_message(history[4])),
        *[
            (
                "answerCallbackQuery",
                {"callback_query_id": callback["id"], "text": "Observed / مشاهده شد"},
                True,
            )
            for callback in callbacks
        ],
    ):
        expected_writes.append(
            {
                "method": method,
                "parameters": parameters,
                "status": 200,
                "body": {"ok": True, "result": result},
            }
        )
    assert_bot_exchange(bot[1]["api"], expected_updates, expected_writes)


def assert_bot_exchange(
    api: list[dict[str, Any]], updates: list[dict[str, Any]], writes: list[dict[str, Any]]
) -> None:
    """Preserve phases and interleaving, allowing only empty waits and batch partitions."""

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

    # Publication must finish before the first ordinary poll.
    consume(writes[:2])
    delivered = 1
    offset = 2
    aba_applied = False
    while True:
        assert position < len(api)
        entry = api[position]
        position += 1
        batch = entry["body"]["result"]
        assert type(batch) is list
        assert entry == poll({"offset": offset, "timeout": 10}, batch)
        assert batch == updates[delivered : delivered + len(batch)]
        delivered += len(batch)
        if batch:
            offset = batch[-1]["update_id"] + 1
        if updates[-2] in batch:
            # The acknowledgement cannot have existed when this batch was delivered.
            assert not aba_applied and batch[-1] == updates[-2]
            consume(writes[2:5])
            aba_applied = True
        elif updates[-1] in batch:
            assert aba_applied and batch == [updates[-1]]
            break
        else:
            assert all("callback_query" in update for update in batch)
    assert delivered == len(updates)
    # No polling or other write may interrupt answers after the finish command.
    consume(writes[5:])
    consume([poll({"offset": offset}, [])])
    assert position == len(api)
