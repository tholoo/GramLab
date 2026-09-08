"""Literal multipart metadata expectations from pinned TDLib HttpReader/misc semantics."""

import hashlib
import http.client
import io
import json
import sqlite3
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from PIL import Image

from gramlab._document_metadata import clean_document_filename
from gramlab.bot_api import BotAPIServer, _multipart
from gramlab.world import World

CONTENT_TYPE = "multipart/form-data; boundary=literal"


def part(disposition: bytes, payload: bytes, extra: bytes = b"") -> bytes:
    return (
        b"--literal\r\nContent-Disposition: "
        + disposition
        + b"\r\n"
        + extra
        + b"\r\n"
        + payload
        + b"\r\n"
    )


def body(*parts: bytes) -> bytes:
    return b"".join(parts) + b"--literal--\r\n"


@pytest.mark.parametrize(
    "encoded,decoded,cleaned",
    [
        (b"a+b%2Bc.txt", b"a+b+c.txt", "a+b+c.txt"),
        (b"dir%2FUP%2fleaf.PDF", b"dir/UP/leaf.PDF", "leaf.PDF"),
        (b"dir%5cname.bin", b"dir\\name.bin", "name.bin"),
        (b"dir%252Fname.txt", b"dir%2Fname.txt", "dir%2Fname.txt"),
        (b"a%g1%2%00z%.txt", b"a%g1%2\x00z%.txt", "a%g1%2z%.txt"),
        (rb"dir\/name.txt", b"dir/name.txt", "name.txt"),
        (rb"dir\name.txt", b"dirname.txt", "dirname.txt"),
        (rb"dir\\name.txt", b"dir\\name.txt", "name.txt"),
        (rb"a\"b.txt", b'a"b.txt', "a b.txt"),
        (rb"a\%32.txt", b"a2.txt", "a2.txt"),
        (b"a%5Cname.txt", b"a\\name.txt", "name.txt"),
        (b"a%22b.txt", b'a"b.txt', "a b.txt"),
        (b"", b"", "file"),
        (b"%DA%AF%D8%B2%D8%A7%D8%B1%D8%B4.txt", "گزارش.txt".encode(), "گزارش.txt"),
        (b"ok%FF.bin", b"ok\xff.bin", "file"),
        (b"ok\xff.bin", b"ok\xff.bin", "file"),
        (b"%ED%A0%80.txt", b"\xed\xa0\x80.txt", "file"),
    ],
)
def test_literal_filename_decode_and_pinned_cleaner_boundary(
    encoded: bytes, decoded: bytes, cleaned: str
) -> None:
    payload = b"\x00%2F+\xff\r\noriginal payload"
    raw = body(part(b'form-data; name="fi%6Ce+"; filename="' + encoded + b'"', payload))
    fields, uploads = _multipart(raw, CONTENT_TYPE)
    assert fields == {}
    assert list(uploads) == ["file+"]
    upload = uploads["file+"]
    assert upload.filename.encode("utf-8", errors="surrogateescape") == decoded
    assert clean_document_filename(upload.filename) == cleaned
    assert (upload.data, upload.content_type) == (payload, None)


def test_decoded_fields_are_checked_and_text_payload_is_not_url_decoded() -> None:
    raw = body(
        part(rb'form-data; name="te\%78t+"', b"a%2Fb+%FF"),
        part(b'form-data; name="%E2%98%83"; filename=""', b"", b"Content-Type: \r\n"),
    )
    fields, uploads = _multipart(raw, CONTENT_TYPE)
    assert fields == {"text+": "a%2Fb+%FF"}
    assert list(uploads) == ["☃"]
    assert (uploads["☃"].filename, uploads["☃"].data, uploads["☃"].content_type) == ("", b"", "")


INVALID_PARTS = [
    (part(b'form-data; name="%FF"; filename="x.png"', b"file"),),
    (part(b'form-data; name="\xff"; filename="x.png"', b"file"),),
    (part(b'form-data; name=""; filename="x.png"', b"file"),),
    (part(b'form-data; name="photo"; filename="unclosed', b"file"),),
    (part(b'form-data; name="photo"; filename="ends\\"', b"file"),),
    (part(b'form-data; name="photo"; filename="a"junk', b"file"),),
    (part(b'form-data; name="photo"; filename=token', b"file"),),
    (part(b'form-data; name="photo"; filename="a"; filename="b"', b"file"),),
    (part(b'form-data; name="photo"; filename="a\nb"', b"file"),),
    (
        part(b'form-data; name="photo"', b"text"),
        part(b'form-data; name="ph%6Fto"; filename="x.png"', b"file"),
    ),
    (
        part(b'form-data; name="ph%6fto"; filename="x.png"', b"file"),
        part(rb'form-data; name="ph\oto"; filename="y.png"', b"file"),
    ),
]


@pytest.mark.parametrize("parts", INVALID_PARTS)
def test_invalid_disposition_and_decoded_collisions_reject(parts: tuple[bytes, ...]) -> None:
    with pytest.raises(ValueError):
        _multipart(body(*parts), CONTENT_TYPE)


def request(base: str, path: str, data: bytes = b"", *, get: bool = False) -> tuple[int, bytes]:
    url = urlsplit(base)
    assert url.hostname is not None
    connection = http.client.HTTPConnection(url.hostname, url.port, timeout=5)
    try:
        connection.request("GET" if get else "POST", path, data, {"Content-Type": CONTENT_TYPE})
        response = connection.getresponse()
        return response.status, response.read()
    finally:
        connection.close()


def test_http_rejections_preserve_entire_world_and_photo_metadata_never_changes_bytes(
    tmp_path: Path,
) -> None:
    directory = tmp_path / "world"
    with World.create(directory, seed=7, now=50) as world:
        user = world.create_user(first_name="Ada")
        bot = world.create_user(first_name="Bot", is_bot=True)
        world.open_private_chat(user_id=user["id"], bot_id=bot["id"])
        token = world.issue_bot_token(bot["id"])
    with sqlite3.connect(directory / "world.sqlite3") as connection:
        before = list(connection.iterdump())
    chat = part(b'form-data; name="chat_id"', str(user["id"]).encode())
    with BotAPIServer(directory) as server:
        for parts in INVALID_PARTS:
            status, raw = request(server.base_url, f"/bot{token}/sendPhoto", body(chat, *parts))
            response = json.loads(raw)
            assert status == 400 and response["ok"] is False and response["error_code"] == 400
            assert set(response) == {"ok", "error_code", "description"}
            with sqlite3.connect(directory / "world.sqlite3") as connection:
                assert list(connection.iterdump()) == before
        image = io.BytesIO()
        Image.new("RGB", (3, 2), (10, 20, 30)).save(image, "PNG")
        data = image.getvalue() + b"\r\n--literal-not-delimiter%FF+\x00"
        status, raw = request(
            server.base_url,
            f"/bot{token}/sendPhoto",
            body(
                chat,
                part(
                    rb'form-data; name="ph%6Fto"; filename="dir\\%FF+\".txt"',
                    data,
                    b"Content-Type: Application/X-Unrelated ; Flag=YES\r\n",
                ),
            ),
        )
        response = json.loads(raw)
        assert status == 200, response
        file_id = response["result"]["photo"][0]["file_id"]
        assert isinstance(file_id, str) and file_id.startswith("gramlab_")
        photo = {
            "file_id": file_id,
            "file_unique_id": hashlib.sha256(data).hexdigest(),
            "file_size": len(data),
            "width": 3,
            "height": 2,
        }
        assert response == {
            "ok": True,
            "result": {
                "message_id": 1,
                "date": 50,
                "from": bot,
                "chat": {"id": user["id"], "type": "private", "first_name": "Ada"},
                "photo": [photo],
            },
        }
        status, raw = request(
            server.base_url,
            f"/bot{token}/getFile",
            body(part(b'form-data; name="file_id"', file_id.encode())),
        )
        path = f"photos/{file_id}.png"
        assert status == 200
        assert json.loads(raw) == {
            "ok": True,
            "result": {
                "file_id": file_id,
                "file_unique_id": hashlib.sha256(data).hexdigest(),
                "file_size": len(data),
                "file_path": path,
            },
        }
        assert request(server.base_url, f"/file/bot{token}/{path}", get=True) == (200, data)
    with World.open(directory) as world:
        assert world.history(1) == [
            {
                "id": 1,
                "chat_id": 1,
                "sender_id": bot["id"],
                "date": 50,
                "text": "",
                "photo": {"asset_id": 1},
            }
        ]
        assert world.client_snapshot(user["id"], version=3)["assets"] == [
            {
                "asset_id": 1,
                "sha256": hashlib.sha256(data).hexdigest(),
                "file_size": len(data),
                "mime_type": "image/png",
                "width": 3,
                "height": 2,
            }
        ]
