"""Polling startup reset behavior through the public World and HTTP boundaries."""

import http.client
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event
from urllib.parse import urlencode, urlsplit

import pytest
from test_bot_api import request
from test_polling import polling_world

from gramlab.bot_api import BotAPIServer
from gramlab.world import World


def _state(directory: Path, bot_id: int = 2) -> dict[str, object]:
    with World.open(directory) as world:
        return {
            "history": world.history(1),
            "events": world.events(),
            "snapshot": world.client_snapshot(1),
            "updates": world.poll_updates(bot_id),
        }


def _form_request(server: BotAPIServer, token: str, body: str) -> tuple[int, dict[str, object]]:
    url = urlsplit(server.base_url)
    connection = http.client.HTTPConnection(url.hostname, url.port, timeout=5)
    try:
        connection.request(
            "POST",
            f"/bot{token}/deleteWebhook",
            body,
            {"Content-Type": "application/x-www-form-urlencoded"},
        )
        response = connection.getresponse()
        return response.status, json.loads(response.read())
    finally:
        connection.close()


def test_world_discards_only_one_bot_queue_without_resetting_ids_or_client_state(
    tmp_path: Path,
) -> None:
    directory = tmp_path / "world"
    token = polling_world(directory)
    with World.open(directory) as world:
        choice = world.send_message(chat_id=1, sender_id=2, text="Choose")
        callback = world.create_callback(
            user_id=1, chat_id=1, message_id=choice["id"], data="choose", request_id="tap"
        )
        world.answer_callback(bot_id=2, callback_id=callback["id"], text="Done")
        before_callback = world.get_callback(user_id=1, callback_id=callback["id"])
        world.create_user(first_name="Other", is_bot=True)
        world.open_private_chat(user_id=1, bot_id=3)
        other_token = world.issue_bot_token(3)
        second_chat = world.private_chat_for_bot(3, 1)
        world.send_message(chat_id=second_chat["id"], sender_id=1, text="other pending")
        before_history = world.history(1)
        before_events = world.events()
        before_snapshot = world.client_snapshot(1)
        assert world.discard_pending_updates(2) == 2
        assert world.discard_pending_updates(2) == 0
        assert world.history(1) == before_history
        assert world.events() == before_events
        assert world.client_snapshot(1) == before_snapshot
        assert world.get_callback(user_id=1, callback_id=callback["id"]) == before_callback
        assert [item["update_id"] for item in world.poll_updates(3)] == [1]
        with pytest.raises(ValueError, match="Only bots"):
            world.discard_pending_updates(1)
        arrived = world.send_message(chat_id=1, sender_id=1, text="after reset")
        assert world.poll_updates(2) == [{"update_id": 3, "message": arrived}]
    with BotAPIServer(directory) as server:
        assert request(server, token, "getUpdates")[1]["result"][0]["update_id"] == 3
        assert request(server, other_token, "getUpdates")[1]["result"][0]["update_id"] == 1


@pytest.mark.parametrize(
    ("parameters", "drops"),
    [
        ({}, False),
        ({"drop_pending_updates": False}, False),
        ({"drop_pending_updates": "false"}, False),
        ({"drop_pending_updates": True}, True),
        ({"drop_pending_updates": "true"}, True),
    ],
)
def test_delete_webhook_json_is_repeatable_and_optionally_discards_pending(
    tmp_path: Path, parameters: dict[str, bool | str], drops: bool
) -> None:
    directory = tmp_path / "world"
    token = polling_world(directory)
    before = _state(directory)
    with BotAPIServer(directory) as server:
        expected = (200, {"ok": True, "result": True})
        assert request(server, token, "deleteWebhook", parameters) == expected
        assert request(server, token, "deleteWebhook", parameters) == expected
    after = _state(directory)
    assert after["history"] == before["history"]
    assert after["events"] == before["events"]
    assert after["snapshot"] == before["snapshot"]
    assert after["updates"] == ([] if drops else before["updates"])


@pytest.mark.parametrize("value", [" true ", "YES", "1"])
def test_delete_webhook_textual_true_works_for_form_and_query(tmp_path: Path, value: str) -> None:
    for transport in ("form", "query"):
        directory = tmp_path / f"{transport}-{value.strip()}"
        token = polling_world(directory)
        with BotAPIServer(directory) as server:
            encoded = urlencode({"drop_pending_updates": value})
            response = (
                _form_request(server, token, encoded)
                if transport == "form"
                else request(server, token, f"deleteWebhook?{encoded}", verb="GET")
            )
            assert response == (200, {"ok": True, "result": True})
        assert _state(directory)["updates"] == []


@pytest.mark.parametrize("value", ["false", "no", "0", "anything", ""])
def test_delete_webhook_other_text_is_false(tmp_path: Path, value: str) -> None:
    directory = tmp_path / "world"
    token = polling_world(directory)
    before = _state(directory)
    with BotAPIServer(directory) as server:
        assert _form_request(server, token, urlencode({"drop_pending_updates": value})) == (
            200,
            {"ok": True, "result": True},
        )
    assert _state(directory) == before


@pytest.mark.parametrize("invalid", [None, 0, 1, [], {}])
def test_delete_webhook_rejects_non_boolean_json_without_mutation(
    tmp_path: Path, invalid: object
) -> None:
    directory = tmp_path / "world"
    token = polling_world(directory)
    before = _state(directory)
    with BotAPIServer(directory) as server:
        assert request(server, token, "deleteWebhook", {"drop_pending_updates": invalid}) == (
            400,
            {
                "ok": False,
                "error_code": 400,
                "description": "drop_pending_updates must be a Boolean or text",
            },
        )
        assert request(server, token, "deleteWebhook", {"unsupported": True})[0] == 400
        assert request(server, "wrong", "deleteWebhook", {"drop_pending_updates": True})[0] == 401
        assert request(server, token, "setWebhook", {})[0] == 404
    assert _state(directory) == before


def test_delete_webhook_does_not_interrupt_a_waiting_poll(tmp_path: Path, monkeypatch) -> None:
    directory = tmp_path / "world"
    token = polling_world(directory)
    with World.open(directory) as world:
        world.poll_updates(2, offset=2)
    entered = Event()
    original = World.poll_updates

    def observed_poll(self, *args, **kwargs):
        result = original(self, *args, **kwargs)
        entered.set()
        return result

    monkeypatch.setattr(World, "poll_updates", observed_poll)
    with BotAPIServer(directory) as server, ThreadPoolExecutor() as worker:
        waiting = worker.submit(request, server, token, "getUpdates", {"offset": 2, "timeout": 2})
        assert entered.wait(1)
        assert request(server, token, "deleteWebhook", {"drop_pending_updates": True}) == (
            200,
            {"ok": True, "result": True},
        )
        with World.open(directory) as world:
            message = world.send_message(chat_id=1, sender_id=1, text="after deletion")
        status, body = waiting.result(timeout=3)
        assert status == 200
        assert body["result"] == [
            {
                "update_id": 2,
                "message": {
                    "message_id": message["id"],
                    "from": {"id": 1, "is_bot": False, "first_name": "Alice"},
                    "chat": {"id": 1, "type": "private", "first_name": "Alice"},
                    "date": 100,
                    "text": "after deletion",
                },
            }
        ]


def test_drop_preserves_update_selection_and_rejected_encodings_preserve_state(
    tmp_path: Path,
) -> None:
    directory = tmp_path / "world"
    token = polling_world(directory)
    with BotAPIServer(directory) as server:
        assert (
            request(server, token, "getUpdates", {"allowed_updates": ["callback_query"]})[0] == 200
        )
        assert request(server, token, "deleteWebhook", {"drop_pending_updates": True}) == (
            200,
            {"ok": True, "result": True},
        )
        with World.open(directory) as world:
            choice = world.send_message(chat_id=1, sender_id=2, text="Choose")
            callback = world.create_callback(
                user_id=1,
                chat_id=1,
                message_id=choice["id"],
                data="choose",
                request_id="retained-tap",
            )
        before = _state(directory)
        rejected = request(
            server,
            token,
            "deleteWebhook",
            raw=b'{"drop_pending_updates":true,"drop_pending_updates":false}',
        )
        assert rejected[0] == 400
        assert _state(directory) == before
        rejected = _form_request(
            server, token, "drop_pending_updates=true&drop_pending_updates=false"
        )
        assert rejected[0] == 400
        assert _state(directory) == before
        rejected = request(
            server,
            token,
            "deleteWebhook?drop_pending_updates=true",
            {"drop_pending_updates": False},
        )
        assert rejected[0] == 400
        assert _state(directory) == before
    with BotAPIServer(directory) as restarted:
        status, body = request(restarted, token, "getUpdates")
        assert status == 200
        assert len(body["result"]) == 1
        assert body["result"][0]["update_id"] == 2
        assert body["result"][0]["callback_query"]["id"] == callback["id"]
        assert request(restarted, token, "getUpdates", {"offset": 3}) == (
            200,
            {"ok": True, "result": []},
        )
        with World.open(directory) as world:
            world.send_message(chat_id=1, sender_id=1, text="filtered after restart")
        assert request(restarted, token, "getUpdates") == (200, {"ok": True, "result": []})
