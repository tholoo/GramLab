import io
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pytest
from PIL import Image

from gramlab.world import World


def image_bytes(format: str = "PNG", size: tuple[int, int] = (3, 2)) -> bytes:
    output = io.BytesIO()
    Image.new("RGB", size, (20, 40, 60)).save(output, format)
    return output.getvalue()


def setup_world(path: Path) -> tuple[World, dict[str, Any], dict[str, Any], dict[str, Any]]:
    world = World.create(path, seed=9, now=100)
    user = world.create_user(first_name="Ada")
    bot = world.create_user(first_name="Media", is_bot=True)
    chat = world.open_private_chat(user_id=user["id"], bot_id=bot["id"])
    return world, user, bot, chat


@pytest.mark.parametrize(("format", "mime"), [("PNG", "image/png"), ("JPEG", "image/jpeg")])
def test_photo_is_immutable_reusable_and_persistent(tmp_path: Path, format: str, mime: str) -> None:
    directory = tmp_path / "world"
    world, user, bot, chat = setup_world(directory)
    data = image_bytes(format)
    first = world.send_photo(
        chat_id=chat["id"],
        sender_id=bot["id"],
        photo={"type": "photo", "media": "attach://picture"},
        uploads={"picture": data},
        caption="A 🖼",
        caption_entities=[{"type": "bold", "offset": 0, "length": 1}],
    )
    size = world.photo_size(bot["id"], first["photo"]["asset_id"])
    second = world.send_photo(
        chat_id=chat["id"],
        sender_id=bot["id"],
        photo={"type": "photo", "media": size["file_id"]},
    )
    assert second["photo"] == first["photo"] == {"asset_id": 1}
    assert world.client_snapshot(user["id"], version=3)["assets"] == [
        {
            "asset_id": 1,
            "mime_type": mime,
            "file_size": len(data),
            "sha256": size["file_unique_id"],
            "width": 3,
            "height": 2,
        }
    ]
    info, downloaded = world.bot_file(bot["id"], size["file_id"])
    assert downloaded == data
    assert info["file_path"].startswith("photos/gramlab_")
    world.__exit__(None, None, None)
    with World.open(directory) as reopened:
        assert reopened.bot_file(bot["id"], size["file_id"])[1] == data


def test_rich_photo_caption_edit_revision_and_old_grant(tmp_path: Path) -> None:
    world, user, bot, chat = setup_world(tmp_path / "world")
    first_data, second_data = image_bytes(size=(2, 2)), image_bytes(size=(4, 2))
    first = world.send_rich_message(
        chat_id=chat["id"],
        sender_id=bot["id"],
        uploads={"one": first_data},
        rich_message={
            "skip_entity_detection": True,
            "blocks": [
                {
                    "type": "photo",
                    "photo": {"type": "photo", "media": "attach://one"},
                    "caption": {"credit": {"type": "italic", "text": "source"}},
                }
            ],
        },
    )
    assert first["rich_message"]["blocks"][0]["caption"] == {
        "text": "",
        "credit": {"type": "italic", "text": "source"},
    }
    before = world.client_snapshot(user["id"], version=3)["message_revisions"][0]["revision"]
    edited = world.edit_message(
        chat_id=chat["id"],
        message_id=first["id"],
        bot_id=bot["id"],
        uploads={"two": second_data},
        rich_message={
            "skip_entity_detection": True,
            "blocks": [
                {
                    "type": "photo",
                    "photo": {"type": "photo", "media": "attach://two"},
                    "caption": None,
                }
            ],
        },
    )
    assert edited["rich_message"] == {"blocks": [{"type": "photo", "asset_id": 2}]}
    snapshot = world.client_snapshot(user["id"], version=3)
    assert [asset["asset_id"] for asset in snapshot["assets"]] == [1, 2]
    assert snapshot["message_revisions"][0]["revision"] > before
    assert world.granted_asset(user["id"], 1)[1] == first_data
    with pytest.raises(ValueError, match="v3"):
        world.client_snapshot(user["id"], version=2)
    world.__exit__(None, None, None)


@pytest.mark.parametrize("bad", [b"", b"not an image", image_bytes()[:-8]])
def test_rejected_photo_leaves_identifiers_and_state_unchanged(tmp_path: Path, bad: bytes) -> None:
    world, _user, bot, chat = setup_world(tmp_path / "world")
    before = world.events()
    with pytest.raises(ValueError):
        world.send_photo(
            chat_id=chat["id"],
            sender_id=bot["id"],
            photo={"type": "photo", "media": "attach://bad"},
            uploads={"bad": bad},
        )
    assert world.events() == before
    good = world.send_photo(
        chat_id=chat["id"],
        sender_id=bot["id"],
        photo={"type": "photo", "media": "attach://good"},
        uploads={"good": image_bytes()},
    )
    assert (good["id"], good["photo"]["asset_id"]) == (1, 1)
    world.__exit__(None, None, None)


def test_failed_rich_upload_is_atomic(tmp_path: Path) -> None:
    world, user, bot, chat = setup_world(tmp_path / "world")
    before = world.client_snapshot(user["id"], version=3)
    with pytest.raises(ValueError, match="unused"):
        world.send_rich_message(
            chat_id=chat["id"],
            sender_id=bot["id"],
            uploads={"extra": image_bytes()},
            rich_message={
                "skip_entity_detection": True,
                "blocks": [{"type": "paragraph", "text": "no photo"}],
            },
        )
    assert world.client_snapshot(user["id"], version=3) == before
    sent = world.send_photo(
        chat_id=chat["id"],
        sender_id=bot["id"],
        photo={"type": "photo", "media": "attach://first"},
        uploads={"first": image_bytes()},
    )
    assert (sent["id"], sent["photo"]["asset_id"]) == (1, 1)
    world.__exit__(None, None, None)


def test_schema_five_migration_is_atomic_across_concurrent_openers(tmp_path: Path) -> None:
    directory = tmp_path / "world"
    # A synthetic empty schema-5 fixture: remove every table introduced after v5.
    with World.create(directory, seed=1, now=1):
        pass
    connection = sqlite3.connect(directory / "world.sqlite3")
    with connection:
        for table in (
            "media_group_members",
            "media_groups",
            "media_group_counter",
            "document_grants",
            "bot_document_files",
            "documents",
            "custom_emoji_grants",
            "custom_emoji_registrations",
            "custom_emoji_counter",
            "custom_emoji",
            "callback_revisions",
            "message_revisions",
            "asset_grants",
            "bot_files",
            "assets",
            "media_blobs",
        ):
            connection.execute(f"DROP TABLE {table}")
        connection.execute("PRAGMA user_version=5")
    connection.close()

    def open_version(_index: int) -> int:
        with World.open(directory):
            pass
        check = sqlite3.connect(directory / "world.sqlite3")
        try:
            return int(check.execute("PRAGMA user_version").fetchone()[0])
        finally:
            check.close()

    with ThreadPoolExecutor(max_workers=2) as workers:
        assert list(workers.map(open_version, range(2))) == [10, 10]
    check = sqlite3.connect(directory / "world.sqlite3")
    try:
        assert (
            check.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE name IN "
                "('assets','bot_files','asset_grants','message_revisions','callback_revisions')"
            ).fetchone()[0]
            == 5
        )
    finally:
        check.close()


def test_callback_revision_survives_same_clock_aba_and_restart(tmp_path: Path) -> None:
    directory = tmp_path / "world"
    world, user, bot, chat = setup_world(directory)
    first_data, second_data = image_bytes(size=(2, 2)), image_bytes(size=(3, 2))
    message = world.send_rich_message(
        chat_id=chat["id"],
        sender_id=bot["id"],
        uploads={"a": first_data},
        reply_markup={"inline_keyboard": [[{"text": "Tap", "callback_data": "x"}]]},
        rich_message={
            "skip_entity_detection": True,
            "blocks": [{"type": "photo", "photo": {"type": "photo", "media": "attach://a"}}],
        },
    )
    original_revision = world.client_snapshot(user["id"], version=3)["message_revisions"][0][
        "revision"
    ]
    callback = world.create_callback(
        user_id=user["id"],
        chat_id=chat["id"],
        message_id=message["id"],
        data="x",
        request_id="aba",
        version=3,
    )
    first_id = world.photo_size(bot["id"], 1)["file_id"]
    world.edit_message(
        chat_id=chat["id"],
        message_id=message["id"],
        bot_id=bot["id"],
        uploads={"b": second_data},
        rich_message={
            "skip_entity_detection": True,
            "blocks": [{"type": "photo", "photo": {"type": "photo", "media": "attach://b"}}],
        },
    )
    world.edit_message(
        chat_id=chat["id"],
        message_id=message["id"],
        bot_id=bot["id"],
        rich_message={
            "skip_entity_detection": True,
            "blocks": [{"type": "photo", "photo": {"type": "photo", "media": first_id}}],
        },
    )
    assert (
        world.callback_dependencies(user["id"], callback)["message_revision"] == original_revision
    )
    retried = world.create_callback(
        user_id=user["id"],
        chat_id=chat["id"],
        message_id=message["id"],
        data="x",
        request_id="aba",
        version=3,
    )
    assert retried["id"] == callback["id"]
    world.__exit__(None, None, None)
    with World.open(directory) as reopened:
        stored = reopened.get_callback(user_id=user["id"], callback_id=callback["id"])
        assert (
            reopened.callback_dependencies(user["id"], stored)["message_revision"]
            == original_revision
        )


def test_failed_publication_rolls_back_stored_bytes_grants_and_identifiers(tmp_path: Path) -> None:
    world, user, bot, chat = setup_world(tmp_path / "world")
    with world:
        before = world.snapshot(), world.events(), world.client_snapshot(user["id"], version=4)
        # The first block stores valid bytes; resolution of the second block then fails.
        with pytest.raises(ValueError, match="unavailable"):
            world.send_rich_message(
                chat_id=chat["id"],
                sender_id=bot["id"],
                uploads={"one": image_bytes()},
                rich_message={
                    "skip_entity_detection": True,
                    "blocks": [
                        {"type": "photo", "photo": {"type": "photo", "media": "attach://one"}},
                        {"type": "photo", "photo": {"type": "photo", "media": "unavailable"}},
                    ],
                },
            )
        assert (
            world.snapshot(),
            world.events(),
            world.client_snapshot(user["id"], version=4),
        ) == before
        for table in ("media_blobs", "assets", "bot_files", "asset_grants"):
            assert world._connection.execute(f"SELECT count(*) FROM {table}").fetchone() == (0,)  # noqa: S608
        sent = world.send_photo(
            chat_id=chat["id"],
            sender_id=bot["id"],
            uploads={"one": image_bytes()},
            photo={"type": "photo", "media": "attach://one"},
        )
        assert (sent["id"], sent["photo"]["asset_id"]) == (1, 1)
        assert world.granted_asset(user["id"], 1)[1] == image_bytes()
        assert world._connection.execute("SELECT count(*) FROM media_blobs").fetchone() == (1,)
