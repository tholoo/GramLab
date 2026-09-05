"""Persona-scoped snapshots at the approved semantic client boundary."""

import http.client
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from urllib.parse import urlsplit

import pytest

from gramlab.world import World


def test_client_snapshot_contains_only_the_personas_conversation_at_one_cursor(
    tmp_path: Path,
) -> None:
    directory = tmp_path / "world"
    with World.create(directory, seed=7, now=100) as world:
        world.create_user(first_name="Alice")
        world.create_user(first_name="Echo", is_bot=True)
        world.create_user(first_name="Bob")
        world.open_private_chat(user_id=1, bot_id=2)
        world.open_private_chat(user_id=3, bot_id=2)
        world.send_message(chat_id=1, sender_id=2, text="For Alice")
        world.send_message(chat_id=2, sender_id=2, text="For Bob")
        snapshot = world.client_snapshot(1)
        world_id = snapshot.pop("world_id")
        assert snapshot == {
            "schema": 1,
            "user_id": 1,
            "cursor": 7,
            "now": 100,
            "users": [
                {"id": 1, "is_bot": False, "first_name": "Alice"},
                {"id": 2, "is_bot": True, "first_name": "Echo"},
            ],
            "chats": [{"id": 1, "type": "private", "user_id": 1, "bot_id": 2}],
            "messages": [{"id": 1, "chat_id": 1, "sender_id": 2, "date": 100, "text": "For Alice"}],
        }
    with World.open(directory) as reopened:
        assert reopened.client_snapshot(1)["world_id"] == world_id
    with World.create(tmp_path / "other", seed=7, now=100) as other:
        other.create_user(first_name="Alice")
        assert other.client_snapshot(1)["world_id"] != world_id


def test_previous_world_format_preserves_pending_delivery_when_adding_client_identity(
    tmp_path: Path,
) -> None:
    directory = tmp_path / "legacy"
    directory.mkdir()
    # Construct the committed prior storage format; observe migration only through World.
    connection = sqlite3.connect(directory / "world.sqlite3")
    try:
        connection.executescript(Path("tests/fixtures/world-v1.sql").read_text())
    finally:
        connection.close()
    expected = {"id": 1, "chat_id": 1, "sender_id": 1, "date": 100, "text": "before upgrade"}
    with World.open(directory) as world:
        snapshot = world.client_snapshot(1)
        assert snapshot["messages"] == [expected]
        assert snapshot["cursor"] == 4
        assert world.poll_updates(2) == [{"update_id": 1, "message": expected}]
    with World.open(directory) as reopened:
        assert reopened.client_snapshot(1) == snapshot
        assert reopened.poll_updates(2) == [{"update_id": 1, "message": expected}]


def test_client_cursor_advances_over_hidden_events_without_revealing_them(tmp_path: Path) -> None:
    with World.create(tmp_path / "world", seed=7, now=100) as world:
        world.create_user(first_name="Alice")
        world.create_user(first_name="Echo", is_bot=True)
        world.create_user(first_name="Bob")
        world.open_private_chat(user_id=1, bot_id=2)
        world.open_private_chat(user_id=3, bot_id=2)
        snapshot = world.client_snapshot(1)
        alice = world.send_message(chat_id=1, sender_id=2, text="Alice only")
        world.send_message(chat_id=2, sender_id=2, text="Bob only")
        world.advance_time(5)
        assert world.client_events(1, after=5, limit=2) == {
            "schema": 1,
            "world_id": snapshot["world_id"],
            "user_id": 1,
            "cursor": 7,
            "head": 8,
            "events": [{"sequence": 6, "type": "message.created", "data": alice}],
        }
        assert world.client_events(1, after=7) == {
            "schema": 1,
            "world_id": snapshot["world_id"],
            "user_id": 1,
            "cursor": 8,
            "head": 8,
            "events": [{"sequence": 8, "type": "clock.advanced", "data": {"now": 105}}],
        }
        for cursor in (-1, 9, True):
            with pytest.raises(ValueError):
                world.client_events(1, after=cursor)
        with pytest.raises(ValueError):
            world.client_snapshot(2)


def test_http_bridge_authenticates_the_persona_and_rejects_bot_capabilities(tmp_path: Path) -> None:
    from gramlab.client_bridge import ClientBridge

    directory = tmp_path / "world"
    with World.create(directory, seed=7, now=100) as world:
        world.create_user(first_name="Alice")
        world.create_user(first_name="Echo", is_bot=True)
        world.create_user(first_name="Bob")
        world.open_private_chat(user_id=1, bot_id=2)
        world.open_private_chat(user_id=3, bot_id=2)
        world.send_message(chat_id=1, sender_id=2, text="Alice only")
        world.send_message(chat_id=2, sender_id=2, text="Bob only")
        alice_token = world.issue_client_token(1)
        bob_token = world.issue_client_token(3)
        bot_token = world.issue_bot_token(2)
        with pytest.raises(ValueError):
            world.issue_client_token(2)
    with World.create(tmp_path / "other", seed=7, now=100) as other:
        other.create_user(first_name="Alice")
        other_token = other.issue_client_token(1)

    def request(server, token, path):
        import json

        url = urlsplit(server.base_url)
        connection = http.client.HTTPConnection("127.0.0.1", url.port, timeout=5)
        try:
            connection.request("GET", path, headers={"Authorization": "Bearer " + token})
            response = connection.getresponse()
            return response.status, json.loads(response.read())
        finally:
            connection.close()

    with ClientBridge(directory) as server:
        for token, persona, text in [(alice_token, 1, "Alice only"), (bob_token, 3, "Bob only")]:
            status, snapshot = request(server, token, "/v1/snapshot")
            assert status == 200
            assert snapshot["user_id"] == persona
            assert [message["text"] for message in snapshot["messages"]] == [text]
            assert request(server, token, "/v1/events?after=7")[1]["events"] == []
        for token in (bot_token, other_token, "invalid"):
            assert request(server, token, "/v1/snapshot") == (
                401,
                {
                    "schema": 1,
                    "error": {"code": "unauthorized", "message": "Client capability required"},
                },
            )
        assert request(server, alice_token, "/v1/snapshot?user_id=3")[0] == 400
        assert request(server, alice_token, "/v1/events?after=999")[0] == 400
        for path in (
            "/v1/events",
            "/v1/events?after=0&after=1",
            "/v1/events?after=bad",
            "/v1/events?after=0&limit=0",
        ):
            assert request(server, alice_token, path)[0] == 400
        assert request(server, alice_token, "/v1/unknown")[0] == 404

    # The endpoint can stop and restart without replacing its world or capabilities.
    with ClientBridge(directory) as restarted:
        assert request(restarted, alice_token, "/v1/snapshot")[0] == 200


def test_snapshot_cursor_and_messages_stay_consistent_with_a_concurrent_writer(
    tmp_path: Path,
) -> None:
    directory = tmp_path / "world"
    with World.create(directory, seed=7, now=100) as world:
        world.create_user(first_name="Alice")
        world.create_user(first_name="Echo", is_bot=True)
        world.open_private_chat(user_id=1, bot_id=2)
    phase = Barrier(2)

    def write():
        with World.open(directory) as world:
            for number in range(30):
                phase.wait(timeout=5)
                world.send_message(chat_id=1, sender_id=2, text=str(number))
                phase.wait(timeout=5)

    with ThreadPoolExecutor(max_workers=1) as executor, World.open(directory) as reader:
        writer = executor.submit(write)
        for _ in range(30):
            phase.wait(timeout=5)
            snapshot = reader.client_snapshot(1)
            assert snapshot["cursor"] == 3 + len(snapshot["messages"])
            assert [m["id"] for m in snapshot["messages"]] == list(
                range(1, len(snapshot["messages"]) + 1)
            )
            phase.wait(timeout=5)
        writer.result(timeout=5)
        assert len(reader.client_snapshot(1)["messages"]) == 30
