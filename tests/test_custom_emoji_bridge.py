import hashlib
import http.client
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from gramlab.client_bridge import ClientBridge
from gramlab.world import World

ASSETS = Path(__file__).parent / "assets" / "custom-emoji"


def request(
    base: str, token: str, method: str, path: str, body: dict[str, Any] | None = None
) -> tuple[int, dict[str, Any]]:
    url = urlsplit(base)
    raw = b"" if body is None else json.dumps(body).encode()
    assert url.hostname is not None
    connection = http.client.HTTPConnection(url.hostname, url.port, timeout=5)
    headers = {"Authorization": f"Bearer {token}"}
    if body is not None:
        headers |= {"Content-Type": "application/json", "Content-Length": str(len(raw))}
    connection.request(method, path, raw, headers)
    response = connection.getresponse()
    result = response.status, json.loads(response.read())
    connection.close()
    return result


def test_v4_message_snapshot_and_document_authorization(tmp_path: Path) -> None:
    directory = tmp_path / "world"
    with World.create(directory, seed=1, now=2) as world:
        user = world.create_user(first_name="Ada")
        bot = world.create_user(first_name="Bot", is_bot=True)
        chat = world.open_private_chat(user_id=user["id"], bot_id=bot["id"])
        token = world.issue_client_token(user["id"])
        world.register_custom_emoji(
            request_id="one",
            main=(ASSETS / "emoji-static.webp").read_bytes(),
            thumbnail=(ASSETS / "emoji-thumbnail.webp").read_bytes(),
            fallback="🙂",
            custom_emoji_id=7,
        )
        world_id = world.world_id
    main = (ASSETS / "emoji-static.webp").read_bytes()
    thumbnail = (ASSETS / "emoji-thumbnail.webp").read_bytes()
    descriptor = {
        "custom_emoji_id": "7",
        "fallback": "🙂",
        "free": True,
        "needs_repainting": False,
        "main_asset_id": 1,
        "thumbnail_asset_id": 2,
        "duration_ms": 0,
    }
    assets = [
        {
            "asset_id": 1,
            "mime_type": "image/webp",
            "file_size": len(main),
            "sha256": hashlib.sha256(main).hexdigest(),
            "width": 100,
            "height": 100,
        },
        {
            "asset_id": 2,
            "mime_type": "image/webp",
            "file_size": len(thumbnail),
            "sha256": hashlib.sha256(thumbnail).hexdigest(),
            "width": 16,
            "height": 16,
        },
    ]
    message = {
        "id": 1,
        "chat_id": 1,
        "sender_id": 1,
        "date": 2,
        "text": "🙂",
        "entities": [{"type": "custom_emoji", "offset": 0, "length": 2, "custom_emoji_id": "7"}],
    }
    sent = {"request_id": "send", "position": 1, "message": message}
    with ClientBridge(directory) as bridge:
        status, result = request(
            bridge.base_url,
            token,
            "POST",
            "/v4/messages",
            {
                "request_id": "send",
                "chat_id": chat["id"],
                "text": "🙂",
                "entities": [
                    {"type": "custom_emoji", "offset": 0, "length": 2, "custom_emoji_id": 7}
                ],
            },
        )
        assert status == 200
        assert result == {
            "schema": 4,
            "world_id": world_id,
            "user_id": 1,
            "send": sent,
            "users": [
                {"id": 1, "is_bot": False, "first_name": "Ada"},
                {"id": 2, "is_bot": True, "first_name": "Bot"},
            ],
            "assets": assets,
            "custom_emoji": [descriptor],
            "message_revision": 4,
        }
        status, changes = request(bridge.base_url, token, "GET", "/v4/changes?after=0")
        assert status == 200
        assert changes == {
            "schema": 4,
            "world_id": world_id,
            "user_id": 1,
            "cursor": 1,
            "head": 1,
            "now": 2,
            "changes": [
                {
                    "position": 1,
                    "type": "message.created",
                    "data": message,
                    "revision": 4,
                    "request_id": "send",
                }
            ],
            "users": [
                {"id": 1, "is_bot": False, "first_name": "Ada"},
                {"id": 2, "is_bot": True, "first_name": "Bot"},
            ],
            "assets": assets,
            "custom_emoji": [descriptor],
        }
        status, snapshot = request(bridge.base_url, token, "GET", "/v4/snapshot")
        assert status == 200
        assert snapshot == {
            "schema": 4,
            "world_id": world_id,
            "user_id": 1,
            "cursor": 4,
            "now": 2,
            "users": [
                {"id": 1, "is_bot": False, "first_name": "Ada"},
                {"id": 2, "is_bot": True, "first_name": "Bot"},
            ],
            "chats": [{"id": 1, "type": "private", "user_id": 1, "bot_id": 2}],
            "messages": [message],
            "message_position": 1,
            "sends": [sent],
            "assets": assets,
            "message_revisions": [{"chat_id": 1, "message_id": 1, "revision": 4}],
            "custom_emoji": [descriptor],
        }
        status, documents = request(
            bridge.base_url,
            token,
            "POST",
            "/v4/custom-emoji-documents",
            {"custom_emoji_ids": ["7"]},
        )
        assert status == 200
        assert documents == {
            "schema": 4,
            "world_id": world_id,
            "user_id": 1,
            "custom_emoji": [descriptor],
            "assets": assets,
        }
        status, legacy = request(bridge.base_url, token, "GET", "/v3/snapshot")
        assert status == 400 and "v4" in legacy["error"]["message"]


def test_v4_frozen_callback_complete_envelope_and_v1_rejection(tmp_path: Path) -> None:
    directory = tmp_path / "world"
    main = (ASSETS / "emoji-static.webp").read_bytes()
    thumbnail = (ASSETS / "emoji-thumbnail.webp").read_bytes()
    with World.create(directory, seed=1, now=2) as world:
        user = world.create_user(first_name="Ada")
        bot = world.create_user(first_name="Bot", is_bot=True)
        chat = world.open_private_chat(user_id=user["id"], bot_id=bot["id"])
        token = world.issue_client_token(user["id"])
        world.register_custom_emoji(
            request_id="one", main=main, thumbnail=thumbnail, fallback="🙂", custom_emoji_id=7
        )
        message = world.send_message(
            chat_id=chat["id"],
            sender_id=bot["id"],
            text="🙂",
            entities=[{"type": "custom_emoji", "offset": 0, "length": 2, "custom_emoji_id": 7}],
        )
        world_id = world.world_id
    descriptor = {
        "custom_emoji_id": "7",
        "fallback": "🙂",
        "free": True,
        "needs_repainting": False,
        "main_asset_id": 1,
        "thumbnail_asset_id": 2,
        "duration_ms": 0,
    }
    assets = [
        {
            "asset_id": 1,
            "mime_type": "image/webp",
            "file_size": len(main),
            "sha256": hashlib.sha256(main).hexdigest(),
            "width": 100,
            "height": 100,
        },
        {
            "asset_id": 2,
            "mime_type": "image/webp",
            "file_size": len(thumbnail),
            "sha256": hashlib.sha256(thumbnail).hexdigest(),
            "width": 16,
            "height": 16,
        },
    ]
    with ClientBridge(directory) as bridge:
        command = {"request_id": "callback", "chat_id": 1, "message_id": 1, "data": "tap"}
        status, response = request(bridge.base_url, token, "POST", "/v4/callbacks", command)
        callback_id = response["callback"]["id"]
        callback = {
            "id": callback_id,
            "user_id": 1,
            "chat_id": 1,
            "message": message,
            "data": "tap",
            "chat_instance": hashlib.sha256(f"{world_id}:1".encode()).hexdigest(),
            "answer": None,
        }
        assert status == 200
        assert response == {
            "schema": 4,
            "world_id": world_id,
            "user_id": 1,
            "callback": callback,
            "users": [
                {"id": 1, "is_bot": False, "first_name": "Ada"},
                {"id": 2, "is_bot": True, "first_name": "Bot"},
            ],
            "assets": assets,
            "custom_emoji": [descriptor],
            "message_revision": 4,
        }
        with World.open(directory) as world:
            world.edit_message(chat_id=1, message_id=1, bot_id=2, text="plain")
        status, legacy = request(bridge.base_url, token, "GET", f"/v1/callbacks/{callback_id}")
        assert status == 400
        assert legacy == {
            "schema": 1,
            "error": {
                "code": "invalid_request",
                "message": "GRAMLAB_UNSUPPORTED: custom emoji requires client bridge v4",
            },
        }
