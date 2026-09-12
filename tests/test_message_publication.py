from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from gramlab.documents import DocumentUpload
from gramlab.world import World

PHOTO = Path("tests/assets/rich-media/photo-square-16x16.png")


def text(world: World, bot_id: int, chat_id: int) -> object:
    return world.send_message(chat_id=chat_id, sender_id=bot_id, text="plain")


def rich(world: World, bot_id: int, chat_id: int) -> object:
    return world.send_rich_message(
        chat_id=chat_id,
        sender_id=bot_id,
        rich_message={"blocks": [{"type": "paragraph", "text": "rich"}]},
    )


def photo(world: World, bot_id: int, chat_id: int) -> object:
    return world.send_photo(
        chat_id=chat_id,
        sender_id=bot_id,
        photo={"type": "photo", "media": "attach://photo"},
        uploads={"photo": PHOTO.read_bytes()},
    )


def document(world: World, bot_id: int, chat_id: int) -> object:
    return world.send_document(
        chat_id=chat_id,
        sender_id=bot_id,
        document={"media": "attach://document"},
        uploads={"document": DocumentUpload(b"document", "document.txt")},
    )


def media_group(world: World, bot_id: int, chat_id: int) -> object:
    return world.send_media_group(
        chat_id=chat_id,
        sender_id=bot_id,
        media=[
            {"type": "photo", "media": "attach://one"},
            {"type": "photo", "media": "attach://two"},
        ],
        uploads={"one": PHOTO.read_bytes(), "two": PHOTO.read_bytes()},
    )


@pytest.mark.parametrize("send", [text, rich, photo, document, media_group])
def test_every_message_kind_rolls_back_through_one_publication_seam(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    send: Callable[[World, int, int], object],
) -> None:
    with World.create(tmp_path / "world", seed=1, now=100) as world:
        user = world.create_user(first_name="User")
        bot = world.create_user(first_name="Bot", is_bot=True)
        chat = world.open_private_chat(user_id=user["id"], bot_id=bot["id"])
        before = list(world._connection.iterdump())

        def fail(**_keywords: Any) -> dict[str, Any]:
            raise RuntimeError("publication interruption")

        monkeypatch.setattr(world._messages, "publish", fail)
        with pytest.raises(RuntimeError, match="publication interruption"):
            send(world, bot["id"], chat["id"])
        assert list(world._connection.iterdump()) == before
