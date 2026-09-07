"""Explicit-only copy/disabled experiment. Simulation alone makes no clipboard claim."""

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

# Independently authored canonical expectations; never loaded from the bot's input.
RICH = {
    "blocks": [
        {
            "type": "buttons",
            "buttons": [{"text": "Copy code", "copy_text": {"text": "GramLab-copy-73Q9"}}],
        },
        {
            "type": "paragraph",
            "text": [
                "Choose: ",
                {"type": "button", "button": {"text": "Unavailable", "disabled": {}}},
            ],
        },
    ]
}
USER = {"id": 1, "is_bot": False, "first_name": "Sara", "language_code": "en"}
BOT = {"id": 2, "is_bot": True, "first_name": "Echo", "username": "gramlab_echo_bot"}
CHAT = {"id": 1, "type": "private", "first_name": "Sara"}
REQUEST = {"id": 1, "chat_id": 1, "sender_id": 1, "date": 1700000000, "text": "Show rich effects"}
MESSAGE = {
    "id": 2,
    "chat_id": 1,
    "sender_id": 2,
    "date": 1700000000,
    "text": "",
    "rich_message": RICH,
}
API_MESSAGE = {"message_id": 2, "from": BOT, "chat": CHAT, "date": 1700000000, "rich_message": RICH}


def stage(directory: Path, profile: RuntimeProfile) -> None:
    shutil.copytree(
        "src/gramlab", directory / "gramlab", ignore=shutil.ignore_patterns("__pycache__")
    )
    (directory / "component-profile.json").write_text(json.dumps(asdict(profile)))
    (directory / "effect-expected.json").write_text(json.dumps({"world_initial": MESSAGE}))
    for name in ("component_bot.py", "rich_action_effect_round_trip.py"):
        shutil.copy2(Path("tests/probes") / name, directory / name)
    shutil.copy2(
        "tests/fixtures/rich_action_effect_bot.py", directory / "rich_action_effect_bot.py"
    )


def assert_scenario(observed: dict[str, Any], mode: str) -> None:
    assert str(UUID(observed["world_id"])) == observed["world_id"]
    assert observed["mode"] == mode
    assert observed["initial"] == {"event": "ready", "initial": API_MESSAGE}
    assert observed["finished"] == {"event": "finished", "updates": []}
    events = [
        ("user.created", USER),
        ("user.created", BOT),
        ("chat.created", {"id": 1, "type": "private", "user_id": 1, "bot_id": 2}),
        ("message.created", REQUEST),
        ("message.created", MESSAGE),
    ]
    expected = {
        "snapshot": {
            "schema": 2,
            "message_position": 2,
            "sends": [],
            "world_id": observed["world_id"],
            "user_id": 1,
            "now": 1700000000,
            "cursor": 5,
            "users": [USER, BOT],
            "chats": [{"id": 1, "type": "private", "user_id": 1, "bot_id": 2}],
            "messages": [REQUEST, MESSAGE],
        },
        "events": [
            {"sequence": i + 1, "type": kind, "data": data} for i, (kind, data) in enumerate(events)
        ],
        "history": [REQUEST, MESSAGE],
        "pending": [],
    }
    assert observed["before"] == expected
    assert observed["after"] == expected
    assert observed["final"] == expected

    def api(method: str, parameters: dict[str, Any], result: Any) -> dict[str, Any]:
        return {
            "method": method,
            "parameters": parameters,
            "response": {"ok": True, "result": result},
        }

    assert observed["api"] == [
        api(
            "getUpdates",
            {},
            [
                {
                    "update_id": 1,
                    "message": {
                        "message_id": 1,
                        "from": USER,
                        "chat": CHAT,
                        "date": 1700000000,
                        "text": "Show rich effects",
                    },
                }
            ],
        ),
        api(
            "sendRichMessage",
            {"chat_id": 1, "rich_message": RICH | {"skip_entity_detection": True}},
            API_MESSAGE,
        ),
        api("getUpdates", {"offset": 2}, []),
        api("getUpdates", {"offset": 2}, []),
    ]


def test_simulation_real_bot_copy_disabled_content_without_ui_effects(tmp_path: Path) -> None:
    profile = RuntimeProfile.load(Path(os.environ["GRAMLAB_RUNTIME_PROFILE"]))
    stage(tmp_path, profile)
    result = Sandbox(profile).supervise(
        [profile.python, "/work/rich_action_effect_round_trip.py"], data=tmp_path, timeout=45
    )
    (tmp_path / "simulation-result.json").write_text(result.stdout)
    (tmp_path / "simulation-stderr.log").write_text(result.stderr)
    assert result.returncode == 0, result.stderr
    observed = json.loads(result.stdout)
    assert_scenario(observed, "simulation")
    assert observed["client"] == {}


@pytest.mark.android
def test_experimental_original_copy_and_disabled_effects(tmp_path: Path) -> None:
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
        "rich_round_trip.py",
        "android_rich_messages.py",
        "android_rich_action_effect.py",
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
            "/work/android_rich_action_effect.py",
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
    experiment = observed["input"]
    initial_codec = json.loads((tmp_path / "initial-codec.json").read_text())
    expected_codec = {
        "persona": 1,
        "cursor": 5,
        "now": 1700000000,
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
                "rich_message": RICH,
            },
            {
                "id": 1,
                "sender_id": 1,
                "recipient_id": 2,
                "out": True,
                "date": 1700000000,
                "text": "Show rich effects",
            },
        ],
    }
    assert initial_codec == expected_codec
    assert experiment["restarted_codec"] == expected_codec
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
    wrong = experiment["wrong_identity"]
    assert wrong["available"] is False and wrong["reason"] == "message_not_unique_or_visible"
    assert experiment["wrong_identity_unchanged"] is True
    assert absent["pid"] != wrong["pid"] != experiment["taps"][0]["sample"]["pid"]
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
    assert wrong["nonce"] == wrong_activation["nonce"] and wrong["message_id"] == 1000002
    assert wrong["peer_id"] == 2 and wrong["schema"] == 1
    assert wrong["pid"] == experiment["wrong_checked_pid"] and wrong["generation"] > 0
    assert 0 <= experiment["wrong_checked_uptime_ms"] - wrong["uptime_ms"] <= 5000
    assert len(experiment["taps"]) == 2
    minimum = 0
    for index, tap in enumerate(experiment["taps"]):
        sample = tap["sample"]
        assert sample["available"] is True and sample["schema"] == 1
        assert sample["nonce"] == correct_activation["nonce"]
        assert sample["message_id"] == 2 and sample["peer_id"] == 2
        assert sample["pid"] == experiment["taps"][0]["sample"]["pid"]
        assert sample["generation"] > minimum
        assert 0 <= tap["guest_uptime_before_tap_ms"] - sample["uptime_ms"] <= 5000
        assert tap["world_before"] == tap["world_after"] == observed["before"]
        assert tap["target"] == sample["targets"][index] and len(sample["targets"]) == 2
        target = tap["target"]
        action = {"copy_text": "GramLab-copy-73Q9"} if index == 0 else {"disabled": True}
        assert {
            key: value
            for key, value in target.items()
            if key not in {"local_bounds", "origin", "screen_bounds"}
        } == {
            "kind": "row" if index == 0 else "inline",
            "block": index,
            "index": 0,
            "text": "Copy code" if index == 0 else "Unavailable",
        } | action
        left, top, right, bottom = target["screen_bounds"]
        assert left < tap["x"] < right and top < tap["y"] < bottom
        minimum = sample["generation"]
    assert experiment["pastes"] == [
        {"phase": phase, "text": "GramLab-copy-73Q9", "cleared": True}
        for phase in ("before-copy", "before-disabled")
    ]
    for launch in [
        *(experiment[name] for name in ("wrong_launch", "correct_launch", "restart_launch")),
        (tmp_path / "initial-launch.log").read_text(),
    ]:
        assert "Status: ok" in launch and "LaunchState: COLD" in launch
    trace = [
        json.loads(line) for line in (tmp_path / "effect-trace.jsonl").read_text().splitlines()
    ]
    assert not any(record.get("method") == "TL_messages_getBotCallbackAnswer" for record in trace)
    phases = ["initial", "before-wrong"]
    for name in ("before-copy", "before-disabled"):
        phases.extend([name, name + "-after-tap", name + "-pasted", name + "-cleared"])
    phases.append("restarted")
    for phase in phases:
        assert (tmp_path / f"{phase}.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
        assert (tmp_path / f"{phase}.xml").read_text()
    write_report(
        tmp_path / "report.html",
        Report(
            run_id="rich-action-effect-experiment",
            title="Original rich copy and disabled effects",
            mode="headless-android",
            outcome="passed",
            seed=21,
            profile={
                "APK SHA-256": hashlib.sha256(Path(apk).read_bytes()).hexdigest(),
                "Display": "320 x 640, 160 dpi; short LTR scene",
            },
            summary="Original copy input pastes the exact payload into the original composer. "
            "Disabled input preserves it. World and bot state stay unchanged.",
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
                "Opt-in experiment only; public targeting remains unimplemented.",
                "Copy row and disabled inline only; no RTL, nesting or long-press proof.",
                "No atomic observe/touch guarantee or input retry.",
                "Original bounds, copy feedback and disabled styling require visual review.",
            ],
        ),
    )
