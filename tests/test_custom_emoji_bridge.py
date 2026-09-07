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
        assert status == 200 and result["schema"] == 4
        assert result["custom_emoji"][0]["custom_emoji_id"] == "7"
        status, snapshot = request(bridge.base_url, token, "GET", "/v4/snapshot")
        assert status == 200 and snapshot["custom_emoji"] == result["custom_emoji"]
        status, documents = request(
            bridge.base_url,
            token,
            "POST",
            "/v4/custom-emoji-documents",
            {"custom_emoji_ids": ["7"]},
        )
        assert status == 200 and documents["custom_emoji"] == result["custom_emoji"]
        status, legacy = request(bridge.base_url, token, "GET", "/v3/snapshot")
        assert status == 400 and "v4" in legacy["error"]["message"]
