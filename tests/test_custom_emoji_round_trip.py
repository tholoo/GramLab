"""Independent oracle for the real contained custom-emoji bot lifecycle."""

import hashlib
import json
import os
import re
import shutil
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Any

from gramlab.runtime import RuntimeProfile, Sandbox

ASSETS = Path("tests/assets/custom-emoji")
USER = {"id": 1, "is_bot": False, "first_name": "Sara", "language_code": "fa"}
BOT = {
    "id": 2,
    "is_bot": True,
    "first_name": "Echo",
    "username": "gramlab_echo_bot",
}
OTHER = {"id": 3, "is_bot": False, "first_name": "Uninvolved"}
CHAT = {"id": 1, "type": "private", "user_id": 1, "bot_id": 2}
PUBLIC_CHAT = {"id": 1, "type": "private", "first_name": "Sara"}
KEYBOARD = {"inline_keyboard": [[{"text": "Animate / متحرک", "callback_data": "emoji:animate"}]]}
NOOP = {
    "status": 400,
    "body": {"ok": False, "error_code": 400, "description": "MESSAGE_NOT_MODIFIED"},
}
ANSWER = {"text": "Animated / متحرک شد", "show_alert": False, "cache_time": 0}


def stage_scenario(directory: Path, core: RuntimeProfile) -> None:
    shutil.copytree(
        "src/gramlab", directory / "gramlab", ignore=shutil.ignore_patterns("__pycache__")
    )
    (directory / "component-profile.json").write_text(json.dumps(asdict(core)))
    shutil.copy2("tests/fixtures/custom_emoji_bot.py", directory / "custom_emoji_bot.py")
    for name in ("component_bot.py", "custom_emoji_round_trip.py"):
        shutil.copy2(Path("tests/probes") / name, directory / name)
    target = directory / "custom-emoji"
    target.mkdir()
    for name in ("emoji-static.webp", "emoji-animated.webm", "emoji-thumbnail.webp"):
        shutil.copy2(ASSETS / name, target / name)


def emoji_entity(identifier: str, offset: int) -> dict[str, Any]:
    return {
        "type": "custom_emoji",
        "offset": offset,
        "length": 5,
        "custom_emoji_id": identifier,
    }


def rich_content(identifier: str) -> dict[str, Any]:
    return {
        "blocks": [
            {
                "type": "paragraph",
                "text": [
                    "Rich ",
                    {
                        "type": "custom_emoji",
                        "custom_emoji_id": identifier,
                        "alternative_text": "different",
                    },
                ],
            },
            {
                "type": "buttons",
                "buttons": [
                    {
                        "text": [
                            "Badge ",
                            {
                                "type": "custom_emoji",
                                "custom_emoji_id": identifier,
                                "alternative_text": "",
                            },
                        ],
                        "disabled": {},
                    }
                ],
            },
        ]
    }


def world_message(message_id: int, identifier: str, *, initial: bool) -> dict[str, Any]:
    if message_id == 1:
        return {
            "id": 1,
            "chat_id": 1,
            "sender_id": 1,
            "date": 1700000000,
            "text": "سلام 👩‍💻",
            "entities": [emoji_entity("1", 5)],
        }
    result: dict[str, Any] = {
        "id": message_id,
        "chat_id": 1,
        "sender_id": 2,
        "date": 1700000000,
        "text": "Ordinary 👩‍💻" if message_id == 2 else "",
    }
    if not initial:
        result["edit_date"] = 1700000005
    if message_id == 2:
        if initial:
            result["reply_markup"] = KEYBOARD
        result["entities"] = [emoji_entity(identifier, 9)]
    else:
        result["rich_message"] = rich_content(identifier)
    return result


def public_message(message_id: int, identifier: str, *, initial: bool) -> dict[str, Any]:
    world = world_message(message_id, identifier, initial=initial)
    result = {
        "message_id": message_id,
        "from": USER if message_id == 1 else BOT,
        "chat": PUBLIC_CHAT,
        "date": 1700000000,
    }
    for key in ("text", "edit_date", "reply_markup", "entities", "rich_message"):
        if key in world and not (message_id == 3 and key == "text"):
            result[key] = world[key]
    return result


def asset_descriptors() -> list[dict[str, Any]]:
    specs = (
        (1, "emoji-static.webp", "image/webp", 100, 100),
        (2, "emoji-thumbnail.webp", "image/webp", 16, 16),
        (3, "emoji-animated.webm", "video/webm", 100, 100),
    )
    return [
        {
            "asset_id": asset_id,
            "mime_type": mime,
            "file_size": (ASSETS / name).stat().st_size,
            "sha256": hashlib.sha256((ASSETS / name).read_bytes()).hexdigest(),
            "width": width,
            "height": height,
        }
        for asset_id, name, mime, width, height in specs
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


def snapshot(world_id: str, phase: str) -> dict[str, Any]:
    initial = phase == "initial"
    messages = [
        world_message(1, "1", initial=True),
        world_message(2, "1" if initial else "1109", initial=initial),
        world_message(3, "1" if initial else "1109", initial=initial),
    ]
    return {
        "schema": 4,
        "world_id": world_id,
        "user_id": 1,
        "cursor": 7 if initial else 12,
        "now": 1700000000 if initial else 1700000005,
        "users": [USER, BOT],
        "chats": [CHAT],
        "messages": messages,
        "message_position": 3 if initial else 5,
        "sends": [],
        "assets": asset_descriptors()[:2] if initial else asset_descriptors(),
        "message_revisions": [
            {"chat_id": 1, "message_id": 1, "revision": 5},
            {"chat_id": 1, "message_id": 2, "revision": 6 if initial else 11},
            {"chat_id": 1, "message_id": 3, "revision": 7 if initial else 12},
        ],
        "custom_emoji": emoji_descriptors()[:1] if initial else emoji_descriptors(),
    }


def ok(value: Any) -> dict[str, Any]:
    return {"status": 200, "body": {"ok": True, "result": value}}


def api_record(method: str, response: dict[str, Any], *, form: bool = False) -> dict[str, Any]:
    return {"method": method, "encoding": "form" if form else "json", "response": response}


def assert_scenario(observed: dict[str, Any]) -> None:
    world_id = observed["world_id"]
    assert str(uuid.UUID(world_id)) == world_id
    callback_id = observed["callbacks"]["created"]["callback"]["id"]
    assert str(uuid.UUID(callback_id)) == callback_id
    chat_instance = hashlib.sha256(f"{world_id}:1".encode()).hexdigest()
    assets = asset_descriptors()
    descriptors = emoji_descriptors()
    initial_world = [
        world_message(1, "1", initial=True),
        world_message(2, "1", initial=True),
        world_message(3, "1", initial=True),
    ]
    final_world = [
        world_message(1, "1", initial=True),
        world_message(2, "1109", initial=False),
        world_message(3, "1109", initial=False),
    ]
    initial_update = {"update_id": 1, "message": public_message(1, "1", initial=True)}
    frozen_callback = {
        "id": callback_id,
        "user_id": 1,
        "chat_id": 1,
        "message": initial_world[1],
        "data": "emoji:animate",
        "chat_instance": chat_instance,
    }
    callback_update = {
        "update_id": 2,
        "callback_query": {
            "id": callback_id,
            "from": USER,
            "message": public_message(2, "1", initial=True),
            "chat_instance": chat_instance,
            "data": "emoji:animate",
        },
    }

    stickers = observed["bot"]["initial"]["stickers"]
    assert len(stickers) == 2
    file_ids = [stickers[0]["file_id"], stickers[0]["thumbnail"]["file_id"], stickers[1]["file_id"]]
    assert len(set(file_ids)) == 3
    assert all(re.fullmatch(r"gramlab_[A-Za-z0-9_-]{32}", value) for value in file_ids)
    thumbnail = {
        "file_id": file_ids[1],
        "file_unique_id": assets[1]["sha256"],
        "width": 16,
        "height": 16,
        "file_size": assets[1]["file_size"],
    }
    expected_stickers = [
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
    assert stickers == expected_stickers
    download_specs = {
        "static_main": (file_ids[0], assets[0], "webp"),
        "static_thumbnail": (file_ids[1], assets[1], "webp"),
        "animated_main": (file_ids[2], assets[2], "webm"),
        "animated_thumbnail": (file_ids[1], assets[1], "webp"),
    }
    downloads = {}
    for name, (file_id, asset, extension) in download_specs.items():
        downloads[name] = {
            "get_file": {
                "file_id": file_id,
                "file_unique_id": asset["sha256"],
                "file_size": asset["file_size"],
                "file_path": f"stickers/{file_id}.{extension}",
            },
            "content_type": asset["mime_type"],
            "size": asset["file_size"],
            "sha256": asset["sha256"],
        }
    bot = {
        "initial": {
            "event": "initial",
            "update": initial_update,
            "stickers": expected_stickers,
            "downloads": downloads,
            "ordinary": public_message(2, "1", initial=True),
            "rich": public_message(3, "1", initial=True),
            "noop": NOOP,
        },
        "edited": {
            "event": "edited",
            "update": callback_update,
            "answer": True,
            "ordinary": public_message(2, "1109", initial=False),
            "rich": public_message(3, "1109", initial=False),
        },
    }

    callback_base = {
        "schema": 4,
        "world_id": world_id,
        "user_id": 1,
        "users": [USER, BOT],
        "assets": assets[:2],
        "message_revision": 6,
        "custom_emoji": descriptors[:1],
    }
    callbacks = {
        "created": callback_base | {"callback": frozen_callback | {"answer": None}},
        "answered": callback_base | {"callback": frozen_callback | {"answer": ANSWER}},
        "restarted": callback_base | {"callback": frozen_callback | {"answer": ANSWER}},
    }
    unavailable = {
        "status": 404,
        "body": {
            "schema": 4,
            "error": {"code": "document_unavailable", "message": "Document is unavailable"},
        },
    }
    document_body = {
        "schema": 4,
        "world_id": world_id,
        "user_id": 1,
        "custom_emoji": descriptors,
        "assets": assets,
    }
    asset_responses = {
        str(asset["asset_id"]): {
            "status": 200,
            "content_type": asset["mime_type"],
            "content_length": str(asset["file_size"]),
            "cache_control": "no-store",
            "connection": "close",
            "size": asset["file_size"],
            "sha256": asset["sha256"],
        }
        for asset in assets
    }
    documents = {
        "static_initial": {
            "status": 200,
            "body": document_body | {"custom_emoji": descriptors[:1], "assets": assets[:2]},
        },
        "ungranted": unavailable,
        "mixed": unavailable,
        "integer": {
            "status": 400,
            "body": {
                "schema": 4,
                "error": {
                    "code": "invalid_request",
                    "message": "custom_emoji_ids must contain decimal strings",
                },
            },
        },
        "uninvolved_snapshot": {
            "status": 200,
            "body": {
                "schema": 4,
                "world_id": world_id,
                "user_id": 3,
                "cursor": 7,
                "now": 1700000000,
                "users": [OTHER],
                "chats": [],
                "messages": [],
                "message_position": 0,
                "sends": [],
                "assets": [],
                "message_revisions": [],
                "custom_emoji": [],
            },
        },
        "both_edited": {"status": 200, "body": document_body},
        "assets_edited": asset_responses,
        "both_restarted": {"status": 200, "body": document_body},
        "assets_restarted": asset_responses,
    }

    changes_list = [
        {"position": 1, "type": "message.created", "data": initial_world[0], "revision": 5},
        {"position": 2, "type": "message.created", "data": initial_world[1], "revision": 6},
        {"position": 3, "type": "message.created", "data": initial_world[2], "revision": 7},
        {"position": 4, "type": "message.edited", "data": final_world[1], "revision": 11},
        {"position": 5, "type": "message.edited", "data": final_world[2], "revision": 12},
    ]
    change_base = {
        "schema": 4,
        "world_id": world_id,
        "user_id": 1,
        "cursor": 5,
        "head": 5,
        "now": 1700000005,
        "users": [USER, BOT],
    }
    changes = {
        "all": change_base
        | {"changes": changes_list, "assets": assets, "custom_emoji": descriptors},
        "edited": change_base
        | {
            "changes": changes_list[3:],
            "assets": assets[1:],
            "custom_emoji": descriptors[1:],
        },
    }
    events = [
        {"sequence": 1, "type": "user.created", "data": USER},
        {"sequence": 2, "type": "user.created", "data": BOT},
        {"sequence": 3, "type": "user.created", "data": OTHER},
        {"sequence": 4, "type": "chat.created", "data": CHAT},
        {"sequence": 5, "type": "message.created", "data": initial_world[0]},
        {"sequence": 6, "type": "message.created", "data": initial_world[1]},
        {"sequence": 7, "type": "message.created", "data": initial_world[2]},
        {"sequence": 8, "type": "clock.advanced", "data": {"now": 1700000005}},
        {"sequence": 9, "type": "callback.created", "data": frozen_callback},
        {
            "sequence": 10,
            "type": "callback.answered",
            "data": {"id": callback_id, "user_id": 1, "answer": ANSWER},
        },
        {"sequence": 11, "type": "message.edited", "data": final_world[1]},
        {"sequence": 12, "type": "message.edited", "data": final_world[2]},
    ]

    api = [
        api_record("getUpdates", ok([initial_update])),
        api_record("getCustomEmojiStickers", ok(expected_stickers)),
    ]
    for name in ("static_main", "static_thumbnail", "animated_main", "animated_thumbnail"):
        api.append(api_record("getFile", ok(downloads[name]["get_file"])))
    api.extend(
        [
            api_record("sendMessage", ok(public_message(2, "1", initial=True))),
            api_record("sendRichMessage", ok(public_message(3, "1", initial=True))),
            api_record("editMessageText", NOOP, form=True),
            api_record("getUpdates", ok([callback_update])),
            api_record("answerCallbackQuery", ok(True)),
            api_record("editMessageText", ok(public_message(2, "1109", initial=False))),
            api_record("editMessageText", ok(public_message(3, "1109", initial=False)), form=True),
            api_record("getUpdates", ok([])),
        ]
    )
    assert {key: value for key, value in observed.items() if key != "client"} == {
        "world_id": world_id,
        "bot": bot,
        "snapshots": {
            "initial": snapshot(world_id, "initial"),
            "edited": snapshot(world_id, "edited"),
            "restarted": snapshot(world_id, "restarted"),
        },
        "callbacks": callbacks,
        "documents": documents,
        "changes": changes,
        "history": final_world,
        "events": events,
        "pending": [],
        "api": api,
    }


def test_real_bot_custom_emoji_lifecycle(tmp_path: Path) -> None:
    profile = RuntimeProfile.load(Path(os.environ["GRAMLAB_RUNTIME_PROFILE"]))
    stage_scenario(tmp_path, profile)
    result = Sandbox(profile).supervise(
        [profile.python, "/work/custom_emoji_round_trip.py"], data=tmp_path, timeout=60
    )
    (tmp_path / "custom-emoji-result.json").write_text(result.stdout)
    (tmp_path / "custom-emoji-stderr.log").write_text(result.stderr)
    assert result.returncode == 0, result.stderr
    assert_scenario(json.loads(result.stdout))
