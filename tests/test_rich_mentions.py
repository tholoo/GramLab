from pathlib import Path

import pytest

from gramlab.world import World


def world_with_contacts(path: Path):
    world = World.create(path, seed=3, now=100)
    recipient = world.create_user(first_name="Sara", language_code="fa")
    bot = world.create_user(first_name="Echo", is_bot=True, username="echo_bot")
    referenced = world.create_user(first_name="Mina", username="mina")
    hidden = world.create_user(first_name="Hidden")
    chat = world.open_private_chat(user_id=recipient["id"], bot_id=bot["id"])
    world.open_private_chat(user_id=referenced["id"], bot_id=bot["id"])
    return world, recipient, bot, referenced, hidden, chat


def rich(user: dict, text="برنده Winner") -> dict:
    return {
        "skip_entity_detection": True,
        "blocks": [
            {
                "type": "paragraph",
                "text": {
                    "type": "text_mention",
                    "text": {"type": "bold", "text": text},
                    "user": user,
                },
            }
        ],
    }


def test_world_stores_only_admitted_id_and_round_trips_after_restart(tmp_path: Path) -> None:
    directory = tmp_path / "world"
    world, recipient, bot, referenced, _hidden, chat = world_with_contacts(directory)
    message = world.send_rich_message(
        chat_id=chat["id"],
        sender_id=bot["id"],
        rich_message=rich({"id": referenced["id"], "first_name": "forged", "is_bot": True}),
    )
    canonical = {
        "blocks": [
            {
                "type": "paragraph",
                "text": {
                    "type": "text_mention",
                    "text": {"type": "bold", "text": "برنده Winner"},
                    "user_id": referenced["id"],
                },
            }
        ]
    }
    assert message["rich_message"] == canonical
    assert world.history(chat["id"])[0]["rich_message"] == canonical
    world.__exit__(None, None, None)
    with World.open(directory) as reopened:
        assert reopened.history(chat["id"])[0]["rich_message"] == canonical
        assert reopened.client_snapshot(recipient["id"], version=3)["users"][-1] == referenced


@pytest.mark.parametrize("identifier", [True, 1.0, None, 0, -1, 2**63])
def test_invalid_or_inaccessible_mentions_are_atomic(tmp_path: Path, identifier) -> None:
    world, _recipient, bot, _referenced, hidden, chat = world_with_contacts(tmp_path / "world")
    before = world.events()
    user = {"id": hidden["id"]} if identifier is None else {"id": identifier}
    with pytest.raises(ValueError):
        world.send_rich_message(chat_id=chat["id"], sender_id=bot["id"], rich_message=rich(user))
    assert world.events() == before and world.history(chat["id"]) == []
    sent = world.send_rich_message(
        chat_id=chat["id"], sender_id=bot["id"], rich_message=rich({"id": bot["id"]})
    )
    assert (sent["id"], sent["rich_message"]["blocks"][0]["text"]["user_id"]) == (1, bot["id"])
    world.__exit__(None, None, None)


def test_returned_user_noop_and_edit_remove_preserve_identity_rules(tmp_path: Path) -> None:
    world, recipient, bot, referenced, _hidden, chat = world_with_contacts(tmp_path / "world")
    sent = world.send_rich_message(
        chat_id=chat["id"], sender_id=bot["id"], rich_message=rich(referenced)
    )
    before = (world.events(), world.client_snapshot(recipient["id"], version=3))
    with pytest.raises(ValueError, match="MESSAGE_NOT_MODIFIED"):
        world.edit_message(
            chat_id=chat["id"],
            message_id=sent["id"],
            bot_id=bot["id"],
            rich_message=rich(referenced),
        )
    assert (world.events(), world.client_snapshot(recipient["id"], version=3)) == before
    world.edit_message(
        chat_id=chat["id"],
        message_id=sent["id"],
        bot_id=bot["id"],
        rich_message={
            "skip_entity_detection": True,
            "blocks": [{"type": "paragraph", "text": "plain"}],
        },
    )
    assert [user["id"] for user in world.client_snapshot(recipient["id"], version=3)["users"]] == [
        recipient["id"],
        bot["id"],
    ]
    world.__exit__(None, None, None)
