import http.client
import json
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urlsplit

import pytest
from test_multipart_filename_decoding import CONTENT_TYPE, body, part

from gramlab.bot_api import BotAPIServer, _multipart
from gramlab.world import World

PHOTO = Path(__file__).parent / "assets" / "rich-media" / "photo-square-16x16.png"


def request(
    base_url: str,
    route: str,
    payload: bytes | dict[str, Any],
    *,
    content_type: str | None = None,
) -> tuple[int, dict[str, Any]]:
    url = urlsplit(base_url)
    assert url.hostname is not None
    raw = json.dumps(payload).encode() if isinstance(payload, dict) else payload
    default_type = "application/json" if isinstance(payload, dict) else CONTENT_TYPE
    headers = {"Content-Type": content_type or default_type}
    connection = http.client.HTTPConnection(url.hostname, url.port, timeout=10)
    try:
        connection.request("POST", route, raw, headers)
        response = connection.getresponse()
        value = json.loads(response.read())
        assert isinstance(value, dict)
        return response.status, value
    finally:
        connection.close()


def setup(path: Path) -> tuple[dict[str, Any], dict[str, Any], str, str]:
    with World.create(path, seed=112, now=112) as world:
        user = world.create_user(first_name="Ada")
        bot = world.create_user(first_name="Albums", is_bot=True)
        chat = world.open_private_chat(user_id=user["id"], bot_id=bot["id"])
        photo = world.send_photo(
            chat_id=chat["id"],
            sender_id=bot["id"],
            photo={"type": "photo", "media": "attach://p"},
            uploads={"p": PHOTO.read_bytes()},
        )
        file_id = world.photo_size(bot["id"], photo["photo"]["asset_id"])["file_id"]
        return user, bot, world.issue_bot_token(bot["id"]), file_id


def state(path: Path) -> list[str]:
    with closing(sqlite3.connect(path / "world.sqlite3")) as connection:
        return list(connection.iterdump())


def oversized_request(base_url: str, route: str, length: int) -> tuple[int, dict[str, Any]]:
    url = urlsplit(base_url)
    assert url.hostname is not None
    connection = http.client.HTTPConnection(url.hostname, url.port, timeout=10)
    try:
        connection.putrequest("POST", route)
        connection.putheader("Content-Type", CONTENT_TYPE)
        connection.putheader("Content-Length", str(length))
        connection.endheaders()
        response = connection.getresponse()
        value = json.loads(response.read())
        assert isinstance(value, dict)
        return response.status, value
    finally:
        connection.close()


def test_json_and_form_send_media_group_project_ordered_public_messages(tmp_path: Path) -> None:
    directory = tmp_path / "world"
    user, bot, token, file_id = setup(directory)
    media = [
        {"type": "photo", "media": file_id, "caption": "first"},
        {"type": "photo", "media": file_id, "caption": "second"},
    ]
    with BotAPIServer(directory) as server:
        status, response = request(
            server.base_url,
            f"/bot{token}/sendMediaGroup",
            {"chat_id": user["id"], "media": media},
        )
        assert status == 200
        result = response["result"]
        assert [message["message_id"] for message in result] == [2, 3]
        assert {message["media_group_id"] for message in result} == {"1"}
        assert [message["caption"] for message in result] == ["first", "second"]
        assert all(message["from"] == bot for message in result)
        assert all(message["chat"]["id"] == user["id"] for message in result)

        encoded = urlencode({"chat_id": user["id"], "media": json.dumps(media)}).encode()
        status, response = request(
            server.base_url,
            f"/bot{token}/sendMediaGroup",
            encoded,
            content_type="application/x-www-form-urlencoded",
        )
        assert status == 200
        assert [message["message_id"] for message in response["result"]] == [4, 5]
        assert {message["media_group_id"] for message in response["result"]} == {"2"}


def test_multipart_repeated_photo_and_forced_document_album(tmp_path: Path) -> None:
    directory = tmp_path / "world"
    user, _bot, token, _file_id = setup(directory)
    photo_media = [
        {"type": "photo", "media": "attach://same", "caption": "first"},
        {"type": "photo", "media": "attach://same", "caption": "second"},
    ]
    photo_body = body(
        part(b'form-data; name="chat_id"', str(user["id"]).encode()),
        part(b'form-data; name="media"', json.dumps(photo_media).encode()),
        part(
            b'form-data; name="same"; filename="same.png"',
            PHOTO.read_bytes(),
            b"Content-Type: image/png\r\n",
        ),
    )
    document_media = [
        {
            "type": "document",
            "media": "attach://gif",
            "disable_content_type_detection": False,
        },
        {"type": "document", "media": "attach://gif"},
    ]
    document_body = body(
        part(b'form-data; name="chat_id"', str(user["id"]).encode()),
        part(b'form-data; name="media"', json.dumps(document_media).encode()),
        part(
            b'form-data; name="gif"; filename="animation.gif"',
            b"GIF89a album ordinary file",
            b"Content-Type: image/gif\r\n",
        ),
    )
    with BotAPIServer(directory) as server:
        status, photo_response = request(server.base_url, f"/bot{token}/sendMediaGroup", photo_body)
        assert status == 200
        assert [message["caption"] for message in photo_response["result"]] == [
            "first",
            "second",
        ]
        status, document_response = request(
            server.base_url, f"/bot{token}/sendMediaGroup", document_body
        )
        assert status == 200
        documents = [message["document"] for message in document_response["result"]]
        assert documents[0] == documents[1]
        assert documents[0]["file_name"] == "animation.gif"
        assert documents[0]["file_size"] == len(b"GIF89a album ordinary file")


@pytest.mark.parametrize(
    "payload",
    [
        {"chat_id": 1, "media": [], "extra": True},
        {"chat_id": 1, "media": "not-json-array"},
        {
            "chat_id": 1,
            "media": [
                {"type": [], "media": "missing"},
                {"type": "photo", "media": "missing"},
            ],
        },
        {
            "chat_id": 1,
            "media": [
                {"type": "photo", "media": "missing"},
                {"type": "document", "media": "missing"},
            ],
        },
        {
            "chat_id": 1,
            "media": [
                {"type": "photo", "media": "missing", "reply_markup": {}},
                {"type": "photo", "media": "missing"},
            ],
        },
    ],
)
def test_http_rejections_are_strict_and_atomic(tmp_path: Path, payload: dict[str, Any]) -> None:
    directory = tmp_path / "world"
    _user, _bot, token, _file_id = setup(directory)
    before = state(directory)
    with BotAPIServer(directory) as server:
        status, response = request(server.base_url, f"/bot{token}/sendMediaGroup", payload)
    assert status == 400 and response["ok"] is False
    assert state(directory) == before


def test_http_required_album_fields_reject_with_stable_400_and_no_mutation(
    tmp_path: Path,
) -> None:
    directory = tmp_path / "world"
    _user, _bot, token, _file_id = setup(directory)
    before = state(directory)
    valid_media = [
        {"type": "photo", "media": "missing"},
        {"type": "photo", "media": "missing"},
    ]
    with BotAPIServer(directory) as server:
        for payload in ({"media": valid_media}, {"chat_id": 1}):
            status, response = request(server.base_url, f"/bot{token}/sendMediaGroup", payload)
            assert status == 400
            assert response == {
                "ok": False,
                "error_code": 400,
                "description": "chat_id and media are required",
            }
            assert state(directory) == before


def test_grouped_edit_methods_reject_without_mutation(tmp_path: Path) -> None:
    directory = tmp_path / "world"
    user, _bot, token, file_id = setup(directory)
    with BotAPIServer(directory) as server:
        status, created = request(
            server.base_url,
            f"/bot{token}/sendMediaGroup",
            {
                "chat_id": user["id"],
                "media": [
                    {"type": "photo", "media": file_id},
                    {"type": "photo", "media": file_id},
                ],
            },
        )
        assert status == 200
        before = state(directory)
        message_id = created["result"][0]["message_id"]
        for method, payload in (
            (
                "editMessageCaption",
                {"chat_id": user["id"], "message_id": message_id, "caption": "new"},
            ),
            (
                "editMessageMedia",
                {
                    "chat_id": user["id"],
                    "message_id": message_id,
                    "media": {"type": "photo", "media": file_id},
                },
            ),
        ):
            status, response = request(server.base_url, f"/bot{token}/{method}", payload)
            assert status == 400 and "editing grouped media" in response["description"]
            assert state(directory) == before


def test_album_multipart_upload_aggregate_is_bounded() -> None:
    raw = body(
        part(b'form-data; name="chat_id"', b"1"),
        part(b'form-data; name="media"', b"[]"),
        part(b'form-data; name="one"; filename="one.bin"', b"a" * 5),
        part(b'form-data; name="two"; filename="two.bin"', b"b" * 6),
    )
    with pytest.raises(ValueError, match="Uploaded file data exceeds"):
        _multipart(raw, CONTENT_TYPE, maximum_upload_bytes=10)


def test_album_http_request_rejects_one_byte_above_frozen_envelope(tmp_path: Path) -> None:
    directory = tmp_path / "world"
    _user, _bot, token, _file_id = setup(directory)
    before = state(directory)
    with BotAPIServer(directory) as server:
        status, response = oversized_request(
            server.base_url, f"/bot{token}/sendMediaGroup", 100_200_001
        )
    assert status == 400
    assert response == {
        "ok": False,
        "error_code": 400,
        "description": "Request body exceeds the prototype limit",
    }
    assert state(directory) == before
