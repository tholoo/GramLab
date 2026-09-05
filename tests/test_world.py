"""Behavior at the approved persistent-world boundary."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

import pytest

from gramlab.world import World


def test_virtual_conversation_survives_restart_without_leaking_to_another_world(
    tmp_path: Path,
) -> None:
    expected = {
        "schema": 1,
        "seed": 17,
        "now": 1700000000,
        "users": [
            {"id": 1, "is_bot": False, "first_name": "سارا", "language_code": "fa"},
            {"id": 2, "is_bot": True, "first_name": "Echo", "username": "gramlab_echo_bot"},
        ],
        "chats": [{"id": 1, "type": "private", "user_id": 1, "bot_id": 2}],
    }
    with World.create(tmp_path / "first", seed=17, now=1700000000) as first:
        user = first.create_user(first_name="سارا", language_code="fa")
        bot = first.create_user(first_name="Echo", username="gramlab_echo_bot", is_bot=True)
        first.open_private_chat(user_id=user["id"], bot_id=bot["id"])
        assert first.snapshot() == expected
    with World.open(tmp_path / "first") as restarted:
        assert restarted.snapshot() == expected
        with World.create(tmp_path / "second", seed=17, now=1700000000) as independent:
            assert independent.snapshot() == {
                "schema": 1,
                "seed": 17,
                "now": 1700000000,
                "users": [],
                "chats": [],
            }
            independent.create_user(first_name="Other")
            assert restarted.snapshot() == expected


def test_rejected_identity_and_chat_changes_leave_the_world_unchanged(tmp_path: Path) -> None:
    with World.create(tmp_path / "world", seed=4, now=100) as world:
        user = world.create_user(first_name="Alice")
        bot = world.create_user(first_name="Echo", is_bot=True)
        before = world.snapshot()
        for user_id, bot_id in [(1, 999), (999, 2), (2, 1), (1, 1), (True, 2)]:
            with pytest.raises(ValueError):
                world.open_private_chat(user_id=user_id, bot_id=bot_id)
            assert world.snapshot() == before
        with pytest.raises(ValueError):
            world.create_user(first_name="")
        assert world.snapshot() == before
        chat = world.open_private_chat(user_id=user["id"], bot_id=bot["id"])
        assert world.open_private_chat(user_id=user["id"], bot_id=bot["id"]) == chat
        assert world.snapshot()["chats"] == [chat]


def test_world_clock_is_explicit_persistent_and_cannot_move_backwards(tmp_path: Path) -> None:
    directory = tmp_path / "world"
    with World.create(directory, seed=9, now=1700000000) as world:
        assert world.advance_time(30) == 1700000030
        before = world.snapshot()
        for seconds in (-1, True, 0.5):
            with pytest.raises(ValueError):
                world.advance_time(seconds)
        with pytest.raises(FileExistsError):
            World.create(directory, seed=999, now=0)
        assert world.snapshot() == before
    with World.open(directory) as reopened:
        assert reopened.snapshot()["now"] == 1700000030
        assert reopened.snapshot()["seed"] == 9


def test_messages_and_bot_delivery_commit_together_and_recover_after_restart(
    tmp_path: Path,
) -> None:
    directory = tmp_path / "world"
    with World.create(directory, seed=7, now=1700000000) as world:
        world.create_user(first_name="Alice")
        world.create_user(first_name="Echo", is_bot=True)
        world.open_private_chat(user_id=1, bot_id=2)
        assert world.send_message(chat_id=1, sender_id=1, text="/start") == {
            "id": 1,
            "chat_id": 1,
            "sender_id": 1,
            "date": 1700000000,
            "text": "/start",
        }
    expected_update = {
        "update_id": 1,
        "message": {"id": 1, "chat_id": 1, "sender_id": 1, "date": 1700000000, "text": "/start"},
    }
    with World.open(directory) as world:
        assert world.poll_updates(2) == [expected_update]
        assert world.poll_updates(2) == [expected_update]
        assert world.poll_updates(2, offset=2) == []
        world.advance_time(5)
        reply = world.send_message(chat_id=1, sender_id=2, text="Hello, Alice!")
        assert reply == {
            "id": 2,
            "chat_id": 1,
            "sender_id": 2,
            "date": 1700000005,
            "text": "Hello, Alice!",
        }
        assert world.poll_updates(2) == []
        assert world.history(1) == [expected_update["message"], reply]
        assert world.events(after=4) == [
            {"sequence": 5, "type": "clock.advanced", "data": {"now": 1700000005}},
            {"sequence": 6, "type": "message.created", "data": reply},
        ]
    with World.open(directory) as restarted:
        assert restarted.poll_updates(2) == []
        assert restarted.history(1) == [expected_update["message"], reply]


def test_failed_message_leaves_no_history_event_or_bot_update(tmp_path: Path) -> None:
    with World.create(tmp_path / "world", seed=7, now=100) as world:
        world.create_user(first_name="Alice")
        world.create_user(first_name="Echo", is_bot=True)
        world.create_user(first_name="Other")
        world.open_private_chat(user_id=1, bot_id=2)
        before = world.events()
        for sender, text in [(3, "wrong actor"), (1, ""), (1, "x" * 4097), (1, "\ud800")]:
            with pytest.raises(ValueError):
                world.send_message(chat_id=1, sender_id=sender, text=text)
            assert world.history(1) == []
            assert world.events() == before
            assert world.poll_updates(2) == []
        assert world.send_message(chat_id=1, sender_id=1, text="hello")["id"] == 1
        assert world.poll_updates(2)[0]["update_id"] == 1


def test_concurrent_senders_publish_unique_ordered_messages_and_bot_updates(tmp_path: Path) -> None:
    directory = tmp_path / "world"
    with World.create(directory, seed=7, now=100) as world:
        world.create_user(first_name="Alice")
        world.create_user(first_name="Echo", is_bot=True)
        world.open_private_chat(user_id=1, bot_id=2)
    barrier = Barrier(4)

    def send(worker):
        with World.open(directory) as world:
            for step in range(10):
                barrier.wait(timeout=5)
                world.send_message(chat_id=1, sender_id=1, text=f"{worker}:{step}")

    with ThreadPoolExecutor(max_workers=4) as workers:
        list(workers.map(send, range(4)))
    with World.open(directory) as world:
        messages = world.history(1)
        assert [m["id"] for m in messages] == list(range(1, 41))
        assert {m["text"] for m in messages} == {f"{w}:{s}" for w in range(4) for s in range(10)}
        updates = world.poll_updates(2)
        assert [u["update_id"] for u in updates] == list(range(1, 41))
        assert [u["message"] for u in updates] == messages
        events = world.events(after=3)
        assert [e["sequence"] for e in events] == list(range(4, 44))
        assert [e["data"] for e in events] == messages


def test_polling_one_bot_cannot_read_or_acknowledge_another_bots_updates(tmp_path: Path) -> None:
    with World.create(tmp_path / "world", seed=7, now=100) as world:
        world.create_user(first_name="Alice")
        world.create_user(first_name="First bot", is_bot=True)
        world.create_user(first_name="Second bot", is_bot=True)
        world.open_private_chat(user_id=1, bot_id=2)
        world.open_private_chat(user_id=1, bot_id=3)
        first = world.send_message(chat_id=1, sender_id=1, text="first")
        second = world.send_message(chat_id=2, sender_id=1, text="second")
        assert world.poll_updates(2) == [{"update_id": 1, "message": first}]
        assert world.poll_updates(2, offset=2) == []
        assert world.poll_updates(3) == [{"update_id": 1, "message": second}]
        assert world.poll_updates(3, offset=2) == []
        third = world.send_message(chat_id=2, sender_id=1, text="third")
        assert world.poll_updates(3) == [{"update_id": 2, "message": third}]


def test_invalid_poll_options_cannot_acknowledge_pending_delivery(tmp_path: Path) -> None:
    with World.create(tmp_path / "world", seed=7, now=100) as world:
        world.create_user(first_name="Alice")
        world.create_user(first_name="Echo", is_bot=True)
        world.open_private_chat(user_id=1, bot_id=2)
        message = world.send_message(chat_id=1, sender_id=1, text="pending")
        for offset, limit in [(2, 0), (2, 101), (2, True), (-1, 100), (True, 100), (2**63, 100)]:
            with pytest.raises(ValueError):
                world.poll_updates(2, offset=offset, limit=limit)
            assert world.poll_updates(2) == [{"update_id": 1, "message": message}]
