"""World acceptance for standalone ordinary media edits."""

import hashlib
import io
import json
import sqlite3
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from PIL import Image

from gramlab.documents import DocumentUpload
from gramlab.world import World


def png(colour: tuple[int, int, int] = (20, 40, 60)) -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (3, 2), colour).save(output, "PNG")
    return output.getvalue()


def setup(path: Path) -> tuple[World, dict[str, Any], dict[str, Any], dict[str, Any]]:
    world = World.create(path, seed=106, now=100)
    user = world.create_user(first_name="Ada")
    bot = world.create_user(first_name="Media", is_bot=True)
    other = world.create_user(first_name="Other", is_bot=True)
    chat = world.open_private_chat(user_id=user["id"], bot_id=bot["id"])
    world.open_private_chat(user_id=user["id"], bot_id=other["id"])
    return world, user, bot, chat


def logical_database(world: World) -> list[str]:
    return list(world._connection.iterdump())


def test_caption_and_cross_kind_edits_preserve_history_grants_callback_and_reopen(
    tmp_path: Path,
) -> None:
    directory = tmp_path / "world"
    world, user, bot, chat = setup(directory)
    keyboard = {"inline_keyboard": [[{"text": "Tap", "callback_data": "old"}]]}
    first_bytes = png()
    original = world.send_photo(
        chat_id=chat["id"],
        sender_id=bot["id"],
        photo={"type": "photo", "media": "attach://old"},
        uploads={"old": first_bytes},
        caption="old",
        reply_markup=keyboard,
    )
    original_file = world.photo_size(bot["id"], 1)["file_id"]
    callback = world.create_callback(
        user_id=user["id"],
        chat_id=chat["id"],
        message_id=original["id"],
        data="old",
        request_id="before-edit",
        version=5,
    )
    original_dependencies = world.callback_dependencies(user["id"], callback, version=5)
    world.advance_time(5)
    captioned = world.edit_caption(
        chat_id=chat["id"],
        message_id=original["id"],
        bot_id=bot["id"],
        caption="فایل Report",
        caption_entities=[{"type": "bold", "offset": 5, "length": 6}],
    )
    assert captioned == {
        "id": 1,
        "chat_id": 1,
        "sender_id": bot["id"],
        "date": 100,
        "text": "",
        "photo": {"asset_id": 1},
        "caption": "فایل Report",
        "caption_entities": [{"type": "bold", "offset": 5, "length": 6}],
        "edit_date": 105,
    }
    document_bytes = b"replacement document"
    document = world.edit_media(
        chat_id=1,
        message_id=1,
        bot_id=bot["id"],
        media={"type": "document", "media": "attach://new"},
        uploads={"new": DocumentUpload(document_bytes, "گزارش.pdf")},
        caption="document",
        reply_markup=keyboard,
    )
    assert document["document"] == {"document_id": "1"}
    assert "photo" not in document and document["caption"] == "document"
    assert world.granted_asset(user["id"], 1)[1] == first_bytes
    assert world.granted_document(user["id"], "1")[1] == document_bytes
    restored = world.edit_media(
        chat_id=1,
        message_id=1,
        bot_id=bot["id"],
        media={"type": "photo", "media": original_file},
    )
    assert restored["photo"] == {"asset_id": 1}
    assert not ({"document", "caption", "caption_entities", "reply_markup"} & restored.keys())
    assert world.callback_dependencies(user["id"], callback, version=5) == original_dependencies
    assert world.events()[-3:] == [
        {"sequence": 9, "type": "message.edited", "data": captioned},
        {"sequence": 10, "type": "message.edited", "data": document},
        {"sequence": 11, "type": "message.edited", "data": restored},
    ]
    asset = {
        "asset_id": 1,
        "mime_type": "image/png",
        "file_size": len(first_bytes),
        "sha256": hashlib.sha256(first_bytes).hexdigest(),
        "width": 3,
        "height": 2,
    }
    descriptor = {
        "document_id": "1",
        "file_name": "گزارش.pdf",
        "mime_type": "application/pdf",
        "file_size": len(document_bytes),
        "sha256": hashlib.sha256(document_bytes).hexdigest(),
    }
    other = {"id": 3, "first_name": "Other", "is_bot": True}
    users = [user, bot, other]
    assert world.client_changes(user["id"], after=0, version=5) == {
        "schema": 5,
        "world_id": world.world_id,
        "user_id": user["id"],
        "cursor": 4,
        "head": 4,
        "now": 105,
        "changes": [
            {"position": 1, "type": "message.created", "data": original, "revision": 6},
            {"position": 2, "type": "message.edited", "data": captioned, "revision": 9},
            {"position": 3, "type": "message.edited", "data": document, "revision": 10},
            {"position": 4, "type": "message.edited", "data": restored, "revision": 11},
        ],
        "users": users,
        "assets": [asset],
        "custom_emoji": [],
        "documents": [descriptor],
    }
    assert original_dependencies == {
        "users": users,
        "assets": [asset],
        "message_revision": 6,
        "custom_emoji": [],
        "documents": [],
    }
    snapshot = {
        "schema": 5,
        "world_id": world.world_id,
        "user_id": user["id"],
        "cursor": 11,
        "now": 105,
        "users": users,
        "chats": [chat, {"id": 2, "type": "private", "user_id": 1, "bot_id": 3}],
        "messages": [restored],
        "message_position": 4,
        "sends": [],
        "assets": [asset],
        "message_revisions": [{"chat_id": 1, "message_id": 1, "revision": 11}],
        "custom_emoji": [],
        "documents": [descriptor],
    }
    assert world.client_snapshot(user["id"], version=5) == snapshot
    world.__exit__(None, None, None)
    with World.open(directory) as reopened:
        assert reopened.get_message(1, 1) == restored
        assert reopened.client_snapshot(user["id"], version=5) == snapshot
        assert reopened.granted_asset(user["id"], 1)[1] == first_bytes
        assert reopened.granted_document(user["id"], "1")[1] == document_bytes


def test_document_reuse_and_noop_or_invalid_edits_preserve_complete_database(
    tmp_path: Path,
) -> None:
    world, _user, bot, chat = setup(tmp_path / "world")
    item = DocumentUpload(b"one", "one.pdf")
    message = world.send_document(
        chat_id=chat["id"],
        sender_id=bot["id"],
        document={"media": "attach://one"},
        uploads={"one": item},
    )
    file_id = world.document_file(bot["id"], "1")["file_id"]
    before = logical_database(world)
    with pytest.raises(ValueError, match="MESSAGE_NOT_MODIFIED"):
        world.edit_media(
            chat_id=1,
            message_id=message["id"],
            bot_id=bot["id"],
            media={"type": "document", "media": file_id},
        )
    assert logical_database(world) == before
    operations: tuple[Callable[[], object], ...] = (
        lambda: world.edit_media(
            chat_id=1,
            message_id=1,
            bot_id=bot["id"],
            media={"type": "photo", "media": file_id},
        ),
        lambda: world.edit_media(
            chat_id=1,
            message_id=1,
            bot_id=bot["id"],
            media={"type": "document", "media": "attach://x"},
            uploads={"x": b"wrong type"},
        ),
        lambda: world.edit_caption(chat_id=1, message_id=1, bot_id=3, caption="wrong bot"),
    )
    for operation in operations:
        with pytest.raises((TypeError, ValueError)):
            operation()
        assert logical_database(world) == before
    world.__exit__(None, None, None)


def test_late_edit_failure_rolls_back_new_media_and_retry_is_deterministic(tmp_path: Path) -> None:
    world, user, bot, _chat = setup(tmp_path / "world")
    world.send_photo(
        chat_id=1,
        sender_id=bot["id"],
        photo={"type": "photo", "media": "attach://one"},
        uploads={"one": png()},
    )
    with world._connection:
        world._connection.execute(
            "CREATE TRIGGER interrupt_media_edit AFTER INSERT ON document_grants "
            "BEGIN SELECT RAISE(ABORT, 'edit interruption'); END"
        )
    before = logical_database(world)
    with pytest.raises(sqlite3.IntegrityError, match="edit interruption"):
        world.edit_media(
            chat_id=1,
            message_id=1,
            bot_id=bot["id"],
            media={"type": "document", "media": "attach://new"},
            uploads={"new": DocumentUpload(b"new", "new.bin")},
        )
    assert logical_database(world) == before
    with world._connection:
        world._connection.execute("DROP TRIGGER interrupt_media_edit")
    edited = world.edit_media(
        chat_id=1,
        message_id=1,
        bot_id=bot["id"],
        media={"type": "document", "media": "attach://new"},
        uploads={"new": DocumentUpload(b"new", "new.bin")},
    )
    assert edited["document"] == {"document_id": "1"}
    assert world.granted_document(user["id"], "1")[1] == b"new"
    world.__exit__(None, None, None)


def test_same_kind_uploads_and_custom_emoji_caption_grants_are_retained(tmp_path: Path) -> None:
    world, user, bot, _chat = setup(tmp_path / "world")
    first = world.send_photo(
        chat_id=1,
        sender_id=bot["id"],
        photo={"type": "photo", "media": "attach://one"},
        uploads={"one": png()},
    )
    second_bytes = png((90, 80, 70))
    photo = world.edit_media(
        chat_id=1,
        message_id=first["id"],
        bot_id=bot["id"],
        media={"type": "photo", "media": "attach://two"},
        uploads={"two": second_bytes},
    )
    assert photo["photo"] == {"asset_id": 2}
    document = world.send_document(
        chat_id=1,
        sender_id=bot["id"],
        document={"media": "attach://one"},
        uploads={"one": DocumentUpload(b"one", "one.pdf")},
    )
    changed = world.edit_media(
        chat_id=1,
        message_id=document["id"],
        bot_id=bot["id"],
        media={"type": "document", "media": "attach://two"},
        uploads={"two": DocumentUpload(b"two", "two.pdf")},
    )
    assert changed["document"] == {"document_id": "2"}
    assets = Path("tests/assets/custom-emoji")
    world.register_custom_emoji(
        request_id="edit-caption",
        custom_emoji_id=1109,
        main=(assets / "emoji-static.webp").read_bytes(),
        thumbnail=(assets / "emoji-thumbnail.webp").read_bytes(),
        fallback="👩‍💻",
    )
    world.edit_caption(
        chat_id=1,
        message_id=document["id"],
        bot_id=bot["id"],
        caption="A 👩‍💻",
        caption_entities=[
            {"type": "custom_emoji", "offset": 2, "length": 5, "custom_emoji_id": "1109"}
        ],
    )
    descriptor = world.granted_custom_emoji(user["id"], ["1109"])[0][0]
    world.edit_caption(chat_id=1, message_id=document["id"], bot_id=bot["id"])
    assert world.granted_custom_emoji(user["id"], ["1109"])[0] == [descriptor]
    assert world.granted_asset(user["id"], 1)[1] == png()
    assert world.granted_asset(user["id"], 2)[1] == second_bytes
    assert world.granted_document(user["id"], "1")[1] == b"one"
    assert world.granted_document(user["id"], "2")[1] == b"two"
    world.__exit__(None, None, None)


def test_non_media_and_grouped_messages_reject_explicitly(tmp_path: Path) -> None:
    world, _user, bot, _chat = setup(tmp_path / "world")
    text = world.send_message(chat_id=1, sender_id=bot["id"], text="plain")
    with pytest.raises(ValueError, match="non-media"):
        world.edit_caption(chat_id=1, message_id=text["id"], bot_id=bot["id"], caption="x")
    photo = world.send_photo(
        chat_id=1,
        sender_id=bot["id"],
        photo={"type": "photo", "media": "attach://one"},
        uploads={"one": png()},
    )
    grouped = dict(photo, media_group_id="group")
    with world._connection:
        world._connection.execute(
            "UPDATE messages SET body=? WHERE chat_id=1 AND id=?",
            (json.dumps(grouped), photo["id"]),
        )
    with pytest.raises(ValueError, match="grouped"):
        world.edit_caption(chat_id=1, message_id=photo["id"], bot_id=bot["id"], caption="x")
    world.__exit__(None, None, None)


@pytest.mark.parametrize(
    ("kind", "operation"),
    [
        ("photo", "caption"),
        ("photo", "media"),
        ("document", "caption"),
        ("document", "media"),
    ],
)
def test_empty_caption_noop_is_semantic_and_positive_edit_still_publishes(
    tmp_path: Path, kind: str, operation: str
) -> None:
    world, _user, bot, _chat = setup(tmp_path / f"{kind}-{operation}")
    if kind == "photo":
        message = world.send_photo(
            chat_id=1,
            sender_id=bot["id"],
            photo={"type": "photo", "media": "attach://item"},
            uploads={"item": png()},
            caption="",
        )
        file_id = world.photo_size(bot["id"], 1)["file_id"]
    else:
        message = world.send_document(
            chat_id=1,
            sender_id=bot["id"],
            document={"media": "attach://item"},
            uploads={"item": DocumentUpload(b"item", "item.pdf")},
            caption="",
        )
        file_id = world.document_file(bot["id"], "1")["file_id"]
    before = logical_database(world)
    with pytest.raises(ValueError, match="MESSAGE_NOT_MODIFIED"):
        if operation == "caption":
            world.edit_caption(chat_id=1, message_id=message["id"], bot_id=bot["id"])
        else:
            world.edit_media(
                chat_id=1,
                message_id=message["id"],
                bot_id=bot["id"],
                media={"type": kind, "media": file_id},
            )
    assert logical_database(world) == before
    changed = world.edit_caption(
        chat_id=1,
        message_id=message["id"],
        bot_id=bot["id"],
        caption="changed",
        reply_markup={"inline_keyboard": [[{"text": "New", "callback_data": "new"}]]},
    )
    assert changed["caption"] == "changed" and "reply_markup" in changed
    assert world.events()[-1]["type"] == "message.edited"
    assert world.events()[-1]["data"] == changed
    world.__exit__(None, None, None)


def test_own_message_rejects_foreign_bot_media_id_and_wrong_upload_types(tmp_path: Path) -> None:
    world, _user, bot, _chat = setup(tmp_path / "world")
    own = world.send_photo(
        chat_id=1,
        sender_id=bot["id"],
        photo={"type": "photo", "media": "attach://own"},
        uploads={"own": png()},
    )
    foreign_photo = world.send_photo(
        chat_id=2,
        sender_id=3,
        photo={"type": "photo", "media": "attach://foreign"},
        uploads={"foreign": png((4, 5, 6))},
    )
    foreign_photo_id = world.photo_size(3, foreign_photo["photo"]["asset_id"])["file_id"]
    foreign_document = world.send_document(
        chat_id=2,
        sender_id=3,
        document={"media": "attach://foreign"},
        uploads={"foreign": DocumentUpload(b"foreign", "foreign.pdf")},
    )
    foreign_document_id = world.document_file(3, foreign_document["document"]["document_id"])[
        "file_id"
    ]
    for kind, file_id in (("photo", foreign_photo_id), ("document", foreign_document_id)):
        before = logical_database(world)
        with pytest.raises(ValueError, match="unavailable"):
            world.edit_media(
                chat_id=1,
                message_id=own["id"],
                bot_id=bot["id"],
                media={"type": kind, "media": file_id},
            )
        assert logical_database(world) == before
    for kind, upload in (
        ("photo", DocumentUpload(b"wrong", "wrong.bin")),
        ("document", b"wrong"),
    ):
        before = logical_database(world)
        with pytest.raises(TypeError):
            world.edit_media(
                chat_id=1,
                message_id=own["id"],
                bot_id=bot["id"],
                media={"type": kind, "media": "attach://wrong"},
                uploads={"wrong": upload},
            )
        assert logical_database(world) == before
    world.__exit__(None, None, None)
