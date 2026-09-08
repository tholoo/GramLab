import gc
import hashlib
import json
import sqlite3
import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pytest

from gramlab.documents import MAX_DOCUMENT_BYTES, DocumentUpload
from gramlab.world import World


def setup_world(path: Path) -> tuple[World, dict[str, Any], dict[str, Any], dict[str, Any]]:
    world = World.create(path, seed=99, now=1_700_000_000)
    user = world.create_user(first_name="Ada")
    bot = world.create_user(first_name="Documents", is_bot=True)
    chat = world.open_private_chat(user_id=user["id"], bot_id=bot["id"])
    return world, user, bot, chat


def upload(
    data: bytes = b"ordinary document bytes", filename: str = "report.PDF"
) -> DocumentUpload:
    return DocumentUpload(data=data, filename=filename, content_type="declared/ignored")


def send(
    world: World,
    chat: dict[str, Any],
    bot: dict[str, Any],
    item: DocumentUpload,
    **keywords: Any,
) -> dict[str, Any]:
    return world.send_document(
        chat_id=chat["id"],
        sender_id=bot["id"],
        document={"media": "attach://file"},
        uploads={"file": item},
        **keywords,
    )


def test_upload_metadata_is_immutable_and_uses_pinned_semantic_identity() -> None:
    item = DocumentUpload(b"abc", "dir\\Résumé.PDF", "image/png")
    assert item.data == b"abc" and item.filename == "dir\\Résumé.PDF"
    assert item.content_type == "image/png"
    assert item.file_name == "Résumé.PDF"
    assert item.mime_type == "application/pdf"
    assert item.sha256 == hashlib.sha256(b"abc").hexdigest()
    encoded = json.dumps(
        ["document", item.sha256, "Résumé.PDF", "application/pdf"],
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode()
    assert item.file_unique_id == "gramlab_document_unique_" + hashlib.sha256(encoded).hexdigest()
    with pytest.raises(AttributeError):
        item.filename = "changed"  # type: ignore[misc]


def test_document_publish_reuse_download_grant_and_reopen(tmp_path: Path) -> None:
    directory = tmp_path / "world"
    world, user, bot, chat = setup_world(directory)
    item = upload()
    keyboard = {"inline_keyboard": [[{"text": "Open", "callback_data": "doc:open"}]]}
    first = send(
        world,
        chat,
        bot,
        item,
        caption="A report",
        caption_entities=[{"type": "bold", "offset": 0, "length": 1}],
        reply_markup=keyboard,
    )
    document = world.document_file(bot["id"], "1")
    second = world.send_document(
        chat_id=chat["id"],
        sender_id=bot["id"],
        document={"media": document["file_id"]},
    )
    assert first == {
        "id": 1,
        "chat_id": 1,
        "sender_id": 2,
        "date": 1_700_000_000,
        "text": "",
        "reply_markup": keyboard,
        "document": {"document_id": "1"},
        "caption": "A report",
        "caption_entities": [{"type": "bold", "offset": 0, "length": 1}],
    }
    assert second == {
        "id": 2,
        "chat_id": 1,
        "sender_id": 2,
        "date": 1_700_000_000,
        "text": "",
        "document": {"document_id": "1"},
    }
    descriptor = {
        "document_id": "1",
        "file_name": "report.PDF",
        "mime_type": "application/pdf",
        "file_size": len(item.data),
        "sha256": item.sha256,
    }
    assert world.document_descriptor("1") == descriptor
    assert document == {
        "file_id": document["file_id"],
        "file_unique_id": item.file_unique_id,
        "file_size": len(item.data),
        "file_name": "report.PDF",
        "mime_type": "application/pdf",
    }
    assert document["file_id"].startswith("gramlab_document_")
    assert world.granted_document(user["id"], "1") == (descriptor, item.data)
    info, body = world.bot_file(bot["id"], document["file_id"])
    assert body == item.data
    assert info == document | {"file_path": f"documents/{document['file_id']}"}
    assert world.history(chat["id"]) == [first, second]
    assert [event["data"] for event in world.events() if event["type"] == "message.created"] == [
        first,
        second,
    ]
    world.__exit__(None, None, None)
    with World.open(directory) as reopened:
        assert reopened.history(chat["id"]) == [first, second]
        assert reopened.granted_document(user["id"], "1") == (descriptor, item.data)
        assert reopened.bot_file(bot["id"], document["file_id"]) == (info, item.data)


def test_identical_bytes_share_blob_but_metadata_and_typed_ids_are_independent(
    tmp_path: Path,
) -> None:
    world, user, bot, chat = setup_world(tmp_path / "world")
    data = b"same neutral bytes"
    one = send(world, chat, bot, upload(data, "one.txt"))
    two = send(world, chat, bot, upload(data, "two.pdf"))
    three = send(world, chat, bot, DocumentUpload(data, "one.txt", "another/declaration"))
    assert [one["document"], two["document"], three["document"]] == [
        {"document_id": "1"},
        {"document_id": "2"},
        {"document_id": "1"},
    ]
    assert world._connection.execute("SELECT count(*) FROM media_blobs").fetchone() == (1,)
    assert world._connection.execute("SELECT count(*) FROM documents").fetchone() == (2,)
    documents = world.client_snapshot(user["id"], version=5)["documents"]
    assert [item["document_id"] for item in documents] == ["1", "2"]
    world.__exit__(None, None, None)


def test_bot_persona_world_and_media_kinds_do_not_transfer_authority(tmp_path: Path) -> None:
    world, _user, bot, chat = setup_world(tmp_path / "one")
    stranger = world.create_user(first_name="Stranger")
    other_bot = world.create_user(first_name="Other", is_bot=True)
    other_chat = world.open_private_chat(user_id=stranger["id"], bot_id=other_bot["id"])
    item = upload()
    message = send(world, chat, bot, item)
    own = world.document_file(bot["id"], message["document"]["document_id"])
    with pytest.raises(ValueError, match="unavailable"):
        world.granted_document(stranger["id"], "1")
    with pytest.raises(ValueError, match="unavailable"):
        world.bot_file(other_bot["id"], own["file_id"])
    with pytest.raises(ValueError, match="unavailable"):
        world.send_document(
            chat_id=other_chat["id"],
            sender_id=other_bot["id"],
            document={"media": own["file_id"]},
        )
    independent = send(world, other_chat, other_bot, item)
    other = world.document_file(other_bot["id"], independent["document"]["document_id"])
    assert independent["document"] == message["document"] == {"document_id": "1"}
    assert other["file_id"] != own["file_id"]
    assert other["file_unique_id"] == own["file_unique_id"]
    assert world.granted_document(stranger["id"], "1")[1] == item.data

    photo = Path("tests/assets/rich-media/photo-square-16x16.png").read_bytes()
    photo_message = world.send_photo(
        chat_id=chat["id"],
        sender_id=bot["id"],
        photo={"type": "photo", "media": "attach://p"},
        uploads={"p": photo},
    )
    photo_file = world.photo_size(bot["id"], photo_message["photo"]["asset_id"])["file_id"]
    with pytest.raises(ValueError, match="Document file identifier"):
        world.send_document(chat_id=chat["id"], sender_id=bot["id"], document={"media": photo_file})
    with pytest.raises(ValueError, match="Photo file identifier"):
        world.send_photo(
            chat_id=chat["id"],
            sender_id=bot["id"],
            photo={"type": "photo", "media": own["file_id"]},
        )
    world.__exit__(None, None, None)

    isolated, isolated_user, isolated_bot, isolated_chat = setup_world(tmp_path / "two")
    with isolated:
        with pytest.raises(ValueError, match="unavailable"):
            isolated.bot_file(isolated_bot["id"], own["file_id"])
        with pytest.raises(ValueError, match="unavailable"):
            isolated.granted_document(isolated_user["id"], "1")
        sent = send(isolated, isolated_chat, isolated_bot, item)
        assert sent["document"] == {"document_id": "1"}


def test_v5_snapshot_changes_and_callback_bind_exact_historical_documents(tmp_path: Path) -> None:
    world, user, bot, chat = setup_world(tmp_path / "world")
    markup = {"inline_keyboard": [[{"text": "Tap", "callback_data": "document"}]]}
    first = send(world, chat, bot, upload(b"one", "one.txt"), reply_markup=markup)
    first_revision = world.client_snapshot(user["id"], version=5)["message_revisions"][0][
        "revision"
    ]
    callback = world.create_callback(
        user_id=user["id"],
        chat_id=chat["id"],
        message_id=first["id"],
        data="document",
        request_id="document-callback",
        version=5,
    )
    before_legacy_retry = world.events()
    with pytest.raises(ValueError, match="documents require client bridge v5"):
        world.create_callback(
            user_id=user["id"],
            chat_id=chat["id"],
            message_id=first["id"],
            data="document",
            request_id="document-callback",
            version=4,
        )
    assert world.events() == before_legacy_retry
    second = send(world, chat, bot, upload(b"two", "two.bin"))
    later = world.send_message(chat_id=chat["id"], sender_id=bot["id"], text="later")
    first_descriptor = world.document_descriptor("1")
    second_descriptor = world.document_descriptor("2")
    assert first_revision == 4
    assert callback == {
        "id": callback["id"],
        "user_id": user["id"],
        "chat_id": chat["id"],
        "message": first,
        "data": "document",
        "chat_instance": hashlib.sha256(f"{world.world_id}:{chat['id']}".encode()).hexdigest(),
        "answer": None,
    }
    assert world.history(chat["id"]) == [first, second, later]
    assert world.events() == [
        {"sequence": 1, "type": "user.created", "data": user},
        {"sequence": 2, "type": "user.created", "data": bot},
        {"sequence": 3, "type": "chat.created", "data": chat},
        {
            "sequence": 4,
            "type": "message.created",
            "data": first,
        },
        {
            "sequence": 5,
            "type": "callback.created",
            "data": {key: value for key, value in callback.items() if key != "answer"},
        },
        {"sequence": 6, "type": "message.created", "data": second},
        {"sequence": 7, "type": "message.created", "data": later},
    ]
    snapshot = world.client_snapshot(user["id"], version=5)
    assert snapshot == {
        "schema": 5,
        "world_id": world.world_id,
        "user_id": user["id"],
        "cursor": 7,
        "now": 1_700_000_000,
        "users": [user, bot],
        "chats": [chat],
        "messages": [first, second, later],
        "message_position": 3,
        "sends": [],
        "assets": [],
        "message_revisions": [
            {"chat_id": 1, "message_id": 1, "revision": 4},
            {"chat_id": 1, "message_id": 2, "revision": 6},
            {"chat_id": 1, "message_id": 3, "revision": 7},
        ],
        "custom_emoji": [],
        "documents": [first_descriptor, second_descriptor],
    }
    first_page = world.client_changes(user["id"], after=0, limit=1, version=5)
    assert first_page == {
        "schema": 5,
        "world_id": world.world_id,
        "user_id": user["id"],
        "cursor": 1,
        "head": 3,
        "now": 1_700_000_000,
        "changes": [{"position": 1, "type": "message.created", "data": first, "revision": 4}],
        "users": [user, bot],
        "assets": [],
        "custom_emoji": [],
        "documents": [first_descriptor],
    }
    later_page = world.client_changes(user["id"], after=1, version=5)
    assert later_page == {
        "schema": 5,
        "world_id": world.world_id,
        "user_id": user["id"],
        "cursor": 3,
        "head": 3,
        "now": 1_700_000_000,
        "changes": [
            {"position": 2, "type": "message.created", "data": second, "revision": 6},
            {"position": 3, "type": "message.created", "data": later, "revision": 7},
        ],
        "users": [user, bot],
        "assets": [],
        "custom_emoji": [],
        "documents": [second_descriptor],
    }
    dependencies = world.callback_dependencies(user["id"], callback, version=5)
    assert dependencies == {
        "users": [user, bot],
        "assets": [],
        "message_revision": 4,
        "custom_emoji": [],
        "documents": [first_descriptor],
    }
    retried = world.create_callback(
        user_id=user["id"],
        chat_id=chat["id"],
        message_id=first["id"],
        data="document",
        request_id="document-callback",
        version=5,
    )
    assert retried == callback
    assert world.callback_dependencies(user["id"], retried, version=5) == dependencies
    world.__exit__(None, None, None)


@pytest.mark.parametrize("version", [1, 2, 3, 4])
def test_legacy_snapshot_rejects_document_without_cursor_mutation(
    tmp_path: Path, version: int
) -> None:
    world, user, bot, chat = setup_world(tmp_path / str(version))
    message = send(
        world,
        chat,
        bot,
        upload(),
        reply_markup={"inline_keyboard": [[{"text": "Tap", "callback_data": "x"}]]},
    )
    before = world.events()
    with pytest.raises(ValueError, match="documents require client bridge v5"):
        world.client_snapshot(user["id"], version=version)
    if version == 1:
        with pytest.raises(ValueError, match="documents require client bridge v5"):
            world.client_events(user["id"], after=0)
    if version >= 2:
        with pytest.raises(ValueError, match="documents require client bridge v5"):
            world.client_changes(user["id"], after=0, version=version)
    callback_version = version if version in (1, 3, 4) else 1
    with pytest.raises(ValueError, match="documents require client bridge v5"):
        world.create_callback(
            user_id=user["id"],
            chat_id=chat["id"],
            message_id=message["id"],
            data="x",
            request_id=f"legacy-{version}",
            version=callback_version,
        )
    assert world.events() == before
    assert world._connection.execute("SELECT count(*) FROM callbacks").fetchone() == (0,)
    if version == 1:
        callback = world.create_callback(
            user_id=user["id"],
            chat_id=chat["id"],
            message_id=message["id"],
            data="x",
            request_id="v5-callback",
            version=5,
        )
        callback_sequence = world.events()[-1]["sequence"]
        with pytest.raises(ValueError, match="documents require client bridge v5"):
            world.client_events(user["id"], after=callback_sequence - 1)
        assert world.get_callback(user_id=user["id"], callback_id=callback["id"]) == callback
    world.__exit__(None, None, None)


def test_callback_dependencies_use_one_sqlite_read_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    directory = tmp_path / "world"
    world, user, bot, chat = setup_world(directory)
    message = send(
        world,
        chat,
        bot,
        upload(b"stable", "stable.txt"),
        reply_markup={"inline_keyboard": [[{"text": "Tap", "callback_data": "x"}]]},
    )
    callback = world.create_callback(
        user_id=user["id"],
        chat_id=chat["id"],
        message_id=message["id"],
        data="x",
        request_id="snapshot",
        version=5,
    )
    ready, written = threading.Event(), threading.Event()
    original = world._identity_dependencies

    def pause(user_id: int, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        ready.set()
        assert written.wait(timeout=10)
        return original(user_id, messages)

    def writer() -> None:
        assert ready.wait(timeout=10)
        with sqlite3.connect(directory / "world.sqlite3") as connection:
            connection.execute("UPDATE documents SET file_name='changed.txt' WHERE id=1")
        written.set()

    monkeypatch.setattr(world, "_identity_dependencies", pause)
    with ThreadPoolExecutor(max_workers=1) as workers:
        future = workers.submit(writer)
        dependencies = world.callback_dependencies(user["id"], callback, version=5)
        future.result(timeout=10)
    assert dependencies["documents"] == [
        {
            "document_id": "1",
            "file_name": "stable.txt",
            "mime_type": "text/plain",
            "file_size": 6,
            "sha256": hashlib.sha256(b"stable").hexdigest(),
        }
    ]
    assert world._connection.in_transaction is False
    assert world.document_descriptor("1")["file_name"] == "changed.txt"
    world.__exit__(None, None, None)


def test_document_caption_custom_emoji_dependencies_follow_v5_rules(tmp_path: Path) -> None:
    world, user, bot, chat = setup_world(tmp_path / "world")
    assets = Path("tests/assets/custom-emoji")
    emoji = world.register_custom_emoji(
        request_id="document-caption",
        main=(assets / "emoji-static.webp").read_bytes(),
        thumbnail=(assets / "emoji-thumbnail.webp").read_bytes(),
        fallback="🙂",
    )
    message = send(
        world,
        chat,
        bot,
        upload(),
        caption="🙂 report",
        caption_entities=[
            {"type": "custom_emoji", "offset": 0, "length": 2, "custom_emoji_id": "1"}
        ],
    )
    photo_data = Path("tests/assets/rich-media/photo-square-16x16.png").read_bytes()
    photo = world.send_photo(
        chat_id=chat["id"],
        sender_id=bot["id"],
        photo={"type": "photo", "media": "attach://photo"},
        uploads={"photo": photo_data},
    )
    referenced = world.create_user(first_name="Referenced")
    world.open_private_chat(user_id=referenced["id"], bot_id=bot["id"])
    mention = world.send_rich_message(
        chat_id=chat["id"],
        sender_id=bot["id"],
        rich_message={
            "skip_entity_detection": True,
            "blocks": [
                {
                    "type": "paragraph",
                    "text": {
                        "type": "text_mention",
                        "text": "Referenced",
                        "user": {"id": referenced["id"]},
                    },
                }
            ],
        },
    )
    snapshot = world.client_snapshot(user["id"], version=5)
    assert snapshot["messages"] == [message, photo, mention]
    assert snapshot["users"] == [user, bot, referenced]
    assert snapshot["custom_emoji"] == [emoji]
    assert {item["asset_id"] for item in snapshot["assets"]} == {
        emoji["main_asset_id"],
        emoji["thumbnail_asset_id"],
        photo["photo"]["asset_id"],
    }
    assert snapshot["documents"] == [world.document_descriptor("1")]
    changes = world.client_changes(user["id"], after=0, limit=1, version=5)
    assert changes["custom_emoji"] == [emoji]
    assert {item["asset_id"] for item in changes["assets"]} == {
        emoji["main_asset_id"],
        emoji["thumbnail_asset_id"],
    }
    assert changes["documents"] == [world.document_descriptor("1")]
    mention_changes = world.client_changes(user["id"], after=2, version=5)
    assert mention_changes["changes"][0]["data"] == mention
    assert mention_changes["users"] == [user, bot, referenced]
    assert mention_changes["documents"] == []
    world.__exit__(None, None, None)


InvalidCall = Callable[[World, dict[str, Any], dict[str, Any], dict[str, Any]], None]


def invalid_missing_upload(
    world: World, _user: dict[str, Any], bot: dict[str, Any], chat: dict[str, Any]
) -> None:
    world.send_document(
        chat_id=chat["id"], sender_id=bot["id"], document={"media": "attach://missing"}
    )


def invalid_extra_upload(
    world: World, _user: dict[str, Any], bot: dict[str, Any], chat: dict[str, Any]
) -> None:
    world.send_document(
        chat_id=chat["id"],
        sender_id=bot["id"],
        document={"media": "attach://one"},
        uploads={"one": upload(), "extra": upload(b"two")},
    )


def invalid_shape(
    world: World, _user: dict[str, Any], bot: dict[str, Any], chat: dict[str, Any]
) -> None:
    world.send_document(
        chat_id=chat["id"],
        sender_id=bot["id"],
        document={"media": "attach://one", "type": "document"},
        uploads={"one": upload()},
    )


def invalid_external(
    world: World, _user: dict[str, Any], bot: dict[str, Any], chat: dict[str, Any]
) -> None:
    world.send_document(
        chat_id=chat["id"], sender_id=bot["id"], document={"media": "https://example.test/a"}
    )


def invalid_path(
    world: World, _user: dict[str, Any], bot: dict[str, Any], chat: dict[str, Any]
) -> None:
    world.send_document(
        chat_id=chat["id"],
        sender_id=bot["id"],
        document={"media": "/tmp/report.pdf"},  # noqa: S108 — rejected path input
    )


def invalid_empty_payload(
    _world: World, _user: dict[str, Any], _bot: dict[str, Any], _chat: dict[str, Any]
) -> None:
    DocumentUpload(b"", "empty.bin")


def invalid_nonbyte_payload(
    _world: World, _user: dict[str, Any], _bot: dict[str, Any], _chat: dict[str, Any]
) -> None:
    DocumentUpload(bytearray(b"x"), "mutable.bin")  # type: ignore[arg-type]


def invalid_sender(
    world: World, user: dict[str, Any], _bot: dict[str, Any], chat: dict[str, Any]
) -> None:
    world.send_document(
        chat_id=chat["id"],
        sender_id=user["id"],
        document={"media": "attach://one"},
        uploads={"one": upload()},
    )


def invalid_caption(
    world: World, _user: dict[str, Any], bot: dict[str, Any], chat: dict[str, Any]
) -> None:
    send(world, chat, bot, upload(), caption="x" * 1025)


def invalid_caption_entities(
    world: World, _user: dict[str, Any], bot: dict[str, Any], chat: dict[str, Any]
) -> None:
    send(
        world,
        chat,
        bot,
        upload(),
        caption="x",
        caption_entities=[{"type": "bold", "offset": 1, "length": 1}],
    )


def invalid_keyboard(
    world: World, _user: dict[str, Any], bot: dict[str, Any], chat: dict[str, Any]
) -> None:
    send(world, chat, bot, upload(), reply_markup={"keyboard": []})


@pytest.mark.parametrize(
    "operation",
    [
        invalid_missing_upload,
        invalid_extra_upload,
        invalid_shape,
        invalid_external,
        invalid_path,
        invalid_empty_payload,
        invalid_nonbyte_payload,
        invalid_sender,
        invalid_caption,
        invalid_caption_entities,
        invalid_keyboard,
    ],
)
def test_invalid_publication_is_atomic_and_does_not_consume_identifiers(
    tmp_path: Path, operation: InvalidCall
) -> None:
    world, user, bot, chat = setup_world(tmp_path / operation.__name__)
    before = (world.snapshot(), world.events(), world.history(chat["id"]))
    with pytest.raises((TypeError, ValueError)):
        operation(world, user, bot, chat)
    assert (world.snapshot(), world.events(), world.history(chat["id"])) == before
    good = send(world, chat, bot, upload())
    assert good["id"] == 1 and good["document"] == {"document_id": "1"}
    world.__exit__(None, None, None)


@pytest.mark.parametrize(
    "value",
    ["0", "-1", "+1", "01", " 1", "1 ", "1.0", "9223372036854775808", 1, 1.0, None],
)
def test_public_document_ids_require_canonical_positive_decimal_strings(
    tmp_path: Path, value: Any
) -> None:
    world, _user, _bot, _chat = setup_world(tmp_path / str(value).replace("/", "_"))
    with pytest.raises(ValueError, match="Invalid document ID"):
        world.document_descriptor(value)
    world.__exit__(None, None, None)


def test_empty_and_unknown_mime_are_valid_metadata(tmp_path: Path) -> None:
    world, _user, bot, chat = setup_world(tmp_path / "world")
    no_mime = send(world, chat, bot, upload(b"one", "README"))
    unknown = send(world, chat, bot, upload(b"two", "file.gramlab_unknown"))
    assert world.document_descriptor(no_mime["document"]["document_id"])["mime_type"] == ""
    assert world.document_descriptor(unknown["document"]["document_id"])["mime_type"] == ""
    assert "mime_type" not in world.document_file(bot["id"], "1")
    file_id = world.document_file(bot["id"], "1")["file_id"]
    assert world.bot_file(bot["id"], file_id)[0]["mime_type"] == ""
    world.__exit__(None, None, None)


def test_exact_local_size_boundary_is_inclusive_and_oversize_rejects(tmp_path: Path) -> None:
    world, _user, bot, chat = setup_world(tmp_path / "world")
    boundary = b"x" * MAX_DOCUMENT_BYTES
    message = send(world, chat, bot, upload(boundary, "boundary.bin"))
    assert message["document"] == {"document_id": "1"}
    assert world.document_descriptor("1")["file_size"] == MAX_DOCUMENT_BYTES
    world.__exit__(None, None, None)
    del boundary
    gc.collect()

    rejected, _user, rejected_bot, rejected_chat = setup_world(tmp_path / "rejected")
    oversized = b"x" * (MAX_DOCUMENT_BYTES + 1)
    with pytest.raises(ValueError, match="50000000-byte"):
        upload(oversized, "too-large.bin")
    del oversized
    gc.collect()
    accepted = send(rejected, rejected_chat, rejected_bot, upload(b"small", "small.bin"))
    assert accepted["id"] == 1 and accepted["document"] == {"document_id": "1"}
    rejected.__exit__(None, None, None)


@pytest.mark.parametrize(
    ("arguments", "error"),
    [
        ({"data": bytearray(b"x"), "filename": "x.bin"}, TypeError),
        ({"data": b"", "filename": "x.bin"}, ValueError),
        ({"data": b"x", "filename": 1}, TypeError),
        ({"data": b"x", "filename": "x.bin", "content_type": 1}, TypeError),
    ],
)
def test_upload_rejects_malformed_values(arguments: dict[str, Any], error: type[Exception]) -> None:
    with pytest.raises(error):
        DocumentUpload(**arguments)


def test_failed_publication_rolls_back_every_typed_row_and_retries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    world, _user, bot, chat = setup_world(tmp_path / "world")
    original = world._insert_message

    def fail(**_keywords: Any) -> dict[str, Any]:
        raise RuntimeError("publication interruption")

    monkeypatch.setattr(world, "_insert_message", fail)
    with pytest.raises(RuntimeError, match="publication interruption"):
        send(world, chat, bot, upload())
    for table in ("media_blobs", "documents", "bot_document_files", "document_grants", "messages"):
        assert world._connection.execute(f"SELECT count(*) FROM {table}").fetchone() == (0,)  # noqa: S608
    monkeypatch.setattr(world, "_insert_message", original)
    message = send(world, chat, bot, upload())
    assert message["id"] == 1 and message["document"] == {"document_id": "1"}
    world.__exit__(None, None, None)


def test_existing_text_edit_rejects_document_conversion_and_preserves_grant(tmp_path: Path) -> None:
    world, user, bot, chat = setup_world(tmp_path / "world")
    message = send(world, chat, bot, upload())
    before = (world.history(chat["id"]), world.events())
    with pytest.raises(ValueError, match="editing ordinary document"):
        world.edit_message(
            chat_id=chat["id"], message_id=message["id"], bot_id=bot["id"], text="plain"
        )
    assert (world.history(chat["id"]), world.events()) == before
    assert world.granted_document(user["id"], "1")[1] == upload().data
    world.__exit__(None, None, None)
