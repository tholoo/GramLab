"""Real Bot API HTTP acceptance for standalone media edits."""

import hashlib
import http.client
import io
import json
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from PIL import Image
from test_multipart_filename_decoding import CONTENT_TYPE, body, part

from gramlab.bot_api import BotAPIServer
from gramlab.documents import DocumentUpload
from gramlab.world import World


def png(colour: tuple[int, int, int]) -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (2, 2), colour).save(output, "PNG")
    return output.getvalue()


def request(base: str, route: str, payload: dict[str, Any] | bytes) -> tuple[int, dict[str, Any]]:
    url = urlsplit(base)
    assert url.hostname is not None
    connection = http.client.HTTPConnection(url.hostname, url.port, timeout=10)
    data = json.dumps(payload).encode() if isinstance(payload, dict) else payload
    content_type = "application/json" if isinstance(payload, dict) else CONTENT_TYPE
    try:
        connection.request("POST", route, data, {"Content-Type": content_type})
        response = connection.getresponse()
        return response.status, json.loads(response.read())
    finally:
        connection.close()


def database(path: Path) -> list[str]:
    with closing(sqlite3.connect(path / "world.sqlite3")) as connection:
        return list(connection.iterdump())


def setup(path: Path) -> tuple[dict[str, Any], dict[str, Any], str, str, str, str]:
    with World.create(path, seed=106, now=500) as world:
        user = world.create_user(first_name="Ada")
        bot = world.create_user(first_name="Media", is_bot=True)
        other = world.create_user(first_name="Other", is_bot=True)
        chat = world.open_private_chat(user_id=user["id"], bot_id=bot["id"])
        world.open_private_chat(user_id=user["id"], bot_id=other["id"])
        photo = world.send_photo(
            chat_id=chat["id"],
            sender_id=bot["id"],
            photo={"type": "photo", "media": "attach://photo"},
            uploads={"photo": png((10, 20, 30))},
            caption="old",
            reply_markup={"inline_keyboard": [[{"text": "Old", "callback_data": "old"}]]},
        )
        document = world.send_document(
            chat_id=chat["id"],
            sender_id=bot["id"],
            document={"media": "attach://document"},
            uploads={"document": DocumentUpload(b"document", "file.pdf")},
        )
        return (
            user,
            bot,
            world.issue_bot_token(bot["id"]),
            world.issue_bot_token(other["id"]),
            world.photo_size(bot["id"], photo["photo"]["asset_id"])["file_id"],
            world.document_file(bot["id"], document["document"]["document_id"])["file_id"],
        )


def test_http_caption_and_cross_kind_media_edits_return_complete_messages(tmp_path: Path) -> None:
    directory = tmp_path / "world"
    user, bot, token, _other, photo_id, document_id = setup(directory)
    chat = {"id": user["id"], "type": "private", "first_name": "Ada"}
    original_photo = png((10, 20, 30))
    photo_unique = hashlib.sha256(original_photo).hexdigest()
    document_unique = DocumentUpload(b"document", "file.pdf").file_unique_id
    with BotAPIServer(directory) as server:
        status, response = request(
            server.base_url,
            f"/bot{token}/editMessageCaption",
            {
                "chat_id": user["id"],
                "message_id": 1,
                "caption": "فایل Report",
                "caption_entities": [{"type": "bold", "offset": 5, "length": 6}],
            },
        )
        assert status == 200
        assert response == {
            "ok": True,
            "result": {
                "message_id": 1,
                "from": bot,
                "chat": chat,
                "date": 500,
                "photo": [
                    {
                        "file_id": photo_id,
                        "file_unique_id": photo_unique,
                        "width": 2,
                        "height": 2,
                        "file_size": len(original_photo),
                    }
                ],
                "caption": "فایل Report",
                "caption_entities": [{"type": "bold", "offset": 5, "length": 6}],
                "edit_date": 500,
            },
        }
        status, response = request(
            server.base_url,
            f"/bot{token}/editMessageMedia",
            {
                "chat_id": 1,
                "message_id": 1,
                "media": {"type": "document", "media": document_id, "caption": "same file"},
            },
        )
        assert status == 200
        assert response == {
            "ok": True,
            "result": {
                "message_id": 1,
                "from": bot,
                "chat": chat,
                "date": 500,
                "document": {
                    "file_id": document_id,
                    "file_unique_id": document_unique,
                    "file_size": 8,
                    "file_name": "file.pdf",
                    "mime_type": "application/pdf",
                },
                "caption": "same file",
                "edit_date": 500,
            },
        }
        status, response = request(
            server.base_url,
            f"/bot{token}/editMessageMedia",
            {"chat_id": 1, "message_id": 2, "media": {"type": "photo", "media": photo_id}},
        )
        assert status == 200
        assert response == {
            "ok": True,
            "result": {
                "message_id": 2,
                "from": bot,
                "chat": chat,
                "date": 500,
                "photo": [
                    {
                        "file_id": photo_id,
                        "file_unique_id": photo_unique,
                        "width": 2,
                        "height": 2,
                        "file_size": len(original_photo),
                    }
                ],
                "edit_date": 500,
            },
        }
    with World.open(directory) as world:
        assert world.granted_asset(user["id"], 1)[1] == png((10, 20, 30))
        assert world.granted_document(user["id"], "1")[1] == b"document"
        assert [event["type"] for event in world.events()[-3:]] == [
            "message.edited",
            "message.edited",
            "message.edited",
        ]


def test_http_rejections_and_noop_preserve_database(tmp_path: Path) -> None:
    directory = tmp_path / "world"
    user, _bot, token, other, photo_id, document_id = setup(directory)
    with BotAPIServer(directory) as server:
        cases = [
            (
                token,
                "editMessageCaption",
                {
                    "chat_id": 1,
                    "message_id": 1,
                    "caption": "old",
                    "reply_markup": {
                        "inline_keyboard": [[{"text": "Old", "callback_data": "old"}]]
                    },
                },
            ),
            (
                token,
                "editMessageCaption",
                {"chat_id": 1, "message_id": 1, "caption": "x", "show_caption_above_media": True},
            ),
            (
                token,
                "editMessageMedia",
                {"chat_id": 1, "message_id": 1, "media": {"type": "photo", "media": document_id}},
            ),
            (
                token,
                "editMessageMedia",
                {"chat_id": 1, "message_id": 1, "media": {"type": "document", "media": photo_id}},
            ),
            (
                other,
                "editMessageMedia",
                {
                    "chat_id": user["id"],
                    "message_id": 1,
                    "media": {"type": "photo", "media": photo_id},
                },
            ),
            (
                token,
                "editMessageMedia",
                {"chat_id": 1, "message_id": 1, "media": {"type": "video", "media": "x"}},
            ),
        ]
        for selected_token, method, payload in cases:
            before = database(directory)
            status, response = request(server.base_url, f"/bot{selected_token}/{method}", payload)
            assert status == 400 and response["ok"] is False
            assert database(directory) == before


def test_http_multipart_media_edits_admit_exact_typed_upload(tmp_path: Path) -> None:
    directory = tmp_path / "world"
    user, _bot, token, _other, _photo_id, _document_id = setup(directory)
    document_bytes = b"new document bytes"
    document_media = json.dumps(
        {
            "type": "document",
            "media": "attach://replacement",
            "disable_content_type_detection": True,
        }
    )
    document_request = body(
        part(b'form-data; name="chat_id"', str(user["id"]).encode()),
        part(b'form-data; name="message_id"', b"1"),
        part(b'form-data; name="media"', document_media.encode()),
        part(
            b'form-data; name="replacement"; filename="new.pdf"',
            document_bytes,
            b"Content-Type: application/pdf\r\n",
        ),
    )
    photo_bytes = png((100, 110, 120))
    photo_request = body(
        part(b'form-data; name="chat_id"', str(user["id"]).encode()),
        part(b'form-data; name="message_id"', b"2"),
        part(
            b'form-data; name="media"',
            json.dumps({"type": "photo", "media": "attach://replacement"}).encode(),
        ),
        part(
            b'form-data; name="replacement"; filename="new.png"',
            photo_bytes,
            b"Content-Type: image/png\r\n",
        ),
    )
    with BotAPIServer(directory) as server:
        status, document = request(
            server.base_url, f"/bot{token}/editMessageMedia", document_request
        )
        assert status == 200
        assert document["result"]["document"]["file_name"] == "new.pdf"
        document_file = document["result"]["document"]["file_id"]
        status, photo = request(server.base_url, f"/bot{token}/editMessageMedia", photo_request)
        assert status == 200 and photo["result"]["photo"][0]["file_size"] == len(photo_bytes)
        photo_file = photo["result"]["photo"][0]["file_id"]
    with World.open(directory) as world:
        assert world.bot_file(2, document_file)[1] == document_bytes
        assert world.bot_file(2, photo_file)[1] == photo_bytes
