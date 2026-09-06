"""Long-poll HTTP delivery and interruption against durable world updates."""

import http.client
import json
import os
import shutil
import socket
import time
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import asdict
from pathlib import Path
from urllib.parse import urlsplit

from test_bot_api import request

from gramlab.bot_api import BotAPIServer
from gramlab.runtime import RuntimeProfile, Sandbox
from gramlab.world import World


def test_empty_long_poll_waits_without_advancing_world_time(tmp_path: Path) -> None:
    directory = tmp_path / "world"
    with World.create(directory, seed=7, now=100) as world:
        world.create_user(first_name="Alice")
        world.create_user(first_name="Echo", is_bot=True)
        world.open_private_chat(user_id=1, bot_id=2)
        token = world.issue_bot_token(2)
        before = world.events()
    with BotAPIServer(directory) as server:
        started = time.monotonic()
        assert request(server, token, "getUpdates?timeout=1", verb="GET") == (
            200,
            {"ok": True, "result": []},
        )
        assert time.monotonic() - started >= 0.9
        assert request(server, token, "getUpdates", {"timeout": 0}) == (
            200,
            {"ok": True, "result": []},
        )
    with World.open(directory) as world:
        assert world.snapshot()["now"] == 100
        assert world.events() == before


def polling_world(directory: Path) -> str:
    with World.create(directory, seed=7, now=100) as world:
        world.create_user(first_name="Alice")
        world.create_user(first_name="Echo", is_bot=True)
        world.open_private_chat(user_id=1, bot_id=2)
        world.send_message(chat_id=1, sender_id=1, text="acknowledge me")
        return world.issue_bot_token(2)


def wait_for_confirmation(directory: Path, response: Future, *, bot_id: int = 2) -> None:
    # A committed public acknowledgment proves that the HTTP poll reached the world.
    # Poll this condition with a deadline instead of guessing server scheduling with a sleep.
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        assert not response.done(), response.result() if response.done() else None
        with World.open(directory) as world:
            if not world.poll_updates(bot_id):
                return
        time.sleep(0.005)
    raise AssertionError("Long poll did not confirm the sentinel update")


def test_waiting_poll_delivers_new_updates_and_repeats_them_until_acknowledged(
    tmp_path: Path,
) -> None:
    directory = tmp_path / "world"
    token = polling_world(directory)
    expected = {
        "ok": True,
        "result": [
            {
                "update_id": 2,
                "message": {
                    "message_id": 2,
                    "from": {"id": 1, "is_bot": False, "first_name": "Alice"},
                    "chat": {"id": 1, "type": "private", "first_name": "Alice"},
                    "date": 105,
                    "text": "سلام from another writer",
                },
            }
        ],
    }
    with BotAPIServer(directory) as server, ThreadPoolExecutor(max_workers=1) as worker:
        waiting = worker.submit(request, server, token, "getUpdates", {"offset": 2, "timeout": 50})
        wait_for_confirmation(directory, waiting)
        with World.open(directory) as world:
            world.advance_time(5)
            world.send_message(chat_id=1, sender_id=1, text="سلام from another writer")
        assert waiting.result(timeout=3) == (200, expected)
        assert request(server, token, "getUpdates", {"timeout": 50}) == (200, expected)
        assert request(server, token, "getUpdates", {"offset": 3}) == (
            200,
            {"ok": True, "result": []},
        )


def test_new_poll_interrupts_the_previous_consumer_for_the_same_bot(tmp_path: Path) -> None:
    directory = tmp_path / "world"
    token = polling_world(directory)
    with BotAPIServer(directory) as server, ThreadPoolExecutor(max_workers=1) as worker:
        waiting = worker.submit(request, server, token, "getUpdates", {"offset": 2, "timeout": 2})
        wait_for_confirmation(directory, waiting)
        assert request(server, token, "getUpdates", {"offset": 2}) == (
            200,
            {"ok": True, "result": []},
        )
        assert waiting.result(timeout=3) == (
            409,
            {
                "ok": False,
                "error_code": 409,
                "description": "Conflict: terminated by other getUpdates request; "
                "make sure that only one bot instance is running",
            },
        )


def test_server_shutdown_releases_pending_long_polls(tmp_path: Path) -> None:
    directory = tmp_path / "world"
    token = polling_world(directory)
    with ThreadPoolExecutor(max_workers=1) as worker:
        with BotAPIServer(directory) as server:
            waiting = worker.submit(
                request, server, token, "getUpdates", {"offset": 2, "timeout": 50}
            )
            wait_for_confirmation(directory, waiting)
            started = time.monotonic()
        assert time.monotonic() - started < 2
        assert waiting.result(timeout=1) == (
            503,
            {
                "ok": False,
                "error_code": 503,
                "description": "GRAMLAB_SHUTDOWN: Bot API server is stopping",
            },
        )
    with World.open(directory) as world:
        assert world.history(1)[0]["text"] == "acknowledge me"


def test_invalid_polling_options_neither_acknowledge_nor_interrupt_a_valid_poll(
    tmp_path: Path,
) -> None:
    directory = tmp_path / "world"
    token = polling_world(directory)
    invalid = [
        {"timeout": True},
        {"timeout": None},
        {"timeout": 0.5},
        {"timeout": "bad"},
        {"timeout": 2**63},
        {"limit": 0},
        {"limit": 101},
        {"limit": True},
        {"allowed_updates": []},
    ]
    with BotAPIServer(directory) as server, ThreadPoolExecutor(max_workers=1) as worker:
        for values in invalid:
            assert request(server, token, "getUpdates", {"offset": 999} | values)[0] == 400
        with World.open(directory) as world:
            assert [update["update_id"] for update in world.poll_updates(2)] == [1]
        waiting = worker.submit(request, server, token, "getUpdates", {"offset": 2, "timeout": 50})
        wait_for_confirmation(directory, waiting)
        for values in invalid:
            assert request(server, token, "getUpdates", {"offset": 999} | values)[0] == 400
        assert request(server, "invalid", "getUpdates", {"offset": 999})[0] == 401
        with World.open(directory) as world:
            world.send_message(chat_id=1, sender_id=1, text="still waiting")
        assert waiting.result(timeout=3) == (
            200,
            {
                "ok": True,
                "result": [
                    {
                        "update_id": 2,
                        "message": {
                            "message_id": 2,
                            "from": {"id": 1, "is_bot": False, "first_name": "Alice"},
                            "chat": {"id": 1, "type": "private", "first_name": "Alice"},
                            "date": 100,
                            "text": "still waiting",
                        },
                    }
                ],
            },
        )


def test_polls_for_other_bots_and_worlds_do_not_interrupt_each_other(tmp_path: Path) -> None:
    first_dir, second_dir = tmp_path / "first", tmp_path / "second"
    first_token, second_token = polling_world(first_dir), polling_world(second_dir)
    with World.open(first_dir) as world:
        world.create_user(first_name="Other", is_bot=True)
        world.open_private_chat(user_id=1, bot_id=3)
        third_token = world.issue_bot_token(3)
        world.send_message(chat_id=2, sender_id=1, text="other sentinel")
    with (
        BotAPIServer(first_dir) as first,
        BotAPIServer(second_dir) as second,
        ThreadPoolExecutor(max_workers=3) as workers,
    ):
        first_poll = workers.submit(
            request, first, first_token, "getUpdates", {"offset": 2, "timeout": 50}
        )
        second_poll = workers.submit(
            request, second, second_token, "getUpdates", {"offset": 2, "timeout": 50}
        )
        third_poll = workers.submit(
            request, first, third_token, "getUpdates", {"offset": 2, "timeout": 50}
        )
        wait_for_confirmation(first_dir, first_poll)
        wait_for_confirmation(second_dir, second_poll)
        wait_for_confirmation(first_dir, third_poll, bot_id=3)
        assert request(first, first_token, "getUpdates")[0] == 200
        assert first_poll.result(timeout=3)[0] == 409
        for directory, chat_id, text in [
            (first_dir, 2, "other bot"),
            (second_dir, 1, "other world"),
        ]:
            with World.open(directory) as world:
                world.send_message(chat_id=chat_id, sender_id=1, text=text)
        for future, message_id, text in [
            (third_poll, 2, "other bot"),
            (second_poll, 2, "other world"),
        ]:
            assert future.result(timeout=3) == (
                200,
                {
                    "ok": True,
                    "result": [
                        {
                            "update_id": 2,
                            "message": {
                                "message_id": message_id,
                                "from": {"id": 1, "is_bot": False, "first_name": "Alice"},
                                "chat": {"id": 1, "type": "private", "first_name": "Alice"},
                                "date": 100,
                                "text": text,
                            },
                        }
                    ],
                },
            )


def test_disconnected_bot_can_retry_without_losing_updates_or_logging_capabilities(
    tmp_path: Path, capsys
) -> None:
    directory = tmp_path / "world"
    token = polling_world(directory)
    with BotAPIServer(directory) as server:
        endpoint = urlsplit(server.base_url)
        connection = http.client.HTTPConnection(endpoint.hostname, endpoint.port, timeout=5)
        try:
            connection.request("GET", f"/bot{token}/getUpdates?offset=2&timeout=50")
            wait_for_confirmation(directory, Future())
            connection.sock.shutdown(socket.SHUT_RDWR)
        finally:
            connection.close()
        with World.open(directory) as world:
            world.send_message(chat_id=1, sender_id=1, text="retained after disconnect")
        expected = {
            "ok": True,
            "result": [
                {
                    "update_id": 2,
                    "message": {
                        "message_id": 2,
                        "from": {"id": 1, "is_bot": False, "first_name": "Alice"},
                        "chat": {"id": 1, "type": "private", "first_name": "Alice"},
                        "date": 100,
                        "text": "retained after disconnect",
                    },
                }
            ],
        }
        assert request(server, token, "getUpdates", {"offset": 2}) == (200, expected)
    # Closing joins handlers, so this observes all diagnostics from the disconnected request.
    assert capsys.readouterr() == ("", "")
    with BotAPIServer(directory) as restarted:
        assert request(restarted, token, "getUpdates", {"offset": 2}) == (200, expected)
        assert request(restarted, token, "getUpdates", {"offset": 3}) == (
            200,
            {"ok": True, "result": []},
        )


def test_shutdown_also_closes_an_incomplete_http_request(tmp_path: Path, capsys) -> None:
    directory = tmp_path / "world"
    token = polling_world(directory)
    connection = None
    try:
        with BotAPIServer(directory) as server:
            endpoint = urlsplit(server.base_url)
            connection = http.client.HTTPConnection(endpoint.hostname, endpoint.port, timeout=5)
            connection.putrequest("POST", f"/bot{token}/getUpdates")
            connection.putheader("Content-Type", "application/json")
            connection.putheader("Content-Length", "100")
            connection.endheaders(b"{")
            assert request(server, token, "getMe")[0] == 200
            started = time.monotonic()
        assert time.monotonic() - started < 2
    finally:
        if connection is not None:
            connection.close()
    assert capsys.readouterr() == ("", "")
    with World.open(directory) as world:
        assert [update["update_id"] for update in world.poll_updates(2)] == [1]


def test_real_private_bot_waits_then_answers_the_virtual_user(tmp_path: Path) -> None:
    profile = RuntimeProfile.load(Path(os.environ["GRAMLAB_RUNTIME_PROFILE"]))
    shutil.copytree(
        "src/gramlab", tmp_path / "gramlab", ignore=shutil.ignore_patterns("__pycache__")
    )
    (tmp_path / "component-profile.json").write_text(json.dumps(asdict(profile)))
    shutil.copy2("tests/probes/component_bot.py", tmp_path / "component_bot.py")
    shutil.copy2("tests/fixtures/echo_bot.py", tmp_path / "echo_bot.py")
    result = Sandbox(profile).supervise(
        [profile.python, "-c", Path("tests/probes/long_poll_bot.py").read_text()],
        data=tmp_path,
        timeout=20,
    )
    assert result.returncode == 0, result.stderr
    (tmp_path / "long-poll.json").write_text(result.stdout)
    user = {"id": 1, "is_bot": False, "first_name": "Alice"}
    bot = {"id": 2, "is_bot": True, "first_name": "Echo"}
    chat = {"id": 1, "type": "private", "first_name": "Alice"}
    incoming = {
        "message_id": 2,
        "from": user,
        "chat": chat,
        "date": 100,
        "text": "سلام after polling",
    }
    outgoing = {
        "message_id": 3,
        "from": bot,
        "chat": chat,
        "date": 100,
        "text": "Echo: سلام after polling",
    }
    assert json.loads(result.stdout) == {
        "bot": [
            {"method": "getMe", "parameters": {}, "response": {"ok": True, "result": bot}},
            {
                "method": "getUpdates",
                "parameters": {"offset": 2, "timeout": 30},
                "response": {"ok": True, "result": [{"update_id": 2, "message": incoming}]},
            },
            {
                "method": "sendMessage",
                "parameters": {"chat_id": 1, "text": "Echo: سلام after polling"},
                "response": {"ok": True, "result": outgoing},
            },
            {
                "method": "getUpdates",
                "parameters": {"offset": 3},
                "response": {"ok": True, "result": []},
            },
        ],
        "history": [
            {"id": 1, "chat_id": 1, "sender_id": 1, "date": 100, "text": "readiness sentinel"},
            {"id": 2, "chat_id": 1, "sender_id": 1, "date": 100, "text": "سلام after polling"},
            {
                "id": 3,
                "chat_id": 1,
                "sender_id": 2,
                "date": 100,
                "text": "Echo: سلام after polling",
            },
        ],
        "pending": [],
    }
