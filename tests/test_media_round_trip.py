"""A real contained bot specifies durable local photo behavior at public boundaries."""

import hashlib
import json
import os
import shutil
from dataclasses import asdict
from pathlib import Path
from typing import Any

from gramlab.runtime import RuntimeProfile, Sandbox

PNG = Path("tests/assets/rich-media/photo-square-16x16.png")
JPEG = Path("tests/assets/rich-media/photo-quadrants-64x48.jpg")


def stage_media_scenario(directory: Path, core: RuntimeProfile) -> None:
    shutil.copytree(
        "src/gramlab", directory / "gramlab", ignore=shutil.ignore_patterns("__pycache__")
    )
    (directory / "component-profile.json").write_text(json.dumps(asdict(core)))
    for name in ("component_bot.py", "media_round_trip.py"):
        shutil.copy2(Path("tests/probes") / name, directory / name)
    for name in ("media_bot.py", "media-scene.json"):
        shutil.copy2(Path("tests/fixtures") / name, directory / name)
    shutil.copy2(PNG, directory / PNG.name)
    shutil.copy2(JPEG, directory / JPEG.name)


def assert_media_scenario(observed: dict[str, Any]) -> None:
    scene = json.loads(Path("tests/fixtures/media-scene.json").read_text())
    world_id = observed["world_id"]
    published = observed["bot"]["published"]
    ordinary = published["ordinary"]
    ordinary_reuse = published["ordinary_reuse"]
    rich = published["rich"]
    rich_reuse = published["rich_reuse"]
    edited = observed["bot"]["edited"]

    bot_user = {
        "id": 2,
        "is_bot": True,
        "first_name": "Echo",
        "username": "gramlab_echo_bot",
    }
    chat = {"id": 1, "type": "private", "first_name": "Sara"}
    png_size = ordinary["photo"][0]
    jpeg_size = rich["rich_message"]["blocks"][0]["photo"][0]
    assert set(png_size) == {"file_id", "file_unique_id", "width", "height", "file_size"}
    assert set(jpeg_size) == set(png_size)
    assert png_size | {} == {
        "file_id": png_size["file_id"],
        "file_unique_id": png_size["file_unique_id"],
        "width": 16,
        "height": 16,
        "file_size": PNG.stat().st_size,
    }
    assert jpeg_size | {} == {
        "file_id": jpeg_size["file_id"],
        "file_unique_id": jpeg_size["file_unique_id"],
        "width": 64,
        "height": 48,
        "file_size": JPEG.stat().st_size,
    }
    assert png_size["file_id"] != jpeg_size["file_id"]
    assert png_size["file_unique_id"] != jpeg_size["file_unique_id"]

    ordinary_expected = {
        "message_id": 2,
        "from": bot_user,
        "chat": chat,
        "date": 1700000000,
        "photo": [png_size],
        "caption": scene["ordinary_caption"],
        "caption_entities": scene["ordinary_entities"],
    }
    ordinary_reuse_expected = {
        "message_id": 3,
        "from": bot_user,
        "chat": chat,
        "date": 1700000000,
        "photo": [png_size],
    }
    rich_initial_block = {
        "type": "photo",
        "photo": [jpeg_size],
        "caption": scene["rich_initial_caption"],
    }
    keyboard = {
        "inline_keyboard": [[{"text": "Inspect / بررسی", "callback_data": scene["callback_data"]}]]
    }
    rich_expected = {
        "message_id": 4,
        "from": bot_user,
        "chat": chat,
        "date": 1700000000,
        "rich_message": {"blocks": [rich_initial_block]},
        "reply_markup": keyboard,
    }
    rich_reuse_expected = {
        "message_id": 5,
        "from": bot_user,
        "chat": chat,
        "date": 1700000000,
        "rich_message": {"blocks": [{"type": "photo", "photo": [jpeg_size]}]},
    }
    edited_expected = {
        "message_id": 4,
        "from": bot_user,
        "chat": chat,
        "date": 1700000000,
        "edit_date": 1700000005,
        "rich_message": {
            "blocks": [
                {
                    "type": "photo",
                    "photo": [png_size],
                    "caption": scene["rich_edited_caption"],
                }
            ],
            "is_rtl": True,
        },
    }
    assert ordinary == ordinary_expected
    assert ordinary_reuse == ordinary_reuse_expected
    assert rich == rich_expected
    assert rich_reuse == rich_reuse_expected
    assert edited == edited_expected

    for name, source, size in (
        ("png_download", PNG, png_size),
        ("jpeg_download", JPEG, jpeg_size),
    ):
        download = published[name]
        assert download == {
            "get_file": {
                "file_id": size["file_id"],
                "file_unique_id": size["file_unique_id"],
                "file_size": source.stat().st_size,
                "file_path": download["get_file"]["file_path"],
            },
            "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "size": source.stat().st_size,
        }
        assert download["get_file"]["file_path"].startswith("photos/")
        assert ".." not in download["get_file"]["file_path"]
    for rejection in (published["malformed"], published["foreign"]):
        assert rejection["status"] == 400
        assert rejection["body"]["ok"] is False
        assert set(rejection["body"]) == {"ok", "error_code", "description"}

    world_request = {
        "id": 1,
        "chat_id": 1,
        "sender_id": 1,
        "date": 1700000000,
        "text": "Show local photos",
    }
    world_ordinary = {
        "id": 2,
        "chat_id": 1,
        "sender_id": 2,
        "date": 1700000000,
        "text": "",
        "photo": {"asset_id": 1},
        "caption": scene["ordinary_caption"],
        "caption_entities": scene["ordinary_entities"],
    }
    world_ordinary_reuse = {
        "id": 3,
        "chat_id": 1,
        "sender_id": 2,
        "date": 1700000000,
        "text": "",
        "photo": {"asset_id": 1},
    }
    world_rich_initial = {
        "id": 4,
        "chat_id": 1,
        "sender_id": 2,
        "date": 1700000000,
        "text": "",
        "rich_message": {
            "blocks": [
                {
                    "type": "photo",
                    "photo": {"asset_id": 2},
                    "caption": scene["rich_initial_caption"],
                }
            ]
        },
        "reply_markup": keyboard,
    }
    world_rich_edited = {
        "id": 4,
        "chat_id": 1,
        "sender_id": 2,
        "date": 1700000000,
        "edit_date": 1700000005,
        "text": "",
        "rich_message": {
            "blocks": [
                {
                    "type": "photo",
                    "photo": {"asset_id": 1},
                    "caption": scene["rich_edited_caption"],
                }
            ],
            "is_rtl": True,
        },
    }
    world_rich_reuse = {
        "id": 5,
        "chat_id": 1,
        "sender_id": 2,
        "date": 1700000000,
        "text": "",
        "rich_message": {"blocks": [{"type": "photo", "photo": {"asset_id": 2}}]},
    }
    assert observed["history"] == [
        world_request,
        world_ordinary,
        world_ordinary_reuse,
        world_rich_edited,
        world_rich_reuse,
    ]
    assert observed["pending"] == []

    assets = [
        {
            "asset_id": 1,
            "mime_type": "image/png",
            "file_size": PNG.stat().st_size,
            "sha256": hashlib.sha256(PNG.read_bytes()).hexdigest(),
            "width": 16,
            "height": 16,
        },
        {
            "asset_id": 2,
            "mime_type": "image/jpeg",
            "file_size": JPEG.stat().st_size,
            "sha256": hashlib.sha256(JPEG.read_bytes()).hexdigest(),
            "width": 64,
            "height": 48,
        },
    ]
    initial_snapshot = observed["v3"]["initial_snapshot"]
    edited_snapshot = observed["v3"]["edited_snapshot"]
    restarted_snapshot = observed["v3"]["restarted_snapshot"]
    assert initial_snapshot["schema"] == edited_snapshot["schema"] == 3
    assert initial_snapshot["world_id"] == edited_snapshot["world_id"] == world_id
    assert initial_snapshot["assets"] == edited_snapshot["assets"] == assets
    snapshot_base = {
        "schema": 3,
        "world_id": world_id,
        "user_id": 1,
        "users": [
            {"id": 1, "is_bot": False, "first_name": "Sara", "language_code": "fa"},
            bot_user,
            {
                "id": 3,
                "is_bot": True,
                "first_name": "Other",
                "username": "other_media_bot",
            },
        ],
        "chats": [
            {"id": 1, "type": "private", "user_id": 1, "bot_id": 2},
            {"id": 2, "type": "private", "user_id": 1, "bot_id": 3},
        ],
        "assets": assets,
    }
    assert initial_snapshot["messages"] == [
        world_request,
        world_ordinary,
        world_ordinary_reuse,
        world_rich_initial,
        world_rich_reuse,
    ]
    assert initial_snapshot["message_revisions"] == [
        {"chat_id": 1, "message_id": message_id, "revision": revision}
        for message_id, revision in ((1, 6), (2, 7), (3, 8), (4, 9), (5, 10))
    ]
    assert initial_snapshot == snapshot_base | {
        "cursor": 10,
        "now": 1700000000,
        "messages": initial_snapshot["messages"],
        "message_revisions": initial_snapshot["message_revisions"],
    }
    assert edited_snapshot["messages"] == observed["history"]
    assert edited_snapshot["message_revisions"] == [
        {"chat_id": 1, "message_id": message_id, "revision": revision}
        for message_id, revision in ((1, 6), (2, 7), (3, 8), (4, 14), (5, 10))
    ]
    assert edited_snapshot == snapshot_base | {
        "cursor": 14,
        "now": 1700000005,
        "messages": edited_snapshot["messages"],
        "message_revisions": edited_snapshot["message_revisions"],
    }
    assert restarted_snapshot == edited_snapshot
    assert observed["v3"]["restarted_changes"] == observed["v3"]["edited_changes"]
    assert observed["v3"]["assets_after_restart"] == observed["v3"]["assets_after_edit"]
    for asset in assets:
        transfer = observed["v3"]["assets_after_edit"][str(asset["asset_id"])]
        assert transfer == {
            "status": 200,
            "content_type": asset["mime_type"],
            "content_length": str(asset["file_size"]),
            "cache_control": "no-store",
            "connection": "close",
            "sha256": asset["sha256"],
            "size": asset["file_size"],
        }

    callback_created = observed["v3"]["callback_created"]
    callback_after = observed["v3"]["callback_after"]
    callback = callback_created["callback"]
    assert set(callback) == {
        "id",
        "user_id",
        "chat_id",
        "message",
        "data",
        "chat_instance",
        "answer",
    }
    assert callback["message"] == world_rich_initial
    assert callback["data"] == scene["callback_data"]
    assert callback_created == {
        "schema": 3,
        "world_id": world_id,
        "user_id": 1,
        "callback": callback,
        "users": callback_created["users"],
        "assets": [assets[1]],
        "message_revision": 9,
    }
    answered_callback = callback | {
        "answer": {"text": "دریافت شد / Received", "show_alert": False, "cache_time": 0}
    }
    assert callback_after == callback_created | {"callback": answered_callback}
    assert observed["v3"]["restarted_callback"] == callback_after

    initial_changes = observed["v3"]["initial_changes"]
    changes = observed["v3"]["edited_changes"]
    assert changes["schema"] == 3
    assert changes["assets"] == assets
    assert [(item["type"], item["revision"]) for item in changes["changes"]] == [
        ("message.created", 6),
        ("message.created", 7),
        ("message.created", 8),
        ("message.created", 9),
        ("message.created", 10),
        ("message.edited", 14),
    ]
    assert [item["data"] for item in changes["changes"]] == [
        world_request,
        world_ordinary,
        world_ordinary_reuse,
        world_rich_initial,
        world_rich_reuse,
        world_rich_edited,
    ]
    changes_base = {
        "schema": 3,
        "world_id": world_id,
        "user_id": 1,
        "users": snapshot_base["users"],
        "assets": assets,
    }
    assert initial_changes == changes_base | {
        "cursor": 5,
        "head": 5,
        "now": 1700000000,
        "changes": changes["changes"][:5],
    }
    assert changes == changes_base | {
        "cursor": 6,
        "head": 6,
        "now": 1700000005,
        "changes": changes["changes"],
    }

    message_events = [event for event in observed["events"] if event["type"].startswith("message.")]
    assert message_events == [
        {"sequence": revision, "type": kind, "data": message}
        for revision, kind, message in (
            (6, "message.created", world_request),
            (7, "message.created", world_ordinary),
            (8, "message.created", world_ordinary_reuse),
            (9, "message.created", world_rich_initial),
            (10, "message.created", world_rich_reuse),
            (14, "message.edited", world_rich_edited),
        )
    ]
    callback_created_event = {key: value for key, value in callback.items() if key != "answer"}
    assert observed["events"] == [
        {
            "sequence": 1,
            "type": "user.created",
            "data": snapshot_base["users"][0],
        },
        {"sequence": 2, "type": "user.created", "data": bot_user},
        {
            "sequence": 3,
            "type": "user.created",
            "data": snapshot_base["users"][2],
        },
        {
            "sequence": 4,
            "type": "chat.created",
            "data": snapshot_base["chats"][0],
        },
        {
            "sequence": 5,
            "type": "chat.created",
            "data": snapshot_base["chats"][1],
        },
        *message_events[:5],
        {"sequence": 11, "type": "clock.advanced", "data": {"now": 1700000005}},
        {"sequence": 12, "type": "callback.created", "data": callback_created_event},
        {
            "sequence": 13,
            "type": "callback.answered",
            "data": {
                "id": callback["id"],
                "user_id": 1,
                "answer": answered_callback["answer"],
            },
        },
        message_events[5],
    ]
    assert [entry["operation"] for entry in observed["api"]] == [
        "getUpdates:1",
        "sendPhoto:1",
        "sendPhoto:2",
        "sendRichMessage:1",
        "sendRichMessage:2",
        "sendPhoto:3",
        "sendPhoto:4",
        "getFile:1",
        "getFile:2",
        "getUpdates:2",
        "answerCallbackQuery:1",
        "editMessageText:1",
        "getUpdates:3",
    ]
    for entry in observed["api"]:
        assert set(entry) == {"operation", "method", "response"}
        assert entry["operation"].startswith(entry["method"] + ":")
    api_responses = [entry["response"] for entry in observed["api"]]
    assert api_responses[1] == {"status": 200, "body": {"ok": True, "result": ordinary}}
    assert api_responses[2] == {
        "status": 200,
        "body": {"ok": True, "result": ordinary_reuse},
    }
    assert api_responses[3] == {"status": 200, "body": {"ok": True, "result": rich}}
    assert api_responses[4] == {"status": 200, "body": {"ok": True, "result": rich_reuse}}
    assert api_responses[5:7] == [published["malformed"], published["foreign"]]
    assert api_responses[7]["body"] == {
        "ok": True,
        "result": published["png_download"]["get_file"],
    }
    assert api_responses[8]["body"] == {
        "ok": True,
        "result": published["jpeg_download"]["get_file"],
    }
    assert api_responses[10] == {"status": 200, "body": {"ok": True, "result": True}}
    assert api_responses[11] == {"status": 200, "body": {"ok": True, "result": edited}}
    assert api_responses[12] == {"status": 200, "body": {"ok": True, "result": []}}


def test_real_bot_uploads_reuses_downloads_edits_and_restarts_photos(tmp_path: Path) -> None:
    profile = RuntimeProfile.load(Path(os.environ["GRAMLAB_RUNTIME_PROFILE"]))
    stage_media_scenario(tmp_path, profile)
    result = Sandbox(profile).supervise(
        [profile.python, "/work/media_round_trip.py"], data=tmp_path, timeout=60
    )
    (tmp_path / "media-result.json").write_text(result.stdout)
    (tmp_path / "media-stderr.log").write_text(result.stderr)
    assert result.returncode == 0, result.stderr
    assert_media_scenario(json.loads(result.stdout))
