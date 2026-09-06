"""Durable semantic sends and persona message positions through actual client HTTP."""

import http.client
import json
import socket
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
from threading import Barrier
from urllib.parse import urlsplit

from gramlab.client_bridge import ClientBridge
from gramlab.world import World


def client_world(directory):
    with World.create(directory, seed=7, now=100) as world:
        world.create_user(first_name="Alice", language_code="fa")
        world.create_user(first_name="Echo", is_bot=True)
        world.create_user(first_name="Bob")
        world.create_user(first_name="Other", is_bot=True)
        world.open_private_chat(user_id=1, bot_id=2)
        world.open_private_chat(user_id=3, bot_id=2)
        world.open_private_chat(user_id=1, bot_id=4)
        return world.world_id, world.issue_client_token(1), world.issue_client_token(3)


def call(server, token, path, body=None, *, raw=None):
    url = urlsplit(server.base_url)
    connection = http.client.HTTPConnection(url.hostname, url.port, timeout=5)
    try:
        headers = {"Authorization": f"Bearer {token}"}
        payload = None
        if body is not None or raw is not None:
            headers["Content-Type"] = "application/json"
            payload = raw if raw is not None else json.dumps(body)
        connection.request("POST" if payload is not None else "GET", path, payload, headers)
        response = connection.getresponse()
        return response.status, json.loads(response.read())
    finally:
        connection.close()


def envelope(world_id, user_id=1):
    return {"schema": 2, "world_id": world_id, "user_id": user_id}


def test_committed_send_replays_identically_after_response_loss_and_restart(tmp_path, capsys):
    directory = tmp_path / "world"
    world_id, token, _ = client_world(directory)
    command = {"chat_id": 1, "request_id": "-9223372036854775808", "text": "سلام hello 😀"}
    message = {"id": 1, "chat_id": 1, "sender_id": 1, "date": 100, "text": command["text"]}
    result = {"request_id": command["request_id"], "position": 1, "message": message}
    with ClientBridge(directory) as server:
        url = urlsplit(server.base_url)
        connection = http.client.HTTPConnection(url.hostname, url.port, timeout=5)
        try:
            connection.request(
                "POST",
                "/v2/messages",
                json.dumps(command),
                {"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            )
            deadline = time.monotonic() + 3
            while True:
                with World.open(directory) as world:
                    if world.history(1):
                        break
                assert time.monotonic() < deadline, "Client send never committed"
                time.sleep(0.005)
            connection.sock.shutdown(socket.SHUT_RDWR)
        finally:
            connection.close()
    with World.open(directory) as world:
        world.advance_time(5)
        world.send_message(chat_id=1, sender_id=2, text="Echo reply")
    with ClientBridge(directory) as restarted:
        assert call(restarted, token, "/v2/messages", command) == (
            200,
            envelope(world_id) | {"send": result},
        )
        status, snapshot = call(restarted, token, "/v2/snapshot")
        assert status == 200 and snapshot["message_position"] == 2
        assert snapshot["sends"] == [result]
        assert snapshot["messages"] == [
            message,
            {"id": 2, "chat_id": 1, "sender_id": 2, "date": 105, "text": "Echo reply"},
        ]
        assert call(restarted, token, "/v2/changes?after=0") == (
            200,
            envelope(world_id)
            | {
                "cursor": 2,
                "head": 2,
                "now": 105,
                "changes": [
                    {
                        "position": 1,
                        "type": "message.created",
                        "data": message,
                        "request_id": command["request_id"],
                    },
                    {"position": 2, "type": "message.created", "data": snapshot["messages"][1]},
                ],
            },
        )
    with World.open(directory) as world:
        assert world.poll_updates(2) == [{"update_id": 1, "message": message}]
        assert len([event for event in world.events() if event["type"] == "message.created"]) == 2
    assert capsys.readouterr() == ("", "")


def test_persona_positions_count_only_its_message_changes_across_peers(tmp_path):
    directory = tmp_path / "world"
    world_id, alice, bob = client_world(directory)
    with World.open(directory) as world:
        world.advance_time(4)
        first = world.send_message(chat_id=1, sender_id=2, text="first")
        hidden = world.send_message(chat_id=2, sender_id=2, text="Bob only")
        second = world.send_message(chat_id=3, sender_id=4, text="second peer")
        world.create_callback(user_id=1, chat_id=1, message_id=1, data="tap", request_id="tap")
        edited = world.edit_message(chat_id=1, bot_id=2, message_id=1, text="edited")
    with ClientBridge(directory) as server:
        assert call(server, alice, "/v2/changes?after=0&limit=2") == (
            200,
            envelope(world_id)
            | {
                "cursor": 2,
                "head": 3,
                "now": 104,
                "changes": [
                    {"position": 1, "type": "message.created", "data": first},
                    {"position": 2, "type": "message.created", "data": second},
                ],
            },
        )
        assert call(server, alice, "/v2/changes?after=2") == (
            200,
            envelope(world_id)
            | {
                "cursor": 3,
                "head": 3,
                "now": 104,
                "changes": [{"position": 3, "type": "message.edited", "data": edited}],
            },
        )
        assert call(server, bob, "/v2/changes?after=0") == (
            200,
            envelope(world_id, 3)
            | {
                "cursor": 1,
                "head": 1,
                "now": 104,
                "changes": [{"position": 1, "type": "message.created", "data": hidden}],
            },
        )
        assert call(server, alice, "/v2/changes?after=3") == (
            200,
            envelope(world_id) | {"cursor": 3, "head": 3, "now": 104, "changes": []},
        )
        for query in (
            "after=-1",
            "after=4",
            "after=true",
            "after=0&limit=0",
            "after=0&limit=1001",
            "after=0&user_id=3",
        ):
            assert call(server, alice, "/v2/changes?" + query)[0] == 400


def test_concurrent_send_retries_commit_once_but_equal_text_and_other_peers_are_distinct(tmp_path):
    directory = tmp_path / "world"
    world_id, alice, bob = client_world(directory)
    command = {"chat_id": 1, "request_id": "same-id", "text": "identical text"}
    barrier = Barrier(6)
    with ClientBridge(directory) as server:

        def send(_):
            barrier.wait()
            return call(server, alice, "/v2/messages", command)

        with ThreadPoolExecutor(max_workers=6) as workers:
            results = list(workers.map(send, range(6)))
        assert all(result == results[0] for result in results)
        assert results[0] == (
            200,
            envelope(world_id)
            | {
                "send": {
                    "request_id": "same-id",
                    "position": 1,
                    "message": {
                        "id": 1,
                        "chat_id": 1,
                        "sender_id": 1,
                        "date": 100,
                        "text": "identical text",
                    },
                }
            },
        )
        for token, changes, position, message_id in (
            (alice, {"request_id": "new-id"}, 2, 2),
            (alice, {"chat_id": 3}, 3, 1),
            (bob, {"chat_id": 2}, 1, 1),
        ):
            status, body = call(server, token, "/v2/messages", command | changes)
            assert status == 200 and body["send"]["position"] == position
            assert body["send"]["message"]["id"] == message_id
    with World.open(directory) as world:
        assert len(world.history(1)) == 2
        assert len(world.poll_updates(2)) == 3
        assert len(world.poll_updates(4)) == 1


def test_invalid_or_wrong_identity_send_cannot_consume_positions_or_expose_prior_results(tmp_path):
    directory = tmp_path / "world"
    _, alice, bob = client_world(directory)
    _, foreign, _ = client_world(tmp_path / "foreign")
    command = {"chat_id": 1, "request_id": "once", "text": "valid"}
    with ClientBridge(directory) as server:
        assert call(server, alice, "/v2/messages", command)[0] == 200
        with World.open(directory) as world:
            before = world.client_snapshot(1)
            pending = world.poll_updates(2)
            bot_token = world.issue_bot_token(2)
        for changes in (
            {"text": "different"},
            {"text": ""},
            {"text": "x" * 4097},
            {"text": "\ud800"},
            {"request_id": ""},
            {"request_id": True},
            {"request_id": "x" * 129},
            {"chat_id": True},
            {"chat_id": 999},
            {"user_id": 3},
            {"reply_markup": {}},
            {"entities": [{"type": "bold", "offset": 2, "length": 99}]},
        ):
            assert call(server, alice, "/v2/messages", command | changes)[0] == 400
        assert call(server, bob, "/v2/messages", command)[0] == 400
        for token in (foreign, bot_token, "invalid"):
            assert call(server, token, "/v2/messages", command)[0] == 401
        for raw in (b"{", b"[]", b'{"chat_id":1,"chat_id":2}', b"\xff"):
            assert call(server, alice, "/v2/messages", raw=raw)[0] == 400
        assert call(server, alice, "/v2/messages?user_id=3", command)[0] == 400
        assert call(server, alice, "/v2/snapshot?after=0")[0] == 400
        with World.open(directory) as world:
            assert world.client_snapshot(1) == before
            assert world.poll_updates(2) == pending
        assert call(server, alice, "/v2/snapshot")[1]["message_position"] == 1


def test_formatted_client_send_uses_the_existing_utf16_contract(tmp_path):
    directory = tmp_path / "world"
    _, token, _ = client_world(directory)
    command = {
        "chat_id": 1,
        "request_id": "format",
        "text": "😀 سلام",
        "entities": [{"type": "bold", "offset": 3, "length": 4}],
    }
    with ClientBridge(directory) as server:
        status, body = call(server, token, "/v2/messages", command)
        assert status == 200
        message = {
            "id": 1,
            "chat_id": 1,
            "sender_id": 1,
            "date": 100,
            "text": "😀 سلام",
            "entities": command["entities"],
        }
        assert body["send"] == {"request_id": "format", "position": 1, "message": message}
        assert call(server, token, "/v2/messages", command) == (status, body)
    with World.open(directory) as world:
        assert world.history(1) == [message]
        assert world.poll_updates(2) == [{"update_id": 1, "message": message}]


def test_concurrent_v4_upgrade_preserves_filters_and_backfills_persona_positions(tmp_path):
    directory = tmp_path / "world"
    directory.mkdir()
    with closing(sqlite3.connect(directory / "world.sqlite3")) as connection:
        connection.executescript(Path("tests/fixtures/world-v4.sql").read_text())
    barrier = Barrier(4)

    def open_snapshot(_):
        barrier.wait()
        with World.open(directory) as world:
            return world.client_snapshot(1, version=2)

    with ThreadPoolExecutor(max_workers=4) as workers:
        results = list(workers.map(open_snapshot, range(4)))
    assert all(result == results[0] for result in results)
    assert results[0]["message_position"] == 2 and results[0]["sends"] == []
    with World.open(directory) as world:
        assert world.authenticate_bot("2:gramlab_" + "a" * 43) == 2
        assert world.authenticate_client("gramlab-client_" + "b" * 43) == 1
        assert len(world.poll_updates(2)) == 2
        assert (
            world.get_callback(user_id=1, callback_id="legacy-callback")["answer"]["text"]
            == "retained"
        )
        result = world.send_client_message(
            user_id=1, chat_id=1, request_id="after-upgrade", text="new"
        )
        assert result["position"] == 3
        assert len(world.poll_updates(2)) == 2  # The prior callback-only filter survives.
        assert (
            world.client_snapshot(1, version=2)["world_id"]
            == "11111111-2222-4333-8444-555555555555"
        )


def test_snapshot_position_correlations_and_messages_are_one_committed_version(tmp_path):
    directory = tmp_path / "world"
    client_world(directory)
    barrier = Barrier(2)

    def writer():
        with World.open(directory) as world:
            barrier.wait()
            for index in range(40):
                world.send_client_message(
                    user_id=1, chat_id=1, request_id=str(index), text=str(index)
                )

    with ThreadPoolExecutor(max_workers=1) as workers:
        pending = workers.submit(writer)
        barrier.wait()
        for _ in range(40):
            with World.open(directory) as world:
                snapshot = world.client_snapshot(1, version=2)
            assert (
                len(snapshot["messages"]) == snapshot["message_position"] == len(snapshot["sends"])
            )
            assert [send["message"] for send in snapshot["sends"]] == snapshot["messages"]
        pending.result(timeout=5)
    with World.open(directory) as world:
        assert world.client_snapshot(1, version=2)["message_position"] == 40


def test_nonpersistent_bridge_advertises_close_for_success_and_rejections(tmp_path):
    directory = tmp_path / "world"
    world_id, token, _ = client_world(directory)
    command = {"chat_id": 1, "request_id": "101", "text": "connection contract"}
    sent = {
        "request_id": "101",
        "position": 1,
        "message": {"id": 1, "chat_id": 1, "sender_id": 1, "date": 100, "text": command["text"]},
    }
    cases = [
        (token, "/v2/messages", command, 200, envelope(world_id) | {"send": sent}),
        (
            "wrong-capability",
            "/v2/messages",
            command,
            401,
            {
                "schema": 2,
                "error": {"code": "unauthorized", "message": "Client capability required"},
            },
        ),
        (
            token,
            "/v2/unknown",
            command,
            404,
            {
                "schema": 2,
                "error": {"code": "unsupported", "message": "Unknown client bridge operation"},
            },
        ),
        (
            token,
            "/v2/messages",
            {},
            400,
            {
                "schema": 2,
                "error": {
                    "code": "invalid_request",
                    "message": "Client command has missing or unsupported fields",
                },
            },
        ),
    ]
    with ClientBridge(directory) as server:
        url = urlsplit(server.base_url)
        for capability, path, parameters, status, expected in cases:
            payload = json.dumps(parameters).encode()
            headers = (
                f"POST {path} HTTP/1.1\r\nHost: localhost\r\n"
                f"Authorization: Bearer {capability}\r\nConnection: keep-alive\r\n"
                f"Content-Type: application/json\r\nContent-Length: {len(payload)}\r\n\r\n"
            )
            with socket.create_connection((url.hostname, url.port), timeout=5) as connection:
                connection.sendall(headers.encode() + payload)
                response = http.client.HTTPResponse(connection)
                response.begin()
                assert (response.status, json.loads(response.read())) == (status, expected)
                # Observe the actual EOF, not just a header or Python's will_close inference.
                assert connection.recv(1) == b""
                assert response.getheader("Connection", "").lower() == "close"
    with World.open(directory) as world:
        assert world.history(1) == [sent["message"]]
        assert world.poll_updates(2) == [{"update_id": 1, "message": sent["message"]}]
