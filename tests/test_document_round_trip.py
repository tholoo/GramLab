"""A contained real bot specifies the forced ordinary-document lifecycle."""

import hashlib
import json
import os
import shutil
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Any

from gramlab.runtime import RuntimeProfile, Sandbox

EMOJI = Path("tests/assets/custom-emoji")
DOCUMENT_BYTES = (
    b"%PDF-1.4\n% GramLab forced ordinary document\n"
    b"Persian-English filename; exact local bytes.\x00\xff\n%%EOF\n"
)
SCENE: dict[str, Any] = {
    "request_text": "Send the forced document / فایل را بفرست",
    "file_name": "گزارش-English.pdf",
    "upload_name": "%DA%AF%D8%B2%D8%A7%D8%B1%D8%B4-English.pdf",
    "caption": "فایل Report 👩‍💻",
    "caption_entities": [
        {"type": "bold", "offset": 5, "length": 6},
        {"type": "custom_emoji", "offset": 12, "length": 5, "custom_emoji_id": "1109"},
    ],
    "button_text": "Reuse / استفاده دوباره",
    "callback_data": "document:reuse",
    "answer_text": "دریافت شد / Received",
    "reuse_caption": "Same file / همان فایل",
}


def stage_document_scenario(directory: Path, core: RuntimeProfile) -> None:
    shutil.copytree(
        "src/gramlab", directory / "gramlab", ignore=shutil.ignore_patterns("__pycache__")
    )
    (directory / "component-profile.json").write_text(json.dumps(asdict(core)))
    for name in ("component_bot.py", "document_round_trip.py"):
        shutil.copy2(Path("tests/probes") / name, directory / name)
    shutil.copy2(Path("tests/fixtures/document_bot.py"), directory / "document_bot.py")
    target = directory / "custom-emoji"
    target.mkdir()
    for name in ("emoji-static.webp", "emoji-thumbnail.webp"):
        shutil.copy2(EMOJI / name, target / name)


def assert_document_scenario(observed: dict[str, Any]) -> None:
    published = observed["bot"]["published"]
    sent = published["sent"]
    reused = observed["bot"]["callback"]["reused"]
    document = sent["document"]
    digest = hashlib.sha256(DOCUMENT_BYTES).hexdigest()
    identity = json.dumps(
        ["document", digest, SCENE["file_name"], "application/pdf"],
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode()
    assert document == {
        "file_id": document["file_id"],
        "file_unique_id": "gramlab_document_unique_" + hashlib.sha256(identity).hexdigest(),
        "file_size": len(DOCUMENT_BYTES),
        "file_name": SCENE["file_name"],
        "mime_type": "application/pdf",
    }
    bot = {
        "id": 2,
        "is_bot": True,
        "first_name": "Files",
        "username": "gramlab_files_bot",
    }
    chat = {"id": 1, "type": "private", "first_name": "Sara"}
    keyboard = {
        "inline_keyboard": [
            [{"text": SCENE["button_text"], "callback_data": SCENE["callback_data"]}]
        ]
    }
    assert sent == {
        "message_id": 2,
        "from": bot,
        "chat": chat,
        "date": 1_700_000_000,
        "document": document,
        "caption": SCENE["caption"],
        "caption_entities": SCENE["caption_entities"],
        "reply_markup": keyboard,
    }
    assert reused == {
        "message_id": 3,
        "from": bot,
        "chat": chat,
        "date": 1_700_000_005,
        "document": document,
        "caption": SCENE["reuse_caption"],
    }
    download = published["download"]
    assert download == {
        "get_file": {
            "file_id": document["file_id"],
            "file_unique_id": document["file_unique_id"],
            "file_size": len(DOCUMENT_BYTES),
            "file_path": f"documents/{document['file_id']}",
        },
        "status": 200,
        "content_type": "application/pdf",
        "content_length": str(len(DOCUMENT_BYTES)),
        "cache_control": "no-store",
        "sha256": digest,
        "size": len(DOCUMENT_BYTES),
    }
    assert published["cross_kind"] == {
        "status": 400,
        "body": {
            "ok": False,
            "error_code": 400,
            "description": "Photo file identifier is unavailable",
        },
    }
    assert published["foreign"] == {
        "status": 400,
        "body": {
            "ok": False,
            "error_code": 400,
            "description": "Document file identifier is unavailable",
        },
    }
    descriptor = {
        "document_id": "1",
        "file_name": SCENE["file_name"],
        "mime_type": "application/pdf",
        "file_size": len(DOCUMENT_BYTES),
        "sha256": digest,
    }
    assert observed["grant"] == {
        "descriptor": descriptor,
        "file": document,
        "size": len(DOCUMENT_BYTES),
        "sha256": digest,
    }
    assert observed["pending"] == []
    world_request = {
        "id": 1,
        "chat_id": 1,
        "sender_id": 1,
        "date": 1_700_000_000,
        "text": SCENE["request_text"],
    }
    world_sent = {
        "id": 2,
        "chat_id": 1,
        "sender_id": 2,
        "date": 1_700_000_000,
        "text": "",
        "reply_markup": keyboard,
        "document": {"document_id": "1"},
        "caption": SCENE["caption"],
        "caption_entities": SCENE["caption_entities"],
    }
    world_reused = {
        "id": 3,
        "chat_id": 1,
        "sender_id": 2,
        "date": 1_700_000_005,
        "text": "",
        "document": {"document_id": "1"},
        "caption": SCENE["reuse_caption"],
    }
    assert observed["history"] == [world_request, world_sent, world_reused]

    user = {"id": 1, "is_bot": False, "first_name": "Sara", "language_code": "fa"}
    other = {
        "id": 3,
        "is_bot": True,
        "first_name": "Other",
        "username": "other_files_bot",
    }
    users = [user, bot, other]
    chats = [
        {"id": 1, "type": "private", "user_id": 1, "bot_id": 2},
        {"id": 2, "type": "private", "user_id": 1, "bot_id": 3},
    ]
    assets = [
        {
            "asset_id": asset_id,
            "mime_type": "image/webp",
            "file_size": source.stat().st_size,
            "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "width": size,
            "height": size,
        }
        for asset_id, source, size in (
            (1, EMOJI / "emoji-static.webp", 100),
            (2, EMOJI / "emoji-thumbnail.webp", 16),
        )
    ]
    custom_emoji = [
        {
            "custom_emoji_id": "1109",
            "fallback": "👩‍💻",
            "free": True,
            "needs_repainting": False,
            "main_asset_id": 1,
            "thumbnail_asset_id": 2,
            "duration_ms": 0,
        }
    ]
    world_id = observed["world_id"]
    assert str(uuid.UUID(world_id)) == world_id
    snapshot_base = {
        "schema": 5,
        "world_id": world_id,
        "user_id": 1,
        "users": users,
        "chats": chats,
        "sends": [],
        "assets": assets,
        "custom_emoji": custom_emoji,
        "documents": [descriptor],
    }
    initial_snapshot = observed["v5"]["initial_snapshot"]
    reused_snapshot = observed["v5"]["reused_snapshot"]
    assert initial_snapshot == snapshot_base | {
        "cursor": 7,
        "now": 1_700_000_000,
        "messages": [world_request, world_sent],
        "message_position": 2,
        "message_revisions": [
            {"chat_id": 1, "message_id": 1, "revision": 6},
            {"chat_id": 1, "message_id": 2, "revision": 7},
        ],
    }
    assert reused_snapshot == snapshot_base | {
        "cursor": 11,
        "now": 1_700_000_005,
        "messages": [world_request, world_sent, world_reused],
        "message_position": 3,
        "message_revisions": [
            {"chat_id": 1, "message_id": 1, "revision": 6},
            {"chat_id": 1, "message_id": 2, "revision": 7},
            {"chat_id": 1, "message_id": 3, "revision": 11},
        ],
    }
    assert observed["v5"]["restarted_snapshot"] == observed["v5"]["reused_snapshot"]
    assert observed["v5"]["restarted_changes"] == observed["v5"]["reused_changes"]
    assert observed["v5"]["restarted_callback"] == observed["v5"]["callback_after"]

    expected_changes = [
        {"position": position, "type": "message.created", "data": message, "revision": revision}
        for position, message, revision in (
            (1, world_request, 6),
            (2, world_sent, 7),
            (3, world_reused, 11),
        )
    ]
    changes_base = {
        "schema": 5,
        "world_id": world_id,
        "user_id": 1,
        "users": users,
        "assets": assets,
        "custom_emoji": custom_emoji,
        "documents": [descriptor],
    }
    assert observed["v5"]["initial_changes"] == changes_base | {
        "cursor": 2,
        "head": 2,
        "now": 1_700_000_000,
        "changes": expected_changes[:2],
    }
    assert observed["v5"]["reused_changes"] == changes_base | {
        "cursor": 3,
        "head": 3,
        "now": 1_700_000_005,
        "changes": expected_changes,
    }

    callback_update = observed["bot"]["callback"]["update"]
    callback = callback_update["callback_query"]
    callback_id = callback["id"]
    assert str(uuid.UUID(callback_id)) == callback_id
    chat_instance = hashlib.sha256(f"{world_id}:1".encode()).hexdigest()
    api_sent = sent
    expected_callback_update = {
        "update_id": 2,
        "callback_query": {
            "id": callback_id,
            "from": user,
            "message": api_sent,
            "chat_instance": chat_instance,
            "data": SCENE["callback_data"],
        },
    }
    assert callback_update == expected_callback_update
    assert observed["bot"]["callback"]["answer"] is True
    callback_after = observed["v5"]["callback_after"]
    expected_answer = {
        "text": SCENE["answer_text"],
        "show_alert": False,
        "cache_time": 0,
    }
    assert callback_after == {
        "schema": 5,
        "world_id": world_id,
        "user_id": 1,
        "callback": {
            "id": callback_id,
            "user_id": 1,
            "chat_id": 1,
            "message": world_sent,
            "data": SCENE["callback_data"],
            "chat_instance": chat_instance,
            "answer": expected_answer,
        },
        "users": users,
        "assets": assets,
        "message_revision": 7,
        "custom_emoji": custom_emoji,
        "documents": [descriptor],
    }

    expected_events = [
        {"sequence": 1, "type": "user.created", "data": user},
        {"sequence": 2, "type": "user.created", "data": bot},
        {"sequence": 3, "type": "user.created", "data": other},
        {"sequence": 4, "type": "chat.created", "data": chats[0]},
        {"sequence": 5, "type": "chat.created", "data": chats[1]},
        {"sequence": 6, "type": "message.created", "data": world_request},
        {"sequence": 7, "type": "message.created", "data": world_sent},
        {"sequence": 8, "type": "clock.advanced", "data": {"now": 1_700_000_005}},
        {
            "sequence": 9,
            "type": "callback.created",
            "data": {
                "id": callback_id,
                "user_id": 1,
                "chat_id": 1,
                "message": world_sent,
                "data": SCENE["callback_data"],
                "chat_instance": chat_instance,
            },
        },
        {
            "sequence": 10,
            "type": "callback.answered",
            "data": {"id": callback_id, "user_id": 1, "answer": expected_answer},
        },
        {"sequence": 11, "type": "message.created", "data": world_reused},
    ]
    assert observed["events"] == expected_events

    assert [row["operation"] for row in observed["api"]] == [
        "getUpdates:1",
        "sendDocument:1",
        "getFile:1",
        "getFile:2",
        "sendPhoto:1",
        "sendDocument:2",
        "getUpdates:2",
        "answerCallbackQuery:1",
        "sendDocument:3",
        "getUpdates:3",
    ]
    for row in observed["api"]:
        assert set(row) == {"operation", "method", "response"}
        assert row["operation"].startswith(row["method"] + ":")
    responses = [row["response"] for row in observed["api"]]
    assert responses == [
        {
            "status": 200,
            "body": {
                "ok": True,
                "result": [
                    {
                        "update_id": 1,
                        "message": {
                            "message_id": 1,
                            "from": user,
                            "chat": chat,
                            "date": 1_700_000_000,
                            "text": SCENE["request_text"],
                        },
                    }
                ],
            },
        },
        {"status": 200, "body": {"ok": True, "result": sent}},
        {"status": 200, "body": {"ok": True, "result": download["get_file"]}},
        {"status": 200, "body": {"ok": True, "result": download["get_file"]}},
        published["cross_kind"],
        published["foreign"],
        {"status": 200, "body": {"ok": True, "result": [expected_callback_update]}},
        {"status": 200, "body": {"ok": True, "result": True}},
        {"status": 200, "body": {"ok": True, "result": reused}},
        {"status": 200, "body": {"ok": True, "result": []}},
    ]
    for name in ("initial_download", "reused_download", "restarted_download"):
        assert observed["v5"][name] == {
            "status": 200,
            "content_type": "application/pdf",
            "content_length": str(len(DOCUMENT_BYTES)),
            "cache_control": "no-store",
            "connection": "close",
            "size": len(DOCUMENT_BYTES),
            "sha256": digest,
        }


def test_real_bot_uploads_downloads_reuses_and_restarts_document(tmp_path: Path) -> None:
    profile = RuntimeProfile.load(Path(os.environ["GRAMLAB_RUNTIME_PROFILE"]))
    stage_document_scenario(tmp_path, profile)
    result = Sandbox(profile).supervise(
        [profile.python, "/work/document_round_trip.py"], data=tmp_path, timeout=60
    )
    (tmp_path / "document-result.json").write_text(result.stdout)
    (tmp_path / "document-stderr.log").write_text(result.stderr)
    assert result.returncode == 0, result.stderr
    assert_document_scenario(json.loads(result.stdout))
