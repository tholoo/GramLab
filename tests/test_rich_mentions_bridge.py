import http.client
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import pytest
from test_rich_mentions import rich, world_with_contacts

from gramlab.client_bridge import ClientBridge
from gramlab.world import World


def bridge_call(
    server: ClientBridge, token: str, path: str, body: dict[str, Any] | None = None
) -> tuple[int, dict[str, Any]]:
    url = urlsplit(server.base_url)
    assert url.hostname is not None
    connection = http.client.HTTPConnection(url.hostname, url.port, timeout=5)
    try:
        payload = None if body is None else json.dumps(body)
        headers = {"Authorization": f"Bearer {token}"}
        if payload is not None:
            headers["Content-Type"] = "application/json"
        connection.request("GET" if body is None else "POST", path, payload, headers)
        response = connection.getresponse()
        return response.status, dict(json.loads(response.read()))
    finally:
        connection.close()


def test_v3_dependencies_follow_exact_versions_and_frozen_callback(tmp_path: Path) -> None:
    world, recipient, bot, referenced, _hidden, chat = world_with_contacts(tmp_path / "world")
    message = world.send_rich_message(
        chat_id=chat["id"],
        sender_id=bot["id"],
        rich_message=rich(referenced),
        reply_markup={"inline_keyboard": [[{"text": "Tap", "callback_data": "x"}]]},
    )
    callback = world.create_callback(
        user_id=recipient["id"],
        chat_id=chat["id"],
        message_id=message["id"],
        data="x",
        request_id="mention",
        version=3,
    )
    world.edit_message(
        chat_id=chat["id"],
        message_id=message["id"],
        bot_id=bot["id"],
        rich_message={
            "skip_entity_detection": True,
            "blocks": [{"type": "paragraph", "text": "removed"}],
        },
    )
    base_ids = [recipient["id"], bot["id"]]
    assert [
        user["id"] for user in world.client_snapshot(recipient["id"], version=3)["users"]
    ] == base_ids
    first = world.client_changes(recipient["id"], after=0, limit=1, version=3)
    assert [user["id"] for user in first["users"]] == [*base_ids, referenced["id"]]
    second = world.client_changes(recipient["id"], after=1, version=3)
    assert [user["id"] for user in second["users"]] == base_ids
    assert [
        user["id"] for user in world.callback_dependencies(recipient["id"], callback)["users"]
    ] == [*base_ids, referenced["id"]]
    with pytest.raises(ValueError, match="rich mentions"):
        world.client_changes(recipient["id"], after=0, limit=1, version=2)
    before = world.events()
    with pytest.raises(ValueError, match="rich mentions"):
        world.create_callback(
            user_id=recipient["id"],
            chat_id=chat["id"],
            message_id=message["id"],
            data="x",
            request_id="mention",
            version=1,
        )
    assert world.events() == before
    world.__exit__(None, None, None)


def test_two_recipients_derive_different_identity_envelopes(tmp_path: Path) -> None:
    world, recipient, bot, referenced, _hidden, chat = world_with_contacts(tmp_path / "world")
    other = world.create_user(first_name="Other")
    other_chat = world.open_private_chat(user_id=other["id"], bot_id=bot["id"])
    world.send_rich_message(chat_id=chat["id"], sender_id=bot["id"], rich_message=rich(referenced))
    world.send_rich_message(
        chat_id=other_chat["id"],
        sender_id=bot["id"],
        rich_message={
            "skip_entity_detection": True,
            "blocks": [{"type": "paragraph", "text": "ordinary"}],
        },
    )
    assert referenced["id"] in {
        entry["id"] for entry in world.client_snapshot(recipient["id"], version=3)["users"]
    }
    assert referenced["id"] not in {
        entry["id"] for entry in world.client_snapshot(other["id"], version=3)["users"]
    }
    world.__exit__(None, None, None)


def test_http_bridge_versions_exact_replay_and_frozen_callback(tmp_path: Path) -> None:
    directory = tmp_path / "world"
    world, recipient, bot, referenced, _hidden, chat = world_with_contacts(directory)
    try:
        token = world.issue_client_token(recipient["id"])
        message = world.send_rich_message(
            chat_id=chat["id"],
            sender_id=bot["id"],
            rich_message=rich(referenced),
            reply_markup={"inline_keyboard": [[{"text": "Tap", "callback_data": "x"}]]},
        )
        revision = world.client_snapshot(recipient["id"], version=3)["message_revisions"][0][
            "revision"
        ]
        callback = world.create_callback(
            user_id=recipient["id"],
            chat_id=chat["id"],
            message_id=message["id"],
            data="x",
            request_id="http",
            version=3,
        )
        world.edit_message(
            chat_id=chat["id"],
            message_id=message["id"],
            bot_id=bot["id"],
            rich_message={
                "skip_entity_detection": True,
                "blocks": [{"type": "paragraph", "text": "removed"}],
            },
        )
        world.send_rich_message(
            chat_id=chat["id"], sender_id=bot["id"], rich_message=rich(referenced, "current")
        )
        world_id = world.world_id
        current_state = world.client_snapshot(recipient["id"], version=3)
        head = current_state["message_position"]
        current_revision = current_state["message_revisions"][1]["revision"]
        cursor = current_state["cursor"]
        before_legacy = world.events()
    finally:
        world.__exit__(None, None, None)
    users = [recipient, bot, referenced]
    expected_original = {
        "id": 1,
        "chat_id": chat["id"],
        "sender_id": bot["id"],
        "date": 100,
        "text": "",
        "reply_markup": {"inline_keyboard": [[{"text": "Tap", "callback_data": "x"}]]},
        "rich_message": {
            "blocks": [
                {
                    "type": "paragraph",
                    "text": {
                        "type": "text_mention",
                        "text": {"type": "bold", "text": "برنده Winner"},
                        "user_id": referenced["id"],
                    },
                }
            ]
        },
    }
    expected_edited = {
        "id": 1,
        "chat_id": chat["id"],
        "sender_id": bot["id"],
        "date": 100,
        "text": "",
        "rich_message": {"blocks": [{"type": "paragraph", "text": "removed"}]},
        "edit_date": 100,
    }
    expected_current = {
        "id": 2,
        "chat_id": chat["id"],
        "sender_id": bot["id"],
        "date": 100,
        "text": "",
        "rich_message": {
            "blocks": [
                {
                    "type": "paragraph",
                    "text": {
                        "type": "text_mention",
                        "text": {"type": "bold", "text": "current"},
                        "user_id": referenced["id"],
                    },
                }
            ]
        },
    }
    expected_stored_callback = {
        "id": callback["id"],
        "user_id": recipient["id"],
        "chat_id": chat["id"],
        "message": expected_original,
        "data": "x",
        "chat_instance": callback["chat_instance"],
        "answer": None,
    }
    expected_callback = {
        "schema": 3,
        "world_id": world_id,
        "user_id": recipient["id"],
        "callback": expected_stored_callback,
        "users": users,
        "assets": [],
        "message_revision": revision,
    }
    command = {
        "request_id": "http",
        "chat_id": chat["id"],
        "message_id": message["id"],
        "data": "x",
    }
    with ClientBridge(directory) as server:
        assert bridge_call(server, token, "/v3/callbacks", command) == (200, expected_callback)
        assert bridge_call(server, token, f"/v3/callbacks/{callback['id']}") == (
            200,
            expected_callback,
        )
        assert bridge_call(server, token, "/v3/snapshot") == (
            200,
            {
                "schema": 3,
                "world_id": world_id,
                "user_id": recipient["id"],
                "cursor": cursor,
                "now": 100,
                "users": users,
                "chats": [
                    {
                        "id": chat["id"],
                        "type": "private",
                        "user_id": recipient["id"],
                        "bot_id": bot["id"],
                    }
                ],
                "messages": [
                    expected_edited,
                    expected_current,
                ],
                "message_position": head,
                "sends": [],
                "assets": [],
                "message_revisions": [
                    {"chat_id": chat["id"], "message_id": 1, "revision": revision + 2},
                    {"chat_id": chat["id"], "message_id": 2, "revision": current_revision},
                ],
            },
        )
        status, changes = bridge_call(server, token, "/v3/changes?after=0&limit=1")
        assert (status, changes) == (
            200,
            {
                "schema": 3,
                "world_id": world_id,
                "user_id": recipient["id"],
                "cursor": 1,
                "head": head,
                "now": 100,
                "changes": [
                    {
                        "position": 1,
                        "type": "message.created",
                        "data": expected_original,
                        "revision": revision,
                    }
                ],
                "users": users,
                "assets": [],
            },
        )
        for path, schema in (
            ("/v1/snapshot", 1),
            ("/v2/snapshot", 2),
            ("/v1/events?after=0", 1),
            ("/v2/changes?after=0&limit=1", 2),
        ):
            status, error = bridge_call(server, token, path)
            assert (status, error) == (
                400,
                {
                    "schema": schema,
                    "error": {
                        "code": "invalid_request",
                        "message": "GRAMLAB_UNSUPPORTED: rich mentions require client bridge v3",
                    },
                },
            )
        status, error = bridge_call(server, token, "/v1/callbacks", command)
        assert (status, error) == (
            400,
            {
                "schema": 1,
                "error": {
                    "code": "invalid_request",
                    "message": "GRAMLAB_UNSUPPORTED: rich mentions require client bridge v3",
                },
            },
        )
    with World.open(directory) as reopened:
        assert reopened.events() == before_legacy


def test_http_legacy_callback_retry_uses_frozen_plain_message(tmp_path: Path) -> None:
    directory = tmp_path / "world"
    with World.create(directory, seed=4, now=20) as world:
        recipient = world.create_user(first_name="Sara")
        bot = world.create_user(first_name="Echo", is_bot=True)
        referenced = world.create_user(first_name="Mina")
        chat = world.open_private_chat(user_id=recipient["id"], bot_id=bot["id"])
        world.open_private_chat(user_id=referenced["id"], bot_id=bot["id"])
        message = world.send_message(
            chat_id=chat["id"],
            sender_id=bot["id"],
            text="plain",
            reply_markup={"inline_keyboard": [[{"text": "Tap", "callback_data": "x"}]]},
        )
        token = world.issue_client_token(recipient["id"])
        world_id = world.world_id
    command = {
        "request_id": "plain-frozen",
        "chat_id": chat["id"],
        "message_id": message["id"],
        "data": "x",
    }
    with ClientBridge(directory) as server:
        status, first = bridge_call(server, token, "/v1/callbacks", command)
        assert status == 200
    with World.open(directory) as world:
        world.edit_message(
            chat_id=chat["id"],
            message_id=message["id"],
            bot_id=bot["id"],
            rich_message=rich(referenced),
        )
        before_retry = world.events()
    with ClientBridge(directory) as server:
        assert bridge_call(server, token, "/v1/callbacks", command) == (
            200,
            {
                "schema": 1,
                "world_id": world_id,
                "user_id": recipient["id"],
                "callback": {
                    "id": first["callback"]["id"],
                    "user_id": recipient["id"],
                    "chat_id": chat["id"],
                    "message": {
                        "id": 1,
                        "chat_id": chat["id"],
                        "sender_id": bot["id"],
                        "date": 20,
                        "text": "plain",
                        "reply_markup": {
                            "inline_keyboard": [[{"text": "Tap", "callback_data": "x"}]]
                        },
                    },
                    "data": "x",
                    "chat_instance": first["callback"]["chat_instance"],
                    "answer": None,
                },
            },
        )
    with World.open(directory) as world:
        assert world.events() == before_retry
