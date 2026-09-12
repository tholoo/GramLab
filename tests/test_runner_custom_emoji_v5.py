"""Public bridge-v5 custom-emoji workflow through the contained runner."""

from __future__ import annotations

import hashlib
import http.client
import json
import os
import re
import shutil
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any

import pytest
from PIL import Image

from gramlab.client_bridge import ClientBridge
from gramlab.world import World

ASSETS = Path("tests/assets/custom-emoji")
BOT = {"id": 1, "is_bot": True, "first_name": "emoji"}
USER = {"id": 2, "is_bot": False, "first_name": "Sara", "language_code": "fa"}
CHAT = {"id": 1, "type": "private", "user_id": 2, "bot_id": 1}
PUBLIC_CHAT = {"id": 2, "type": "private", "first_name": "Sara"}
KEYBOARD = {"inline_keyboard": [[{"text": "Animate / متحرک", "callback_data": "emoji:animate"}]]}
ANSWER = {"text": "Animated / متحرک شد", "show_alert": False, "cache_time": 0}
MEDIA = (
    (1, "emoji-static.webp", "image/webp", 100, 100),
    (2, "emoji-thumbnail.webp", "image/webp", 16, 16),
    (3, "emoji-animated.webm", "video/webm", 100, 100),
)


def project(directory: Path, *, mode: str) -> Path:
    directory.mkdir()
    timeout = 60 if mode == "simulation-only" else 300
    manifest = directory / "run.toml"
    manifest.write_text(
        f'schema = 1\nmode = "{mode}"\nseed = 116\nnow = 1700000000\n'
        f"timeout = {timeout}\n"
        '[scenario]\nentry = "scenario.py"\n'
        'files = ["scenario.py", "emoji-static.webp", "emoji-animated.webm", '
        '"emoji-thumbnail.webp"]\n'
        '[bots.emoji]\nentry = "bot.py"\n'
        'files = ["bot.py", "emoji-static.webp", "emoji-animated.webm", '
        '"emoji-thumbnail.webp"]\n'
    )
    shutil.copy2("tests/custom_emoji_runner_scenario.py", directory / "scenario.py")
    shutil.copy2("tests/fixtures/custom_emoji_runner_bot.py", directory / "bot.py")
    for name in ("emoji-static.webp", "emoji-animated.webm", "emoji-thumbnail.webp"):
        shutil.copy2(ASSETS / name, directory / name)
    return manifest


def invoke(directory: Path, *, mode: str) -> tuple[dict[str, Any], Path, Path]:
    manifest = project(directory, mode=mode)
    output = directory.parent / (mode + "-run")
    arguments = [
        sys.executable,
        "-m",
        "gramlab",
        "run",
        str(manifest),
        "--output",
        str(output),
        "--bridge-version",
        "5",
    ]
    if mode == "headless-android":
        android_profile = os.environ.get("GRAMLAB_ANDROID_RUNTIME_PROFILE")
        apk = os.environ.get("GRAMLAB_ANDROID_PROBE_APK")
        if android_profile is None or apk is None or not os.access("/dev/kvm", os.R_OK | os.W_OK):
            pytest.skip("Requires the Android profile, reviewed normal30 APK and accessible KVM")
        arguments.extend(("--android-profile", android_profile, "--android-apk", apk))
    result = subprocess.run(  # noqa: S603 - public CLI inside the outer network namespace
        arguments,
        capture_output=True,
        text=True,
        timeout=90 if mode == "simulation-only" else 420,
        env=os.environ.copy(),
    )
    (output.parent / (mode + "-stdout.log")).write_text(result.stdout)
    (output.parent / (mode + "-stderr.log")).write_text(result.stderr)
    recorded = json.loads((output / "result.json").read_text())
    assert result.returncode == 0, recorded
    assert recorded["outcome"] == "passed" and recorded["failure"] is None
    return recorded, output, manifest


def process_json(recorded: dict[str, Any], name: str) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in recorded["processes"][name]["stdout"].splitlines()
        if line.strip()
    ]


def emoji_entity(identifier: str) -> dict[str, Any]:
    return {
        "type": "custom_emoji",
        "offset": 9,
        "length": 5,
        "custom_emoji_id": identifier,
    }


def rich_content(identifier: str) -> dict[str, Any]:
    return {
        "blocks": [
            {
                "type": "paragraph",
                "text": [
                    "Rich / غنی ",
                    {
                        "type": "custom_emoji",
                        "custom_emoji_id": identifier,
                        "alternative_text": "RICH-ALT",
                    },
                ],
            },
            {
                "type": "buttons",
                "buttons": [
                    {
                        "text": [
                            "Badge / نشان ",
                            {
                                "type": "custom_emoji",
                                "custom_emoji_id": identifier,
                                "alternative_text": "BUTTON-ALT",
                            },
                        ],
                        "disabled": {},
                    }
                ],
            },
        ]
    }


def rich_input(identifier: str) -> dict[str, Any]:
    return {"skip_entity_detection": True, **rich_content(identifier)}


def world_message(message_id: int, identifier: str, *, initial: bool) -> dict[str, Any]:
    if message_id == 1:
        return {
            "id": 1,
            "chat_id": 1,
            "sender_id": 2,
            "date": 1_700_000_000,
            "text": "Incoming 👩‍💻",
            "entities": [emoji_entity("1")],
        }
    result: dict[str, Any] = {
        "id": message_id,
        "chat_id": 1,
        "sender_id": 1,
        "date": 1_700_000_000,
        "text": "Ordinary 👩‍💻" if message_id == 2 else "",
    }
    if not initial:
        result["edit_date"] = 1_700_000_005
    if message_id == 2:
        if initial:
            result["reply_markup"] = KEYBOARD
        result["entities"] = [emoji_entity(identifier)]
    else:
        result["rich_message"] = rich_content(identifier)
    return result


def public_message(message_id: int, identifier: str, *, initial: bool) -> dict[str, Any]:
    world = world_message(message_id, identifier, initial=initial)
    result: dict[str, Any] = {
        "message_id": message_id,
        "from": USER if message_id == 1 else BOT,
        "chat": PUBLIC_CHAT,
        "date": 1_700_000_000,
    }
    for key in ("text", "edit_date", "reply_markup", "entities", "rich_message"):
        if key in world and not (message_id == 3 and key == "text"):
            result[key] = world[key]
    return result


def asset_descriptors() -> list[dict[str, Any]]:
    return [
        {
            "asset_id": asset_id,
            "mime_type": mime_type,
            "file_size": (ASSETS / name).stat().st_size,
            "sha256": hashlib.sha256((ASSETS / name).read_bytes()).hexdigest(),
            "width": width,
            "height": height,
        }
        for asset_id, name, mime_type, width, height in MEDIA
    ]


def emoji_descriptors() -> list[dict[str, Any]]:
    return [
        {
            "custom_emoji_id": "1",
            "fallback": "👩‍💻",
            "free": True,
            "needs_repainting": False,
            "main_asset_id": 1,
            "thumbnail_asset_id": 2,
            "duration_ms": 0,
        },
        {
            "custom_emoji_id": "1109",
            "fallback": "👩‍💻",
            "free": True,
            "needs_repainting": False,
            "main_asset_id": 3,
            "thumbnail_asset_id": 2,
            "duration_ms": 1000,
        },
    ]


def expected_messages(*, initial: bool) -> list[dict[str, Any]]:
    identifier = "1" if initial else "1109"
    return [
        world_message(1, "1", initial=True),
        world_message(2, identifier, initial=initial),
        world_message(3, identifier, initial=initial),
    ]


def public_ok(result: Any) -> dict[str, Any]:
    return {"ok": True, "result": result}


def strip_android(record: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in record.items() if key != "android"}


def expected_events(callback: dict[str, Any]) -> list[dict[str, Any]]:
    initial = expected_messages(initial=True)
    final = expected_messages(initial=False)
    frozen = {key: value for key, value in callback.items() if key != "answer"}
    return [
        {"sequence": 1, "type": "user.created", "data": BOT},
        {"sequence": 2, "type": "user.created", "data": USER},
        {"sequence": 3, "type": "chat.created", "data": CHAT},
        {"sequence": 4, "type": "message.created", "data": initial[0]},
        {"sequence": 5, "type": "message.created", "data": initial[1]},
        {"sequence": 6, "type": "message.created", "data": initial[2]},
        {"sequence": 7, "type": "clock.advanced", "data": {"now": 1_700_000_005}},
        {"sequence": 8, "type": "callback.created", "data": frozen},
        {
            "sequence": 9,
            "type": "callback.answered",
            "data": {"id": callback["id"], "user_id": 2, "answer": ANSWER},
        },
        {"sequence": 10, "type": "message.edited", "data": final[1]},
        {"sequence": 11, "type": "message.edited", "data": final[2]},
    ]


def assert_stickers_and_downloads(initial: dict[str, Any]) -> list[dict[str, Any]]:
    assets = asset_descriptors()
    stickers = initial["stickers"]
    assert len(stickers) == 2
    file_ids = [
        stickers[0]["file_id"],
        stickers[0]["thumbnail"]["file_id"],
        stickers[1]["file_id"],
    ]
    assert len(set(file_ids)) == 3
    assert all(re.fullmatch(r"gramlab_[A-Za-z0-9_-]{32}", value) for value in file_ids)
    thumbnail = {
        "file_id": file_ids[1],
        "file_unique_id": assets[1]["sha256"],
        "width": 16,
        "height": 16,
        "file_size": assets[1]["file_size"],
    }
    expected = [
        {
            "file_id": file_ids[0],
            "file_unique_id": assets[0]["sha256"],
            "file_size": assets[0]["file_size"],
            "type": "custom_emoji",
            "width": 100,
            "height": 100,
            "is_animated": False,
            "is_video": False,
            "custom_emoji_id": "1",
            "emoji": "👩‍💻",
            "thumbnail": thumbnail,
        },
        {
            "file_id": file_ids[2],
            "file_unique_id": assets[2]["sha256"],
            "file_size": assets[2]["file_size"],
            "type": "custom_emoji",
            "width": 100,
            "height": 100,
            "is_animated": False,
            "is_video": True,
            "custom_emoji_id": "1109",
            "emoji": "👩‍💻",
            "thumbnail": thumbnail,
        },
    ]
    assert stickers == expected
    download_specs = {
        "static_main": (file_ids[0], assets[0], "webp"),
        "static_thumbnail": (file_ids[1], assets[1], "webp"),
        "animated_main": (file_ids[2], assets[2], "webm"),
        "animated_thumbnail": (file_ids[1], assets[1], "webp"),
    }
    expected_downloads = {}
    for name, (file_id, asset, extension) in download_specs.items():
        expected_downloads[name] = {
            "get_file": {
                "file_id": file_id,
                "file_unique_id": asset["sha256"],
                "file_size": asset["file_size"],
                "file_path": f"stickers/{file_id}.{extension}",
            },
            "status": 200,
            "content_type": asset["mime_type"],
            "content_length": str(asset["file_size"]),
            "cache_control": "no-store",
            "size": asset["file_size"],
            "sha256": asset["sha256"],
        }
    assert initial["downloads"] == expected_downloads
    return expected


def assert_bot_api(
    recorded: dict[str, Any], callback: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    lines = process_json(recorded, "bot:emoji")
    assert [line["event"] for line in lines] == ["initial", "edited"]
    initial, edited = lines
    expected_stickers = assert_stickers_and_downloads(initial)
    initial_update = {"update_id": 1, "message": public_message(1, "1", initial=True)}
    callback_update = {
        "update_id": 2,
        "callback_query": {
            "id": callback["id"],
            "from": USER,
            "message": public_message(2, "1", initial=True),
            "chat_instance": callback["chat_instance"],
            "data": "emoji:animate",
        },
    }
    assert {key: initial[key] for key in ("event", "update", "ordinary", "rich")} == {
        "event": "initial",
        "update": initial_update,
        "ordinary": public_message(2, "1", initial=True),
        "rich": public_message(3, "1", initial=True),
    }
    assert {key: edited[key] for key in ("event", "update", "answer", "ordinary", "rich")} == {
        "event": "edited",
        "update": callback_update,
        "answer": True,
        "ordinary": public_message(2, "1109", initial=False),
        "rich": public_message(3, "1109", initial=False),
    }

    api = edited["api"]
    assert all(record["status"] == 200 and record["body"].get("ok") is True for record in api)
    update_records = [record for record in api if record["method"] == "getUpdates"]
    nonempty_updates = [
        record["body"]["result"] for record in update_records if record["body"]["result"]
    ]
    assert nonempty_updates == [[initial_update], [callback_update]]
    assert update_records[-1] == {
        "method": "getUpdates",
        "encoding": "json",
        "parameters": {"offset": 3},
        "status": 200,
        "body": public_ok([]),
    }
    initial_index = next(
        index
        for index, record in enumerate(update_records)
        if record["body"]["result"] == [initial_update]
    )
    callback_index = next(
        index
        for index, record in enumerate(update_records)
        if record["body"]["result"] == [callback_update]
    )
    assert initial_index < callback_index < len(update_records) - 1
    assert all(
        record["parameters"] == {"timeout": 10} for record in update_records[: initial_index + 1]
    )
    assert all(
        record["parameters"] == {"offset": 2, "timeout": 10}
        for record in update_records[initial_index + 1 : callback_index + 1]
    )
    assert all(
        not record["body"]["result"]
        for index, record in enumerate(update_records)
        if index not in (initial_index, callback_index)
    )

    ordinary_parameters = {
        "chat_id": 2,
        "text": "Ordinary 👩‍💻",
        "entities": [{"type": "custom_emoji", "offset": 9, "length": 5, "custom_emoji_id": 1}],
        "reply_markup": KEYBOARD,
    }
    non_updates = [record for record in api if record["method"] != "getUpdates"]
    expected_non_updates = [
        (
            "getCustomEmojiStickers",
            "json",
            {"custom_emoji_ids": ["1109", "1", "1109"]},
            expected_stickers,
        ),
        *[
            (
                "getFile",
                "json",
                {"file_id": initial["downloads"][name]["get_file"]["file_id"]},
                initial["downloads"][name]["get_file"],
            )
            for name in (
                "static_main",
                "static_thumbnail",
                "animated_main",
                "animated_thumbnail",
            )
        ],
        ("sendMessage", "json", ordinary_parameters, public_message(2, "1", initial=True)),
        (
            "sendRichMessage",
            "json",
            {"chat_id": 2, "rich_message": rich_input("1")},
            public_message(3, "1", initial=True),
        ),
        (
            "answerCallbackQuery",
            "json",
            {"callback_query_id": callback["id"], "text": ANSWER["text"]},
            True,
        ),
        (
            "editMessageText",
            "json",
            {
                "chat_id": 2,
                "message_id": 2,
                "text": "Ordinary 👩‍💻",
                "entities": [emoji_entity("1109")],
            },
            public_message(2, "1109", initial=False),
        ),
        (
            "editMessageText",
            "form",
            {"chat_id": 2, "message_id": 3, "rich_message": rich_input("1109")},
            public_message(3, "1109", initial=False),
        ),
    ]
    assert len(non_updates) == len(expected_non_updates)
    for actual, (method, encoding, parameters, result) in zip(
        non_updates, expected_non_updates, strict=True
    ):
        assert actual == {
            "method": method,
            "encoding": encoding,
            "parameters": parameters,
            "status": 200,
            "body": public_ok(result),
        }
    return initial_update, callback_update


def assert_v5_state(output: Path, world_id: str, callback: dict[str, Any]) -> None:
    assets = asset_descriptors()
    descriptors = emoji_descriptors()
    initial = expected_messages(initial=True)
    final = expected_messages(initial=False)
    expected_snapshot = {
        "schema": 5,
        "world_id": world_id,
        "user_id": 2,
        "cursor": 11,
        "now": 1_700_000_005,
        "users": [BOT, USER],
        "chats": [CHAT],
        "messages": final,
        "message_position": 5,
        "sends": [],
        "assets": assets,
        "message_revisions": [
            {"chat_id": 1, "message_id": 1, "revision": 4},
            {"chat_id": 1, "message_id": 2, "revision": 10},
            {"chat_id": 1, "message_id": 3, "revision": 11},
        ],
        "custom_emoji": descriptors,
        "documents": [],
    }
    expected_changes = {
        "schema": 5,
        "world_id": world_id,
        "user_id": 2,
        "cursor": 5,
        "head": 5,
        "now": 1_700_000_005,
        "changes": [
            {
                "position": position,
                "type": kind,
                "data": message,
                "revision": revision,
            }
            for position, kind, message, revision in (
                (1, "message.created", initial[0], 4),
                (2, "message.created", initial[1], 5),
                (3, "message.created", initial[2], 6),
                (4, "message.edited", final[1], 10),
                (5, "message.edited", final[2], 11),
            )
        ],
        "users": [BOT, USER],
        "assets": assets,
        "custom_emoji": descriptors,
        "documents": [],
    }
    with World.open(output / "world") as world:
        assert world.client_snapshot(2, version=5) == expected_snapshot
        assert world.client_changes(2, after=0, limit=100, version=5) == expected_changes
        assert world.get_callback(user_id=2, callback_id=callback["id"]) == callback | {
            "answer": ANSWER
        }
        assert world.callback_dependencies(2, callback, version=5) == {
            "users": [BOT, USER],
            "assets": assets[:2],
            "message_revision": 5,
            "custom_emoji": descriptors[:1],
            "documents": [],
        }
        assert world.granted_custom_emoji(2, ["1109", "1", "1109"]) == (
            descriptors,
            assets,
        )
        with pytest.raises(LookupError, match="Document is unavailable"):
            world.granted_custom_emoji(1, ["1"])
        for descriptor, (_, name, _, _, _) in zip(assets, MEDIA, strict=True):
            assert world.granted_asset(2, descriptor["asset_id"]) == (
                descriptor,
                (ASSETS / name).read_bytes(),
            )
            with pytest.raises(ValueError, match="Asset is unavailable"):
                world.granted_asset(1, descriptor["asset_id"])
        capability = world.issue_client_token(2)

    with ClientBridge(output / "world") as bridge:
        host, port = bridge.base_url.removeprefix("http://").split(":")

        def json_request(method: str, path: str, body: dict[str, Any] | None = None) -> Any:
            connection = http.client.HTTPConnection(host, int(port), timeout=10)
            try:
                encoded = json.dumps(body).encode() if body is not None else None
                connection.request(
                    method,
                    path,
                    encoded,
                    {
                        "Authorization": "Bearer " + capability,
                        "Content-Type": "application/json",
                    },
                )
                response = connection.getresponse()
                payload = json.loads(response.read())
                assert response.status == 200
                return payload
            finally:
                connection.close()

        assert json_request("GET", "/v5/snapshot") == expected_snapshot
        assert json_request("GET", "/v5/changes?after=0&limit=100") == expected_changes
        assert json_request(
            "POST", "/v5/custom-emoji-documents", {"custom_emoji_ids": ["1109", "1"]}
        ) == {
            "schema": 5,
            "world_id": world_id,
            "user_id": 2,
            "custom_emoji": descriptors,
            "assets": assets,
        }
        for descriptor, (_, name, _, _, _) in zip(assets, MEDIA, strict=True):
            connection = http.client.HTTPConnection(host, int(port), timeout=10)
            try:
                connection.request(
                    "GET",
                    f"/v5/assets/{descriptor['asset_id']}",
                    headers={"Authorization": "Bearer " + capability},
                )
                response = connection.getresponse()
                payload = response.read()
                assert response.status == 200
                assert response.getheader("Content-Type") == descriptor["mime_type"]
                assert response.getheader("Content-Length") == str(descriptor["file_size"])
                assert response.getheader("Cache-Control") == "no-store"
                assert payload == (ASSETS / name).read_bytes()
            finally:
                connection.close()


def assert_sources(recorded: dict[str, Any], project_directory: Path) -> None:
    selected = {
        "scenario": [
            "scenario.py",
            "emoji-static.webp",
            "emoji-animated.webm",
            "emoji-thumbnail.webp",
        ],
        "bots/emoji": [
            "bot.py",
            "emoji-static.webp",
            "emoji-animated.webm",
            "emoji-thumbnail.webp",
        ],
    }
    assert recorded["sources"] == {
        component: {
            name: hashlib.sha256((project_directory / name).read_bytes()).hexdigest()
            for name in names
        }
        for component, names in selected.items()
    }


def assert_public_result(
    recorded: dict[str, Any], output: Path, manifest: Path, *, native: bool
) -> None:
    world_id = recorded["run_id"]
    assert str(uuid.UUID(world_id)) == world_id
    assert recorded["mode"] == ("headless-android" if native else "simulation-only")
    assert recorded["world"] == {
        "schema": 1,
        "seed": 116,
        "now": 1_700_000_005,
        "users": [BOT, USER],
        "chats": [CHAT],
    }
    callback = recorded["interactions"][0]["callback"]
    assert str(uuid.UUID(callback["id"])) == callback["id"]
    assert callback == {
        "id": callback["id"],
        "user_id": 2,
        "chat_id": 1,
        "message": world_message(2, "1", initial=True),
        "data": "emoji:animate",
        "chat_instance": hashlib.sha256(f"{world_id}:1".encode()).hexdigest(),
        "answer": None,
    }
    assert strip_android(recorded["interactions"][0]) == {
        "chat_id": 1,
        "message_id": 2,
        "row": 0,
        "column": 0,
        "native": native,
        "callback": callback,
    }
    assert ("android" in recorded["interactions"][0]) is native

    initial = expected_messages(initial=True)
    final = expected_messages(initial=False)
    assert recorded["histories"] == {"1": final}
    events = expected_events(callback)
    assert recorded["events"] == events
    capture_bases = [
        {
            "chat_id": 1,
            "label": label,
            "history": initial if label.endswith("initial") else final,
            "rendered": native,
        }
        for label in (
            "custom-emoji-initial",
            "custom-emoji-edited",
            "custom-emoji-relaunch",
        )
    ]
    assert [strip_android(capture) for capture in recorded["captures"]] == capture_bases
    assert all(("android" in capture) is native for capture in recorded["captures"])

    scenario_lines = process_json(recorded, "scenario")
    assert len(scenario_lines) == 1
    scenario = scenario_lines[0]
    assert scenario == {
        "static": emoji_descriptors()[0],
        "animated": emoji_descriptors()[1],
        "incoming": initial[0],
        "initial_history": initial,
        "initial_capture": recorded["captures"][0],
        "interaction": recorded["interactions"][0],
        "answer": ANSWER,
        "edited_capture": recorded["captures"][1],
        "relaunch_capture": recorded["captures"][2],
        "final_history": final,
        "events": events,
    }
    assert_bot_api(recorded, callback)
    assert_v5_state(output, world_id, callback)
    assert_sources(recorded, manifest.parent)
    assert recorded["rich_button_recovery"] == {
        "artifact": "rich-button-recovery.json",
        "failure": None,
    }
    assert recorded["lifecycle"] == []
    for process in recorded["processes"].values():
        assert {key: process[key] for key in process if key not in {"stdout", "stderr"}} == {
            "exit_code": 0,
            "stopped_by_runner": False,
            "stopped_by_scenario": False,
            "generation": 1,
            "stdout_complete": True,
            "stderr_complete": True,
        }
        assert process["stderr"] == ""
    serialized = json.dumps(recorded, ensure_ascii=False)
    assert "gramlab_bot_" not in serialized
    assert "gramlab_client_" not in serialized
    assert "gramlab-control_" not in serialized


def test_public_runner_verifies_complete_custom_emoji_v5_workflow(tmp_path: Path) -> None:
    recorded, output, manifest = invoke(tmp_path / "project", mode="simulation-only")
    assert_public_result(recorded, output, manifest, native=False)
    assert recorded["android"] == {}
    assert recorded["configuration"] == {
        "schema": 1,
        "mode": "simulation-only",
        "seed": 116,
        "now": 1_700_000_000,
        "timeout": 60,
        "scenario": {
            "entry": "scenario.py",
            "files": [
                "scenario.py",
                "emoji-static.webp",
                "emoji-animated.webm",
                "emoji-thumbnail.webp",
            ],
        },
        "bots": {
            "emoji": {
                "entry": "bot.py",
                "files": [
                    "bot.py",
                    "emoji-static.webp",
                    "emoji-animated.webm",
                    "emoji-thumbnail.webp",
                ],
            }
        },
    }
    assert all(capture["rendered"] is False for capture in recorded["captures"])
    assert (output / "report.html").read_text().count("data:image/png;base64,") == 0


@pytest.mark.android
def test_public_runner_captures_custom_emoji_in_original_android_at_v5(tmp_path: Path) -> None:
    recorded, output, manifest = invoke(tmp_path / "project", mode="headless-android")
    assert_public_result(recorded, output, manifest, native=True)
    apk = Path(os.environ["GRAMLAB_ANDROID_PROBE_APK"])
    assert recorded["configuration"]["android"] == {
        "apk_sha256": hashlib.sha256(apk.read_bytes()).hexdigest(),
        "profile_sha256": recorded["configuration"]["android"]["profile_sha256"],
        "image_package": "system-images;android-36;default;x86_64",
        "bridge_version": 5,
    }
    observed = recorded["android"]
    assert observed["api"] == "36" and observed["abi"] == "x86_64"
    assert observed["network"] == {"ipv4": 1, "ipv6": 1}
    assert observed["filesystem"] == {
        "world_visible": False,
        "bot_visible": False,
        "scenario_visible": False,
        "private_avd_visible": True,
        "same_pid_namespace": False,
        "same_network": True,
    }
    assert recorded["interactions"][0]["android"]["target"]["text"] == ("Animate / متحرک")
    for capture in recorded["captures"]:
        android = capture["android"]
        assert "Accounts: 0" in android["accounts"]
        assert "Status: ok" in android["launch"] and "LaunchState: COLD" in android["launch"]
        assert all(label in android["ui"] for label in ("Incoming", "Ordinary", "Rich", "Badge"))
        png = output / "captures" / f"{capture['label']}.png"
        assert png.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
        with Image.open(png) as image:
            assert image.format == "PNG" and image.size == (320, 640)
    assert (output / "report.html").read_text().count("data:image/png;base64,") == 3
