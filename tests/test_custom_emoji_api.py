import http.client
import json
from pathlib import Path
from urllib.parse import urlsplit

from gramlab.bot_api import BotAPIServer
from gramlab.world import World

ASSETS = Path(__file__).parent / "assets" / "custom-emoji"


def request(
    base: str, method: str, path: str, body: dict[str, object] | None = None
) -> tuple[int, dict[str, str], bytes]:
    url = urlsplit(base)
    raw = b"" if body is None else json.dumps(body).encode()
    assert url.hostname is not None
    connection = http.client.HTTPConnection(url.hostname, url.port, timeout=5)
    connection.request(
        method, path, raw, {"Content-Type": "application/json", "Content-Length": str(len(raw))}
    )
    response = connection.getresponse()
    result = response.status, dict(response.getheaders()), response.read()
    connection.close()
    return result


def test_bot_lookup_projection_getfile_and_download(tmp_path: Path) -> None:
    directory = tmp_path / "world"
    with World.create(directory, seed=1, now=2) as world:
        bot = world.create_user(first_name="Bot", is_bot=True)
        token = world.issue_bot_token(bot["id"])
        world.register_custom_emoji(
            request_id="one",
            main=(ASSETS / "emoji-static.webp").read_bytes(),
            thumbnail=(ASSETS / "emoji-thumbnail.webp").read_bytes(),
            fallback="🙂",
            custom_emoji_id=7,
        )
    with BotAPIServer(directory) as server:
        status, _, raw = request(
            server.base_url,
            "POST",
            f"/bot{token}/getCustomEmojiStickers",
            {"custom_emoji_ids": ["8", "7", "7"]},
        )
        assert status == 200
        sticker = json.loads(raw)["result"][0]
        assert sticker["custom_emoji_id"] == "7" and sticker["type"] == "custom_emoji"
        status, _, raw = request(
            server.base_url, "POST", f"/bot{token}/getFile", {"file_id": sticker["file_id"]}
        )
        info = json.loads(raw)["result"]
        assert status == 200 and info["file_path"].startswith("stickers/")
        status, headers, data = request(
            server.base_url, "GET", f"/file/bot{token}/{info['file_path']}"
        )
        assert status == 200 and headers["Content-Type"] == "image/webp"
        assert data == (ASSETS / "emoji-static.webp").read_bytes()
