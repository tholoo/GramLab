"""Delivery contracts from the pinned independent references, exercised over real HTTP."""

import http.client
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
from threading import Barrier, Event
from urllib.parse import urlencode, urlsplit

import pytest
from test_bot_api import request
from test_polling import polling_world, wait_for_confirmation

from gramlab.bot_api import BotAPIServer
from gramlab.world import World


def message_update(update_id, message_id, text):
    return {
        "update_id": update_id,
        "message": {
            "message_id": message_id,
            "from": {"id": 1, "is_bot": False, "first_name": "Alice"},
            "chat": {"id": 1, "type": "private", "first_name": "Alice"},
            "date": 100,
            "text": text,
        },
    }


def test_selection_preserves_pending_updates_and_client_history_across_restart(tmp_path: Path):
    directory = tmp_path / "world"
    token = polling_world(directory)
    pending = message_update(1, 1, "acknowledge me")
    with BotAPIServer(directory) as server:
        assert request(server, token, "getUpdates", {"allowed_updates": ["callback_query"]}) == (
            200,
            {"ok": True, "result": [pending]},
        )
    with World.open(directory) as world:
        before = world.client_snapshot(1)
        hidden = world.send_message(chat_id=1, sender_id=1, text="visible to the client")
        reply = world.send_message(chat_id=1, sender_id=2, text="Choose")
        callback = world.create_callback(
            user_id=1, chat_id=1, message_id=3, data="choose", request_id="tap"
        )
        assert world.client_snapshot(1)["messages"] == before["messages"] + [hidden, reply]
        assert [
            event["type"] for event in world.client_events(1, after=before["cursor"])["events"]
        ] == ["message.created", "message.created", "callback.created"]
    expected_callback = {
        "update_id": 2,
        "callback_query": {
            "id": callback["id"],
            "from": pending["message"]["from"],
            "message": {
                "message_id": 3,
                "from": {"id": 2, "is_bot": True, "first_name": "Echo"},
                "chat": pending["message"]["chat"],
                "date": 100,
                "text": "Choose",
            },
            "chat_instance": callback["chat_instance"],
            "data": "choose",
        },
    }
    with BotAPIServer(directory) as restarted:
        assert request(restarted, token, "getUpdates") == (
            200,
            {"ok": True, "result": [pending, expected_callback]},
        )
        assert request(restarted, token, "getUpdates", {"offset": 3, "allowed_updates": []}) == (
            200,
            {"ok": True, "result": []},
        )
        with World.open(directory) as world:
            world.send_message(chat_id=1, sender_id=1, text="delivered again")
        assert request(restarted, token, "getUpdates") == (
            200,
            {"ok": True, "result": [message_update(3, 4, "delivered again")]},
        )


@pytest.mark.parametrize(
    "selection,deliver",
    [
        (["MESSAGE", "message", "unknown"], True),
        ([" message "], True),  # Unknown-only resets the default; names are not trimmed.
        (["guest_message", "unknown"], False),
        (["custom_event", "custom_query"], False),
        (["callback_query"], False),
        ([], True),
    ],
)
def test_filter_names_and_default_reset(tmp_path: Path, selection, deliver):
    directory = tmp_path / "world"
    token = polling_world(directory)
    with BotAPIServer(directory) as server:
        assert (
            request(server, token, "getUpdates", {"allowed_updates": ["callback_query"]})[0] == 200
        )
        assert request(
            server, token, "getUpdates", {"offset": 2, "allowed_updates": selection}
        ) == (200, {"ok": True, "result": []})
        with World.open(directory) as world:
            world.send_message(chat_id=1, sender_id=1, text="next")
        assert request(server, token, "getUpdates") == (
            200,
            {"ok": True, "result": [message_update(2, 2, "next")] if deliver else []},
        )


@pytest.mark.parametrize(
    "selection", [None, True, 3, {}, ["message", 3], "[", '["message",null]', '"message"']
)
def test_malformed_filter_retains_selection_but_still_acknowledges(tmp_path: Path, selection):
    directory = tmp_path / "world"
    token = polling_world(directory)
    with BotAPIServer(directory) as server:
        assert (
            request(server, token, "getUpdates", {"allowed_updates": ["callback_query"]})[0] == 200
        )
        assert request(
            server, token, "getUpdates", {"offset": 2, "allowed_updates": selection}
        ) == (200, {"ok": True, "result": []})
        with World.open(directory) as world:
            world.send_message(chat_id=1, sender_id=1, text="still filtered")
        assert request(server, token, "getUpdates") == (200, {"ok": True, "result": []})


def test_invalid_poll_cannot_change_selection_or_pending_delivery(tmp_path: Path):
    directory = tmp_path / "world"
    token = polling_world(directory)
    with BotAPIServer(directory) as server:
        for parameters in ({"offset": 2, "limit": 0}, {"offset": True}, {"timeout": None}):
            assert (
                request(server, token, "getUpdates", parameters | {"allowed_updates": ["poll"]})[0]
                == 400
            )
        assert request(server, "wrong", "getUpdates", {"allowed_updates": ["poll"]})[0] == 401
        assert request(server, token, "getUpdates", raw=b'{"allowed_updates":["poll"]')[0] == 400
        with World.open(directory) as world:
            world.send_message(chat_id=1, sender_id=1, text="still delivered")
        assert request(server, token, "getUpdates") == (
            200,
            {
                "ok": True,
                "result": [
                    message_update(1, 1, "acknowledge me"),
                    message_update(2, 2, "still delivered"),
                ],
            },
        )


def test_serialized_filter_uses_query_and_json_parameter_encodings(tmp_path: Path):
    directory = tmp_path / "world"
    token = polling_world(directory)
    with BotAPIServer(directory) as server:
        query = urlencode({"offset": 2, "allowed_updates": '["callback_query"]'})
        assert request(server, token, "getUpdates?" + query, verb="GET") == (
            200,
            {"ok": True, "result": []},
        )
        with World.open(directory) as world:
            world.send_message(chat_id=1, sender_id=1, text="filtered")
        assert request(server, token, "getUpdates", {"allowed_updates": "[]"}) == (
            200,
            {"ok": True, "result": []},
        )
        with World.open(directory) as world:
            world.send_message(chat_id=1, sender_id=1, text="reset")
        assert request(server, token, "getUpdates") == (
            200,
            {"ok": True, "result": [message_update(2, 3, "reset")]},
        )


def test_form_filter_suppresses_callbacks_without_erasing_durable_actions(tmp_path: Path):
    directory = tmp_path / "world"
    token = polling_world(directory)
    with BotAPIServer(directory) as server:
        url = urlsplit(server.base_url)
        connection = http.client.HTTPConnection(url.hostname, url.port, timeout=5)
        try:
            connection.request(
                "POST",
                f"/bot{token}/getUpdates",
                urlencode({"offset": 2, "allowed_updates": '["message"]'}),
                {"Content-Type": "application/x-www-form-urlencoded"},
            )
            response = connection.getresponse()
            assert response.status == 200
            assert json.loads(response.read()) == {"ok": True, "result": []}
        finally:
            connection.close()
        with World.open(directory) as world:
            world.send_message(chat_id=1, sender_id=2, text="Choose")
            callback = world.create_callback(
                user_id=1, chat_id=1, message_id=2, data="yes", request_id="suppressed"
            )
        assert request(server, token, "getUpdates", {"allowed_updates": []}) == (
            200,
            {"ok": True, "result": []},
        )
        with World.open(directory) as world:
            assert (
                world.create_callback(
                    user_id=1, chat_id=1, message_id=2, data="yes", request_id="suppressed"
                )
                == callback
            )
            assert world.poll_updates(2) == []
            world.send_message(chat_id=1, sender_id=1, text="after suppressed tap")
        assert request(server, token, "getUpdates") == (
            200,
            {"ok": True, "result": [message_update(2, 3, "after suppressed tap")]},
        )


def test_subscription_is_scoped_to_one_bot_in_one_world(tmp_path: Path):
    first, second = tmp_path / "first", tmp_path / "second"
    token = polling_world(first)
    polling_world(second)
    with World.open(first) as world:
        world.create_user(first_name="Other", is_bot=True)
        world.open_private_chat(user_id=1, bot_id=3)
    with BotAPIServer(first) as server:
        assert (
            request(server, token, "getUpdates", {"offset": 2, "allowed_updates": ["poll"]})[0]
            == 200
        )
    with World.open(first) as world:
        world.send_message(chat_id=1, sender_id=1, text="filtered")
        other = world.send_message(chat_id=2, sender_id=1, text="other bot")
        assert world.poll_updates(2) == []
        assert world.poll_updates(3) == [{"update_id": 1, "message": other}]
    with World.open(second) as world:
        initial = world.history(1)[0]
        another = world.send_message(chat_id=1, sender_id=1, text="other world")
        assert world.poll_updates(2) == [
            {"update_id": 1, "message": initial},
            {"update_id": 2, "message": another},
        ]


@pytest.mark.parametrize("offset,first", [(-2, 3), (-1, 4), (-99, 1), (-(2**63), 1)])
def test_negative_offsets_keep_the_tail_before_applying_limit(tmp_path: Path, offset, first):
    directory = tmp_path / "world"
    token = polling_world(directory)
    texts = ["acknowledge me", "second", "third", "fourth"]
    with World.open(directory) as world:
        for text in texts[1:]:
            world.send_message(chat_id=1, sender_id=1, text=text)
        world.create_user(first_name="Other", is_bot=True)
        world.open_private_chat(user_id=1, bot_id=3)
        other = world.send_message(chat_id=2, sender_id=1, text="independent")
    with BotAPIServer(directory) as server:
        assert request(server, token, "getUpdates", {"offset": offset, "limit": 1}) == (
            200,
            {"ok": True, "result": [message_update(first, first, texts[first - 1])]},
        )
    with BotAPIServer(directory) as restarted:
        assert request(restarted, token, "getUpdates") == (
            200,
            {"ok": True, "result": [message_update(i, i, texts[i - 1]) for i in range(first, 5)]},
        )
    with World.open(directory) as world:
        assert len(world.history(1)) == 4
        assert world.poll_updates(3) == [{"update_id": 1, "message": other}]


def test_negative_offset_is_applied_once_before_waiting_for_an_arrival_burst(
    tmp_path: Path, monkeypatch
):
    directory = tmp_path / "world"
    token = polling_world(directory)
    with World.open(directory) as world:
        world.poll_updates(2, offset=2)
    read_empty, release = Event(), Event()
    original = World.poll_updates

    def scheduled_poll(self, *args, **kwargs):
        result = original(self, *args, **kwargs)
        if kwargs.get("offset") == -1 and not read_empty.is_set():
            read_empty.set()
            assert release.wait(3)
        return result

    monkeypatch.setattr(World, "poll_updates", scheduled_poll)
    with BotAPIServer(directory) as server, ThreadPoolExecutor(max_workers=1) as worker:
        waiting = worker.submit(request, server, token, "getUpdates", {"offset": -1, "timeout": 2})
        try:
            assert read_empty.wait(2)
            with World.open(directory) as world:
                world.send_message(chat_id=1, sender_id=1, text="first arrival")
                world.send_message(chat_id=1, sender_id=1, text="second arrival")
        finally:
            release.set()
        assert waiting.result(timeout=3) == (
            200,
            {
                "ok": True,
                "result": [
                    message_update(2, 2, "first arrival"),
                    message_update(3, 3, "second arrival"),
                ],
            },
        )


def test_negative_offset_counts_pending_rows_in_a_sparse_legacy_queue(tmp_path: Path):
    directory = tmp_path / "world"
    directory.mkdir()
    with closing(sqlite3.connect(directory / "world.sqlite3")) as connection:
        connection.executescript(Path("tests/fixtures/world-v3.sql").read_text())
        with connection:
            for old_id, new_id in ((2, 20), (1, 10)):
                body = json.loads(
                    connection.execute("SELECT body FROM updates WHERE id=?", (old_id,)).fetchone()[
                        0
                    ]
                )
                body["update_id"] = new_id
                connection.execute(
                    "UPDATE updates SET id=?, body=? WHERE id=?", (new_id, json.dumps(body), old_id)
                )
            connection.execute("UPDATE bots SET next_update=21")
    with BotAPIServer(directory) as server:
        status, body = request(
            server, "2:gramlab_" + "a" * 43, "getUpdates", {"offset": -2, "limit": 1}
        )
        assert (status, body) == (
            200,
            {"ok": True, "result": [message_update(10, 1, "before upgrade")]},
        )
    with World.open(directory) as world:
        assert [update["update_id"] for update in world.poll_updates(2)] == [10, 20]


def test_waiting_poll_does_not_reapply_its_old_selection(tmp_path: Path):
    directory = tmp_path / "world"
    token = polling_world(directory)
    with BotAPIServer(directory) as server, ThreadPoolExecutor(max_workers=1) as worker:
        waiting = worker.submit(
            request,
            server,
            token,
            "getUpdates",
            {"offset": 2, "timeout": 2, "allowed_updates": ["callback_query"]},
        )
        wait_for_confirmation(directory, waiting)
        with World.open(directory) as world:
            world.poll_updates(2, allowed_updates=["message"])
            world.send_message(chat_id=1, sender_id=1, text="new selection")
        assert waiting.result(timeout=3) == (
            200,
            {"ok": True, "result": [message_update(2, 2, "new selection")]},
        )
        with World.open(directory) as world:
            world.send_message(chat_id=1, sender_id=1, text="selection still retained")
        assert request(server, token, "getUpdates", {"offset": 3}) == (
            200,
            {"ok": True, "result": [message_update(3, 3, "selection still retained")]},
        )


def test_waiting_filter_does_not_consume_ids_for_suppressed_messages(tmp_path: Path):
    directory = tmp_path / "world"
    token = polling_world(directory)
    with BotAPIServer(directory) as server, ThreadPoolExecutor(max_workers=1) as worker:
        waiting = worker.submit(
            request,
            server,
            token,
            "getUpdates",
            {"offset": 2, "timeout": 2, "allowed_updates": ["callback_query"]},
        )
        wait_for_confirmation(directory, waiting)
        with World.open(directory) as world:
            world.send_message(chat_id=1, sender_id=1, text="no bot notification")
            world.send_message(chat_id=1, sender_id=2, text="Choose")
            callback = world.create_callback(
                user_id=1, chat_id=1, message_id=3, data="yes", request_id="tap"
            )
        status, body = waiting.result(timeout=3)
        assert status == 200
        assert len(body["result"]) == 1
        assert body["result"][0]["update_id"] == 2
        assert body["result"][0]["callback_query"]["id"] == callback["id"]


def test_concurrent_v3_migration_preserves_capabilities_callbacks_and_world_identity(
    tmp_path: Path,
):
    directory = tmp_path / "world"
    directory.mkdir()
    with closing(sqlite3.connect(directory / "world.sqlite3")) as connection:
        connection.executescript(Path("tests/fixtures/world-v3.sql").read_text())
    barrier = Barrier(4)

    def migrate(_):
        barrier.wait()
        with World.open(directory) as world:
            return (
                world.client_snapshot(1),
                world.poll_updates(2),
                world.get_callback(user_id=1, callback_id="legacy-callback"),
            )

    with ThreadPoolExecutor(max_workers=4) as workers:
        results = list(workers.map(migrate, range(4)))
    assert all(result == results[0] for result in results)
    snapshot, pending, callback = results[0]
    assert snapshot["world_id"] == "11111111-2222-4333-8444-555555555555"
    assert pending == [
        {"update_id": 1, "message": snapshot["messages"][0]},
        {
            "update_id": 2,
            "callback_query": {key: value for key, value in callback.items() if key != "answer"},
        },
    ]
    assert callback["answer"] == {"text": "retained", "show_alert": False, "cache_time": 0}
    with World.open(directory) as world:
        assert world.authenticate_bot("2:gramlab_" + "a" * 43) == 2
        assert world.authenticate_client("gramlab-client_" + "b" * 43) == 1
        world.poll_updates(2, offset=3, allowed_updates=["callback_query"])
        world.send_message(chat_id=1, sender_id=1, text="filtered after migration")
        assert world.poll_updates(2) == []
        world.create_user(first_name="New bot", is_bot=True)
