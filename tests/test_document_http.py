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


def request(
    base: str,
    route: str,
    payload: bytes | dict[str, Any] | None = None,
    *,
    extra_headers: dict[str, str] | None = None,
) -> tuple[int, dict[str, str], bytes]:
    url = urlsplit(base)
    assert url.hostname is not None
    connection = http.client.HTTPConnection(url.hostname, url.port, timeout=10)
    headers: dict[str, str] = {}
    if isinstance(payload, dict):
        payload = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    elif isinstance(payload, bytes):
        headers["Content-Type"] = CONTENT_TYPE
    headers.update(extra_headers or {})
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


def test_document_rejections_and_typed_reuse_leave_complete_database_unchanged(
    tmp_path: Path,
) -> None:
    directory = tmp_path / "world"
    user, _bot, token, _ = setup(directory)
    image = (Path(__file__).parent / "assets/rich-media/photo-square-16x16.png").read_bytes()
    with BotAPIServer(directory) as server:
        status, _, raw = request(
            server.base_url, f"/bot{token}/sendDocument", upload_request(user, image, b"image.png")
        )
        assert status == 200
        file_id = json.loads(raw)["result"]["document"]["file_id"]
        photo_body = body(
            part(b'form-data; name="chat_id"', str(user["id"]).encode()),
            part(
                b'form-data; name="photo"; filename="x.png"',
                image,
            ),
        )
        status, _, raw = request(server.base_url, f"/bot{token}/sendPhoto", photo_body)
        assert status == 200
        photo_id = json.loads(raw)["result"]["photo"][0]["file_id"]
        assert photo_id != file_id
        status, _, raw = request(server.base_url, f"/bot{token}/getFile", {"file_id": photo_id})
        assert status == 200
        photo_path = json.loads(raw)["result"]["file_path"]
        for download_path in [f"documents/{file_id}", photo_path]:
            status, headers, downloaded = request(
                server.base_url, f"/file/bot{token}/{download_path}"
            )
            assert status == 200 and downloaded == image
            assert headers["Content-Type"] == "image/png"
        with World.open(directory) as world:
            messages = world.history(1)
            assert messages[0] == {
                "id": 1,
                "chat_id": 1,
                "sender_id": _bot["id"],
                "date": 50,
                "text": "",
                "document": {"document_id": "1"},
            }
            assert "photo" in messages[1] and "document" not in messages[1]
            assert world.document_descriptor("1") == {
                "document_id": "1",
                "file_name": "image.png",
                "mime_type": "image/png",
                "file_size": len(image),
                "sha256": hashlib.sha256(image).hexdigest(),
            }
        before = state(directory)
        for download_path in [f"documents/{photo_id}", f"photos/{file_id}.png"]:
            status, _, raw = request(server.base_url, f"/file/bot{token}/{download_path}")
            assert status == 404
            assert json.loads(raw) == {"ok": False, "error_code": 404, "description": "Not Found"}
            assert state(directory) == before
        base = {"chat_id": user["id"], "document": file_id}
        invalid: list[dict[str, Any]] = [
            {"chat_id": user["id"]},
            *[
                base | {"document": value}
                for value in [
                    None,
                    1,
                    {},
                    "missing",
                    "https://example.invalid/document",
                    "/etc/passwd",
                    photo_id,
                    "attach://missing",
                ]
            ],
            base | {"chat_id": 9999},
            base | {"disable_content_type_detection": 1},
            base | {"caption": "x" * 1025},
            base | {"caption": "\ud800"},
            base
            | {"caption": "x", "caption_entities": [{"type": "bold", "offset": 0, "length": 2}]},
            base | {"reply_markup": {"inline_keyboard": [[{"text": "Bad"}]]}},
            base | {"thumbnail": "attach://thumb"},
            base | {"parse_mode": "HTML"},
            base | {"unexpected": True},
        ]
        for parameters in invalid:
            status, _, raw = request(server.base_url, f"/bot{token}/sendDocument", parameters)
            response = json.loads(raw)
            assert status == 400 and response["ok"] is False and response["error_code"] == 400, (
                parameters
            )
            assert set(response) == {"ok", "error_code", "description"}
            assert state(directory) == before
        chat = part(b'form-data; name="chat_id"', str(user["id"]).encode())
        document = part(b'form-data; name="document"; filename="x.txt"', b"file")
        force = part(b'form-data; name="disable_content_type_detection"', b"true")
        bad_uploads = [
            body(chat, document),
            body(
                chat, document, part(b'form-data; name="disable_content_type_detection"', b"false")
            ),
            body(chat, force, part(b'form-data; name="document"; filename="empty"', b"")),
            body(chat, force, document, part(b'form-data; name="unused"; filename="u"', b"other")),
            body(chat, force, document, part(b'form-data; name="caption"', b"x" * 65537)),
        ]
        for index, raw_upload in enumerate(bad_uploads):
            status, _, raw = request(server.base_url, f"/bot{token}/sendDocument", raw_upload)
            assert status == 400 and json.loads(raw)["ok"] is False
            if index < 2:
                assert json.loads(raw) == {
                    "ok": False,
                    "error_code": 400,
                    "description": "GRAMLAB_UNSUPPORTED: document upload content detection",
                }
            assert state(directory) == before
        status, _, raw = request(
            server.base_url, f"/bot{token}/sendPhoto", {"chat_id": user["id"], "photo": file_id}
        )
        assert status == 400 and json.loads(raw)["ok"] is False
        assert state(directory) == before
        status, _, raw = request(
            server.base_url,
            f"/file/bot{token}/documents/{file_id}",
            extra_headers={"Range": "bytes=0-1"},
        )
        assert status == 400 and json.loads(raw)["ok"] is False
        assert state(directory) == before


def test_explicit_attachment_and_form_reuse_follow_existing_boolean_rules(tmp_path: Path) -> None:
    directory = tmp_path / "world"
    user, _bot, token, _ = setup(directory)
    payload = body(
        part(b'form-data; name="chat_id"', str(user["id"]).encode()),
        part(b'form-data; name="document"', b"attach://named"),
        part(b'form-data; name="disable_content_type_detection"', b"YES"),
        part(b'form-data; name="named"; filename="note.txt"', b"note"),
    )
    with BotAPIServer(directory) as server:
        status, _, raw = request(server.base_url, f"/bot{token}/sendDocument", payload)
        assert status == 200, raw
        first = json.loads(raw)["result"]
        file_id = first["document"]["file_id"]
        status, _, raw = request(
            server.base_url,
            f"/bot{token}/sendDocument",
            f"chat_id={user['id']}&document={file_id}&disable_content_type_detection=false".encode(),
            extra_headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert status == 200, raw
        assert json.loads(raw) == {"ok": True, "result": first | {"message_id": 2}}


def test_http_document_byte_limit_is_inclusive_without_widening_photo_limit(tmp_path: Path) -> None:
    directory = tmp_path / "world"
    user, bot, token, _ = setup(directory)
    with BotAPIServer(directory) as server:
        payload = b"x" * 50_000_000
        status, _, raw = request(
            server.base_url,
            f"/bot{token}/sendDocument",
            upload_request(user, payload, b"boundary.bin"),
        )
        assert status == 200, raw
        document = json.loads(raw)["result"]["document"]
        assert document["file_size"] == 50_000_000
        status, headers, data = request(
            server.base_url, f"/file/bot{token}/documents/{document['file_id']}"
        )
        assert status == 200 and data == payload and headers["Content-Length"] == "50000000"
        del payload, data
        # Compare logical state without materializing the 50MB BLOB as a 100MB SQL literal.
        with World.open(directory) as world:
            before = (
                world.history(1),
                world.events(),
                world.client_snapshot(user["id"], version=5),
            )
        for method, size in [("sendDocument", 50_000_001)]:
            rejected = b"x" * size
            raw_upload = upload_request(user, rejected, b"too-large.bin")
            status, _, raw = request(server.base_url, f"/bot{token}/{method}", raw_upload)
            assert status == 400 and json.loads(raw)["ok"] is False
            del rejected, raw_upload
            with World.open(directory) as world:
                assert (
                    world.history(1),
                    world.events(),
                    world.client_snapshot(user["id"], version=5),
                ) == before
                assert world._connection.execute("SELECT count(*) FROM media_blobs").fetchone() == (
                    1,
                )
                assert world._connection.execute("SELECT count(*) FROM documents").fetchone() == (
                    1,
                )
                assert world.bot_file(bot["id"], document["file_id"])[0]["file_size"] == 50_000_000

        # Reject an oversized photo at its declared body boundary before sending a body.
        # A full send races the intentional early close and may raise BrokenPipe client-side.
        status, _, raw = request(
            server.base_url,
            f"/bot{token}/sendPhoto",
            b"",
            extra_headers={"Content-Length": "20200001"},
        )
        assert status == 400
        assert json.loads(raw) == {
            "ok": False,
            "error_code": 400,
            "description": "Request body exceeds the prototype limit",
        }
        with World.open(directory) as world:
            assert (
                world.history(1),
                world.events(),
                world.client_snapshot(user["id"], version=5),
            ) == before


def test_document_caption_custom_emoji_survives_http_and_rejected_reuse(tmp_path: Path) -> None:
    directory = tmp_path / "world"
    user, bot, token, _ = setup(directory)
    assets = Path(__file__).parent / "assets/custom-emoji"
    main = (assets / "emoji-static.webp").read_bytes()
    thumbnail = (assets / "emoji-thumbnail.webp").read_bytes()
    with World.open(directory) as world:
        emoji = world.register_custom_emoji(
            request_id="caption",
            main=main,
            thumbnail=thumbnail,
            fallback="🙂",
            custom_emoji_id=7,
        )
    entities = [{"type": "custom_emoji", "offset": 0, "length": 2, "custom_emoji_id": "7"}]
    digest = hashlib.sha256(b"file").hexdigest()
    identity = json.dumps(
        ["document", digest, "note.txt", "text/plain"], separators=(",", ":")
    ).encode()
    with BotAPIServer(directory) as server:
        status, _, raw = request(
            server.base_url,
            f"/bot{token}/sendDocument",
            upload_request(
                user, b"file", b"note.txt", caption="🙂", caption_entities=json.dumps(entities)
            ),
        )
        assert status == 200, raw
        file_id = json.loads(raw)["result"]["document"]["file_id"]
        message = {
            "message_id": 1,
            "date": 50,
            "from": bot,
            "chat": {"id": user["id"], "type": "private", "first_name": "Ada"},
            "document": {
                "file_id": file_id,
                "file_unique_id": "gramlab_document_unique_" + hashlib.sha256(identity).hexdigest(),
                "file_size": 4,
                "file_name": "note.txt",
                "mime_type": "text/plain",
            },
            "caption": "🙂",
            "caption_entities": entities,
        }
        assert json.loads(raw) == {"ok": True, "result": message}
        before = state(directory)
        parameters = {"chat_id": user["id"], "document": file_id, "caption": "🙂"}
        status, _, raw = request(
            server.base_url,
            f"/bot{token}/sendDocument",
            parameters | {"caption_entities": [entities[0] | {"custom_emoji_id": "8"}]},
        )
        assert status == 400 and json.loads(raw)["ok"] is False
        assert state(directory) == before
        status, _, raw = request(
            server.base_url,
            f"/bot{token}/sendDocument",
            parameters | {"caption_entities": entities},
        )
        assert status == 200
        assert json.loads(raw) == {"ok": True, "result": message | {"message_id": 2}}
    with World.open(directory) as world:
        assert world.history(1) == [
            {
                "id": identifier,
                "chat_id": 1,
                "sender_id": bot["id"],
                "date": 50,
                "text": "",
                "document": {"document_id": "1"},
                "caption": "🙂",
                "caption_entities": entities,
            }
            for identifier in [1, 2]
        ]
        descriptors, _ = world.granted_custom_emoji(user["id"], ["7"])
        assert descriptors == [emoji]
        assert world.granted_asset(user["id"], emoji["main_asset_id"])[1] == main
        assert world.granted_asset(user["id"], emoji["thumbnail_asset_id"])[1] == thumbnail
