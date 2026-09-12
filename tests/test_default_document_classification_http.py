"""HTTP admission and atomicity for default document classification."""

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
from gramlab.documents import MAX_DOCUMENT_BYTES
from gramlab.world import World

UNSUPPORTED = "GRAMLAB_UNSUPPORTED: default document content classification"


def setup(path: Path) -> tuple[dict[str, Any], dict[str, Any], str]:
    with World.create(path, seed=110, now=1_700_000_000) as world:
        user = world.create_user(first_name="Sara")
        bot = world.create_user(first_name="Files", is_bot=True)
        world.open_private_chat(user_id=user["id"], bot_id=bot["id"])
        return user, bot, world.issue_bot_token(bot["id"])


def request(
    base_url: str, route: str, payload: bytes | dict[str, Any]
) -> tuple[int, dict[str, Any]]:
    endpoint = urlsplit(base_url)
    assert endpoint.hostname is not None
    connection = http.client.HTTPConnection(endpoint.hostname, endpoint.port, timeout=20)
    data = json.dumps(payload).encode() if isinstance(payload, dict) else payload
    content_type = "application/json" if isinstance(payload, dict) else CONTENT_TYPE
    try:
        connection.request("POST", route, data, {"Content-Type": content_type})
        response = connection.getresponse()
        return response.status, dict(json.loads(response.read()))
    finally:
        connection.close()


def database(path: Path) -> list[str]:
    with closing(sqlite3.connect(path / "world.sqlite3")) as connection:
        return list(connection.iterdump())


def upload_body(
    user_id: int,
    data: bytes,
    filename: str,
    *,
    force_file: bool | None,
) -> bytes:
    fields = [part(b'form-data; name="chat_id"', str(user_id).encode())]
    if force_file is not None:
        fields.append(
            part(
                b'form-data; name="disable_content_type_detection"',
                str(force_file).lower().encode(),
            )
        )
    fields.append(
        part(
            f'form-data; name="document"; filename="{filename}"'.encode(),
            data,
            b"Content-Type: video/mp4\r\n",
        )
    )
    return body(*fields)


def edit_body(
    data: bytes,
    filename: str,
    *,
    force_file: bool | None,
) -> bytes:
    media: dict[str, Any] = {"type": "document", "media": "attach://replacement"}
    if force_file is not None:
        media["disable_content_type_detection"] = force_file
    return body(
        part(b'form-data; name="chat_id"', b"1"),
        part(b'form-data; name="message_id"', b"1"),
        part(b'form-data; name="media"', json.dumps(media).encode()),
        part(
            f'form-data; name="replacement"; filename="{filename}"'.encode(),
            data,
            b"Content-Type: application/octet-stream\r\n",
        ),
    )


@pytest.mark.parametrize("force_file", [None, False])
@pytest.mark.parametrize(
    "data,filename,mime_type",
    [
        (b"\x89PNG\r\n\x1a\nbody", "picture.png", "image/png"),
        (b"\xff\xd8\xffbody", "picture.jpg", "image/jpeg"),
        (b"%PDF-1.7\nbody", "report.pdf", "application/pdf"),
        (b"PK\x03\x04body", "archive.zip", "application/zip"),
        (b"plain text", "note.txt", "text/plain"),
        (b"\x00\xffopaque", "unknown.bin", "application/octet-stream"),
    ],
)
def test_send_document_admits_general_uploads_for_omitted_and_false(
    tmp_path: Path,
    force_file: bool | None,
    data: bytes,
    filename: str,
    mime_type: str,
) -> None:
    directory = tmp_path / "world"
    user, bot, token = setup(directory)
    with BotAPIServer(directory) as server:
        status, response = request(
            server.base_url,
            f"/bot{token}/sendDocument",
            upload_body(user["id"], data, filename, force_file=force_file),
        )

    assert status == 200, response
    result = response["result"]
    assert set(result) == {"message_id", "from", "chat", "date", "document"}
    assert result["from"] == bot
    assert result["document"]["file_name"] == filename
    assert result["document"]["file_size"] == len(data)
    assert result["document"]["mime_type"] == mime_type
    with World.open(directory) as world:
        assert world.history(1) == [
            {
                "id": 1,
                "chat_id": 1,
                "sender_id": bot["id"],
                "date": 1_700_000_000,
                "text": "",
                "document": {"document_id": "1"},
            }
        ]


@pytest.mark.parametrize("force_file", [None, False])
def test_specialized_send_rejection_is_atomic_and_forced_retry_and_reuse_are_unchanged(
    tmp_path: Path, force_file: bool | None
) -> None:
    directory = tmp_path / "world"
    user, _bot, token = setup(directory)
    specialized = b"GIF89a truncated-specialized-family"
    before = database(directory)
    with BotAPIServer(directory) as server:
        status, response = request(
            server.base_url,
            f"/bot{token}/sendDocument",
            upload_body(user["id"], specialized, "image.gif", force_file=force_file),
        )
        assert status == 400
        assert response == {"ok": False, "error_code": 400, "description": UNSUPPORTED}
        assert database(directory) == before

        status, forced = request(
            server.base_url,
            f"/bot{token}/sendDocument",
            upload_body(user["id"], specialized, "image.gif", force_file=True),
        )
        assert status == 200, forced
        file_id = forced["result"]["document"]["file_id"]
        status, reused = request(
            server.base_url,
            f"/bot{token}/sendDocument",
            {
                "chat_id": user["id"],
                "document": file_id,
                "disable_content_type_detection": False,
            },
        )
        assert status == 200, reused

    assert reused["result"]["document"] == forced["result"]["document"]
    assert reused["result"]["message_id"] == forced["result"]["message_id"] + 1


@pytest.mark.parametrize("force_file", [None, False])
def test_specialized_default_media_edit_is_atomic_then_forced_retry_succeeds(
    tmp_path: Path, force_file: bool | None
) -> None:
    directory = tmp_path / "world"
    user, _bot, token = setup(directory)
    with BotAPIServer(directory) as server:
        status, sent = request(
            server.base_url,
            f"/bot{token}/sendDocument",
            upload_body(user["id"], b"initial", "initial.bin", force_file=True),
        )
        assert status == 200, sent
        before = database(directory)

        status, rejected = request(
            server.base_url,
            f"/bot{token}/editMessageMedia",
            edit_body(b"OggS truncated", "sound.ogg", force_file=force_file),
        )
        assert status == 400
        assert rejected == {"ok": False, "error_code": 400, "description": UNSUPPORTED}
        assert database(directory) == before

        status, edited = request(
            server.base_url,
            f"/bot{token}/editMessageMedia",
            edit_body(b"OggS truncated", "sound.ogg", force_file=True),
        )
        assert status == 200, edited

    assert edited["result"]["message_id"] == sent["result"]["message_id"]
    assert edited["result"]["document"]["file_name"] == "sound.ogg"


def test_ordinary_default_media_edits_admit_omitted_and_false(tmp_path: Path) -> None:
    directory = tmp_path / "world"
    user, _bot, token = setup(directory)
    with BotAPIServer(directory) as server:
        status, sent = request(
            server.base_url,
            f"/bot{token}/sendDocument",
            upload_body(user["id"], b"initial", "initial.bin", force_file=True),
        )
        assert status == 200, sent
        for force_file, data, filename in (
            (None, b"%PDF-1.7\nreplacement", "replacement.pdf"),
            (False, b"PK\x03\x04replacement", "replacement.zip"),
        ):
            status, edited = request(
                server.base_url,
                f"/bot{token}/editMessageMedia",
                edit_body(data, filename, force_file=force_file),
            )
            assert status == 200, edited
            assert edited["result"]["document"]["file_name"] == filename


def test_default_document_http_size_limit_is_inclusive(tmp_path: Path) -> None:
    directory = tmp_path / "world"
    user, _bot, token = setup(directory)
    with BotAPIServer(directory) as server:
        maximum = b"x" * MAX_DOCUMENT_BYTES
        status, response = request(
            server.base_url,
            f"/bot{token}/sendDocument",
            upload_body(user["id"], maximum, "maximum.bin", force_file=None),
        )
        assert status == 200, response
        assert response["result"]["document"]["file_size"] == MAX_DOCUMENT_BYTES
        del maximum

        before = database(directory)
        oversized = b"x" * (MAX_DOCUMENT_BYTES + 1)
        status, response = request(
            server.base_url,
            f"/bot{token}/sendDocument",
            upload_body(user["id"], oversized, "oversized.bin", force_file=False),
        )
        assert status == 400
        assert response["description"] == "Uploaded file data exceeds the request limit"
        assert database(directory) == before
