"""Quoted code and pre entities at the public World and Bot API boundaries."""

import http.client
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urlsplit

import pytest

from gramlab.bot_api import BotAPIServer
from gramlab.entities import formatting_entities
from gramlab.world import World

TEXT = "😀Q\ncode\nZ"
USER = {"id": 1, "is_bot": False, "first_name": "Alice"}
BOT = {"id": 2, "is_bot": True, "first_name": "Echo"}
CHAT = {"id": 1, "type": "private", "first_name": "Alice"}


def request(
    server: BotAPIServer,
    token: str,
    method: str,
    parameters: dict[str, Any],
    *,
    form: bool,
) -> tuple[int, dict[str, Any]]:
    url = urlsplit(server.base_url)
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
    assert url.hostname is not None
    connection = http.client.HTTPConnection(url.hostname, url.port, timeout=5)
    try:
        connection.request("POST", f"/bot{token}/{method}", body, {"Content-Type": content_type})
        response = connection.getresponse()
        return response.status, json.loads(response.read())
    finally:
        connection.close()


def world(directory: Path) -> str:
    with World.create(directory, seed=26, now=100) as current:
        current.create_user(first_name="Alice")
        current.create_user(first_name="Echo", is_bot=True)
        current.open_private_chat(user_id=1, bot_id=2)
        return current.issue_bot_token(2)


@pytest.mark.parametrize("quote", ["blockquote", "expandable_blockquote"])
@pytest.mark.parametrize("code", ["code", "pre"])
@pytest.mark.parametrize("equal", [False, True])
@pytest.mark.parametrize("reverse", [False, True])
def test_quotes_are_canonical_ancestors_of_code_and_pre(
    quote: str, code: str, equal: bool, reverse: bool
) -> None:
    quote_entity: dict[str, Any] = {"type": quote, "offset": 0, "length": 10}
    code_entity: dict[str, Any] = {
        "type": code,
        "offset": 0 if equal else 4,
        "length": 10 if equal else 4,
    }
    if code == "pre":
        code_entity["language"] = "python"
    supplied: list[dict[str, Any]] = [quote_entity, code_entity]
    if reverse:
        supplied.reverse()
    assert formatting_entities(TEXT, [*supplied, dict(code_entity)]) == [
        quote_entity,
        code_entity,
    ]


@pytest.mark.parametrize("form", [False, True])
def test_http_quoted_code_send_edit_noop_and_reopen(tmp_path: Path, form: bool) -> None:
    directory = tmp_path / "world"
    token = world(directory)
    quote = {"type": "blockquote", "offset": 0, "length": 10}
    code = {"type": "code", "offset": 0, "length": 10}
    sent_entities = [quote, code]
    sent = {
        "message_id": 1,
        "from": BOT,
        "chat": CHAT,
        "date": 100,
        "text": TEXT,
        "entities": sent_entities,
    }
    with BotAPIServer(directory) as server:
        assert request(
            server,
            token,
            "sendMessage",
            {"chat_id": 1, "text": TEXT, "entities": [code, quote, code]},
            form=form,
        ) == (200, {"ok": True, "result": sent})
        with World.open(directory) as current:
            current.advance_time(5)
        expandable = {"type": "expandable_blockquote", "offset": 0, "length": 10}
        pre = {"type": "pre", "offset": 4, "length": 4, "language": "python"}
        edited_entities = [expandable, pre]
        edited = sent | {"edit_date": 105, "entities": edited_entities}
        parameters = {
            "chat_id": 1,
            "message_id": 1,
            "text": TEXT,
            "entities": [pre, expandable],
        }
        assert request(server, token, "editMessageText", parameters, form=form) == (
            200,
            {"ok": True, "result": edited},
        )
        assert request(
            server,
            token,
            "editMessageText",
            parameters | {"entities": [expandable, pre, pre]},
            form=form,
        ) == (
            400,
            {"ok": False, "error_code": 400, "description": "MESSAGE_NOT_MODIFIED"},
        )

    created = {
        "id": 1,
        "chat_id": 1,
        "sender_id": 2,
        "date": 100,
        "text": TEXT,
        "entities": sent_entities,
    }
    persisted = {
        "id": 1,
        "chat_id": 1,
        "sender_id": 2,
        "date": 100,
        "edit_date": 105,
        "text": TEXT,
        "entities": edited_entities,
    }
    with World.open(directory) as current:
        assert current.history(1) == [persisted]
        assert current.client_snapshot(1)["messages"] == [persisted]
        assert current.events(after=3) == [
            {
                "sequence": 4,
                "type": "message.created",
                "data": created,
            },
            {"sequence": 5, "type": "clock.advanced", "data": {"now": 105}},
            {"sequence": 6, "type": "message.edited", "data": persisted},
        ]


def test_world_equal_quote_and_style_order_makes_duplicate_edit_a_noop(tmp_path: Path) -> None:
    directory = tmp_path / "world"
    world(directory)
    quote = {"type": "expandable_blockquote", "offset": 0, "length": 10}
    bold = {"type": "bold", "offset": 0, "length": 10}
    with World.open(directory) as current:
        message = current.send_message(chat_id=1, sender_id=2, text=TEXT, entities=[bold, quote])
        assert message["entities"] == [quote, bold]
        before = (current.history(1), current.events(), current.client_snapshot(1))
        with pytest.raises(ValueError, match="MESSAGE_NOT_MODIFIED"):
            current.edit_message(
                chat_id=1,
                message_id=1,
                bot_id=2,
                text=TEXT,
                entities=[quote, bold, quote],
            )
        assert (current.history(1), current.events(), current.client_snapshot(1)) == before


INVALID = [
    [
        {"type": "bold", "offset": 0, "length": 10},
        {"type": "blockquote", "offset": 2, "length": 8},
        {"type": "code", "offset": 4, "length": 4},
    ],
    [
        {"type": "blockquote", "offset": 0, "length": 10},
        {"type": "italic", "offset": 2, "length": 8},
        {"type": "pre", "offset": 4, "length": 4},
    ],
    [
        {"type": "code", "offset": 0, "length": 10},
        {"type": "blockquote", "offset": 4, "length": 4},
    ],
    [
        {"type": "blockquote", "offset": 0, "length": 10},
        {"type": "expandable_blockquote", "offset": 4, "length": 4},
    ],
    [
        {"type": "blockquote", "offset": 0, "length": 8},
        {"type": "code", "offset": 4, "length": 6},
    ],
    [{"type": "code", "offset": 1, "length": 1}],
    [{"type": "code", "offset": 0, "length": 10, "language": "python"}],
]


def test_invalid_ancestors_and_ranges_leave_state_and_ids_unchanged(tmp_path: Path) -> None:
    directory = tmp_path / "world"
    token = world(directory)
    with BotAPIServer(directory) as server:
        for entities in INVALID:
            status, body = request(
                server,
                token,
                "sendMessage",
                {"chat_id": 1, "text": TEXT, "entities": entities},
                form=False,
            )
            assert status == 400
            assert body["ok"] is False
        valid = [
            {"type": "blockquote", "offset": 0, "length": 10},
            {"type": "code", "offset": 4, "length": 4},
        ]
        status, body = request(
            server,
            token,
            "sendMessage",
            {"chat_id": 1, "text": TEXT, "entities": valid},
            form=False,
        )
        assert status == 200 and body["result"]["message_id"] == 1
        with World.open(directory) as current:
            before_history = current.history(1)
            before_events = current.events()
            before_snapshot = current.client_snapshot(1)
        for entities in INVALID:
            status, body = request(
                server,
                token,
                "editMessageText",
                {"chat_id": 1, "message_id": 1, "text": TEXT, "entities": entities},
                form=True,
            )
            assert status == 400
            assert body["ok"] is False
        with World.open(directory) as current:
            assert current.history(1) == before_history
            assert current.events() == before_events
            assert current.client_snapshot(1) == before_snapshot
            assert current.send_message(chat_id=1, sender_id=2, text="next")["id"] == 2
