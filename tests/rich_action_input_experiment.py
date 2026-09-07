"""Explicit-only experiment: real rich callbacks in simulation or the experimental APK.

This filename is intentionally outside pytest's default test_*.py discovery.
"""

import hashlib
import json
import os
import shutil
from dataclasses import asdict
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest

from gramlab.reports import Report, Screenshot, write_report
from gramlab.runtime import RuntimeProfile, Sandbox

INITIAL = {
    "blocks": [
        {"type": "buttons", "buttons": [{"text": "Row action", "callback_data": "row:1"}]},
        {
            "type": "paragraph",
            "text": [
                "Choose: ",
                {
                    "type": "button",
                    "button": {"text": "Inline action", "callback_data": "inline:1"},
                },
            ],
        },
    ]
}
EDITED = {"blocks": [{"type": "paragraph", "text": "Rich actions complete"}]}
USER = {"id": 1, "is_bot": False, "first_name": "Sara", "language_code": "en"}
BOT = {"id": 2, "is_bot": True, "first_name": "Echo", "username": "gramlab_echo_bot"}
CHAT = {"id": 1, "type": "private", "first_name": "Sara"}
WORLD_REQUEST = {
    "id": 1,
    "chat_id": 1,
    "sender_id": 1,
    "date": 1700000000,
    "text": "Show rich actions",
}
WORLD_INITIAL = {
    "id": 2,
    "chat_id": 1,
    "sender_id": 2,
    "date": 1700000000,
    "text": "",
    "rich_message": INITIAL,
}
API_INITIAL = {
    "message_id": 2,
    "from": BOT,
    "chat": CHAT,
    "date": 1700000000,
    "rich_message": INITIAL,
}
API_EDITED = API_INITIAL | {"edit_date": 1700000010, "rich_message": EDITED}
ANSWER = {"text": "", "show_alert": False, "cache_time": 0}


def stage(directory: Path, profile: RuntimeProfile) -> None:
    shutil.copytree(
        "src/gramlab", directory / "gramlab", ignore=shutil.ignore_patterns("__pycache__")
    )
    (directory / "component-profile.json").write_text(json.dumps(asdict(profile)))
    (directory / "action-expected.json").write_text(json.dumps({"world_initial": WORLD_INITIAL}))
    for name in ("component_bot.py", "rich_action_input_round_trip.py", "rich_round_trip.py"):
        shutil.copy2(Path("tests/probes") / name, directory / name)
    shutil.copy2("tests/fixtures/rich_action_input_bot.py", directory / "rich_action_input_bot.py")


def assert_scenario(observed: dict[str, Any], mode: str) -> None:
    assert observed["mode"] == mode
    assert str(UUID(observed["world_id"])) == observed["world_id"]
    assert observed["initial"] == {"event": "ready", "initial": API_INITIAL}
    assert len(observed["callbacks"]) == 2
    ids = [callback["id"] for callback in observed["callbacks"]]
    assert len(set(ids)) == 2 and all(str(UUID(identifier)) == identifier for identifier in ids)
    instance = hashlib.sha256(f"{observed['world_id']}:1".encode()).hexdigest()
    callbacks = [
        {
            "id": identifier,
            "user_id": 1,
            "chat_id": 1,
            "message": WORLD_INITIAL,
            "data": data,
            "chat_instance": instance,
        }
        for identifier, data in zip(ids, ("row:1", "inline:1"), strict=True)
    ]
    assert observed["callbacks"] == [callback | {"answer": ANSWER} for callback in callbacks]
    updates = [
        {
            "update_id": index + 2,
            "callback_query": {
                "id": callback["id"],
                "from": USER,
                "message": API_INITIAL,
                "chat_instance": instance,
                "data": callback["data"],
            },
        }
        for index, callback in enumerate(callbacks)
    ]
    assert observed["actions"] == [
        {"event": "action", "update": updates[0], "answer": True, "edited": None},
        {"event": "action", "update": updates[1], "answer": True, "edited": API_EDITED},
    ]
    final_message = WORLD_INITIAL | {"edit_date": 1700000010, "rich_message": EDITED}
    assert observed["history"] == [WORLD_REQUEST, final_message]
    assert observed["pending"] == []
    expected_events = [
        ("user.created", USER),
        ("user.created", BOT),
        ("chat.created", {"id": 1, "type": "private", "user_id": 1, "bot_id": 2}),
        ("message.created", WORLD_REQUEST),
        ("message.created", WORLD_INITIAL),
        ("clock.advanced", {"now": 1700000005}),
        ("callback.created", callbacks[0]),
        ("callback.answered", {"id": ids[0], "user_id": 1, "answer": ANSWER}),
        ("clock.advanced", {"now": 1700000010}),
        ("callback.created", callbacks[1]),
        ("callback.answered", {"id": ids[1], "user_id": 1, "answer": ANSWER}),
        ("message.edited", final_message),
    ]
    assert observed["events"] == [
        {"sequence": index + 1, "type": kind, "data": data}
        for index, (kind, data) in enumerate(expected_events)
    ]

    def api(method: str, parameters: dict[str, Any], response: Any) -> dict[str, Any]:
        return {
            "method": method,
            "parameters": parameters,
            "response": {"ok": True, "result": response},
        }

    request = {
        "update_id": 1,
        "message": {
            "message_id": 1,
            "from": USER,
            "chat": CHAT,
            "date": 1700000000,
            "text": "Show rich actions",
        },
    }
    meaningful = []
    for record in observed["api"]:
        if record["method"] == "getUpdates" and record["response"] == {"ok": True, "result": []}:
            assert record in [
                api("getUpdates", {"offset": offset} | timing, [])
                for offset in (2, 3, 4)
                for timing in ({}, {"timeout": 5})
            ]
        else:
            meaningful.append(record)
    assert meaningful == [
        api("getUpdates", {}, [request]),
        api(
            "sendRichMessage",
            {"chat_id": 1, "rich_message": INITIAL | {"skip_entity_detection": True}},
            API_INITIAL,
        ),
        api("getUpdates", {"offset": 2, "timeout": 5}, [updates[0]]),
        api("answerCallbackQuery", {"callback_query_id": ids[0]}, True),
        api("getUpdates", {"offset": 3, "timeout": 5}, [updates[1]]),
        api("answerCallbackQuery", {"callback_query_id": ids[1]}, True),
        api(
            "editMessageText",
            {
                "chat_id": 1,
                "message_id": 2,
                "rich_message": EDITED | {"skip_entity_detection": True},
            },
            API_EDITED,
        ),
    ]


def test_simulation_real_bot_answers_two_rich_callbacks(tmp_path: Path) -> None:
    profile = RuntimeProfile.load(Path(os.environ["GRAMLAB_RUNTIME_PROFILE"]))
    stage(tmp_path, profile)
    result = Sandbox(profile).supervise(
        [profile.python, "/work/rich_action_input_round_trip.py"], data=tmp_path, timeout=45
    )
    (tmp_path / "simulation-result.json").write_text(result.stdout)
    (tmp_path / "simulation-stderr.log").write_text(result.stderr)
    assert result.returncode == 0, result.stderr
    observed = json.loads(result.stdout)
    assert_scenario(observed, "simulation")
    assert observed["client"] == {}


@pytest.mark.android
def test_experimental_original_row_and_inline_callback_taps(tmp_path: Path) -> None:
    # Never silently use the normal APK for this explicitly selected experiment.
    apk = os.environ.get("GRAMLAB_RICH_ACTION_EXPERIMENT_APK")
    manifest = os.environ.get("GRAMLAB_ANDROID_RUNTIME_PROFILE")
    assert apk and manifest and os.access("/dev/kvm", os.R_OK | os.W_OK), (
        "Explicit experimental APK, Android profile and KVM are required"
    )
    profile = RuntimeProfile.load(Path(manifest))
    core = RuntimeProfile.load(Path(os.environ["GRAMLAB_RUNTIME_PROFILE"]))
    stage(tmp_path, core)
    shutil.copy2(apk, tmp_path / "client.apk")
    (tmp_path / "emulator-profile.json").write_text(json.dumps(asdict(profile)))
    for name in (
        "emulator_process.py",
        "android_guest.py",
        "android_rich_messages.py",
        "android_rich_action_input.py",
    ):
        shutil.copy2(Path("tests/probes") / name, tmp_path / name)
    toolchain = json.loads(Path("clients/android/toolchain.json").read_text())
    image_package = (
        f"system-images;android-{toolchain['sdk']['platform']};"
        f"{toolchain['runtime']['imageType']};{toolchain['runtime']['abi']}"
    )
    result = Sandbox(profile).supervise(
        [
            profile.python,
            "/work/android_rich_action_input.py",
            profile.executables["emulator"],
            profile.executables["adb"],
            profile.executables["avdmanager"],
            image_package,
        ],
        data=tmp_path,
        kvm=True,
        timeout=420,
    )
    (tmp_path / "native-result.json").write_text(result.stdout)
    (tmp_path / "native-stderr.log").write_text(result.stderr)
    assert result.returncode == 0, result.stderr
    full = json.loads(result.stdout)
    assert full["host_interfaces"] == [[1, "lo"]]
    assert "Accounts: 0" in full["accounts"]
    assert full["emulator_filesystem"] == {
        "world_visible": False,
        "bot_visible": False,
        "private_avd_visible": True,
        "same_pid_namespace": False,
        "same_network": True,
    }
    assert full["network"]["local"] == "gramlab-local-reply\n"
    assert full["network"]["local_error"] == ""
    for family in ("ipv4", "ipv6"):
        assert full["network"][family] == {
            "returncode": 1,
            "stdout": "",
            "stderr": "nc: connect: Network is unreachable\n",
        }
    observed = full["extra_probe"]
    assert_scenario(observed, "native-input")
    client = observed["client"]
    assert set(client["codecs"]) == {"initial", "edited"}
    for phase, rich, cursor, now in (
        ("initial", INITIAL, 5, 1700000000),
        ("edited", EDITED, 12, 1700000010),
    ):
        assert client["codecs"][phase] == {
            "persona": 1,
            "cursor": cursor,
            "now": now,
            "users": [
                {
                    "id": 1,
                    "first_name": "Sara",
                    "self": True,
                    "bot": False,
                    "username": None,
                    "language_code": "en",
                    "phone": None,
                },
                {
                    "id": 2,
                    "first_name": "Echo",
                    "self": False,
                    "bot": True,
                    "username": "gramlab_echo_bot",
                    "language_code": None,
                    "phone": None,
                },
            ],
            "dialogs": [{"peer_id": 2, "top_message": 2}],
            "dialog_message_count": 1,
            "messages": [
                {
                    "id": 2,
                    "sender_id": 2,
                    "recipient_id": 1,
                    "out": False,
                    "date": 1700000000,
                    "text": "",
                    "rich_message": rich,
                },
                {
                    "id": 1,
                    "sender_id": 1,
                    "recipient_id": 2,
                    "out": True,
                    "date": 1700000000,
                    "text": "Show rich actions",
                },
            ],
        }
    assert "Accounts: 0" in client["accounts"]
    for launch in [
        *client["launches"].values(),
        observed["input"]["wrong_launch"],
        observed["input"]["correct_launch"],
    ]:
        assert "Status: ok" in launch and "LaunchState: COLD" in launch
    experiment = observed["input"]
    absent = experiment["absent_activation"]
    assert absent == {
        "pid": absent["pid"],
        "checked_uptime_ms": absent["checked_uptime_ms"],
        "activation_present": False,
        "geometry_present": False,
        "world_unchanged": True,
    }
    assert type(absent["pid"]) is int and absent["pid"] > 0
    assert type(absent["checked_uptime_ms"]) is int and absent["checked_uptime_ms"] > 0
    assert absent["pid"] != experiment["wrong_identity"]["pid"]
    assert experiment["wrong_identity"]["available"] is False
    assert experiment["wrong_identity"]["reason"] == "message_not_unique_or_visible"
    assert experiment["wrong_identity_unchanged"] is True
    assert experiment["wrong_identity"]["pid"] != experiment["taps"][0]["sample"]["pid"]
    assert [tap["target"]["callback_data"] for tap in experiment["taps"]] == ["row:1", "inline:1"]
    assert [tap["answer"] for tap in experiment["taps"]] == observed["callbacks"]
    assert experiment["age_limit_ms"] == 5000
    wrong_activation, correct_activation = experiment["activations"]
    assert wrong_activation["nonce"] != correct_activation["nonce"]
    for activation, message_id in ((wrong_activation, 1000002), (correct_activation, 2)):
        assert activation == {
            "schema": 1,
            "nonce": activation["nonce"],
            "world_id": observed["world_id"],
            "user_id": 1,
            "peer_id": 2,
            "message_id": message_id,
        }
        assert UUID(hex=activation["nonce"]).hex == activation["nonce"]
    wrong = experiment["wrong_identity"]
    assert wrong["nonce"] == wrong_activation["nonce"]
    assert wrong["message_id"] == 1000002 and wrong["peer_id"] == 2 and wrong["schema"] == 1
    assert wrong["pid"] == experiment["wrong_checked_pid"] and wrong["generation"] > 0
    assert 0 <= experiment["wrong_checked_uptime_ms"] - wrong["uptime_ms"] <= 5000
    previous_generation = 0
    for index, tap in enumerate(experiment["taps"]):
        sample = tap["sample"]
        assert sample["available"] is True and sample["schema"] == 1
        assert sample["nonce"] == correct_activation["nonce"]
        assert sample["message_id"] == 2 and sample["peer_id"] == 2
        assert sample["pid"] == experiment["taps"][0]["sample"]["pid"]
        assert sample["generation"] > previous_generation
        assert 0 <= tap["guest_uptime_before_tap_ms"] - sample["uptime_ms"] <= 5000
        assert tap["world_before"] == {
            "world_id": observed["world_id"],
            "message": WORLD_INITIAL,
            "now": 1700000005 + index * 5,
            "previous_callbacks": [
                {key: value for key, value in callback.items() if key != "answer"}
                for callback in observed["callbacks"][:index]
            ],
        }
        assert tap["target"] == sample["targets"][index] and len(sample["targets"]) == 2
        assert (tap["target"]["kind"], tap["target"]["text"]) == (
            ("row", "Row action") if index == 0 else ("inline", "Inline action")
        )
        left, top, right, bottom = tap["target"]["screen_bounds"]
        assert left < tap["x"] < right and top < tap["y"] < bottom
        previous_generation = sample["generation"]
    phases = ("initial", "before-wrong", "before-row", "before-inline", "edited", "restarted")
    for phase in phases:
        assert (tmp_path / f"{phase}.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
        assert (tmp_path / f"{phase}.xml").read_text()
    for phase in ("edited", "restarted"):
        assert "Rich actions complete" in client[phase]
    trace = [
        json.loads(line) for line in (tmp_path / "edited-trace.jsonl").read_text().splitlines()
    ]
    assert any(record["event"] == "events_applied" for record in trace)
    native_calls = [
        record for record in trace if record["method"] == "TL_messages_getBotCallbackAnswer"
    ]
    assert [record["event"] for record in native_calls] == ["request", "response"] * 2
    assert all(record["account"] == 0 for record in native_calls)
    assert native_calls[0]["token"] == native_calls[1]["token"]
    assert native_calls[2]["token"] == native_calls[3]["token"]
    assert native_calls[0]["token"] != native_calls[2]["token"]
    write_report(
        tmp_path / "report.html",
        Report(
            run_id="rich-action-input-experiment",
            title="Original rich callback input experiment",
            mode="headless-android",
            outcome="passed",
            seed=19,
            profile={
                "APK SHA-256": hashlib.sha256(Path(apk).read_bytes()).hexdigest(),
                "Display": "320 x 640, 160 dpi; short LTR scene",
            },
            summary="Two guest taps use observed original rectangles. The bot answers both "
            "callbacks and edits the same message after the second.",
            evidence={
                "Scenario": observed,
                "Network": full["network"],
                "Emulator filesystem": full["emulator_filesystem"],
            },
            screenshots=[
                Screenshot(caption=phase, png=(tmp_path / f"{phase}.png").read_bytes())
                for phase in phases
            ],
            limitations=[
                "Experimental file observation is not a public targeting API.",
                "Observation and touch are not atomic; no automatic input retry is allowed.",
                "Duplicate, nested, RTL, copy and disabled targeting are not covered.",
                "Rectangle correspondence still requires original PNG inspection.",
            ],
        ),
    )
