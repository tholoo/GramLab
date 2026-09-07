"""Real HTTP coverage for rich callback, copy, and disabled buttons."""

import http.client
import json
from urllib.parse import urlencode, urlsplit

import pytest

from gramlab.bot_api import BotAPIServer
from gramlab.world import World


def request(server, token, method, parameters, *, form):
    url = urlsplit(server.base_url)
    connection = http.client.HTTPConnection(url.hostname, url.port, timeout=5)
    body = (
        urlencode(
            {
                key: json.dumps(value) if isinstance(value, (dict, list)) else value
                for key, value in parameters.items()
            }
        )
        if form
        else json.dumps(parameters)
    )
    content_type = "application/x-www-form-urlencoded" if form else "application/json"
    try:
        connection.request("POST", f"/bot{token}/{method}", body, {"Content-Type": content_type})
        response = connection.getresponse()
        return response.status, json.loads(response.read())
    finally:
        connection.close()


def setup_world(directory):
    with World.create(directory, seed=15, now=300) as world:
        world.create_user(first_name="Alice")
        world.create_user(first_name="Bot", is_bot=True)
        world.create_user(first_name="Other", is_bot=True)
        world.open_private_chat(user_id=1, bot_id=2)
        world.open_private_chat(user_id=1, bot_id=3)
        return world.issue_bot_token(2), world.issue_bot_token(3)


def api_message(rich_message, *, edited=False):
    result = {
        "message_id": 1,
        "from": {"id": 2, "is_bot": True, "first_name": "Bot"},
        "chat": {"id": 1, "type": "private", "first_name": "Alice"},
        "date": 300,
        "rich_message": rich_message,
    }
    if edited:
        result["edit_date"] = 305
    return result


@pytest.mark.parametrize("form", [False, True])
def test_rich_actions_http_send_edit_noop_and_reopen(tmp_path, form):
    directory = tmp_path / "world"
    token, other = setup_world(directory)
    initial_input = {
        "blocks": [
            {
                "type": "buttons",
                "buttons": [
                    {"text": "Choose\tamber", "style": "PRIMARY", "callback_data": "pick:\tamber"},
                    {"text": ["Copy ", "label"], "copy_text": {"text": "Amber\t42"}},
                    {"text": "Later", "disabled": {}},
                ],
                "align": "center",
            }
        ]
    }
    initial = {
        "blocks": [
            {
                "type": "buttons",
                "buttons": [
                    {"text": "Choose amber", "style": "primary", "callback_data": "pick:\tamber"},
                    {"text": ["Copy ", "label"], "copy_text": {"text": "Amber 42"}},
                    {"text": "Later", "disabled": {}},
                ],
                "align": "center",
            }
        ]
    }
    edited_input = {
        "blocks": [
            {
                "type": "paragraph",
                "text": {
                    "type": "button",
                    "button": {"text": "Go\tback", "style": "LINK", "callback_data": "back"},
                },
            }
        ]
    }
    edited = {
        "blocks": [
            {
                "type": "paragraph",
                "text": {
                    "type": "button",
                    "button": {"text": "Go back", "style": "link", "callback_data": "back"},
                },
            }
        ]
    }

    with BotAPIServer(directory) as server:
        assert request(
            server,
            token,
            "sendRichMessage",
            {"chat_id": 1, "rich_message": {**initial_input, "skip_entity_detection": True}},
            form=form,
        ) == (200, {"ok": True, "result": api_message(initial)})
        with World.open(directory) as world:
            world.advance_time(5)
        assert request(
            server,
            token,
            "editMessageText",
            {
                "chat_id": 1,
                "message_id": 1,
                "rich_message": {**edited_input, "skip_entity_detection": True},
            },
            form=form,
        ) == (200, {"ok": True, "result": api_message(edited, edited=True)})
        with World.open(directory) as world:
            before = world.client_snapshot(1, version=2), world.events()
        status, response = request(
            server,
            token,
            "editMessageText",
            {
                "chat_id": 1,
                "message_id": 1,
                "rich_message": {**edited_input, "skip_entity_detection": True},
            },
            form=form,
        )
        assert status == 400
        assert "MESSAGE_NOT_MODIFIED" in response["description"]
        assert (
            request(
                server,
                other,
                "editMessageText",
                {
                    "chat_id": 1,
                    "message_id": 1,
                    "rich_message": {**initial_input, "skip_entity_detection": True},
                },
                form=form,
            )[0]
            == 400
        )
        with World.open(directory) as world:
            assert (world.client_snapshot(1, version=2), world.events()) == before

    first = {
        "id": 1,
        "chat_id": 1,
        "sender_id": 2,
        "date": 300,
        "text": "",
        "rich_message": initial,
    }
    final = {**first, "edit_date": 305, "rich_message": edited}
    with World.open(directory) as world:
        assert world.history(1) == [final]
        assert world.client_changes(1, after=0)["changes"] == [
            {"position": 1, "type": "message.created", "data": first},
            {"position": 2, "type": "message.edited", "data": final},
        ]
        events = [event for event in world.events() if event["type"].startswith("message.")]
        assert [event["data"] for event in events] == [first, final]
