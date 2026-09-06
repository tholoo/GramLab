"""Scenario control crosses HTTP; the world remains the sole authority."""

import errno
import http.client
import json
import os
import shutil
import socket
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from pathlib import Path
from threading import Barrier
from urllib.parse import urlsplit

import pytest

from gramlab.runtime import RuntimeProfile, Sandbox
from gramlab.world import World


def call(server, operation, parameters=None, *, capability=None, world_id=None, raw=None):
    endpoint = urlsplit(server.base_url)
    connection = http.client.HTTPConnection(endpoint.hostname, endpoint.port, timeout=5)
    payload = {
        "schema": 1,
        "world_id": server.world_id if world_id is None else world_id,
        "operation": operation,
        "parameters": parameters or {},
    }
    try:
        connection.request(
            "POST",
            "/v1/world",
            json.dumps(payload) if raw is None else raw,
            {
                "Content-Type": "application/json",
                "Authorization": "Bearer "
                + (server.capability if capability is None else capability),
            },
        )
        response = connection.getresponse()
        return response.status, json.loads(response.read())
    finally:
        connection.close()


def test_control_actions_and_reads_preserve_complete_world_state(tmp_path: Path):
    from gramlab._control import WorldControl

    directory = tmp_path / "world"
    with World.create(directory, seed=7, now=100):
        pass
    with WorldControl(directory) as server:

        def expected(result):
            return 200, {"schema": 1, "world_id": server.world_id, "result": result}

        alice = {"id": 1, "is_bot": False, "first_name": "Alice", "language_code": "fa"}
        echo = {"id": 2, "is_bot": True, "first_name": "Echo"}
        chat = {"id": 1, "type": "private", "user_id": 1, "bot_id": 2}
        message = {"id": 1, "chat_id": 1, "sender_id": 1, "date": 100, "text": "سلام hello"}
        assert call(
            server, "create_user", {"first_name": "Alice", "language_code": "fa"}
        ) == expected(alice)
        assert call(server, "create_user", {"first_name": "Echo", "is_bot": True}) == expected(echo)
        assert call(server, "open_private_chat", {"user_id": 1, "bot_id": 2}) == expected(chat)
        assert call(
            server, "send_message", {"chat_id": 1, "sender_id": 1, "text": "سلام hello"}
        ) == expected(message)
        assert call(server, "advance_time", {"seconds": 5}) == expected(105)
        assert call(server, "history", {"chat_id": 1}) == expected([message])
        state = {"schema": 1, "seed": 7, "now": 105, "users": [alice, echo], "chats": [chat]}
        assert call(server, "snapshot") == expected(state)
        journal = [
            {"sequence": 1, "type": "user.created", "data": alice},
            {"sequence": 2, "type": "user.created", "data": echo},
            {"sequence": 3, "type": "chat.created", "data": chat},
            {"sequence": 4, "type": "message.created", "data": message},
            {"sequence": 5, "type": "clock.advanced", "data": {"now": 105}},
        ]
        assert call(server, "events") == expected(journal)
        assert call(server, "events", {"after": 4}) == expected([journal[-1]])
    with World.open(directory) as world:
        assert world.snapshot() == state
        assert world.history(1) == [message]
        assert world.events() == journal
        assert world.poll_updates(2) == [{"update_id": 1, "message": message}]


def test_control_capability_cannot_cross_worlds_or_issue_other_credentials(tmp_path: Path, capsys):
    from gramlab._control import WorldControl

    directory, other_directory = tmp_path / "world", tmp_path / "other"
    with World.create(directory, seed=7, now=100) as world:
        world.create_user(first_name="Alice")
        world.create_user(first_name="Echo", is_bot=True)
        bot_token = world.issue_bot_token(2)
        client_token = world.issue_client_token(1)
        before = world.snapshot()
        events = world.events()
    with World.create(other_directory, seed=7, now=100):
        pass
    with WorldControl(directory) as server, WorldControl(other_directory) as other:
        for token in ("", "invalid", bot_token, client_token, other.capability):
            assert call(server, "create_user", {"first_name": "forged"}, capability=token) == (
                401,
                {"error": {"code": "unauthorized", "message": "Run control capability required"}},
            )
        assert call(server, "create_user", {"first_name": "forged"}, world_id=other.world_id) == (
            409,
            {
                "error": {
                    "code": "wrong_world",
                    "message": "Control request identifies another world",
                }
            },
        )
        for operation in ("issue_bot_token", "issue_client_token", "__init__", "open", "close"):
            assert call(server, operation, {"bot_id": 2}) == (
                404,
                {"error": {"code": "unsupported", "message": "Unknown world control operation"}},
            )
        previous = server.capability
    with WorldControl(directory) as reopened:
        assert call(reopened, "snapshot", capability=previous)[0] == 401
    with World.open(directory) as world:
        assert world.snapshot() == before
        assert world.events() == events
    output = capsys.readouterr()
    assert output.out == output.err == ""


def test_invalid_control_envelopes_and_parameters_leave_state_unchanged(tmp_path: Path):
    from gramlab._control import WorldControl

    directory = tmp_path / "world"
    with World.create(directory, seed=7, now=100) as world:
        before = world.snapshot()
    with WorldControl(directory) as server:
        base = {
            "schema": 1,
            "world_id": server.world_id,
            "operation": "create_user",
            "parameters": {"first_name": "forged"},
        }
        malformed = [
            {},
            [],
            None,
            base | {"schema": True},
            base | {"schema": 2},
            base | {"unknown": 1},
            base | {"operation": []},
            base | {"parameters": []},
            base | {"parameters": {"first_name": 3}},
            base | {"parameters": {"first_name": "forged", "is_bot": "false"}},
            base | {"parameters": {"first_name": "forged", "username": []}},
            base | {"parameters": {"first_name": "\ud800"}},
            base | {"parameters": {"first_name": "forged", "path": "/world"}},
            base | {"operation": "events", "parameters": {"after": -1}},
        ]
        raw = [json.dumps(value) for value in malformed]
        raw += [
            json.dumps(base).replace('"schema": 1', '"schema": 1, "schema": 1'),
            json.dumps(base).replace('"forged"', '"forged", "first_name": "other"'),
            json.dumps(base).encode("utf-16"),
            '{"schema":' + "[" * 1100 + "]" * 1100 + "}",
        ]
        for index, body in enumerate(raw):
            status, response = call(server, "unused", raw=body)
            assert status == 400, index
            assert response["error"]["code"] == "invalid_request"
            with World.open(directory) as world:
                assert world.snapshot() == before
                assert world.events() == []


def test_control_never_rebinds_its_capability_to_a_replacement_world(tmp_path: Path):
    from gramlab._control import WorldControl

    directory = tmp_path / "world"
    with World.create(directory, seed=7, now=100):
        pass
    with WorldControl(directory) as server:
        directory.rename(tmp_path / "retained")
        with World.create(directory, seed=8, now=200) as replacement:
            before = replacement.snapshot()
        assert call(server, "create_user", {"first_name": "forged"}) == (
            409,
            {"error": {"code": "wrong_world", "message": "Control world has been replaced"}},
        )
    with World.open(directory) as replacement:
        assert replacement.snapshot() == before
        assert replacement.events() == []


def test_control_rejects_ambiguous_http_framing_before_world_effects(tmp_path: Path, capsys):
    from gramlab._control import WorldControl

    directory = tmp_path / "world"
    with World.create(directory, seed=7, now=100):
        pass
    with WorldControl(directory) as server:
        endpoint = urlsplit(server.base_url)
        payload = json.dumps(
            {
                "schema": 1,
                "world_id": server.world_id,
                "operation": "create_user",
                "parameters": {"first_name": "forged"},
            }
        ).encode()
        normal = [
            ("Authorization", "Bearer " + server.capability),
            ("Content-Type", "application/json"),
            ("Content-Length", str(len(payload))),
        ]
        cases = [
            ([*normal, normal[0]], 401),
            (normal[1:], 401),
            ([*normal, normal[2]], 400),
            ([*normal, ("Transfer-Encoding", "chunked")], 400),
            ([normal[0], ("Content-Type", "text/plain"), normal[2]], 400),
        ]
        for headers, expected_status in cases:
            connection = http.client.HTTPConnection(endpoint.hostname, endpoint.port, timeout=5)
            try:
                connection.putrequest("POST", "/v1/world")
                for name, value in headers:
                    connection.putheader(name, value)
                connection.endheaders(payload)
                response = connection.getresponse()
                assert response.status == expected_status
                assert "error" in json.loads(response.read())
            finally:
                connection.close()
            with World.open(directory) as world:
                assert world.snapshot()["users"] == []
                assert world.events() == []
    output = capsys.readouterr()
    assert output.out == output.err == ""


def test_control_callback_retries_observe_the_real_bot_answer(tmp_path: Path):
    from test_bot_api import request

    from gramlab._control import WorldControl
    from gramlab.bot_api import BotAPIServer

    directory = tmp_path / "world"
    with World.create(directory, seed=7, now=100) as world:
        world.create_user(first_name="Alice")
        world.create_user(first_name="Echo", is_bot=True)
        world.open_private_chat(user_id=1, bot_id=2)
        message = world.send_message(chat_id=1, sender_id=2, text="Choose")
        token = world.issue_bot_token(2)
    command = {"user_id": 1, "chat_id": 1, "message_id": 1, "data": "choice", "request_id": "tap-1"}
    with WorldControl(directory) as server, BotAPIServer(directory) as api:
        status, result = call(server, "create_callback", command)
        assert status == 200
        callback = result["result"]
        assert result == {
            "schema": 1,
            "world_id": server.world_id,
            "result": {
                "id": callback["id"],
                "user_id": 1,
                "chat_id": 1,
                "message": message,
                "data": "choice",
                "chat_instance": callback["chat_instance"],
                "answer": None,
            },
        }
        assert call(server, "create_callback", command) == (200, result)
        assert request(
            api,
            token,
            "answerCallbackQuery",
            {
                "callback_query_id": callback["id"],
                "text": "Confirmed",
                "show_alert": True,
            },
        ) == (200, {"ok": True, "result": True})
        assert call(server, "get_callback", {"user_id": 1, "callback_id": callback["id"]}) == (
            200,
            {
                "schema": 1,
                "world_id": server.world_id,
                "result": callback
                | {
                    "answer": {"text": "Confirmed", "show_alert": True, "cache_time": 0},
                },
            },
        )
    with World.open(directory) as world:
        assert len(world.poll_updates(2)) == 1


def test_private_scenario_process_drives_a_separate_real_bot(tmp_path: Path):
    profile = RuntimeProfile.load(Path(os.environ["GRAMLAB_RUNTIME_PROFILE"]))
    shutil.copytree(
        "src/gramlab", tmp_path / "gramlab", ignore=shutil.ignore_patterns("__pycache__")
    )
    (tmp_path / "component-profile.json").write_text(json.dumps(asdict(profile)))
    for name in ("scenario_actor.py", "echo_bot.py"):
        shutil.copy2(Path("tests/fixtures") / name, tmp_path / name)
    for name in ("scenario_round_trip.py", "component_bot.py"):
        shutil.copy2(Path("tests/probes") / name, tmp_path / name)
    result = Sandbox(profile).supervise(
        [profile.python, "/work/scenario_round_trip.py"],
        data=tmp_path,
        timeout=35,
    )
    assert result.returncode == 0, result.stderr
    (tmp_path / "scenario-result.json").write_text(result.stdout)
    observed = json.loads(result.stdout)
    assert observed["isolation"] == {
        "ready": True,
        "readable": [],
        "interfaces": ["lo"],
        "external_errno": errno.ENETUNREACH,
    }
    history = [
        {"id": 1, "chat_id": 1, "sender_id": 1, "date": 1700000000, "text": "سلام hello"},
        {"id": 2, "chat_id": 1, "sender_id": 2, "date": 1700000000, "text": "Echo: سلام hello"},
    ]
    assert observed["history"] == observed["scenario"]["history"] == history
    assert observed["pending"] == []
    sent = {
        "method": "sendMessage",
        "parameters": {"chat_id": 1, "text": "Echo: سلام hello"},
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
                "text": "Echo: سلام hello",
            },
        },
    }
    sara = {"id": 1, "is_bot": False, "first_name": "Sara", "language_code": "fa"}
    echo = {"id": 2, "is_bot": True, "first_name": "Echo", "username": "gramlab_echo_bot"}
    chat = {"id": 1, "type": "private", "user_id": 1, "bot_id": 2}
    state = {"schema": 1, "seed": 7, "now": 1700000000, "users": [sara, echo], "chats": [chat]}
    journal = [
        {"sequence": 1, "type": "user.created", "data": sara},
        {"sequence": 2, "type": "user.created", "data": echo},
        {"sequence": 3, "type": "chat.created", "data": chat},
        {"sequence": 4, "type": "message.created", "data": history[0]},
        {"sequence": 5, "type": "message.created", "data": history[1]},
    ]
    assert observed["scenario"] == {"history": history, "snapshot": state, "events": journal}
    assert observed["bot"] == [
        {"method": "getMe", "parameters": {}, "response": {"ok": True, "result": echo}},
        {
            "method": "getUpdates",
            "parameters": {"timeout": 30},
            "response": {
                "ok": True,
                "result": [
                    {
                        "update_id": 1,
                        "message": {
                            "message_id": 1,
                            "from": sara,
                            "chat": {"id": 1, "type": "private", "first_name": "Sara"},
                            "date": 1700000000,
                            "text": "سلام hello",
                        },
                    }
                ],
            },
        },
        sent,
        {
            "method": "getUpdates",
            "parameters": {"offset": 2},
            "response": {"ok": True, "result": []},
        },
    ]
    with World.open(tmp_path / "world") as world:
        assert world.snapshot() == state
        assert world.events() == journal
    assert (tmp_path / "scenario" / "scenario-state.txt").read_text() == "private scenario state"
    assert not (tmp_path / "bot" / "scenario-state.txt").exists()


def test_incomplete_control_body_never_commits_or_logs_a_traceback(tmp_path: Path, capsys):
    from gramlab._control import WorldControl

    directory = tmp_path / "world"
    with World.create(directory, seed=7, now=100):
        pass
    with WorldControl(directory) as server:
        endpoint = urlsplit(server.base_url)
        payload = json.dumps(
            {
                "schema": 1,
                "world_id": server.world_id,
                "operation": "create_user",
                "parameters": {"first_name": "forged"},
            }
        ).encode()
        for half_close in (True, False):
            connection = http.client.HTTPConnection(endpoint.hostname, endpoint.port, timeout=3)
            try:
                connection.putrequest("POST", "/v1/world")
                connection.putheader("Authorization", "Bearer " + server.capability)
                connection.putheader("Content-Type", "application/json")
                connection.putheader("Content-Length", str(len(payload) + 1))
                connection.endheaders(payload)
                if half_close:
                    connection.sock.shutdown(socket.SHUT_WR)
                    response = connection.getresponse()
                    assert response.status == 400
                    assert json.loads(response.read())["error"]["code"] == "invalid_request"
                else:
                    with pytest.raises(http.client.RemoteDisconnected):
                        connection.getresponse()
            finally:
                connection.close()
            with World.open(directory) as world:
                assert world.snapshot()["users"] == []
                assert world.events() == []
    output = capsys.readouterr()
    assert output.out == output.err == ""


def test_concurrent_control_writers_keep_worlds_and_event_order_independent(tmp_path: Path):
    from gramlab._control import WorldControl
    from gramlab.scenario import Scenario

    for label in ("alpha", "beta"):
        with World.create(tmp_path / label, seed=7, now=100) as world:
            world.create_user(first_name="Alice")
            world.create_user(first_name="Echo", is_bot=True)
            world.open_private_chat(user_id=1, bot_id=2)
    ready = Barrier(4)
    with WorldControl(tmp_path / "alpha") as alpha, WorldControl(tmp_path / "beta") as beta:
        clients = {
            label: Scenario(server.base_url, capability=server.capability, world_id=server.world_id)
            for label, server in (("alpha", alpha), ("beta", beta))
        }

        def write(worker):
            label, number = worker
            ready.wait(timeout=5)
            for index in range(3):
                text = f"{label}-{number}-{index}"
                message = clients[label].send_message(chat_id=1, sender_id=1, text=text)
                assert message == {
                    "id": message["id"],
                    "chat_id": 1,
                    "sender_id": 1,
                    "date": 100,
                    "text": text,
                }

        with ThreadPoolExecutor(max_workers=4) as workers:
            list(
                workers.map(
                    write,
                    [
                        ("alpha", 0),
                        ("alpha", 1),
                        ("beta", 0),
                        ("beta", 1),
                    ],
                )
            )
        for label, server in (("alpha", alpha), ("beta", beta)):
            history = call(server, "history", {"chat_id": 1})[1]["result"]
            assert [message["id"] for message in history] == [1, 2, 3, 4, 5, 6]
            assert {message["text"] for message in history} == {
                f"{label}-{worker}-{index}" for worker in range(2) for index in range(3)
            }
            assert call(server, "events", {"after": 3}) == (
                200,
                {
                    "schema": 1,
                    "world_id": server.world_id,
                    "result": [
                        {"sequence": index + 4, "type": "message.created", "data": message}
                        for index, message in enumerate(history)
                    ],
                },
            )
            with World.open(tmp_path / label) as world:
                assert world.history(1) == history
                assert world.poll_updates(2) == [
                    {"update_id": index + 1, "message": message}
                    for index, message in enumerate(history)
                ]
