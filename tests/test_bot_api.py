"""Real bot HTTP contracts in independent process/network containment."""

import http.client
import json
import os
import shutil
from pathlib import Path
from urllib.parse import urlsplit

import pytest

from gramlab.bot_api import BotAPIServer
from gramlab.runtime import RuntimeProfile, Sandbox
from gramlab.world import World


def request(server, token, method, parameters=None, *, raw=None, verb="POST"):
    url = urlsplit(server.base_url)
    connection = http.client.HTTPConnection(url.hostname, url.port, timeout=5)
    try:
        body = raw if raw is not None else json.dumps(parameters or {})
        connection.request(
            verb, f"/bot{token}/{method}", body, {"Content-Type": "application/json"}
        )
        response = connection.getresponse()
        return response.status, json.loads(response.read())
    finally:
        connection.close()


def test_real_bot_receives_and_answers_a_virtual_user_over_http(tmp_path: Path) -> None:
    profile = RuntimeProfile.load(Path(os.environ["GRAMLAB_RUNTIME_PROFILE"]))
    shutil.copytree(
        "src/gramlab", tmp_path / "gramlab", ignore=shutil.ignore_patterns("__pycache__")
    )
    shutil.copy2("tests/fixtures/echo_bot.py", tmp_path / "echo_bot.py")
    result = Sandbox(profile).run(
        [profile.python, "-c", Path("tests/probes/bot_round_trip.py").read_text()],
        data=tmp_path,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    (tmp_path / "round-trip.json").write_text(result.stdout)
    user = {"id": 1, "is_bot": False, "first_name": "Sara", "language_code": "fa"}
    bot = {"id": 2, "is_bot": True, "first_name": "Echo", "username": "gramlab_echo_bot"}
    chat = {"id": 1, "type": "private", "first_name": "Sara"}
    incoming = {
        "message_id": 1,
        "from": user,
        "chat": chat,
        "date": 1700000000,
        "text": "سلام hello",
    }
    outgoing = {
        "message_id": 2,
        "from": bot,
        "chat": chat,
        "date": 1700000000,
        "text": "Echo: سلام hello",
    }
    assert json.loads(result.stdout) == {
        "bot": [
            {"method": "getMe", "parameters": {}, "response": {"ok": True, "result": bot}},
            {
                "method": "getUpdates",
                "parameters": {},
                "response": {"ok": True, "result": [{"update_id": 1, "message": incoming}]},
            },
            {
                "method": "sendMessage",
                "parameters": {"chat_id": 1, "text": "Echo: سلام hello"},
                "response": {"ok": True, "result": outgoing},
            },
            {
                "method": "getUpdates",
                "parameters": {"offset": 2},
                "response": {"ok": True, "result": []},
            },
        ],
        "history": [
            {"id": 1, "chat_id": 1, "sender_id": 1, "date": 1700000000, "text": "سلام hello"},
            {"id": 2, "chat_id": 1, "sender_id": 2, "date": 1700000000, "text": "Echo: سلام hello"},
        ],
        "pending": [],
    }


def test_bot_capabilities_are_scoped_to_their_world_and_chat(tmp_path: Path, capsys) -> None:
    first_dir, second_dir = tmp_path / "first", tmp_path / "second"
    tokens = []
    for directory in (first_dir, second_dir):
        with World.create(directory, seed=7, now=100) as world:
            world.create_user(first_name="Alice")
            world.create_user(first_name="Echo", is_bot=True)
            world.open_private_chat(user_id=1, bot_id=2)
            tokens.append(world.issue_bot_token(2))
    assert tokens[0] != tokens[1]
    with World.open(first_dir) as world:
        world.create_user(first_name="Unrelated bot", is_bot=True)
        unrelated = world.issue_bot_token(3)
    with BotAPIServer(first_dir) as first, BotAPIServer(second_dir) as second:
        assert request(first, tokens[0], "GETme", verb="GET") == (
            200,
            {"ok": True, "result": {"id": 2, "is_bot": True, "first_name": "Echo"}},
        )
        for server, token in [(first, tokens[1]), (second, tokens[0]), (first, "2:invalid")]:
            assert request(server, token, "getMe") == (
                401,
                {"ok": False, "error_code": 401, "description": "Unauthorized"},
            )
        assert request(first, unrelated, "sendMessage", {"chat_id": 1, "text": "wrong bot"}) == (
            400,
            {
                "ok": False,
                "error_code": 400,
                "description": "Private chat is not available to this bot",
            },
        )
        assert request(first, tokens[0], "inventedMethod") == (
            404,
            {"ok": False, "error_code": 404, "description": "GRAMLAB_UNSUPPORTED: Bot API method"},
        )
        assert request(
            first, tokens[0], "sendMessage", {"chat_id": 1, "text": "x", "parse_mode": "HTML"}
        ) == (
            400,
            {
                "ok": False,
                "error_code": 400,
                "description": "GRAMLAB_UNSUPPORTED: Bot API parameters",
            },
        )
    with World.open(first_dir) as world:
        assert world.history(1) == []
    assert capsys.readouterr() == ("", "")


@pytest.mark.parametrize(
    "body",
    [
        b'{"chat_id":1,"text":"first","text":"second"}',
        b'{"chat_id":99999999999999999999999999,"text":"x"}',
    ],
)
def test_malformed_requests_cannot_mutate_state_or_crash_the_handler(tmp_path: Path, body) -> None:
    directory = tmp_path / "world"
    with World.create(directory, seed=7, now=100) as world:
        world.create_user(first_name="Alice")
        world.create_user(first_name="Echo", is_bot=True)
        world.open_private_chat(user_id=1, bot_id=2)
        token = world.issue_bot_token(2)
        before = world.events()
    with BotAPIServer(directory) as server:
        status, response = request(server, token, "sendMessage", raw=body)
        assert status == 400
        assert response["ok"] is False
        assert response["error_code"] == 400
        assert request(server, token, "getMe")[0] == 200
    with World.open(directory) as world:
        assert world.history(1) == []
        assert world.events() == before


def test_get_query_parameters_limit_and_confirm_only_the_selected_updates(tmp_path: Path) -> None:
    directory = tmp_path / "world"
    user = {"id": 1, "is_bot": False, "first_name": "Alice", "username": "alice_local"}
    chat = {"id": 1, "type": "private", "first_name": "Alice", "username": "alice_local"}
    with World.create(directory, seed=7, now=100) as world:
        world.create_user(first_name="Alice", username="alice_local")
        world.create_user(first_name="Echo", is_bot=True)
        world.open_private_chat(user_id=1, bot_id=2)
        token = world.issue_bot_token(2)
        world.send_message(chat_id=1, sender_id=1, text="first")
        world.send_message(chat_id=1, sender_id=1, text="second")
    with BotAPIServer(directory) as server:
        assert request(server, token, "getUpdates?limit=1", verb="GET") == (
            200,
            {
                "ok": True,
                "result": [
                    {
                        "update_id": 1,
                        "message": {
                            "message_id": 1,
                            "from": user,
                            "chat": chat,
                            "date": 100,
                            "text": "first",
                        },
                    }
                ],
            },
        )
        assert request(server, token, "getUpdates?offset=2&limit=1", verb="GET") == (
            200,
            {
                "ok": True,
                "result": [
                    {
                        "update_id": 2,
                        "message": {
                            "message_id": 2,
                            "from": user,
                            "chat": chat,
                            "date": 100,
                            "text": "second",
                        },
                    }
                ],
            },
        )
        assert request(server, token, "getUpdates", {"offset": 3}) == (
            200,
            {"ok": True, "result": []},
        )
