import http.client
import io
import json
from pathlib import Path
from urllib.parse import urlsplit

from PIL import Image

from gramlab.bot_api import BotAPIServer
from gramlab.world import World


def png() -> bytes:
    output = io.BytesIO()
    Image.new("RGBA", (5, 4), (1, 2, 3, 120)).save(output, "PNG")
    return output.getvalue()


def request(base: str, method: str, path: str, body: bytes = b"", headers=None):
    url = urlsplit(base)
    connection = http.client.HTTPConnection(url.hostname, url.port, timeout=5)
    connection.request(method, path, body=body, headers=headers or {})
    response = connection.getresponse()
    data = response.read()
    result = response.status, dict(response.getheaders()), data
    connection.close()
    return result


def multipart(fields: dict[str, str], files: dict[str, tuple[str, bytes]]) -> tuple[bytes, str]:
    boundary = "GramLabBoundary42"
    parts = []
    for name, value in fields.items():
        parts.append(
            (
                f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'
            ).encode()
        )
    for name, (filename, value) in files.items():
        parts.append(
            (
                f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"; '
                f'filename="{filename}"\r\nContent-Type: application/octet-stream\r\n\r\n'
            ).encode()
            + value
            + b"\r\n"
        )
    return b"".join(
        parts
    ) + f"--{boundary}--\r\n".encode(), f"multipart/form-data; boundary={boundary}"


def test_standard_upload_reuse_get_file_and_download(tmp_path: Path) -> None:
    directory = tmp_path / "world"
    with World.create(directory, seed=1, now=50) as world:
        user = world.create_user(first_name="Ada")
        bot = world.create_user(first_name="Bot", is_bot=True)
        world.open_private_chat(user_id=user["id"], bot_id=bot["id"])
        token = world.issue_bot_token(bot["id"])
    data = png() + b"\r\n--GramLabBoundary42-not-a-delimiter"
    body, content_type = multipart(
        {"chat_id": str(user["id"]), "caption": "photo"},
        {"photo": ("../../original.png", data)},
    )
    with BotAPIServer(directory) as server:
        status, _, raw = request(
            server.base_url,
            "POST",
            f"/bot{token}/sendPhoto",
            body,
            {"Content-Type": content_type, "Content-Length": str(len(body))},
        )
        assert status == 200
        message = json.loads(raw)["result"]
        assert message["caption"] == "photo" and message["photo"][0]["width"] == 5
        file_id = message["photo"][0]["file_id"]
        encoded = json.dumps({"file_id": file_id}).encode()
        status, _, raw = request(
            server.base_url,
            "POST",
            f"/bot{token}/getFile",
            encoded,
            {"Content-Type": "application/json", "Content-Length": str(len(encoded))},
        )
        info = json.loads(raw)["result"]
        assert status == 200 and "original.png" not in info["file_path"]
        status, headers, downloaded = request(
            server.base_url, "GET", f"/file/bot{token}/{info['file_path']}"
        )
        assert status == 200 and downloaded == data
        assert headers["Content-Type"] == "image/png"
        reused = json.dumps({"chat_id": user["id"], "photo": file_id}).encode()
        status, _, raw = request(
            server.base_url,
            "POST",
            f"/bot{token}/sendPhoto",
            reused,
            {"Content-Type": "application/json", "Content-Length": str(len(reused))},
        )
        assert status == 200 and json.loads(raw)["result"]["photo"][0] == message["photo"][0]
        replacement = {
            "skip_entity_detection": True,
            "blocks": [{"type": "paragraph", "text": "replacement"}],
        }
        edit_body, edit_type = multipart(
            {
                "chat_id": str(user["id"]),
                "message_id": str(message["message_id"]),
                "rich_message": json.dumps(replacement),
            },
            {"unused": ("unused.png", png())},
        )
        status, _, raw = request(
            server.base_url,
            "POST",
            f"/bot{token}/editMessageText",
            edit_body,
            {"Content-Type": edit_type, "Content-Length": str(len(edit_body))},
        )
        assert status == 400 and "ordinary photo" in json.loads(raw)["description"]
    with World.open(directory) as world:
        assert len(world.history(1)) == 2
        assert [
            asset["asset_id"] for asset in world.client_snapshot(user["id"], version=3)["assets"]
        ] == [1]


def test_multipart_rejects_duplicate_and_preserves_boundary_like_file_bytes(tmp_path: Path) -> None:
    directory = tmp_path / "world"
    with World.create(directory, seed=1, now=1) as world:
        user = world.create_user(first_name="Ada")
        bot = world.create_user(first_name="Bot", is_bot=True)
        world.open_private_chat(user_id=user["id"], bot_id=bot["id"])
        token = world.issue_bot_token(bot["id"])
    body, content_type = multipart(
        {"chat_id": str(user["id"]), "photo": "duplicate"}, {"photo": ("x.png", png())}
    )
    with BotAPIServer(directory) as server:
        status, _, raw = request(
            server.base_url,
            "POST",
            f"/bot{token}/sendPhoto",
            body,
            {"Content-Type": content_type, "Content-Length": str(len(body))},
        )
        assert status == 400 and "Repeated" in json.loads(raw)["description"]
    with World.open(directory) as world:
        assert world.history(1) == []

    nested = body.replace(
        b"Content-Type: application/octet-stream", b"Content-Type: multipart/mixed"
    )
    with BotAPIServer(directory) as server:
        status, _, raw = request(
            server.base_url,
            "POST",
            f"/bot{token}/sendPhoto",
            nested,
            {"Content-Type": content_type, "Content-Length": str(len(nested))},
        )
        assert status == 400 and "Nested multipart" in json.loads(raw)["description"]


def test_rich_photo_upload_edit_and_file_id_reuse(tmp_path: Path) -> None:
    directory = tmp_path / "world"
    with World.create(directory, seed=1, now=20) as world:
        user = world.create_user(first_name="Ada")
        bot = world.create_user(first_name="Bot", is_bot=True)
        world.open_private_chat(user_id=user["id"], bot_id=bot["id"])
        token = world.issue_bot_token(bot["id"])
    rich = {
        "skip_entity_detection": True,
        "blocks": [
            {
                "type": "photo",
                "photo": {"type": "photo", "media": "attach://asset"},
                "caption": {"text": {"type": "bold", "text": "first"}},
            }
        ],
    }
    body, content_type = multipart(
        {"chat_id": str(user["id"]), "rich_message": json.dumps(rich)},
        {"asset": ("first.png", png())},
    )
    with BotAPIServer(directory) as server:
        status, _, raw = request(
            server.base_url,
            "POST",
            f"/bot{token}/sendRichMessage",
            body,
            {"Content-Type": content_type, "Content-Length": str(len(body))},
        )
        sent = json.loads(raw)["result"]
        block = sent["rich_message"]["blocks"][0]
        assert status == 200 and block["caption"] == {"text": {"type": "bold", "text": "first"}}
        file_id = block["photo"][0]["file_id"]
        reused = {
            "blocks": [{"type": "photo", "photo": {"type": "photo", "media": file_id}}],
            "skip_entity_detection": True,
        }
        edit = json.dumps(
            {
                "chat_id": user["id"],
                "message_id": sent["message_id"],
                "rich_message": reused,
            }
        ).encode()
        status, _, raw = request(
            server.base_url,
            "POST",
            f"/bot{token}/editMessageText",
            edit,
            {"Content-Type": "application/json", "Content-Length": str(len(edit))},
        )
        assert status == 200
        assert (
            json.loads(raw)["result"]["rich_message"]["blocks"][0]["photo"][0]["file_id"] == file_id
        )
