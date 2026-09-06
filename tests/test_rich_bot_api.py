"""Structured rich content across real HTTP and durable world boundaries."""

import copy
import http.client
import json
from pathlib import Path
from urllib.parse import urlencode, urlsplit

import pytest

from gramlab.bot_api import BotAPIServer
from gramlab.world import World


def request(server, token, method, parameters, *, form=False):
    url = urlsplit(server.base_url)
    connection = http.client.HTTPConnection(url.hostname, url.port, timeout=5)
    if form:
        body = urlencode(
            {k: json.dumps(v) if isinstance(v, (dict, list)) else v for k, v in parameters.items()}
        )
        content_type = "application/x-www-form-urlencoded"
    else:
        body = json.dumps(parameters)
        content_type = "application/json"
    try:
        connection.request("POST", f"/bot{token}/{method}", body, {"Content-Type": content_type})
        response = connection.getresponse()
        return response.status, json.loads(response.read())
    finally:
        connection.close()


def content():
    return {
        "blocks": [
            {"type": "heading", "size": 2, "text": "Round دور"},
            {
                "type": "paragraph",
                "text": [
                    "سلام نیم‌فاصله ",
                    {"type": "bold", "text": {"type": "italic", "text": "EN 👩‍💻"}},
                ],
            },
            {"type": "pre", "text": "print('✓')\n", "language": "python"},
            {
                "type": "table",
                "cells": [
                    [
                        {
                            "text": "نام",
                            "is_header": True,
                            "colspan": 2,
                            "align": "center",
                            "valign": "middle",
                        }
                    ],
                    [
                        {"text": "Ada", "align": "left", "valign": "top"},
                        {"text": "۲", "rowspan": 2, "align": "right", "valign": "bottom"},
                    ],
                ],
                "is_bordered": True,
                "is_striped": True,
                "is_compact": True,
                "caption": {"type": "underline", "text": "Score"},
            },
            {
                "type": "details",
                "summary": "جزئیات",
                "is_open": True,
                "blocks": [
                    {
                        "type": "blockquote",
                        "blocks": [{"type": "paragraph", "text": "Quoted"}],
                        "credit": "Author",
                    }
                ],
            },
            {"type": "expandable_blockquote", "text": "Expandable", "credit": "Source"},
            {"type": "pullquote", "text": "Centered", "credit": "Credit"},
            {"type": "divider"},
            {
                "type": "footer",
                "text": [
                    {"type": name, "text": "x"}
                    for name in (
                        "strikethrough",
                        "spoiler",
                        "subscript",
                        "superscript",
                        "marked",
                        "code",
                    )
                ],
            },
        ],
        "is_rtl": True,
    }


def setup_world(directory):
    with World.create(directory, seed=8, now=100) as world:
        world.create_user(first_name="Alice")
        world.create_user(first_name="Bot", is_bot=True)
        world.create_user(first_name="Other", is_bot=True)
        world.open_private_chat(user_id=1, bot_id=2)
        world.open_private_chat(user_id=1, bot_id=3)
        return world.issue_bot_token(2), world.issue_bot_token(3)


def api_message(rich, *, edited=False):
    result = {
        "message_id": 1,
        "from": {"id": 2, "is_bot": True, "first_name": "Bot"},
        "chat": {"id": 1, "type": "private", "first_name": "Alice"},
        "date": 100,
        "rich_message": rich,
    }
    if edited:
        result["edit_date"] = 105
    return result


@pytest.mark.parametrize("form", [False, True])
def test_rich_http_send_edit_reopen_and_complete_events(tmp_path: Path, form):
    directory = tmp_path / "world"
    token, _ = setup_world(directory)
    initial = content()
    edited = copy.deepcopy(initial)
    edited["blocks"][0]["text"] = "Updated به‌روز ✓"
    with BotAPIServer(directory) as server:
        assert request(
            server,
            token,
            "sendRichMessage",
            {"chat_id": 1, "rich_message": {**initial, "skip_entity_detection": True}},
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
                "rich_message": {**edited, "skip_entity_detection": True},
            },
            form=form,
        ) == (200, {"ok": True, "result": api_message(edited, edited=True)})
    first = {
        "id": 1,
        "chat_id": 1,
        "sender_id": 2,
        "date": 100,
        "text": "",
        "rich_message": initial,
    }
    final = {**first, "edit_date": 105, "rich_message": edited}
    with World.open(directory) as world:
        assert world.history(1) == [final]
        assert world.client_snapshot(1)["messages"] == [final]
        events = [event for event in world.events() if event["type"].startswith("message.")]
        assert [event["data"] for event in events] == [first, final]
        assert [event["type"] for event in events] == ["message.created", "message.edited"]


@pytest.mark.parametrize(
    "rich",
    [
        {},
        {"blocks": []},
        {"blocks": [{"type": "paragraph", "text": "x"}]},
        {"blocks": [{"type": "paragraph", "text": "x"}], "skip_entity_detection": False},
        {"blocks": [{"type": "photo", "photo": "file"}], "skip_entity_detection": True},
        {
            "blocks": [
                {
                    "type": "paragraph",
                    "text": {"type": "url", "text": "x", "url": "https://example.com"},
                }
            ],
            "skip_entity_detection": True,
        },
        {"blocks": [{"type": "heading", "text": "x", "size": True}], "skip_entity_detection": True},
        {
            "blocks": [
                {"type": "details", "summary": "x", "blocks": [{"type": "list", "items": []}]}
            ],
            "skip_entity_detection": True,
        },
        {"blocks": [{"type": "paragraph", "text": "\ud800"}], "skip_entity_detection": True},
        {
            "blocks": [{"type": "paragraph", "text": "x", "unknown": True}],
            "skip_entity_detection": True,
        },
        {"html": "<p>x</p>", "skip_entity_detection": True},
    ],
)
def test_invalid_rich_requests_are_atomic(tmp_path, rich):
    directory = tmp_path / "world"
    token, _ = setup_world(directory)
    with BotAPIServer(directory) as server:
        assert request(server, token, "sendMessage", {"chat_id": 1, "text": "Original"})[0] == 200
        with World.open(directory) as world:
            before = world.client_snapshot(1), world.events()
        for method, extra in (("sendRichMessage", {}), ("editMessageText", {"message_id": 1})):
            status, response = request(
                server, token, method, {"chat_id": 1, "rich_message": rich, **extra}
            )
            assert status == 400
            assert response["ok"] is False
        with World.open(directory) as world:
            assert (world.client_snapshot(1), world.events()) == before


def test_rich_ownership_unchanged_content_and_text_transitions(tmp_path):
    directory = tmp_path / "world"
    token, other = setup_world(directory)
    rich = {"blocks": [{"type": "paragraph", "text": "Rich"}], "skip_entity_detection": True}
    with BotAPIServer(directory) as server:
        assert (
            request(
                server,
                token,
                "sendMessage",
                {
                    "chat_id": 1,
                    "text": "Plain",
                    "entities": [{"type": "bold", "offset": 0, "length": 5}],
                },
            )[0]
            == 200
        )
        args = {"chat_id": 1, "message_id": 1, "rich_message": rich}
        assert request(server, token, "editMessageText", args) == (
            200,
            {"ok": True, "result": {**api_message({"blocks": rich["blocks"]}), "edit_date": 100}},
        )
        with World.open(directory) as world:
            world.send_message(chat_id=1, sender_id=1, text="Incoming")
            before = world.client_snapshot(1), world.events()
        for denied_token, params in (
            (other, args),
            (token, {**args, "message_id": 2}),
            (token, args),
            (token, {**args, "text": "Ambiguous"}),
            (token, {**args, "entities": []}),
        ):
            assert request(server, denied_token, "editMessageText", params)[0] == 400
        with World.open(directory) as world:
            assert (world.client_snapshot(1), world.events()) == before
        assert request(
            server, token, "editMessageText", {"chat_id": 1, "message_id": 1, "text": "Plain again"}
        )[1]["result"] == {
            "message_id": 1,
            "from": {"id": 2, "is_bot": True, "first_name": "Bot"},
            "chat": {"id": 1, "type": "private", "first_name": "Alice"},
            "date": 100,
            "edit_date": 100,
            "text": "Plain again",
        }


def test_rich_callback_update_preserves_structured_message_and_keyboard(tmp_path):
    directory = tmp_path / "world"
    token, _ = setup_world(directory)
    body = {"blocks": [{"type": "paragraph", "text": "Choose انتخاب"}]}
    keyboard = {"inline_keyboard": [[{"text": "Go", "callback_data": "go"}]]}
    with BotAPIServer(directory) as server:
        assert request(
            server,
            token,
            "sendRichMessage",
            {
                "chat_id": 1,
                "rich_message": {**body, "skip_entity_detection": True},
                "reply_markup": keyboard,
            },
        ) == (200, {"ok": True, "result": {**api_message(body), "reply_markup": keyboard}})
        with World.open(directory) as world:
            callback = world.create_callback(
                user_id=1, chat_id=1, message_id=1, data="go", request_id="rich-click"
            )
        status, response = request(server, token, "getUpdates", {})
        assert status == 200
        assert response["ok"] is True
        assert len(response["result"]) == 1
        update = response["result"][0]
        assert update["callback_query"] == {
            "id": callback["id"],
            "from": {"id": 1, "is_bot": False, "first_name": "Alice"},
            "message": {**api_message(body), "reply_markup": keyboard},
            "chat_instance": callback["chat_instance"],
            "data": "go",
        }
