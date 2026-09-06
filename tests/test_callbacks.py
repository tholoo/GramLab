"""Callback actions, bot delivery and durable answers at the owned world/HTTP seams."""

import json
import os
import shutil
import signal
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from pathlib import Path
from threading import Barrier

import pytest
from test_bot_api import request

from gramlab.bot_api import BotAPIServer
from gramlab.runtime import RuntimeProfile, Sandbox
from gramlab.world import World


def test_concurrent_upgrade_preserves_world_identity_and_pending_bot_delivery(
    tmp_path: Path,
) -> None:
    directory = tmp_path / "legacy"
    directory.mkdir()
    connection = sqlite3.connect(directory / "world.sqlite3")
    try:
        connection.executescript(Path("tests/fixtures/world-v2.sql").read_text())
    finally:
        connection.close()
    barrier = Barrier(4)

    def open_and_retry(_: int):
        barrier.wait()
        with World.open(directory) as world:
            return world.world_id, world.create_callback(
                user_id=1,
                chat_id=1,
                message_id=2,
                data="legacy",
                request_id="legacy-tap",
            )

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(open_and_retry, range(4)))
    assert all(value == results[0] for value in results)
    assert results[0][0] == "11111111-2222-4333-8444-555555555555"
    with World.open(directory) as world:
        assert world.history(1) == [
            {"id": 1, "chat_id": 1, "sender_id": 1, "date": 100, "text": "before upgrade"},
            {"id": 2, "chat_id": 1, "sender_id": 2, "date": 100, "text": "Legacy bot reply"},
        ]
        updates = world.poll_updates(2)
        assert updates[0] == {"update_id": 1, "message": world.history(1)[0]}
        assert updates[1]["update_id"] == 2
        assert updates[1]["callback_query"]["id"] == results[0][1]["id"]
        assert len(updates) == 2


def test_real_bot_recovers_a_pending_callback_after_sigkill_and_edits_the_same_message(
    tmp_path: Path,
) -> None:
    profile = RuntimeProfile.load(Path(os.environ["GRAMLAB_RUNTIME_PROFILE"]))
    shutil.copytree(
        "src/gramlab", tmp_path / "gramlab", ignore=shutil.ignore_patterns("__pycache__")
    )
    component_profile = RuntimeProfile.load(Path(os.environ["GRAMLAB_RUNTIME_PROFILE"]))
    (tmp_path / "component-profile.json").write_text(json.dumps(asdict(component_profile)))
    shutil.copy2("tests/probes/component_bot.py", tmp_path / "component_bot.py")
    shutil.copy2("tests/fixtures/callback_bot.py", tmp_path / "callback_bot.py")
    shutil.copy2("tests/probes/callback_round_trip.py", tmp_path / "callback_round_trip.py")
    result = Sandbox(profile).supervise(
        [profile.python, "/work/callback_round_trip.py"], data=tmp_path, timeout=60
    )
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "bot" / "launch-count").read_text() == "2"
    observed = json.loads(result.stdout)
    (tmp_path / "callback-round-trip.json").write_text(result.stdout)
    assert observed["killed"] == -signal.SIGKILL
    assert observed["before"]["callback"]["answer"] is None
    query_id = observed["before"]["callback"]["id"]
    assert observed["after"] == observed["before"] | {
        "callback": observed["before"]["callback"]
        | {
            "answer": {"text": "انجام شد ✓", "show_alert": False, "cache_time": 0},
        }
    }
    assert observed["history"] == [
        {"id": 1, "chat_id": 1, "sender_id": 1, "date": 1700000000, "text": "سلام hello"},
        {
            "id": 2,
            "chat_id": 1,
            "sender_id": 2,
            "date": 1700000000,
            "edit_date": 1700000005,
            "text": "تأیید شد ✓",
        },
    ]
    assert observed["pending"] == []
    for phase in ("bot_before", "bot_after"):
        assert {"event": "callback_received", "id": query_id} in observed[phase]
    api = [record for record in observed["bot_after"] if "method" in record]
    assert [record["method"] for record in api] == [
        "getMe",
        "getUpdates",
        "editMessageText",
        "answerCallbackQuery",
        "getUpdates",
    ]
    assert api[2] == {
        "method": "editMessageText",
        "parameters": {
            "chat_id": 1,
            "message_id": 2,
            "text": "تأیید شد ✓",
            "reply_markup": {"inline_keyboard": []},
        },
        "response": {
            "ok": True,
            "result": {
                "message_id": 2,
                "from": {
                    "id": 2,
                    "is_bot": True,
                    "first_name": "Echo",
                    "username": "gramlab_echo_bot",
                },
                "chat": {"id": 1, "type": "private", "first_name": "Sara"},
                "date": 1700000000,
                "edit_date": 1700000005,
                "text": "تأیید شد ✓",
            },
        },
    }
    assert api[3] == {
        "method": "answerCallbackQuery",
        "parameters": {
            "callback_query_id": query_id,
            "text": "انجام شد ✓",
        },
        "response": {"ok": True, "result": True},
    }


def test_callback_retries_share_one_durable_query_and_only_its_bot_can_answer(
    tmp_path: Path,
) -> None:
    directory = tmp_path / "world"
    keyboard = {"inline_keyboard": [[{"text": "تأیید", "callback_data": "confirm"}]]}
    with World.create(directory, seed=7, now=100) as world:
        world.create_user(first_name="Alice")
        world.create_user(first_name="Echo", is_bot=True)
        world.create_user(first_name="Bob")
        world.create_user(first_name="Other bot", is_bot=True)
        world.open_private_chat(user_id=1, bot_id=2)
        token, other_token = world.issue_bot_token(2), world.issue_bot_token(4)
        world.send_message(chat_id=1, sender_id=2, text="Choose", reply_markup=keyboard)
        query = world.create_callback(
            user_id=1, chat_id=1, message_id=1, data="confirm", request_id="tap-1"
        )
        assert query["answer"] is None
        assert query["id"] and query["chat_instance"]
        assert (
            world.create_callback(
                user_id=1, chat_id=1, message_id=1, data="confirm", request_id="tap-1"
            )
            == query
        )
        with pytest.raises(ValueError):
            world.create_callback(
                user_id=1, chat_id=1, message_id=1, data="different", request_id="tap-1"
            )
        with pytest.raises(ValueError):
            world.create_callback(
                user_id=3, chat_id=1, message_id=1, data="confirm", request_id="tap-1"
            )
    callback = {
        "id": query["id"],
        "from": {"id": 1, "is_bot": False, "first_name": "Alice"},
        "message": {
            "message_id": 1,
            "from": {"id": 2, "is_bot": True, "first_name": "Echo"},
            "chat": {"id": 1, "type": "private", "first_name": "Alice"},
            "date": 100,
            "text": "Choose",
            "reply_markup": keyboard,
        },
        "chat_instance": query["chat_instance"],
        "data": "confirm",
    }
    with BotAPIServer(directory) as server:
        expected_update = {"ok": True, "result": [{"update_id": 1, "callback_query": callback}]}
        assert request(server, token, "getUpdates") == (200, expected_update)
        assert request(server, token, "getUpdates") == (200, expected_update)
        assert request(server, other_token, "getUpdates") == (200, {"ok": True, "result": []})
        params = {"callback_query_id": query["id"], "text": "انجام شد ✓", "show_alert": True}
        for actor, changes in [
            (other_token, {}),
            (token, {"text": "x" * 201}),
            (token, {"show_alert": "false"}),
            (token, {"cache_time": 1}),
            (token, {"url": "https://example.com"}),
        ]:
            assert request(server, actor, "answerCallbackQuery", params | changes)[0] == 400
        assert request(server, token, "answerCallbackQuery", params) == (
            200,
            {"ok": True, "result": True},
        )
        assert request(server, token, "answerCallbackQuery", params)[0] == 400
        assert request(server, token, "getUpdates", {"offset": 2}) == (
            200,
            {"ok": True, "result": []},
        )
    with World.open(directory) as world:
        answered = query | {"answer": {"text": "انجام شد ✓", "show_alert": True, "cache_time": 0}}
        assert world.get_callback(user_id=1, callback_id=query["id"]) == answered
        assert (
            world.create_callback(
                user_id=1, chat_id=1, message_id=1, data="confirm", request_id="tap-1"
            )
            == answered
        )
        assert world.poll_updates(2) == []
        with pytest.raises(ValueError):
            world.get_callback(user_id=3, callback_id=query["id"])
        events = world.client_events(1, after=6)["events"]
        assert [event["type"] for event in events] == ["callback.created", "callback.answered"]
        assert world.client_events(3, after=6)["events"] == []


def test_distinct_taps_and_stale_data_reach_the_bot_but_concurrent_retries_do_not_duplicate(
    tmp_path: Path,
) -> None:
    directory = tmp_path / "world"
    with World.create(directory, seed=7, now=100) as world:
        world.create_user(first_name="Alice")
        world.create_user(first_name="Echo", is_bot=True)
        world.open_private_chat(user_id=1, bot_id=2)
        world.send_message(chat_id=1, sender_id=2, text="Already changed")
    barrier = Barrier(4)

    def retry(_: int):
        with World.open(directory) as world:
            barrier.wait()
            return world.create_callback(
                user_id=1, chat_id=1, message_id=1, data="old-button-data", request_id="tap-1"
            )

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(retry, range(4)))
    assert all(value == results[0] for value in results)
    with World.open(directory) as world:
        second = world.create_callback(
            user_id=1, chat_id=1, message_id=1, data="old-button-data", request_id="tap-2"
        )
        assert second["id"] != results[0]["id"]
        assert second["chat_instance"] == results[0]["chat_instance"]
        updates = world.poll_updates(2)
        assert [update["update_id"] for update in updates] == [1, 2]
        assert [update["callback_query"]["data"] for update in updates] == ["old-button-data"] * 2
        assert len(world.history(1)) == 1
