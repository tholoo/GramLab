from pathlib import Path
from typing import Any

import pytest

from gramlab.world import World

ASSETS = Path(__file__).parent / "assets" / "custom-emoji"
MAIN = (ASSETS / "emoji-static.webp").read_bytes()
THUMB = (ASSETS / "emoji-thumbnail.webp").read_bytes()


def setup(path: Path) -> tuple[World, dict[str, Any], dict[str, Any], dict[str, Any]]:
    world = World.create(path, seed=7, now=20)
    user = world.create_user(first_name="Ada")
    bot = world.create_user(first_name="Bot", is_bot=True)
    chat = world.open_private_chat(user_id=user["id"], bot_id=bot["id"])
    return world, user, bot, chat


def test_registration_publication_lookup_and_reopen(tmp_path: Path) -> None:
    directory = tmp_path / "world"
    with setup(directory)[0] as world:
        user = world.get_user(1)
        bot = world.get_user(2)
        chat = world.get_chat(1)
        descriptor = world.register_custom_emoji(
            request_id="chosen",
            main=MAIN,
            thumbnail=THUMB,
            fallback="🙂",
            custom_emoji_id=2**63 - 1,
        )
        assert descriptor["custom_emoji_id"] == str(2**63 - 1)
        assert (
            world.register_custom_emoji(
                request_id="chosen",
                main=MAIN,
                thumbnail=THUMB,
                fallback="🙂",
                custom_emoji_id=str(2**63 - 1),
            )
            == descriptor
        )
        allocated = world.register_custom_emoji(
            request_id="auto", main=MAIN, thumbnail=THUMB, fallback="x", needs_repainting=True
        )
        assert allocated["custom_emoji_id"] == "1"
        message = world.send_message(
            chat_id=chat["id"],
            sender_id=bot["id"],
            text="🙂",
            entities=[{"type": "custom_emoji", "offset": 0, "length": 2, "custom_emoji_id": "1"}],
        )
        assert message["entities"][0]["custom_emoji_id"] == "1"
        snapshot = world.client_snapshot(user["id"], version=4)
        assert snapshot["custom_emoji"] == [allocated]
        changes = world.client_changes(user["id"], after=0, version=4)
        assert changes["custom_emoji"] == [allocated]
        callback = world.create_callback(
            user_id=user["id"],
            chat_id=chat["id"],
            message_id=message["id"],
            data="tap",
            request_id="callback",
            version=4,
        )
        dependencies = world.callback_dependencies(user["id"], callback, version=4)
        assert dependencies["custom_emoji"] == [allocated]
        with pytest.raises(ValueError, match="v4"):
            world.client_snapshot(user["id"], version=3)
        documents, assets = world.granted_custom_emoji(user["id"], ["1", "1"])
        assert documents == [allocated]
        assert {asset["asset_id"] for asset in assets} == {
            allocated["main_asset_id"],
            allocated["thumbnail_asset_id"],
        }
    with World.open(directory) as reopened:
        assert reopened.custom_emoji_descriptor("1") == allocated


def test_unknown_reference_rolls_back_message_and_grants(tmp_path: Path) -> None:
    world, user, bot, chat = setup(tmp_path / "world")
    with world:
        before = world.events()
        with pytest.raises(ValueError, match="unavailable"):
            world.send_message(
                chat_id=chat["id"],
                sender_id=bot["id"],
                text="🙂",
                entities=[
                    {"type": "custom_emoji", "offset": 0, "length": 2, "custom_emoji_id": 99}
                ],
            )
        assert world.events() == before
        assert world.history(chat["id"]) == []
        with pytest.raises(LookupError):
            world.granted_custom_emoji(user["id"], ["99"])
