"""Bot request encodings preserve the same complete HTTP and world results."""

import http.client
import json
from pathlib import Path
from urllib.parse import urlencode, urlsplit

import pytest

from gramlab.bot_api import BotAPIServer
from gramlab.world import World


@pytest.fixture
def bot_world(tmp_path: Path):
    directory = tmp_path / "world"
    with World.create(directory, seed=7, now=100) as world:
        world.create_user(first_name="Alice")
        world.create_user(first_name="Echo", is_bot=True)
        world.open_private_chat(user_id=1, bot_id=2)
        token = world.issue_bot_token(2)
    return directory, token


def wire(server, token, method, body=b"", *, content_type=None, verb="POST", query=""):
    endpoint = urlsplit(server.base_url)
    connection = http.client.HTTPConnection(endpoint.hostname, endpoint.port, timeout=5)
    headers = {"Content-Type": content_type} if content_type else {}
    try:
        connection.request(verb, f"/bot{token}/{method}" + query, body, headers)
        response = connection.getresponse()
        return response.status, json.loads(response.read())
    finally:
        connection.close()


def test_form_requests_preserve_unicode_and_acknowledge_updates(bot_world):
    directory, token = bot_world
    text = 'سلام نیم\u200cفاصله + & = % 😀 "false"'  # noqa: RUF001 — intentional Persian fixture
    with World.open(directory) as world:
        incoming = world.send_message(chat_id=1, sender_id=1, text="Start")
    content_type = "application/x-www-form-urlencoded; charset=UTF-8"
    with BotAPIServer(directory) as server:
        assert wire(server, token, "getMe", content_type=content_type) == (
            200,
            {"ok": True, "result": {"id": 2, "is_bot": True, "first_name": "Echo"}},
        )
        assert wire(
            server,
            token,
            "sendMessage",
            urlencode({"chat_id": 1, "text": text}).encode(),
            content_type=content_type,
        ) == (
            200,
            {
                "ok": True,
                "result": {
                    "message_id": 2,
                    "from": {"id": 2, "is_bot": True, "first_name": "Echo"},
                    "chat": {"id": 1, "type": "private", "first_name": "Alice"},
                    "date": 100,
                    "text": text,
                },
            },
        )
        assert wire(
            server, token, "getUpdates", b"offset=2&limit=1&timeout=0", content_type=content_type
        ) == (200, {"ok": True, "result": []})
    with World.open(directory) as world:
        assert world.history(1) == [
            incoming,
            {"id": 2, "chat_id": 1, "sender_id": 2, "date": 100, "text": text},
        ]
        assert world.poll_updates(2) == []


@pytest.mark.parametrize("verb", ["POST", "GET"])
def test_text_boolean_callback_answers_match_server_argument_semantics(bot_world, verb):
    directory, token = bot_world
    with World.open(directory) as world:
        world.send_message(chat_id=1, sender_id=2, text="Choose")
    with BotAPIServer(directory) as server:
        for index, (encoded, expected) in enumerate(
            [
                ("true", True),
                (" True ", True),
                ("YES", True),
                ("1", True),
                ("false", False),
                ("0", False),
                ("", False),
                ("no", False),
                ("anything", False),
            ]
        ):
            with World.open(directory) as world:
                callback = world.create_callback(
                    user_id=1, chat_id=1, message_id=1, data="choice", request_id=f"tap-{index}"
                )
            values = urlencode(
                {
                    "callback_query_id": callback["id"],
                    "show_alert": encoded,
                    "text": "",
                    "cache_time": 0,
                }
            )
            assert wire(
                server,
                token,
                "answerCallbackQuery",
                values.encode() if verb == "POST" else b"",
                content_type="application/x-www-form-urlencoded" if verb == "POST" else None,
                verb=verb,
                query="?" + values if verb == "GET" else "",
            ) == (200, {"ok": True, "result": True})
            with World.open(directory) as world:
                assert world.get_callback(user_id=1, callback_id=callback["id"]) == callback | {
                    "answer": {"text": "", "show_alert": expected, "cache_time": 0}
                }


@pytest.mark.parametrize("encoding", ["form", "get", "post-query", "json-strings", "json-native"])
def test_message_encodings_share_complete_keyboard_and_entity_results(bot_world, encoding):
    directory, token = bot_world
    text = "😀 سلام + 100%"
    keyboard = {"inline_keyboard": [[{"text": "تأیید", "callback_data": "a+b&x=1%"}]]}
    entities = [{"type": "bold", "offset": 0, "length": 2}]

    def call(server, method, parameters):
        if encoding != "json-native":
            parameters = {
                key: json.dumps(value, ensure_ascii=False)
                if isinstance(value, (dict, list))
                else value
                for key, value in parameters.items()
            }
        if encoding == "form":
            return wire(
                server,
                token,
                method,
                urlencode(parameters).encode(),
                content_type="application/x-www-form-urlencoded",
            )
        if encoding in {"get", "post-query"}:
            return wire(
                server,
                token,
                method,
                verb="GET" if encoding == "get" else "POST",
                query="?" + urlencode(parameters),
            )
        return wire(
            server, token, method, json.dumps(parameters).encode(), content_type="application/json"
        )

    expected = {
        "message_id": 1,
        "from": {"id": 2, "is_bot": True, "first_name": "Echo"},
        "chat": {"id": 1, "type": "private", "first_name": "Alice"},
        "date": 100,
        "text": text,
        "reply_markup": keyboard,
        "entities": entities,
    }
    with BotAPIServer(directory) as server:
        assert call(
            server,
            "sendMessage",
            {
                "chat_id": 1,
                "text": text,
                "reply_markup": keyboard,
                "entities": entities,
            },
        ) == (200, {"ok": True, "result": expected})
        with World.open(directory) as world:
            world.advance_time(5)
        revised = [{"type": "italic", "offset": 3, "length": 4}]
        assert call(
            server,
            "editMessageText",
            {
                "chat_id": 1,
                "message_id": 1,
                "text": text,
                "reply_markup": {"inline_keyboard": []},
                "entities": revised,
            },
        ) == (
            200,
            {
                "ok": True,
                "result": {
                    key: value
                    for key, value in (expected | {"entities": revised, "edit_date": 105}).items()
                    if key != "reply_markup"
                },
            },
        )
    with World.open(directory) as world:
        assert world.history(1) == [
            {
                "id": 1,
                "chat_id": 1,
                "sender_id": 2,
                "date": 100,
                "edit_date": 105,
                "text": text,
                "entities": [{"type": "italic", "offset": 3, "length": 4}],
            }
        ]
        assert world.client_snapshot(1)["messages"] == world.history(1)
        assert world.poll_updates(2) == []


def test_malformed_or_ambiguous_encodings_do_not_mutate_or_acknowledge(bot_world):
    directory, token = bot_world
    with World.open(directory) as world:
        incoming = world.send_message(chat_id=1, sender_id=1, text="Keep pending")
        before = world.snapshot()
        events = world.events()
    form = "application/x-www-form-urlencoded"
    cases = [
        ("getUpdates", b"offset=2&offset=3", form, ""),
        ("getUpdates", b"offset=2", form, "?offset=2"),
        ("getUpdates", b'{"offset":2}', "application/json", "?offset=2"),
        ("getUpdates", b"offset=2", form, "?timeout=0&timeout=1"),
        ("getUpdates", b"offset=2&limit=%FF", form, ""),
        ("getUpdates", b"offset=2&limit=\xff", form, ""),
        ("getUpdates", b"offset=2", form, "?timeout=%FF"),
        ("getUpdates", b"offset=2&limit=", form, ""),
        ("getUpdates", b"offset=2&" + b"&".join(f"x{i}=0".encode() for i in range(64)), form, ""),
        ("getUpdates", b"offset=2", "multipart/form-data; boundary=unused", ""),
        ("sendMessage", b"chat_id=1&text=", form, ""),
        ("sendMessage", b"chat_id=1&text=forged&text=other", form, ""),
        ("sendMessage", b"chat_id=1&text=x&entities=invalid", form, ""),
        (
            "sendMessage",
            b'chat_id=1&text=x&entities=[{"type":"bold","offset":0,"length":1,"length":2}]',
            form,
            "",
        ),
        (
            "sendMessage",
            b'chat_id=1&text=x&reply_markup={"inline_keyboard":[],"inline_keyboard":[]}',
            form,
            "",
        ),
        ("sendMessage", b"chat_id=1&text=x&reply_markup=[]", form, ""),
        ("sendMessage", b"chat_id=1&text=x&entities={}", form, ""),
        ("sendMessage", b"chat_id=1&text=" + b"x" * 65536, form, ""),
        ("getUpdates", '{"offset":2}'.encode("utf-16"), "application/json", ""),
        ("sendMessage", b"chat_id=1&text=x&entities=" + b"[" * 1100 + b"]" * 1100, form, ""),
        (
            "getUpdates",
            b'{"offset":2,"limit":' + b"[" * 1100 + b"]" * 1100 + b"}",
            "application/json",
            "",
        ),
    ]
    with BotAPIServer(directory) as server:
        for index, (method, body, content_type, query) in enumerate(cases):
            status, response = wire(
                server, token, method, body, content_type=content_type, query=query
            )
            assert (status, response["ok"], response.get("error_code")) == (400, False, 400), index
            with World.open(directory) as world:
                assert world.snapshot() == before
                assert world.events() == events
                assert world.poll_updates(2) == [{"update_id": 1, "message": incoming}]
        assert wire(server, token, "getMe", content_type=form) == (
            200,
            {"ok": True, "result": {"id": 2, "is_bot": True, "first_name": "Echo"}},
        )
