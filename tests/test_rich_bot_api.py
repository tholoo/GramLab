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


def list_content():
    return {
        "blocks": [
            {
                "type": "list",
                "items": [
                    {
                        "blocks": [
                            {
                                "type": "paragraph",
                                "text": ["مرحله ", {"type": "bold", "text": "one"}],
                            }
                        ],
                        "type": "a",
                        "value": 27,
                        "has_checkbox": True,
                        "is_checked": True,
                    },
                    {"blocks": [], "type": "I", "value": 4000},
                ],
            },
            {
                "type": "list",
                "items": [
                    {
                        "blocks": [
                            {
                                "type": "details",
                                "summary": "Nested تو در تو",
                                "blocks": [
                                    {
                                        "type": "list",
                                        "items": [
                                            {
                                                "blocks": [{"type": "paragraph", "text": "inner"}],
                                                "type": "i",
                                                "value": 3999,
                                            }
                                        ],
                                    }
                                ],
                            }
                        ],
                        "type": "",
                        "value": -(2**31),
                        "is_checked": True,
                    },
                    {
                        "blocks": [{"type": "paragraph", "text": "پایان end"}],
                        "value": 2**31 - 1,
                        "has_checkbox": True,
                        "is_checked": False,
                    },
                ],
            },
        ],
        "is_rtl": True,
    }


def canonical_list_content():
    return {
        "blocks": [
            {
                "type": "list",
                "items": [
                    {
                        "label": "aa.",
                        "blocks": [
                            {
                                "type": "paragraph",
                                "text": ["مرحله ", {"type": "bold", "text": "one"}],
                            }
                        ],
                        "has_checkbox": True,
                        "is_checked": True,
                        "type": "a",
                        "value": 27,
                    },
                    {"label": "4000.", "blocks": [], "type": "I", "value": 4000},
                ],
            },
            {
                "type": "list",
                "items": [
                    {
                        "label": "•",
                        "blocks": [
                            {
                                "type": "details",
                                "summary": "Nested تو در تو",
                                "blocks": [
                                    {
                                        "type": "list",
                                        "items": [
                                            {
                                                "label": "mmmcmxcix.",
                                                "blocks": [{"type": "paragraph", "text": "inner"}],
                                                "type": "i",
                                                "value": 3999,
                                            }
                                        ],
                                    }
                                ],
                            }
                        ],
                    },
                    {
                        "label": "•",
                        "blocks": [{"type": "paragraph", "text": "پایان end"}],
                        "has_checkbox": True,
                    },
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


@pytest.mark.parametrize("form", [False, True])
def test_rich_http_cleaning_is_canonical_and_durable(tmp_path: Path, form):
    directory = tmp_path / "world"
    token, _ = setup_world(directory)
    raw = {
        "blocks": [
            {
                "type": "paragraph",
                "text": ["Amber\t42", {"type": "bold", "text": "X\u200e\u200f\u200eY"}],
            },
            {"type": "pre", "text": "A\u030aB\u0333C\u033fD", "language": "py\t\u202ethon"},
        ]
    }
    canonical = {
        "blocks": [
            {
                "type": "paragraph",
                "text": ["Amber 42", {"type": "bold", "text": "X\u200c\u200c\u200eY"}],
            },
            {"type": "pre", "text": "ABCD", "language": "py thon"},
        ]
    }
    raw_edited = {
        "blocks": [
            {"type": "paragraph", "text": "Changed\u2028\tvalue"},
            {
                "type": "pre",
                "text": "سلام\nنیم\u200cفاصله",  # noqa: RUF001
                "language": "py\u0333",
            },
        ]
    }
    canonical_edited = {
        "blocks": [
            {"type": "paragraph", "text": "Changed value"},
            {
                "type": "pre",
                "text": "سلام\nنیم\u200cفاصله",  # noqa: RUF001
                "language": "py",
            },
        ]
    }
    keyboard = {"inline_keyboard": [[{"text": "Inspect", "callback_data": "clean"}]]}

    with BotAPIServer(directory) as server:
        assert request(
            server,
            token,
            "sendRichMessage",
            {
                "chat_id": 1,
                "rich_message": {**raw, "skip_entity_detection": True},
                "reply_markup": keyboard,
            },
            form=form,
        ) == (200, {"ok": True, "result": {**api_message(canonical), "reply_markup": keyboard}})
        created = {
            "id": 1,
            "chat_id": 1,
            "sender_id": 2,
            "date": 100,
            "text": "",
            "rich_message": canonical,
            "reply_markup": keyboard,
        }
        with World.open(directory) as world:
            callback = world.create_callback(
                user_id=1,
                chat_id=1,
                message_id=1,
                data="clean",
                request_id="clean-click",
            )
            world.advance_time(5)
        assert request(
            server,
            token,
            "editMessageText",
            {
                "chat_id": 1,
                "message_id": 1,
                "rich_message": {**raw_edited, "skip_entity_detection": True},
            },
            form=form,
        ) == (200, {"ok": True, "result": api_message(canonical_edited, edited=True)})
        with World.open(directory) as world:
            before_noop = world.client_snapshot(1, version=2), world.events()
        status, response = request(
            server,
            token,
            "editMessageText",
            {
                "chat_id": 1,
                "message_id": 1,
                "rich_message": {**raw_edited, "skip_entity_detection": True},
            },
            form=form,
        )
        assert status == 400
        assert response["ok"] is False
        assert "MESSAGE_NOT_MODIFIED" in response["description"]
        with World.open(directory) as world:
            assert (world.client_snapshot(1, version=2), world.events()) == before_noop

    edited = {**created, "edit_date": 105, "rich_message": canonical_edited}
    edited.pop("reply_markup")
    with World.open(directory) as world:
        assert world.history(1) == [edited]
        assert world.client_changes(1, after=0)["changes"] == [
            {"position": 1, "type": "message.created", "data": created},
            {"position": 2, "type": "message.edited", "data": edited},
        ]
        assert world.get_callback(user_id=1, callback_id=callback["id"])["message"] == created
        message_events = [event for event in world.events() if event["type"].startswith("message.")]
        assert [event["type"] for event in message_events] == [
            "message.created",
            "message.edited",
        ]
        assert [event["data"] for event in message_events] == [created, edited]


@pytest.mark.parametrize("form", [False, True])
def test_list_http_send_edit_callback_differences_and_reopen(tmp_path: Path, form):
    directory = tmp_path / "world"
    token, _ = setup_world(directory)
    initial_input = list_content()
    initial = canonical_list_content()
    edited_input = {
        "blocks": [
            {
                "type": "list",
                "items": [
                    {
                        "blocks": [{"type": "paragraph", "text": "Changed marker only"}],
                        "type": "",
                        "value": 15,
                        "has_checkbox": False,
                        "is_checked": True,
                    },
                    {"blocks": []},
                ],
            }
        ],
        "is_rtl": True,
    }
    edited = {
        "blocks": [
            {
                "type": "list",
                "items": [
                    {
                        "label": "•",
                        "blocks": [{"type": "paragraph", "text": "Changed marker only"}],
                    },
                    {"label": "•", "blocks": []},
                ],
            }
        ],
        "is_rtl": True,
    }
    keyboard = {"inline_keyboard": [[{"text": "Inspect", "callback_data": "list"}]]}

    with BotAPIServer(directory) as server:
        send_status, send_response = request(
            server,
            token,
            "sendRichMessage",
            {
                "chat_id": 1,
                "rich_message": {**initial_input, "skip_entity_detection": True},
                "reply_markup": keyboard,
            },
            form=form,
        )
        assert (send_status, send_response) == (
            200,
            {
                "ok": True,
                "result": {**api_message(initial), "reply_markup": keyboard},
            },
        )
        created = {
            "id": 1,
            "chat_id": 1,
            "sender_id": 2,
            "date": 100,
            "text": "",
            "rich_message": initial,
            "reply_markup": keyboard,
        }
        with World.open(directory) as world:
            assert world.client_snapshot(1, version=2)["messages"] == [created]
            assert world.client_changes(1, after=0)["changes"] == [
                {"position": 1, "type": "message.created", "data": created}
            ]
            callback = world.create_callback(
                user_id=1,
                chat_id=1,
                message_id=1,
                data="list",
                request_id="list-click",
            )

        assert request(server, token, "getUpdates", {}) == (
            200,
            {
                "ok": True,
                "result": [
                    {
                        "update_id": 1,
                        "callback_query": {
                            "id": callback["id"],
                            "from": {"id": 1, "is_bot": False, "first_name": "Alice"},
                            "message": {**api_message(initial), "reply_markup": keyboard},
                            "chat_instance": callback["chat_instance"],
                            "data": "list",
                        },
                    }
                ],
            },
        )
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

        equivalent_input = copy.deepcopy(edited_input)
        equivalent_input["blocks"][0]["items"][0]["value"] = -(2**31)
        equivalent_input["blocks"][0]["items"][0].pop("type")
        with World.open(directory) as world:
            before_noop = world.client_snapshot(1, version=2), world.events()
        status, response = request(
            server,
            token,
            "editMessageText",
            {
                "chat_id": 1,
                "message_id": 1,
                "rich_message": {**equivalent_input, "skip_entity_detection": True},
            },
            form=form,
        )
        assert status == 400
        assert response["ok"] is False
        assert "MESSAGE_NOT_MODIFIED" in response["description"]
        with World.open(directory) as world:
            assert (world.client_snapshot(1, version=2), world.events()) == before_noop

    final = {
        "id": 1,
        "chat_id": 1,
        "sender_id": 2,
        "date": 100,
        "text": "",
        "edit_date": 105,
        "rich_message": edited,
    }
    with World.open(directory) as world:
        assert world.history(1) == [final]
        assert world.client_snapshot(1, version=2)["messages"] == [final]
        assert world.client_changes(1, after=0)["changes"] == [
            {"position": 1, "type": "message.created", "data": created},
            {"position": 2, "type": "message.edited", "data": final},
        ]
        assert world.get_callback(user_id=1, callback_id=callback["id"])["message"] == created
        message_events = [event for event in world.events() if event["type"].startswith("message.")]
        assert [event["type"] for event in message_events] == [
            "message.created",
            "message.edited",
        ]
        assert [event["data"] for event in message_events] == [created, final]


@pytest.mark.parametrize(
    "rich",
    [
        {},
        {"blocks": []},
        {"blocks": [{"type": "photo", "photo": "file"}], "skip_entity_detection": True},
        {
            "blocks": [
                {
                    "type": "paragraph",
                    "text": {"type": "text_link", "text": "x", "url": "https://example.com"},
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
        {
            "blocks": [{"type": "list", "items": []}],
            "skip_entity_detection": True,
        },
        {
            "blocks": [{"type": "list", "items": [{"type": "1"}]}],
            "skip_entity_detection": True,
        },
        {
            "blocks": [
                {
                    "type": "list",
                    "items": [{"blocks": []}, {"blocks": [], "type": "A"}],
                }
            ],
            "skip_entity_detection": True,
        },
        {
            "blocks": [{"type": "list", "items": [{"blocks": [], "type": "x"}]}],
            "skip_entity_detection": True,
        },
        {
            "blocks": [{"type": "list", "items": [{"blocks": [], "value": True}]}],
            "skip_entity_detection": True,
        },
        {
            "blocks": [{"type": "list", "items": [{"blocks": [], "value": 2**31}]}],
            "skip_entity_detection": True,
        },
        {
            "blocks": [{"type": "list", "items": [{"blocks": [], "has_checkbox": "true"}]}],
            "skip_entity_detection": True,
        },
        {
            "blocks": [{"type": "list", "items": [{"blocks": [], "label": "•"}]}],
            "skip_entity_detection": True,
        },
        {
            "blocks": [{"type": "list", "items": [{"blocks": []}], "unknown": "field"}],
            "skip_entity_detection": True,
        },
        {
            "blocks": [{"type": "list", "items": [{"blocks": []} for _ in range(2000)]}],
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
        assert (
            request(server, token, "sendMessage", {"chat_id": 1, "text": "After"})[1]["result"][
                "message_id"
            ]
            == 2
        )


def test_rich_ownership_unchanged_content_and_text_transitions(tmp_path):
    directory = tmp_path / "world"
    token, other = setup_world(directory)
    rich = {
        "blocks": [
            {
                "type": "list",
                "items": [{"blocks": [{"type": "paragraph", "text": "Rich"}], "value": 9}],
            }
        ],
        "skip_entity_detection": True,
    }
    canonical = {
        "blocks": [
            {
                "type": "list",
                "items": [
                    {
                        "label": "•",
                        "blocks": [{"type": "paragraph", "text": "Rich"}],
                    }
                ],
            }
        ]
    }
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
            {"ok": True, "result": {**api_message(canonical), "edit_date": 100}},
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
