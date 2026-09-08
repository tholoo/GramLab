"""World acceptance for standalone ordinary media edits."""

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
    assert [event["type"] for event in world.events()[-3:]] == [
        "message.edited",
        "message.edited",
        "message.edited",
    ]
    world.__exit__(None, None, None)
    with World.open(directory) as reopened:
        assert reopened.get_message(1, 1) == restored
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
