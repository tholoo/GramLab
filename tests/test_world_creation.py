"""Fresh simulated-world initialization is atomic at the public storage boundary."""

import sqlite3
from contextlib import closing
from pathlib import Path
from typing import cast

import pytest

from gramlab.world import World


def test_late_configuration_failure_publishes_no_schema_or_version(tmp_path: Path) -> None:
    directory = tmp_path / "world"

    with pytest.raises(sqlite3.ProgrammingError):
        World.create(directory, seed=cast(int, object()), now=1_700_000_000)

    database = directory / "world.sqlite3"
    assert database.is_file()
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute("PRAGMA journal_mode").fetchone() == ("wal",)
        assert connection.execute("PRAGMA user_version").fetchone() == (0,)
        assert (
            connection.execute(
                "SELECT name FROM sqlite_schema "
                "WHERE type IN ('table', 'index', 'trigger', 'view') "
                "AND name NOT LIKE 'sqlite_%' ORDER BY type, name"
            ).fetchall()
            == []
        )


_APPLICATION_TABLES = [
    "asset_grants",
    "assets",
    "bot_document_files",
    "bot_files",
    "bot_tokens",
    "bots",
    "callback_revisions",
    "callbacks",
    "chats",
    "client_changes",
    "client_sends",
    "client_tokens",
    "configuration",
    "custom_emoji",
    "custom_emoji_counter",
    "custom_emoji_grants",
    "custom_emoji_registrations",
    "document_grants",
    "documents",
    "events",
    "media_blobs",
    "media_group_counter",
    "media_group_members",
    "media_groups",
    "message_revisions",
    "messages",
    "updates",
    "users",
]


def test_fresh_schema_is_complete_and_supports_conversation_after_reopen(tmp_path: Path) -> None:
    directory = tmp_path / "world"
    with World.create(directory, seed=23, now=1_700_000_000) as world:
        assert world.snapshot() == {
            "schema": 1,
            "seed": 23,
            "now": 1_700_000_000,
            "users": [],
            "chats": [],
        }
        assert world.events() == []
        with closing(sqlite3.connect(directory / "world.sqlite3")) as independent:
            assert independent.execute("PRAGMA journal_mode").fetchone() == ("wal",)
            assert independent.execute("PRAGMA user_version").fetchone() == (10,)
            assert independent.execute("PRAGMA foreign_key_check").fetchall() == []
            assert independent.execute("PRAGMA integrity_check").fetchall() == [("ok",)]
            assert independent.execute(
                "SELECT name FROM sqlite_schema "
                "WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            ).fetchall() == [(name,) for name in _APPLICATION_TABLES]
            assert independent.execute(
                "SELECT singleton, next_id FROM custom_emoji_counter"
            ).fetchall() == [(1, 1)]
            assert independent.execute(
                "SELECT seed, now, length(world_id) > 0 FROM configuration"
            ).fetchone() == (23, 1_700_000_000, 1)

        user = world.create_user(first_name="Ada")
        bot = world.create_user(first_name="Echo", is_bot=True)
        chat = world.open_private_chat(user_id=user["id"], bot_id=bot["id"])
        message = world.send_message(
            chat_id=chat["id"], sender_id=user["id"], text="created atomically"
        )
        with World.open(directory) as independent_world:
            assert independent_world.history(chat["id"]) == [message]
            assert independent_world.poll_updates(bot["id"]) == [
                {"update_id": 1, "message": message}
            ]

    with World.open(directory) as reopened:
        assert reopened.history(chat["id"]) == [message]
        assert reopened.poll_updates(bot["id"]) == [{"update_id": 1, "message": message}]
