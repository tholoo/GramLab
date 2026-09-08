"""Real HTTP ordinary-file acceptance under the explicit force-file profile."""

import hashlib
import http.client
import json
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import pytest
from test_multipart_filename_decoding import CONTENT_TYPE, body, part

from gramlab.bot_api import BotAPIServer
from gramlab.world import World


def request(base: str, route: str, payload: bytes | dict[str, Any] | None = None):
    url = urlsplit(base)
    assert url.hostname is not None
    connection = http.client.HTTPConnection(url.hostname, url.port, timeout=10)
    headers = {}
    if isinstance(payload, dict):
        payload = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    elif isinstance(payload, bytes):
        headers["Content-Type"] = CONTENT_TYPE
    try:
        connection.request("GET" if payload is None else "POST", route, payload, headers)
        response = connection.getresponse()
        return response.status, dict(response.getheaders()), response.read()
    finally:
        connection.close()


def setup(path: Path) -> tuple[dict[str, Any], dict[str, Any], str, str]:
    with World.create(path, seed=102, now=50) as world:
        user = world.create_user(first_name="Ada")
        bot = world.create_user(first_name="Files", is_bot=True)
        other = world.create_user(first_name="Other", is_bot=True)
        world.open_private_chat(user_id=user["id"], bot_id=bot["id"])
        world.open_private_chat(user_id=user["id"], bot_id=other["id"])
        return user, bot, world.issue_bot_token(bot["id"]), world.issue_bot_token(other["id"])


def state(path: Path) -> list[str]:
    with closing(sqlite3.connect(path / "world.sqlite3")) as connection:
        return list(connection.iterdump())


def upload_request(user: dict[str, Any], data: bytes, filename: bytes, **fields: str) -> bytes:
    values = {"chat_id": str(user["id"]), "disable_content_type_detection": "true", **fields}
    return body(
        *(
            part(f'form-data; name="{key}"'.encode(), value.encode())
            for key, value in values.items()
        ),
        part(
            b'form-data; name="document"; filename="' + filename + b'"',
            data,
            b"Content-Type: image/png\r\n",
        ),
    )


@pytest.mark.parametrize(
    "filename,cleaned,mime",
    [
        (b"dir%2fr%C3%A9sum%C3%A9.PDF", "résumé.PDF", "application/pdf"),
        (b"%FF.bin", "file", ""),
        (b"", "file", ""),
        (b"readme.unknown", "readme.unknown", ""),
    ],
)
def test_upload_reuse_file_download_and_callback_preserve_complete_document(
    tmp_path: Path,
    filename: bytes,
    cleaned: str,
    mime: str,
) -> None:
    directory = tmp_path / "world"
    user, bot, token, other_token = setup(directory)
    data = b"%PDF-1.4\noriginal bytes\x00\xff"
    caption = "A 😀"
    entities = [{"type": "bold", "offset": 2, "length": 2}]
    keyboard = {"inline_keyboard": [[{"text": "Open", "callback_data": "doc:open"}]]}
    with BotAPIServer(directory) as server:
        status, _, raw = request(
            server.base_url,
            f"/bot{token}/sendDocument",
            upload_request(
                user,
                data,
                filename,
                caption=caption,
                caption_entities=json.dumps(entities),
                reply_markup=json.dumps(keyboard),
            ),
        )
        assert status == 200, raw
        response = json.loads(raw)
        file_id = response["result"]["document"]["file_id"]
        assert isinstance(file_id, str) and file_id.startswith("gramlab_document_")
        digest = hashlib.sha256(data).hexdigest()
        identity = json.dumps(
            ["document", digest, cleaned, mime], ensure_ascii=False, separators=(",", ":")
        ).encode()
        unique = "gramlab_document_unique_" + hashlib.sha256(identity).hexdigest()
        document = {
            "file_id": file_id,
            "file_unique_id": unique,
            "file_size": len(data),
            "file_name": cleaned,
        }
        if mime:
            document["mime_type"] = mime
        message = {
            "message_id": 1,
            "date": 50,
            "from": bot,
            "chat": {"id": user["id"], "type": "private", "first_name": "Ada"},
            "document": document,
            "caption": caption,
            "caption_entities": entities,
            "reply_markup": keyboard,
        }
        assert response == {"ok": True, "result": message}
        status, _, raw = request(
            server.base_url,
            f"/bot{token}/sendDocument",
            {"chat_id": user["id"], "document": file_id},
        )
        assert status == 200, raw
        assert json.loads(raw) == {
            "ok": True,
            "result": {
                "message_id": 2,
                "date": 50,
                "from": bot,
                "chat": message["chat"],
                "document": document,
            },
        }
        status, _, raw = request(server.base_url, f"/bot{token}/getFile", {"file_id": file_id})
        assert status == 200, raw
        path = f"documents/{file_id}"
        assert json.loads(raw) == {
            "ok": True,
            "result": {
                "file_id": file_id,
                "file_unique_id": unique,
                "file_size": len(data),
                "file_path": path,
            },
        }
        status, headers, downloaded = request(server.base_url, f"/file/bot{token}/{path}")
        assert status == 200 and downloaded == data
        assert headers["Content-Type"] == (mime or "application/octet-stream")
        assert (
            headers["Content-Length"] == str(len(data)) and headers["Cache-Control"] == "no-store"
        )
        before = state(directory)
        for route, payload in [
            (f"/bot{other_token}/sendDocument", {"chat_id": user["id"], "document": file_id}),
            (f"/bot{other_token}/getFile", {"file_id": file_id}),
            (f"/file/bot{other_token}/{path}", None),
        ]:
            status, _, raw = request(server.base_url, route, payload)
            assert status == 400 and json.loads(raw)["ok"] is False
            assert state(directory) == before
        with World.open(directory) as world:
            callback = world.create_callback(
                user_id=user["id"],
                chat_id=1,
                message_id=1,
                data="doc:open",
                request_id="click",
                version=5,
            )
        status, _, raw = request(server.base_url, f"/bot{token}/getUpdates", {})
        assert status == 200
        assert json.loads(raw) == {
            "ok": True,
            "result": [
                {
                    "update_id": 1,
                    "callback_query": {
                        "id": callback["id"],
                        "from": user,
                        "message": message,
                        "chat_instance": callback["chat_instance"],
                        "data": "doc:open",
                    },
                }
            ],
        }
    with World.open(directory) as world:
        assert world.history(1) == [
            {
                "id": 1,
                "chat_id": 1,
                "sender_id": bot["id"],
                "date": 50,
                "text": "",
                "document": {"document_id": "1"},
                "caption": caption,
                "caption_entities": entities,
                "reply_markup": keyboard,
            },
            {
                "id": 2,
                "chat_id": 1,
                "sender_id": bot["id"],
                "date": 50,
                "text": "",
                "document": {"document_id": "1"},
            },
        ]
        assert world.granted_document(user["id"], "1") == (
            {
                "document_id": "1",
                "file_name": cleaned,
                "mime_type": mime,
                "file_size": len(data),
                "sha256": digest,
            },
            data,
        )
