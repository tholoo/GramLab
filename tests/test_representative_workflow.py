"""One composed real-bot workflow at the World, Bot API, bridge and client boundaries."""

from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, cast

import pytest
from PIL import Image

from gramlab.bot_api import _message
from gramlab.world import World

EXAMPLE = Path("examples/representative")
ASSET_HASHES = {
    "image/webp": {
        "7e1b283fb74b684cfaed135e5ce02ce6a0fc4824e4fb29c493f83fe05ccc0107",
        "6d97276da8fc4212d117000d1d0c0c83e86025004fd08257768d547e3527c034",
    },
    "video/webm": {"1ecead5fa57be35ec556025eb07f3a83f561b57d6c15c2732fd646223a9721d2"},
    "image/png": {"f4a96a9199d874b45d4c71b0a59ba3dd39abb8639f4022e8b8ada40680f2be82"},
    "image/jpeg": {"60df62b7b4032816fba73c77e9553aff52d1a2f8ca3667d2a3b5b488bae3cfaa"},
}
DOCUMENT_HASHES = {
    "default.txt": "d2a957a54f0867f998555c2d0eb2ff83072c2437aa3ccb413f65e97c747767f0",
    "forced-image.png": "f4a96a9199d874b45d4c71b0a59ba3dd39abb8639f4022e8b8ada40680f2be82",
}
MESSAGE_METHODS = frozenset(
    (
        "sendMessage",
        "sendRichMessage",
        "editMessageText",
        "sendPhoto",
        "sendDocument",
        "sendMediaGroup",
    )
)
UI_BOOLEAN_FALSE = "false"


def invoke(tmp_path: Path, *, native: bool) -> tuple[dict[str, Any], Path]:
    mode = "android" if native else "run"
    output = tmp_path / ("headless-android" if native else "simulation-only")
    arguments = [
        sys.executable,
        "-m",
        "gramlab",
        "run",
        str(EXAMPLE / f"{mode}.toml"),
        "--bridge-version",
        "6",
        "--output",
        str(output),
    ]
    if native:
        profile = os.environ.get("GRAMLAB_ANDROID_RUNTIME_PROFILE")
        apk = os.environ.get("GRAMLAB_ANDROID_PROBE_APK")
        if profile is None or apk is None or not os.access("/dev/kvm", os.R_OK | os.W_OK):
            pytest.skip("Requires the reviewed normal31 APK, Android profile and accessible KVM")
        arguments.extend(("--android-profile", profile, "--android-apk", apk))
    result = subprocess.run(  # noqa: S603 — caller supplies the outer offline namespace.
        arguments,
        capture_output=True,
        text=True,
        timeout=720 if native else 180,
        env=os.environ.copy(),
    )
    (tmp_path / f"{mode}-stdout.log").write_text(result.stdout)
    (tmp_path / f"{mode}-stderr.log").write_text(result.stderr)
    recorded = json.loads((output / "result.json").read_text())
    assert result.returncode == 0, recorded
    assert recorded["outcome"] == "passed" and recorded["failure"] is None
    return recorded, output


def json_lines(recorded: dict[str, Any], process: str) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in recorded["processes"][process]["stdout"].splitlines()
        if line.strip()
    ]


def scenario_interactions(recorded: dict[str, Any]) -> list[dict[str, Any]]:
    """Restore the one non-secret UI boolean redacted from retained Android evidence."""
    interactions = cast(list[dict[str, Any]], copy.deepcopy(recorded["interactions"]))

    def restore(value: Any) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if key == "password" and child == "[REDACTED]":
                    value[key] = UI_BOOLEAN_FALSE
                else:
                    restore(child)
        elif isinstance(value, list):
            for child in value:
                restore(child)

    restore(interactions)
    return interactions


def bot_api_messages(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    for record in records:
        if record["method"] not in MESSAGE_METHODS:
            continue
        result = record["body"]["result"]
        messages.extend(result if isinstance(result, list) else [result])
    return messages


def assert_representative(recorded: dict[str, Any], output: Path, *, native: bool) -> None:
    scenario = json.loads(recorded["processes"]["scenario"]["stdout"])
    first_bot = json_lines(recorded, "bot:representative")
    second_bot = json_lines(recorded, "bot:representative#2")
    assert [row["event"] for row in first_bot] == ["generation", "controls", "checkpoint"]
    assert [row["event"] for row in second_bot] == [
        "generation",
        "recovered",
        "rich-row",
        "rich-inline",
        "photos",
        "documents",
        "finished",
    ]
    assert recorded["processes"]["bot:representative"] | {
        "stdout": "ignored",
        "stderr": "ignored",
    } == {
        "exit_code": -9,
        "stopped_by_runner": False,
        "stopped_by_scenario": True,
        "generation": 1,
        "stdout": "ignored",
        "stdout_complete": True,
        "stderr": "ignored",
        "stderr_complete": True,
    }
    assert recorded["processes"]["bot:representative#2"]["exit_code"] == 0

    history = scenario["history"]
    assert history == recorded["histories"]["1"]
    assert [message["id"] for message in history] == list(range(1, 18))
    assert [history[index]["text"] for index in (0, 1, 2, 4, 5, 12)] == [
        "/start",
        "Incoming 👩‍💻",
        "Recovered — بازیابی شد ✓",
        "Callback received; restart me / بازیابی",
        "publish photos / تصاویر",
        "publish documents / اسناد",
    ]
    assert history[1]["entities"] == [
        {"type": "custom_emoji", "offset": 9, "length": 5, "custom_emoji_id": "1"}
    ]
    initial_rich = scenario["rich_actions"][0]["effect"]["callback"]["message"]["rich_message"]
    assert initial_rich["blocks"][0]["text"] == [
        "Auto ",
        {"type": "url", "text": "example.test", "url": "https://example.test"},
        " ",
        {"type": "mention", "text": "@sample_bot"},
    ]
    assert initial_rich["blocks"][1]["text"] == [
        {"type": "url", "text": "Link", "url": "https://example.test/local"},
        " / ",
        {"type": "text_mention", "text": "Sara", "user_id": 2},
        " / ",
        {
            "type": "custom_emoji",
            "custom_emoji_id": "1",
            "alternative_text": "STATIC-ALT",
        },
    ]
    assert [target["path"] for target in scenario["rich_observation"]["targets"]] == [
        ["blocks", 2, "buttons", 0],
        ["blocks", 3, "text", "button"],
    ]
    assert [action["effect"]["callback"]["data"] for action in scenario["rich_actions"]] == [
        "rich:row",
        "rich:inline",
    ]
    assert all(action["status"] == "succeeded" for action in scenario["rich_actions"])
    assert history[3]["rich_message"] == {
        "blocks": [{"type": "paragraph", "text": "Rich callbacks complete / کنش‌های غنی کامل شد"}]
    }

    assert [message["photo"]["asset_id"] for message in history[6:12]] == [4, 4, 5, 5, 4, 5]
    assert [message.get("media_group_id") for message in history[10:12]] == ["1", "1"]
    assert [message["document"]["document_id"] for message in history[13:17]] == [
        "1",
        "2",
        "1",
        "2",
    ]
    assert [message.get("media_group_id") for message in history[15:17]] == ["2", "2"]
    assert second_bot[4]["value"]["downloads"] == [
        {
            "file": second_bot[4]["value"]["downloads"][0]["file"],
            "size": 821,
            "sha256": next(iter(ASSET_HASHES["image/png"])),
        },
        {
            "file": second_bot[4]["value"]["downloads"][1]["file"],
            "size": 287,
            "sha256": next(iter(ASSET_HASHES["image/jpeg"])),
        },
    ]
    assert [row["sha256"] for row in second_bot[5]["value"]["downloads"]] == [
        DOCUMENT_HASHES["default.txt"],
        DOCUMENT_HASHES["forced-image.png"],
    ]

    interactions = scenario_interactions(recorded)
    assert [
        scenario["start"],
        scenario["ordinary_action"],
        *scenario["rich_actions"],
        scenario["photos_input"],
        scenario["documents_input"],
    ] == interactions
    assert [row.get("operation") for row in interactions] == [
        "start_bot_chat",
        None,
        None,
        None,
        "type_message",
        "type_message",
    ]
    assert [row["sends"][0]["message"]["id"] for row in interactions if "sends" in row] == [
        1,
        6,
        13,
    ]
    assert all(row.get("native", native) is native for row in interactions)

    api_records = second_bot[-1]["api"]
    delivered = [
        update
        for record in api_records
        if record["method"] == "getUpdates"
        for update in record["body"]["result"]
    ]
    assert [update["update_id"] for update in delivered] == [1, 2, 3, 3, 4, 5, 6, 7]
    assert delivered[2] == delivered[3]
    assert [
        update.get("message", {}).get("text") or update.get("callback_query", {}).get("data")
        for update in delivered
    ] == [
        "/start",
        "Incoming 👩‍💻",
        "ordinary:recover",
        "ordinary:recover",
        "rich:row",
        "rich:inline",
        "publish photos / تصاویر",
        "publish documents / اسناد",
    ]

    with World.open(output / "world") as world:
        assert world.history(1) == history
        snapshot = world.client_snapshot(2, version=6)
        changes = world.client_changes(2, after=0, limit=100, version=6)
        assert snapshot["messages"] == history
        assert changes["cursor"] == changes["head"] == 19
        assert [row["position"] for row in changes["changes"]] == list(range(1, 20))
        assert [row["type"] for row in changes["changes"]].count("message.edited") == 2
        assert snapshot["custom_emoji"] == scenario["registrations"]
        observed_assets: dict[str, set[str]] = {}
        for asset in snapshot["assets"]:
            observed_assets.setdefault(asset["mime_type"], set()).add(asset["sha256"])
        assert observed_assets == ASSET_HASHES
        assert {row["file_name"]: row["sha256"] for row in snapshot["documents"]} == (
            DOCUMENT_HASHES
        )
        message_events = [
            event
            for event in recorded["events"]
            if event["type"] in ("message.created", "message.edited")
            and event["data"]["sender_id"] == 1
        ]
        assert bot_api_messages(api_records) == [
            _message(world, event["data"]) for event in message_events
        ]

    assert scenario["events"] == recorded["events"]
    assert [capture["label"] for capture in recorded["captures"]] == [
        "representative-initial",
        "representative-recovered",
        "representative-photos",
        "representative-documents",
        "representative-relaunch",
    ]
    assert all(capture["rendered"] is native for capture in recorded["captures"])
    assert recorded["configuration"]["bridge_version"] == 6
    retained = json.dumps(recorded)
    assert "gramlab_bot_" not in retained
    assert "gramlab_client_" not in retained
    assert "gramlab-control_" not in retained


def test_auto_detected_rich_text_composes_with_rich_button_discovery(tmp_path: Path) -> None:
    recorded, output = invoke(tmp_path, native=False)
    assert recorded["android"] == {}
    assert_representative(recorded, output, native=False)


@pytest.mark.android
def test_representative_workflow_uses_original_android_offline(tmp_path: Path) -> None:
    recorded, output = invoke(tmp_path, native=True)
    assert_representative(recorded, output, native=True)
    assert_android_evidence(recorded, output)


def assert_android_evidence(recorded: dict[str, Any], output: Path) -> None:
    """Check immutable APK identity and original capture evidence."""
    assert recorded["android"]["api"] == "36"
    assert recorded["android"]["abi"] == "x86_64"
    assert recorded["android"]["network"] == {"ipv4": 1, "ipv6": 1}
    assert recorded["android"]["filesystem"] == {
        "world_visible": False,
        "bot_visible": False,
        "scenario_visible": False,
        "private_avd_visible": True,
        "same_pid_namespace": False,
        "same_network": True,
    }
    assert recorded["configuration"]["android"]["apk_sha256"] == (
        "e60a873fc0283b270a35538c63a5f6e701e74cfecb8f10cfce35af670c57be7a"
    )
    for capture in recorded["captures"]:
        assert "Accounts: 0" in capture["android"]["accounts"]
        xml = output / "captures" / f"{capture['label']}.xml"
        image = output / "captures" / f"{capture['label']}.png"
        ET.fromstring(xml.read_text())  # noqa: S314 — retained UIAutomator output.
        with Image.open(image) as screenshot:
            assert screenshot.size == (320, 640)
            assert len(screenshot.convert("RGB").getcolors(maxcolors=320 * 640) or []) > 16
        assert image.stat().st_size > 1_000
