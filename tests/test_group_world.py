"""Behavior at the public World seam for synthetic group conversations."""

import sqlite3
from pathlib import Path

import pytest

from gramlab.world import World


def test_v10_world_migrates_existing_client_journal_before_group_delivery(tmp_path: Path) -> None:
    directory = tmp_path / "world"
    with World.create(directory, seed=30, now=1_700_000_000) as world:
        owner = world.create_user(first_name="Mina")
        bot = world.create_user(first_name="Helper", is_bot=True)
        private = world.open_private_chat(user_id=owner["id"], bot_id=bot["id"])
        existing = world.send_message(chat_id=private["id"], sender_id=bot["id"], text="Existing")
    with sqlite3.connect(directory / "world.sqlite3") as connection:
        connection.execute("PRAGMA foreign_keys=OFF")
        connection.execute("DROP TABLE chat_members")
        connection.execute("DROP TABLE group_chats")
        connection.execute(
            "CREATE TEMP TABLE client_changes_copy AS "
            "SELECT user_id, position, event_sequence FROM client_changes"
        )
        connection.execute("DROP TABLE client_changes")
        connection.execute(
            "CREATE TABLE client_changes ("
            "user_id INTEGER NOT NULL REFERENCES users(id), position INTEGER NOT NULL, "
            "event_sequence INTEGER NOT NULL UNIQUE REFERENCES events(sequence), "
            "PRIMARY KEY(user_id, position))"
        )
        connection.execute(
            "INSERT INTO client_changes "
            "SELECT user_id, position, event_sequence FROM client_changes_copy"
        )
        connection.execute("DROP TABLE client_changes_copy")
        connection.execute("CREATE TEMP TABLE chats_copy AS SELECT id, user_id, bot_id FROM chats")
        connection.execute("DROP TABLE chats")
        connection.execute(
            "CREATE TABLE chats (id INTEGER PRIMARY KEY, "
            "user_id INTEGER NOT NULL REFERENCES users(id), "
            "bot_id INTEGER NOT NULL REFERENCES users(id), UNIQUE(user_id, bot_id))"
        )
        connection.execute("INSERT INTO chats SELECT id, user_id, bot_id FROM chats_copy")
        connection.execute("DROP TABLE chats_copy")
        connection.execute("PRAGMA user_version=10")

    with World.open(directory) as migrated:
        assert migrated.client_snapshot(owner["id"])["messages"] == [existing]
        member = migrated.create_user(first_name="Arman")
        group = migrated.create_group_chat(
            title="Study group",
            creator_id=owner["id"],
            member_ids=[member["id"]],
            bot_ids=[bot["id"]],
        )
        incoming = migrated.send_message(
            chat_id=group["id"], sender_id=member["id"], text="After migration"
        )
        assert migrated.client_changes(owner["id"], after=1)["changes"][0]["data"] == incoming
        assert migrated.client_changes(member["id"], after=0)["changes"][0]["data"] == incoming


def test_group_member_message_reaches_each_bot_and_survives_restart(tmp_path: Path) -> None:
    directory = tmp_path / "world"
    with World.create(directory, seed=31, now=1_700_000_000) as world:
        owner = world.create_user(first_name="Mina", username="mina")
        member = world.create_user(first_name="Arman", username="arman")
        first_bot = world.create_user(first_name="Helper", username="helper_bot", is_bot=True)
        second_bot = world.create_user(first_name="Logger", username="logger_bot", is_bot=True)

        group = world.create_group_chat(
            title="Study group",
            creator_id=owner["id"],
            member_ids=[member["id"]],
            bot_ids=[first_bot["id"], second_bot["id"]],
        )
        assert group == {
            "id": -1,
            "type": "supergroup",
            "title": "Study group",
            "members": [
                {"user_id": 1, "status": "creator"},
                {"user_id": 2, "status": "member"},
                {"user_id": 3, "status": "member"},
                {"user_id": 4, "status": "member"},
            ],
        }
        incoming = world.send_message(
            chat_id=group["id"],
            sender_id=member["id"],
            text="Can both bots see this?",
        )
        expected_update = {"update_id": 1, "message": incoming}
        assert world.poll_updates(first_bot["id"]) == [expected_update]
        assert world.poll_updates(second_bot["id"]) == [expected_update]
        assert world.get_chat_member(group["id"], owner["id"]) == {
            "user": owner,
            "status": "creator",
            "is_anonymous": False,
        }
        assert world.get_chat_member(group["id"], member["id"]) == {
            "user": member,
            "status": "member",
        }
        for user_id in (owner["id"], member["id"]):
            client = world.client_snapshot(user_id)
            assert client["chats"] == [group]
            assert client["messages"] == [incoming]
            assert client["users"] == [owner, member, first_bot, second_bot]

        before = world.snapshot()
        with pytest.raises(ValueError, match="Sender is not a member of this group"):
            outsider = world.create_user(first_name="Outsider")
            world.send_message(chat_id=group["id"], sender_id=outsider["id"], text="No access")
        assert world.history(group["id"]) == [incoming]

    with World.open(directory) as restarted:
        assert restarted.get_chat(group["id"]) == group
        assert restarted.snapshot() == before | {
            "users": [*before["users"], {"id": 5, "is_bot": False, "first_name": "Outsider"}]
        }
        assert restarted.poll_updates(first_bot["id"]) == [expected_update]
        assert restarted.poll_updates(second_bot["id"]) == [expected_update]
        assert restarted.history(group["id"]) == [incoming]


def test_group_member_client_send_is_idempotent_and_survives_restart(tmp_path: Path) -> None:
    directory = tmp_path / "world"
    with World.create(directory, seed=32, now=1_700_000_000) as world:
        owner = world.create_user(first_name="Mina")
        member = world.create_user(first_name="Arman")
        bot = world.create_user(first_name="Helper", is_bot=True)
        outsider = world.create_user(first_name="Outsider")
        group = world.create_group_chat(
            title="Study group",
            creator_id=owner["id"],
            member_ids=[member["id"]],
            bot_ids=[bot["id"]],
        )
        sent = world.send_client_message(
            user_id=member["id"],
            chat_id=group["id"],
            request_id="member-native-send",
            text="Sent from the group client",
            version=6,
        )
        assert sent["message"] == {
            "id": 1,
            "chat_id": -1,
            "sender_id": member["id"],
            "date": 1_700_000_000,
            "text": "Sent from the group client",
        }
        assert (
            world.send_client_message(
                user_id=member["id"],
                chat_id=group["id"],
                request_id="member-native-send",
                text="Sent from the group client",
                version=6,
            )
            == sent
        )
        for rejected_user in (bot["id"], outsider["id"]):
            with pytest.raises(ValueError, match="not available to this persona"):
                world.send_client_message(
                    user_id=rejected_user,
                    chat_id=group["id"],
                    request_id=f"rejected-{rejected_user}",
                    text="No",
                    version=6,
                )

    with World.open(directory) as restarted:
        assert (
            restarted.send_client_message(
                user_id=member["id"],
                chat_id=group["id"],
                request_id="member-native-send",
                text="Sent from the group client",
                version=6,
            )
            == sent
        )
        assert restarted.history(group["id"]) == [sent["message"]]


def test_group_creation_rejects_ambiguous_or_invalid_memberships(tmp_path: Path) -> None:
    with World.create(tmp_path / "world", seed=33, now=1_700_000_000) as world:
        owner = world.create_user(first_name="Mina")
        member = world.create_user(first_name="Arman")
        bot = world.create_user(first_name="Helper", is_bot=True)

        with pytest.raises(ValueError, match="at least one bot"):
            world.create_group_chat(
                title="Study group",
                creator_id=owner["id"],
                member_ids=[member["id"]],
                bot_ids=[],
            )
        with pytest.raises(ValueError, match="must not repeat"):
            world.create_group_chat(
                title="Study group",
                creator_id=owner["id"],
                member_ids=[owner["id"]],
                bot_ids=[bot["id"]],
            )
        with pytest.raises(ValueError, match="must not be bots"):
            world.create_group_chat(
                title="Study group",
                creator_id=owner["id"],
                member_ids=[bot["id"]],
                bot_ids=[member["id"]],
            )
        with pytest.raises(ValueError, match="Unknown virtual user"):
            world.create_group_chat(
                title="Study group",
                creator_id=owner["id"],
                member_ids=[999],
                bot_ids=[bot["id"]],
            )
        with pytest.raises(ValueError, match="1 to 255"):
            world.create_group_chat(
                title="   ",
                creator_id=owner["id"],
                member_ids=[member["id"]],
                bot_ids=[bot["id"]],
            )

        assert world.snapshot()["chats"] == []


def test_group_member_callback_targets_the_group_bot_message(tmp_path: Path) -> None:
    with World.create(tmp_path / "world", seed=32, now=1_700_000_000) as world:
        owner = world.create_user(first_name="Mina")
        member = world.create_user(first_name="Arman")
        outsider = world.create_user(first_name="Nika")
        bot = world.create_user(first_name="Helper", is_bot=True)
        group = world.create_group_chat(
            title="Study group",
            creator_id=owner["id"],
            member_ids=[member["id"]],
            bot_ids=[bot["id"]],
        )
        message = world.send_message(
            chat_id=group["id"],
            sender_id=bot["id"],
            text="Choose",
            reply_markup={"inline_keyboard": [[{"text": "Continue", "callback_data": "continue"}]]},
        )

        callback = world.create_callback(
            user_id=member["id"],
            chat_id=group["id"],
            message_id=message["id"],
            data="continue",
            request_id="group-callback",
        )
        assert callback["user_id"] == member["id"]
        assert callback["chat_id"] == group["id"]
        assert callback["message"] == message
        assert callback["data"] == "continue"
        assert callback["answer"] is None
        assert world.poll_updates(bot["id"]) == [
            {
                "update_id": 1,
                "callback_query": {
                    key: callback[key]
                    for key in ("id", "user_id", "chat_id", "message", "data", "chat_instance")
                },
            }
        ]
        with pytest.raises(ValueError, match="Callback chat is not available to this persona"):
            world.create_callback(
                user_id=outsider["id"],
                chat_id=group["id"],
                message_id=message["id"],
                data="continue",
                request_id="outsider-callback",
            )


def test_group_messages_are_valid_complete_bridge_v6_snapshot_inputs(tmp_path: Path) -> None:
    with World.create(tmp_path / "world", seed=34, now=1_700_000_000) as world:
        owner = world.create_user(first_name="Mina")
        member = world.create_user(first_name="Arman")
        bot = world.create_user(first_name="Helper", is_bot=True)
        group = world.create_group_chat(
            title="Study group",
            creator_id=owner["id"],
            member_ids=[member["id"]],
            bot_ids=[bot["id"]],
        )
        expected = world.send_message(
            chat_id=group["id"], sender_id=bot["id"], text="Ready for the group"
        )

        snapshot = world.client_snapshot(member["id"], version=6)

        assert snapshot["chats"] == [group]
        assert snapshot["messages"] == [expected]
