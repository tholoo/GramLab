"""World ownership and journal revision guard actual rich callback transactions."""

import hashlib
from pathlib import Path
from typing import Any

import pytest

from gramlab.world import World


def content(data: str) -> dict[str, Any]:
    return {
        "blocks": [
            {"type": "buttons", "buttons": [{"text": "انتخاب / Pick", "callback_data": data}]}
        ]
    }


def test_rich_button_snapshot_keeps_owner_message_and_journal_revision(tmp_path: Path) -> None:
    with World.create(tmp_path / "world", seed=7, now=100) as world:
        user = world.create_user(first_name="Sara")
        bot = world.create_user(first_name="Bot", is_bot=True)
        chat = world.open_private_chat(user_id=user["id"], bot_id=bot["id"])
        world.send_rich_message(
            chat_id=chat["id"],
            sender_id=bot["id"],
            rich_message=content("a") | {"skip_entity_detection": True},
        )
        expected = {
            "chat": {"id": 1, "type": "private", "user_id": 1, "bot_id": 2},
            "message": {
                "id": 1,
                "chat_id": 1,
                "sender_id": 2,
                "date": 100,
                "text": "",
                "rich_message": content("a"),
            },
            "revision": 4,
        }
        assert world.rich_button_snapshot(user_id=1, chat_id=1, message_id=1) == expected
        outsider = world.create_user(first_name="Other")
        with pytest.raises(ValueError, match="access_denied"):
            world.rich_button_snapshot(user_id=outsider["id"], chat_id=1, message_id=1)
        assert world.rich_button_snapshot(user_id=1, chat_id=1, message_id=1) == expected
        assert world.events()[-1]["type"] == "user.created"


def test_rich_button_transaction_rejects_same_clock_aba_and_wrong_path(tmp_path: Path) -> None:
    with World.create(tmp_path / "world", seed=7, now=100) as world:
        world.create_user(first_name="Sara")
        world.create_user(first_name="Bot", is_bot=True)
        world.open_private_chat(user_id=1, bot_id=2)
        message = world.send_rich_message(
            chat_id=1, sender_id=2, rich_message=content("a") | {"skip_entity_detection": True}
        )
        for data in ("b", "a"):
            world.edit_message(
                chat_id=1,
                message_id=1,
                bot_id=2,
                rich_message=content(data) | {"skip_entity_detection": True},
            )
        before = world.events()
        selected = {"text": "انتخاب / Pick", "callback_data": "a"}
        with pytest.raises(ValueError, match="message_revision_changed"):
            with world.rich_button_transaction(
                user_id=1,
                chat_id=1,
                message_id=1,
                revision=4,
                path=["blocks", 0, "buttons", 0],
                button=selected,
            ):
                pytest.fail("A restored message body must not restore an old target")
        assert world.events() == before

        assert world.get_message(1, 1) == message | {"edit_date": 100}
        with pytest.raises(ValueError, match="target_unavailable"):
            with world.rich_button_transaction(
                user_id=1,
                chat_id=1,
                message_id=1,
                revision=6,
                path=["blocks", False, "buttons", 0],
                button=selected,
            ):
                pytest.fail("Boolean path indices must not alias numeric indices")
        assert world.events() == before


def test_rich_callback_effect_commits_or_rolls_back_with_its_validated_target(
    tmp_path: Path,
) -> None:
    with World.create(tmp_path / "world", seed=7, now=100) as world:
        world.create_user(first_name="Sara")
        world.create_user(first_name="Bot", is_bot=True)
        world.open_private_chat(user_id=1, bot_id=2)
        message = world.send_rich_message(
            chat_id=1,
            sender_id=2,
            rich_message=content("a") | {"skip_entity_detection": True},
        )
        before = world.events()
        target: dict[str, Any] = {
            "user_id": 1,
            "chat_id": 1,
            "message_id": 1,
            "revision": 4,
            "path": ["blocks", 0, "buttons", 0],
            "button": {"text": "انتخاب / Pick", "callback_data": "a"},
        }
        with pytest.raises(RuntimeError, match="interrupted"):
            with world.rich_button_transaction(**target):
                world._create_callback_locked(
                    user_id=1, chat_id=1, message_id=1, data="a", request_id="once", version=4
                )
                raise RuntimeError("interrupted before transaction commit")
        assert world.events() == before
        assert world.poll_updates(2) == []
        with world.rich_button_transaction(**target) as selected:
            assert selected == {
                "chat": {"id": 1, "type": "private", "user_id": 1, "bot_id": 2},
                "message": message,
                "revision": 4,
            }
            callback = world._create_callback_locked(
                user_id=1, chat_id=1, message_id=1, data="a", request_id="once", version=4
            )
        expected = {
            "id": callback["id"],
            "user_id": 1,
            "chat_id": 1,
            "message": {
                "id": 1,
                "chat_id": 1,
                "sender_id": 2,
                "date": 100,
                "text": "",
                "rich_message": content("a"),
            },
            "data": "a",
            "chat_instance": hashlib.sha256(f"{world.world_id}:1".encode()).hexdigest(),
        }
        assert callback == expected | {"answer": None}
        assert world.poll_updates(2) == [{"update_id": 1, "callback_query": expected}]
        assert world.events(after=4) == [
            {"sequence": 5, "type": "callback.created", "data": expected}
        ]
        assert (
            world.create_callback(
                user_id=1, chat_id=1, message_id=1, data="a", request_id="once", version=4
            )
            == callback
        )
