from pathlib import Path
from typing import Any

import pytest

from gramlab.world import World


def world_with_contacts(
    path: Path,
) -> tuple[World, dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    world = World.create(path, seed=3, now=100)
    recipient = world.create_user(first_name="Sara", language_code="fa")
    bot = world.create_user(first_name="Echo", is_bot=True, username="echo_bot")
    referenced = world.create_user(first_name="Mina", username="mina")
    hidden = world.create_user(first_name="Hidden")
    chat = world.open_private_chat(user_id=recipient["id"], bot_id=bot["id"])
    world.open_private_chat(user_id=referenced["id"], bot_id=bot["id"])
    return world, recipient, bot, referenced, hidden, chat


def rich(user: object, text: str = "برنده Winner") -> dict[str, Any]:
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
def test_invalid_or_inaccessible_mentions_are_atomic(tmp_path: Path, identifier: object) -> None:
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


@pytest.mark.parametrize("user", [None, {}, {"id": 999}])
def test_missing_nonobject_and_unknown_users_reject(tmp_path: Path, user: object) -> None:
    world, _recipient, bot, _referenced, _hidden, chat = world_with_contacts(tmp_path / "world")
    try:
        with pytest.raises(ValueError):
            world.send_rich_message(
                chat_id=chat["id"], sender_id=bot["id"], rich_message=rich(user)
            )
        assert world.history(chat["id"]) == []
    finally:
        world.__exit__(None, None, None)


def test_user_known_only_to_another_bot_rejects(tmp_path: Path) -> None:
    world, _recipient, bot, _referenced, hidden, chat = world_with_contacts(tmp_path / "world")
    try:
        other_bot = world.create_user(first_name="Other bot", is_bot=True)
        world.open_private_chat(user_id=hidden["id"], bot_id=other_bot["id"])
        before = world.snapshot()
        with pytest.raises(ValueError, match="unavailable"):
            world.send_rich_message(
                chat_id=chat["id"], sender_id=bot["id"], rich_message=rich(hidden)
            )
        assert world.snapshot() == before and world.history(chat["id"]) == []
    finally:
        world.__exit__(None, None, None)


def test_rejected_edit_preserves_complete_state_and_next_identifiers(tmp_path: Path) -> None:
    world, recipient, bot, referenced, hidden, chat = world_with_contacts(tmp_path / "world")
    try:
        first = world.send_rich_message(
            chat_id=chat["id"], sender_id=bot["id"], rich_message=rich(referenced)
        )
        before_snapshot = world.client_snapshot(recipient["id"], version=3)
        before = {
            "history": world.history(chat["id"]),
            "events": world.events(),
            "updates": world.poll_updates(bot["id"]),
            "snapshot": before_snapshot,
        }
        before_cursor = before_snapshot["cursor"]
        assert isinstance(before_cursor, int)
        with pytest.raises(ValueError, match="unavailable"):
            world.edit_message(
                chat_id=chat["id"],
                message_id=first["id"],
                bot_id=bot["id"],
                rich_message=rich(hidden),
            )
        after = {
            "history": world.history(chat["id"]),
            "events": world.events(),
            "updates": world.poll_updates(bot["id"]),
            "snapshot": world.client_snapshot(recipient["id"], version=3),
        }
        assert after == before
        second = world.send_rich_message(
            chat_id=chat["id"], sender_id=bot["id"], rich_message=rich(referenced, "next")
        )
        assert second["id"] == 2
        assert world.client_snapshot(recipient["id"], version=3)["message_revisions"][-1] == {
            "chat_id": chat["id"],
            "message_id": 2,
            "revision": before_cursor + 1,
        }
    finally:
        world.__exit__(None, None, None)


def test_nested_duplicate_mentions_deduplicate_dependencies_and_share_budgets(
    tmp_path: Path,
) -> None:
    world, recipient, bot, referenced, _hidden, chat = world_with_contacts(tmp_path / "world")
    try:
        other = world.create_user(first_name="Zara")
        world.open_private_chat(user_id=other["id"], bot_id=bot["id"])

        def mention(user: dict[str, Any], label: str) -> dict[str, Any]:
            return {
                "type": "text_mention",
                "text": label,
                "user": {"id": user["id"], "first_name": "x" * 1000, "future": [1, 2, 3]},
            }

        content = {
            "skip_entity_detection": True,
            "blocks": [
                {
                    "type": "table",
                    "caption": mention(referenced, "caption"),
                    "cells": [[{"text": [mention(other, "cell"), mention(referenced, "again")]}]],
                },
                {
                    "type": "list",
                    "items": [{"blocks": [{"type": "paragraph", "text": mention(other, "list")}]}],
                },
            ],
        }
        world.send_rich_message(chat_id=chat["id"], sender_id=bot["id"], rich_message=content)
        users = world.client_snapshot(recipient["id"], version=3)["users"]
        assert [entry["id"] for entry in users] == sorted(
            {recipient["id"], bot["id"], referenced["id"], other["id"]}
        )
        oversized = rich({"id": referenced["id"], "claim": "x" * 66_000})
        before = world.events()
        with pytest.raises(ValueError, match="byte limit"):
            world.send_rich_message(chat_id=chat["id"], sender_id=bot["id"], rich_message=oversized)
        assert world.events() == before
        claim: object = "leaf"
        for _ in range(34):
            claim = [claim]
        with pytest.raises(ValueError, match="nesting"):
            world.send_rich_message(
                chat_id=chat["id"],
                sender_id=bot["id"],
                rich_message=rich({"id": referenced["id"], "future": claim}),
            )
        assert world.events() == before
    finally:
        world.__exit__(None, None, None)
