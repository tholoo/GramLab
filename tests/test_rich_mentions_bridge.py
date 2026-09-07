from pathlib import Path

import pytest
from test_rich_mentions import rich, world_with_contacts


def test_v3_dependencies_follow_exact_versions_and_frozen_callback(tmp_path: Path) -> None:
    world, recipient, bot, referenced, _hidden, chat = world_with_contacts(tmp_path / "world")
    message = world.send_rich_message(
        chat_id=chat["id"],
        sender_id=bot["id"],
        rich_message=rich(referenced),
        reply_markup={"inline_keyboard": [[{"text": "Tap", "callback_data": "x"}]]},
    )
    callback = world.create_callback(
        user_id=recipient["id"],
        chat_id=chat["id"],
        message_id=message["id"],
        data="x",
        request_id="mention",
        version=3,
    )
    world.edit_message(
        chat_id=chat["id"],
        message_id=message["id"],
        bot_id=bot["id"],
        rich_message={
            "skip_entity_detection": True,
            "blocks": [{"type": "paragraph", "text": "removed"}],
        },
    )
    base_ids = [recipient["id"], bot["id"]]
    assert [
        user["id"] for user in world.client_snapshot(recipient["id"], version=3)["users"]
    ] == base_ids
    first = world.client_changes(recipient["id"], after=0, limit=1, version=3)
    assert [user["id"] for user in first["users"]] == [*base_ids, referenced["id"]]
    second = world.client_changes(recipient["id"], after=1, version=3)
    assert [user["id"] for user in second["users"]] == base_ids
    assert [
        user["id"] for user in world.callback_dependencies(recipient["id"], callback)["users"]
    ] == [*base_ids, referenced["id"]]
    with pytest.raises(ValueError, match="rich mentions"):
        world.client_changes(recipient["id"], after=0, limit=1, version=2)
    before = world.events()
    with pytest.raises(ValueError, match="rich mentions"):
        world.create_callback(
            user_id=recipient["id"],
            chat_id=chat["id"],
            message_id=message["id"],
            data="x",
            request_id="mention",
            version=1,
        )
    assert world.events() == before
    world.__exit__(None, None, None)


def test_two_recipients_derive_different_identity_envelopes(tmp_path: Path) -> None:
    world, recipient, bot, referenced, _hidden, chat = world_with_contacts(tmp_path / "world")
    other = world.create_user(first_name="Other")
    other_chat = world.open_private_chat(user_id=other["id"], bot_id=bot["id"])
    world.send_rich_message(chat_id=chat["id"], sender_id=bot["id"], rich_message=rich(referenced))
    world.send_rich_message(
        chat_id=other_chat["id"],
        sender_id=bot["id"],
        rich_message={
            "skip_entity_detection": True,
            "blocks": [{"type": "paragraph", "text": "ordinary"}],
        },
    )
    assert referenced["id"] in {
        entry["id"] for entry in world.client_snapshot(recipient["id"], version=3)["users"]
    }
    assert referenced["id"] not in {
        entry["id"] for entry in world.client_snapshot(other["id"], version=3)["users"]
    }
    world.__exit__(None, None, None)
