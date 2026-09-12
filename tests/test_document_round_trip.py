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
PHOTO = Path("tests/assets/rich-media/photo-square-16x16.png")
DOCUMENT_BYTES = (
    b"%PDF-1.4\n% GramLab forced ordinary document\n"
    b"Persian-English filename; exact local bytes.\x00\xff\n%%EOF\n"
)
REPLACEMENT_DOCUMENT_BYTES = (
    b"%PDF-1.4\n% GramLab replacement ordinary document\nDistinct D2 exact bytes.\x01\xfe\n%%EOF\n"
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
    "replacement_file_name": "ویرایش-English-2.pdf",
    "replacement_upload_name": "%D9%88%DB%8C%D8%B1%D8%A7%DB%8C%D8%B4-English-2.pdf",
    "edit_sequence": [
        {
            "operation": "editMessageCaption",
            "trigger_data": "document:reuse",
            "caption": "D1 caption edited / زیرنویس سند",
            "caption_entities": [{"type": "bold", "offset": 0, "length": 2}],
            "button_text": "Replace with photo / عکس",
            "callback_data": "document:photo",
            "answer_text": "Caption edited",
        },
        {
            "operation": "editMessageMedia",
            "trigger_data": "document:photo",
            "caption": "P1 initial / عکس نخست",
            "caption_entities": [{"type": "italic", "offset": 0, "length": 2}],
            "button_text": "Edit photo caption / زیرنویس",
            "callback_data": "photo:caption",
            "answer_text": "Photo replaced",
        },
        {
            "operation": "editMessageCaption",
            "trigger_data": "photo:caption",
            "caption": "P1 caption edited / عکس ویرایش شد",
            "caption_entities": [{"type": "bold", "offset": 0, "length": 2}],
            "button_text": "Replace with D2 / سند دوم",
            "callback_data": "photo:document",
            "answer_text": "Photo caption edited",
        },
        {
            "operation": "editMessageMedia",
            "trigger_data": "photo:document",
            "caption": "D2 final / سند نهایی",
            "caption_entities": [{"type": "italic", "offset": 0, "length": 2}],
            "button_text": "Complete / تمام",
            "callback_data": "document:complete",
            "answer_text": "Document replaced",
        },
    ],
}
for _step in SCENE["edit_sequence"]:
    _step["reply_markup"] = {
        "inline_keyboard": [
            [{"text": _step["button_text"], "callback_data": _step["callback_data"]}]
        ]
    }


def stage_document_scenario(directory: Path, core: RuntimeProfile) -> None:
    shutil.copytree(
        "src/gramlab", directory / "gramlab", ignore=shutil.ignore_patterns("__pycache__")
    )
    (directory / "component-profile.json").write_text(json.dumps(asdict(core)))
    for name in ("component_bot.py", "document_round_trip.py"):
        shutil.copy2(Path("tests/probes") / name, directory / name)
    shutil.copy2(Path("tests/fixtures/document_bot.py"), directory / "document_bot.py")
    shutil.copy2(PHOTO, directory / "replacement-photo.png")
    target = directory / "custom-emoji"
    target.mkdir()
    for name in ("emoji-static.webp", "emoji-thumbnail.webp"):
        shutil.copy2(EMOJI / name, target / name)


def assert_document_scenario(observed: dict[str, Any]) -> None:
    """Specify the complete D1 caption → P1 → caption → D2 transaction."""
    records = observed["bot"]
    assert list(records) == [
        "published",
        "document_caption",
        "photo",
        "photo_caption",
        "document_final",
    ]
    user = {"id": 1, "is_bot": False, "first_name": "Sara", "language_code": "fa"}
    bot = {"id": 2, "is_bot": True, "first_name": "Files", "username": "gramlab_files_bot"}
    chat = {"id": 1, "type": "private", "first_name": "Sara"}
    d1 = records["published"]["sent"]["document"]
    p1 = records["photo"]["edited"]["photo"][0]
    d2 = records["document_final"]["edited"]["document"]
    digests = [
        hashlib.sha256(DOCUMENT_BYTES).hexdigest(),
        hashlib.sha256(PHOTO.read_bytes()).hexdigest(),
        hashlib.sha256(REPLACEMENT_DOCUMENT_BYTES).hexdigest(),
    ]
    assert d1["file_size"] == len(DOCUMENT_BYTES)
    assert d1["file_name"] == SCENE["file_name"] and d1["mime_type"] == "application/pdf"
    assert p1 == {
        "file_id": p1["file_id"],
        "file_unique_id": digests[1],
        "width": 16,
        "height": 16,
        "file_size": PHOTO.stat().st_size,
    }
    assert d2["file_size"] == len(REPLACEMENT_DOCUMENT_BYTES)
    assert (
        d2["file_name"] == SCENE["replacement_file_name"] and d2["mime_type"] == "application/pdf"
    )
    for file, digest, name in (
        (d1, digests[0], SCENE["file_name"]),
        (d2, digests[2], SCENE["replacement_file_name"]),
    ):
        identity = json.dumps(
            ["document", digest, name, "application/pdf"],
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode()
        assert (
            file["file_unique_id"]
            == "gramlab_document_unique_" + hashlib.sha256(identity).hexdigest()
        )

    initial_keyboard = {
        "inline_keyboard": [
            [{"text": SCENE["button_text"], "callback_data": SCENE["callback_data"]}]
        ]
    }
    api_base = {"from": bot, "chat": chat, "date": 1_700_000_000}
    api_states = [
        {
            "message_id": 2,
            **api_base,
            "document": d1,
            "caption": SCENE["caption"],
            "caption_entities": SCENE["caption_entities"],
            "reply_markup": initial_keyboard,
        }
    ]
    for index, medium in enumerate((d1, p1, p1, d2)):
        step = SCENE["edit_sequence"][index]
        api_states.append(
            {
                "message_id": 2,
                **api_base,
                "document" if index in (0, 3) else "photo": medium if index in (0, 3) else [medium],
                "caption": step["caption"],
                "caption_entities": step["caption_entities"],
                "reply_markup": step["reply_markup"],
                "edit_date": 1_700_000_005 + index * 5,
            }
        )
    assert records["published"]["sent"] == api_states[0]
    reused = {
        "message_id": 3,
        "from": bot,
        "chat": chat,
        "date": 1_700_000_005,
        "document": d1,
        "caption": SCENE["reuse_caption"],
    }
    assert records["document_caption"]["reused"] == reused

    def expected_download(
        file: dict[str, Any], payload: bytes, directory: str, content_type: str
    ) -> dict[str, Any]:
        suffix = ".png" if directory == "photos" else ""
        return {
            "get_file": {
                "file_id": file["file_id"],
                "file_unique_id": file["file_unique_id"],
                "file_size": len(payload),
                "file_path": f"{directory}/{file['file_id']}{suffix}",
            },
            "status": 200,
            "content_type": content_type,
            "content_length": str(len(payload)),
            "cache_control": "no-store",
            "sha256": hashlib.sha256(payload).hexdigest(),
            "size": len(payload),
        }

    assert records["published"]["download"] == expected_download(
        d1, DOCUMENT_BYTES, "documents", "application/pdf"
    )
    assert records["photo"]["download"] == expected_download(
        p1, PHOTO.read_bytes(), "photos", "image/png"
    )
    assert records["document_final"]["download"] == expected_download(
        d2, REPLACEMENT_DOCUMENT_BYTES, "documents", "application/pdf"
    )

    names = ("document_caption", "photo", "photo_caption", "document_final")
    chat_instance = hashlib.sha256(f"{observed['world_id']}:1".encode()).hexdigest()
    callback_ids = []
    for index, name in enumerate(names):
        record = records[name]
        query = record["update"]["callback_query"]
        callback_ids.append(query["id"])
        assert str(uuid.UUID(query["id"])) == query["id"]
        assert record == (
            {
                "event": name,
                "update": {
                    "update_id": index + 2,
                    "callback_query": {
                        "id": query["id"],
                        "from": user,
                        "message": api_states[index],
                        "chat_instance": chat_instance,
                        "data": SCENE["edit_sequence"][index]["trigger_data"],
                    },
                },
                "answer": True,
                "edited": api_states[index + 1],
            }
            | ({"reused": reused} if index == 0 else {})
            | ({"download": record["download"]} if index in (1, 3) else {})
        )

    world_request = {
        "id": 1,
        "chat_id": 1,
        "sender_id": 1,
        "date": 1_700_000_000,
        "text": SCENE["request_text"],
    }
    world_states = []
    for index, api in enumerate(api_states):
        value = {"id": 2, "chat_id": 1, "sender_id": 2, "date": 1_700_000_000, "text": ""}
        if index:
            value["edit_date"] = api["edit_date"]
        value["document" if "document" in api else "photo"] = (
            {"document_id": "1" if index < 2 else "2"} if "document" in api else {"asset_id": 3}
        )
        value.update({key: api[key] for key in ("caption", "caption_entities", "reply_markup")})
        world_states.append(value)
    world_reused = {
        "id": 3,
        "chat_id": 1,
        "sender_id": 2,
        "date": 1_700_000_005,
        "text": "",
        "document": {"document_id": "1"},
        "caption": SCENE["reuse_caption"],
    }
    assert observed["history"] == [world_request, world_states[-1], world_reused]
    assert observed["pending"] == []
    other = {"id": 3, "is_bot": True, "first_name": "Other", "username": "other_files_bot"}
    world_chats = [
        {"id": 1, "type": "private", "user_id": 1, "bot_id": 2},
        {"id": 2, "type": "private", "user_id": 1, "bot_id": 3},
    ]
    expected_events = [
        {"sequence": 1, "type": "user.created", "data": user},
        {"sequence": 2, "type": "user.created", "data": bot},
        {"sequence": 3, "type": "user.created", "data": other},
        {"sequence": 4, "type": "chat.created", "data": world_chats[0]},
        {"sequence": 5, "type": "chat.created", "data": world_chats[1]},
        {"sequence": 6, "type": "message.created", "data": world_request},
        {"sequence": 7, "type": "message.created", "data": world_states[0]},
    ]
    sequence = 8
    for index, step in enumerate(SCENE["edit_sequence"]):
        now = 1_700_000_005 + index * 5
        expected_events.extend(
            [
                {"sequence": sequence, "type": "clock.advanced", "data": {"now": now}},
                {
                    "sequence": sequence + 1,
                    "type": "callback.created",
                    "data": {
                        "id": callback_ids[index],
                        "user_id": 1,
                        "chat_id": 1,
                        "message": world_states[index],
                        "data": step["trigger_data"],
                        "chat_instance": chat_instance,
                    },
                },
                {
                    "sequence": sequence + 2,
                    "type": "callback.answered",
                    "data": {
                        "id": callback_ids[index],
                        "user_id": 1,
                        "answer": {
                            "text": step["answer_text"],
                            "show_alert": False,
                            "cache_time": 0,
                        },
                    },
                },
            ]
        )
        sequence += 3
        if index == 0:
            expected_events.append(
                {"sequence": sequence, "type": "message.created", "data": world_reused}
            )
            sequence += 1
        expected_events.append(
            {"sequence": sequence, "type": "message.edited", "data": world_states[index + 1]}
        )
        sequence += 1
    assert observed["events"] == expected_events

    expected_operations = [
        "getUpdates:1",
        "sendDocument:1",
        "getFile:1",
        "getFile:2",
        "sendPhoto:1",
        "sendDocument:2",
        "getUpdates:2",
        "answerCallbackQuery:1",
        "sendDocument:3",
        "editMessageCaption:1",
        "getUpdates:3",
        "answerCallbackQuery:2",
        "editMessageMedia:1",
        "getFile:3",
        "getFile:4",
        "getUpdates:4",
        "answerCallbackQuery:3",
        "editMessageCaption:2",
        "getUpdates:5",
        "answerCallbackQuery:4",
        "editMessageMedia:2",
        "getFile:5",
        "getFile:6",
        "getUpdates:6",
    ]
    assert [row["operation"] for row in observed["api"]] == expected_operations
    assert all(set(row) == {"operation", "method", "response"} for row in observed["api"])
    assert records["published"]["cross_kind"] == {
        "status": 400,
        "body": {
            "ok": False,
            "error_code": 400,
            "description": "Photo file identifier is unavailable",
        },
    }
    assert records["published"]["foreign"] == {
        "status": 400,
        "body": {
            "ok": False,
            "error_code": 400,
            "description": "Document file identifier is unavailable",
        },
    }
    for row in observed["api"]:
        assert row["operation"].startswith(row["method"] + ":")
        assert row["response"]["body"]["ok"] is (row["response"]["status"] == 200)

    def ok(result: Any) -> dict[str, Any]:
        return {"status": 200, "body": {"ok": True, "result": result}}

    expected_responses = [
        ok(
            [
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
            ]
        ),
        ok(api_states[0]),
        ok(records["published"]["download"]["get_file"]),
        ok(records["published"]["download"]["get_file"]),
        records["published"]["cross_kind"],
        records["published"]["foreign"],
        ok([records["document_caption"]["update"]]),
        ok(True),
        ok(reused),
        ok(api_states[1]),
        ok([records["photo"]["update"]]),
        ok(True),
        ok(api_states[2]),
        ok(records["photo"]["download"]["get_file"]),
        ok(records["photo"]["download"]["get_file"]),
        ok([records["photo_caption"]["update"]]),
        ok(True),
        ok(api_states[3]),
        ok([records["document_final"]["update"]]),
        ok(True),
        ok(api_states[4]),
        ok(records["document_final"]["download"]["get_file"]),
        ok(records["document_final"]["download"]["get_file"]),
        ok([]),
    ]
    assert [row["response"] for row in observed["api"]] == expected_responses

    assert observed["v5"]["restarted_snapshot"] == observed["v5"]["document_final_snapshot"]
    assert observed["v5"]["restarted_changes"] == observed["v5"]["document_final_changes"]
    assert observed["v5"]["restarted_callback"] == observed["v5"]["document_final_callback"]
    assert [observed["v5"][name + "_snapshot"]["cursor"] for name in ("initial", *names)] == [
        7,
        12,
        16,
        20,
        24,
    ]
    assert [observed["v5"][name + "_changes"]["head"] for name in ("initial", *names)] == [
        2,
        4,
        5,
        6,
        7,
    ]
    assert [row["data"] for row in observed["v5"]["document_final_changes"]["changes"]] == [
        world_request,
        world_states[0],
        world_reused,
        *world_states[1:],
    ]
    assert observed["v5"]["document_final_snapshot"]["messages"] == [
        world_request,
        world_states[-1],
        world_reused,
    ]
    descriptors = [
        {
            "document_id": "1",
            "file_name": SCENE["file_name"],
            "mime_type": "application/pdf",
            "file_size": len(DOCUMENT_BYTES),
            "sha256": digests[0],
        },
        {
            "document_id": "2",
            "file_name": SCENE["replacement_file_name"],
            "mime_type": "application/pdf",
            "file_size": len(REPLACEMENT_DOCUMENT_BYTES),
            "sha256": digests[2],
        },
    ]
    assert observed["grants"] == {
        "documents": [
            {
                "descriptor": descriptors[0],
                "file": d1,
                "size": len(DOCUMENT_BYTES),
                "sha256": digests[0],
            },
            {
                "descriptor": descriptors[1],
                "file": d2,
                "size": len(REPLACEMENT_DOCUMENT_BYTES),
                "sha256": digests[2],
            },
        ],
        "photo": {
            "asset": {
                "asset_id": 3,
                "mime_type": "image/png",
                "file_size": PHOTO.stat().st_size,
                "sha256": digests[1],
                "width": 16,
                "height": 16,
            },
            "file": p1,
            "size": PHOTO.stat().st_size,
            "sha256": digests[1],
        },
    }

    users = [user, bot, other]
    chats = world_chats
    emoji_assets = [
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
    photo_asset = observed["grants"]["photo"]["asset"]
    emoji = [
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
    stage_names = ("initial", *names)
    cursors = (7, 12, 16, 20, 24)
    heads = (2, 4, 5, 6, 7)
    revisions = (7, 12, 16, 20, 24)
    changes = [
        {"position": 1, "type": "message.created", "data": world_request, "revision": 6},
        {"position": 2, "type": "message.created", "data": world_states[0], "revision": 7},
        {"position": 3, "type": "message.created", "data": world_reused, "revision": 11},
        *[
            {
                "position": position,
                "type": "message.edited",
                "data": world_states[index],
                "revision": revisions[index],
            }
            for position, index in zip(range(4, 8), range(1, 5), strict=True)
        ],
    ]
    for index, stage in enumerate(stage_names):
        assets = emoji_assets + ([photo_asset] if index >= 2 else [])
        documents = descriptors[: 2 if index == 4 else 1]
        messages = [world_request, world_states[index]] + ([] if index == 0 else [world_reused])
        message_revisions = [
            {"chat_id": 1, "message_id": 1, "revision": 6},
            {"chat_id": 1, "message_id": 2, "revision": revisions[index]},
        ] + ([] if index == 0 else [{"chat_id": 1, "message_id": 3, "revision": 11}])
        common = {
            "schema": 5,
            "world_id": observed["world_id"],
            "user_id": 1,
            "now": 1_700_000_000 + index * 5,
            "users": users,
            "assets": assets,
            "custom_emoji": emoji,
            "documents": documents,
        }
        assert observed["v5"][stage + "_snapshot"] == common | {
            "cursor": cursors[index],
            "chats": chats,
            "messages": messages,
            "message_position": heads[index],
            "message_revisions": message_revisions,
            "sends": [],
        }
        assert observed["v5"][stage + "_changes"] == common | {
            "cursor": heads[index],
            "head": heads[index],
            "changes": changes[: heads[index]],
        }

    dependency_assets: tuple[list[dict[str, Any]], ...] = (
        emoji_assets,
        [],
        [photo_asset],
        [photo_asset],
    )
    dependency_documents: tuple[list[dict[str, Any]], ...] = (
        [descriptors[0]],
        [descriptors[0]],
        [],
        [],
    )
    dependency_emoji: tuple[list[dict[str, Any]], ...] = (emoji, [], [], [])
    for index, name in enumerate(names):
        step = SCENE["edit_sequence"][index]
        assert observed["v5"][name + "_callback"] == {
            "schema": 5,
            "world_id": observed["world_id"],
            "user_id": 1,
            "callback": {
                "id": callback_ids[index],
                "user_id": 1,
                "chat_id": 1,
                "message": world_states[index],
                "data": step["trigger_data"],
                "chat_instance": chat_instance,
                "answer": {"text": step["answer_text"], "show_alert": False, "cache_time": 0},
            },
            "users": users,
            "assets": dependency_assets[index],
            "message_revision": revisions[index],
            "custom_emoji": dependency_emoji[index],
            "documents": dependency_documents[index],
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


def test_document_scene_specifies_complete_standalone_media_edit_sequence() -> None:
    assert [step["operation"] for step in SCENE["edit_sequence"]] == [
        "editMessageCaption",
        "editMessageMedia",
        "editMessageCaption",
        "editMessageMedia",
    ]
