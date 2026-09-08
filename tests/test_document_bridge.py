import hashlib
import http.client
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from gramlab.client_bridge import ClientBridge
from gramlab.documents import DocumentUpload
from gramlab.world import World

EMOJI = Path(__file__).parent / "assets" / "custom-emoji"
PHOTO = Path(__file__).parent / "assets" / "rich-media" / "photo-square-16x16.png"


@dataclass(frozen=True, slots=True)
class Response:
    status: int
    headers: dict[str, str]
    body: bytes
    will_close: bool

    def json(self) -> dict[str, Any]:
        value = json.loads(self.body)
        assert isinstance(value, dict)
        return value


def request(
    base_url: str,
    token: str | None,
    method: str,
    path: str,
    body: dict[str, Any] | None = None,
    *,
    extra_headers: dict[str, str] | None = None,
) -> Response:
    url = urlsplit(base_url)
    assert url.hostname is not None
    connection = http.client.HTTPConnection(url.hostname, url.port, timeout=5)
    raw = None if body is None else json.dumps(body, separators=(",", ":")).encode()
    headers = {} if token is None else {"Authorization": f"Bearer {token}"}
    if raw is not None:
        headers |= {"Content-Type": "application/json", "Content-Length": str(len(raw))}
    headers |= extra_headers or {}
    try:
        connection.request(method, path, raw, headers)
        reply = connection.getresponse()
        return Response(reply.status, dict(reply.getheaders()), reply.read(), reply.will_close)
    finally:
        connection.close()


def unframed_post(base_url: str, token: str, headers: list[tuple[str, str]]) -> Response:
    url = urlsplit(base_url)
    assert url.hostname is not None
    connection = http.client.HTTPConnection(url.hostname, url.port, timeout=5)
    try:
        connection.putrequest("POST", "/v5/callbacks")
        connection.putheader("Authorization", f"Bearer {token}")
        for name, value in headers:
            connection.putheader(name, value)
        connection.endheaders()
        reply = connection.getresponse()
        return Response(reply.status, dict(reply.getheaders()), reply.read(), reply.will_close)
    finally:
        connection.close()


def duplicate_authorization_get(base_url: str, token: str) -> Response:
    url = urlsplit(base_url)
    assert url.hostname is not None
    connection = http.client.HTTPConnection(url.hostname, url.port, timeout=5)
    try:
        connection.putrequest("GET", "/v5/documents/1")
        connection.putheader("Authorization", f"Bearer {token}")
        connection.putheader("Authorization", f"Bearer {token}")
        connection.endheaders()
        reply = connection.getresponse()
        return Response(reply.status, dict(reply.getheaders()), reply.read(), reply.will_close)
    finally:
        connection.close()


def seed_document(
    world: World, document_id: int, upload: DocumentUpload, *, user_id: int | None = None
) -> None:
    with world._connection:
        world._connection.execute(
            "INSERT INTO media_blobs VALUES (?, ?) ON CONFLICT(sha256) DO NOTHING",
            (upload.sha256, upload.data),
        )
        world._connection.execute(
            "INSERT INTO documents VALUES (?, ?, ?, ?, ?)",
            (
                document_id,
                upload.sha256,
                upload.file_name,
                upload.mime_type,
                upload.file_unique_id,
            ),
        )
        if user_id is not None:
            world._connection.execute(
                "INSERT INTO document_grants VALUES (?, ?)", (user_id, document_id)
            )


def descriptor(document_id: int, upload: DocumentUpload) -> dict[str, Any]:
    return {
        "document_id": str(document_id),
        "file_name": upload.file_name,
        "mime_type": upload.mime_type,
        "file_size": len(upload.data),
        "sha256": upload.sha256,
    }


def assert_binary(reply: Response, data: bytes, mime_type: str) -> None:
    assert reply.status == 200 and reply.body == data
    assert reply.headers["Content-Type"] == mime_type
    assert reply.headers["Content-Length"] == str(len(data))
    assert reply.headers["Cache-Control"] == "no-store"
    assert reply.headers["Connection"] == "close"
    assert "Location" not in reply.headers
    assert reply.will_close


def test_v5_complete_mixed_delivery_callbacks_send_download_and_reopen(tmp_path: Path) -> None:
    directory = tmp_path / "world"
    main, thumbnail, photo_data = (
        (EMOJI / "emoji-static.webp").read_bytes(),
        (EMOJI / "emoji-thumbnail.webp").read_bytes(),
        PHOTO.read_bytes(),
    )
    small = DocumentUpload(b"small retained", "README")
    ten = DocumentUpload(b"ten document", "../ten.txt", "declared/ignored")
    maximum = DocumentUpload(b"maximum document", "maximum.PDF")
    with World.create(directory, seed=103, now=1_700_000_000) as world:
        user = world.create_user(first_name="Ada")
        world.create_user(first_name="Other")
        bot = world.create_user(first_name="Documents", is_bot=True)
        chat = world.open_private_chat(user_id=user["id"], bot_id=bot["id"])
        world.open_private_chat(user_id=2, bot_id=bot["id"])
        token = world.issue_client_token(user["id"])
        emoji = world.register_custom_emoji(
            request_id="emoji",
            main=main,
            thumbnail=thumbnail,
            fallback="🙂",
            custom_emoji_id=7,
        )
        seed_document(world, 2, small, user_id=user["id"])
        seed_document(world, 9, DocumentUpload(b"nine", "nine.bin"))
        ten_message = world.send_document(
            chat_id=chat["id"],
            sender_id=bot["id"],
            document={"media": "attach://document"},
            uploads={"document": ten},
        )
        photo_message = world.send_photo(
            chat_id=chat["id"],
            sender_id=bot["id"],
            photo={"type": "photo", "media": "attach://photo"},
            uploads={"photo": photo_data},
        )
        seed_document(world, 2**63 - 2, DocumentUpload(b"sentinel", "sentinel.bin"))
        keyboard = {"inline_keyboard": [[{"text": "Open", "callback_data": "open"}]]}
        maximum_message = world.send_document(
            chat_id=chat["id"],
            sender_id=bot["id"],
            document={"media": "attach://document"},
            uploads={"document": maximum},
            caption="🙂 maximum",
            caption_entities=[
                {"type": "custom_emoji", "offset": 0, "length": 2, "custom_emoji_id": "7"}
            ],
            reply_markup=keyboard,
        )
        world_id = world.world_id
    users = [
        {"id": 1, "is_bot": False, "first_name": "Ada"},
        {"id": 3, "is_bot": True, "first_name": "Documents"},
    ]
    chat_value = {"id": 1, "type": "private", "user_id": 1, "bot_id": 3}
    ten_message_expected = {
        "id": 1,
        "chat_id": 1,
        "sender_id": 3,
        "date": 1_700_000_000,
        "text": "",
        "document": {"document_id": "10"},
    }
    photo_message_expected = {
        "id": 2,
        "chat_id": 1,
        "sender_id": 3,
        "date": 1_700_000_000,
        "text": "",
        "photo": {"asset_id": 3},
    }
    maximum_message_expected = {
        "id": 3,
        "chat_id": 1,
        "sender_id": 3,
        "date": 1_700_000_000,
        "text": "",
        "reply_markup": keyboard,
        "document": {"document_id": str(2**63 - 1)},
        "caption": "🙂 maximum",
        "caption_entities": [
            {"type": "custom_emoji", "offset": 0, "length": 2, "custom_emoji_id": "7"}
        ],
    }
    assert ten_message == ten_message_expected
    assert photo_message == photo_message_expected
    assert maximum_message == maximum_message_expected
    emoji_descriptor = {
        "custom_emoji_id": "7",
        "fallback": "🙂",
        "free": True,
        "needs_repainting": False,
        "main_asset_id": 1,
        "thumbnail_asset_id": 2,
        "duration_ms": 0,
    }
    assert emoji == emoji_descriptor
    emoji_assets = [
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
    photo_asset = {
        "asset_id": 3,
        "mime_type": "image/png",
        "file_size": len(photo_data),
        "sha256": hashlib.sha256(photo_data).hexdigest(),
        "width": 16,
        "height": 16,
    }
    documents = [descriptor(2, small), descriptor(10, ten), descriptor(2**63 - 1, maximum)]
    callback_command = {
        "request_id": "document-callback",
        "chat_id": 1,
        "message_id": 3,
        "data": "open",
    }
    with ClientBridge(directory) as bridge:
        created = request(bridge.base_url, token, "POST", "/v5/callbacks", callback_command)
        assert created.status == 200
        assert created.headers["Cache-Control"] == "no-store"
        assert created.headers["Content-Length"] == str(len(created.body))
        assert created.headers["Connection"] == "close" and created.will_close
        assert "Location" not in created.headers
        callback_id = created.json()["callback"]["id"]
        callback = {
            "id": callback_id,
            "user_id": 1,
            "chat_id": 1,
            "message": maximum_message_expected,
            "data": "open",
            "chat_instance": hashlib.sha256(f"{world_id}:1".encode()).hexdigest(),
            "answer": None,
        }
        callback_response = {
            "schema": 5,
            "world_id": world_id,
            "user_id": 1,
            "callback": callback,
            "users": users,
            "assets": emoji_assets,
            "message_revision": 8,
            "custom_emoji": [emoji_descriptor],
            "documents": [documents[2]],
        }
        assert created.json() == callback_response
        with World.open(directory) as world:
            later = world.send_message(chat_id=1, sender_id=3, text="later")
        later_expected = {
            "id": 4,
            "chat_id": 1,
            "sender_id": 3,
            "date": 1_700_000_000,
            "text": "later",
        }
        assert later == later_expected
        fetched = request(bridge.base_url, token, "GET", f"/v5/callbacks/{callback_id}")
        assert fetched.status == 200 and fetched.json() == callback_response
        assert (
            request(bridge.base_url, token, "POST", "/v5/callbacks", callback_command).json()
            == callback_response
        )
        snapshot = request(bridge.base_url, token, "GET", "/v5/snapshot")
        assert snapshot.status == 200
        assert snapshot.json() == {
            "schema": 5,
            "world_id": world_id,
            "user_id": 1,
            "cursor": 10,
            "now": 1_700_000_000,
            "users": users,
            "chats": [chat_value],
            "messages": [
                ten_message_expected,
                photo_message_expected,
                maximum_message_expected,
                later_expected,
            ],
            "message_position": 4,
            "sends": [],
            "assets": [*emoji_assets, photo_asset],
            "message_revisions": [
                {"chat_id": 1, "message_id": 1, "revision": 6},
                {"chat_id": 1, "message_id": 2, "revision": 7},
                {"chat_id": 1, "message_id": 3, "revision": 8},
                {"chat_id": 1, "message_id": 4, "revision": 10},
            ],
            "custom_emoji": [emoji_descriptor],
            "documents": documents,
        }
        changes = request(bridge.base_url, token, "GET", "/v5/changes?after=0")
        assert changes.status == 200
        assert changes.json() == {
            "schema": 5,
            "world_id": world_id,
            "user_id": 1,
            "cursor": 4,
            "head": 4,
            "now": 1_700_000_000,
            "changes": [
                {
                    "position": index,
                    "type": "message.created",
                    "data": message,
                    "revision": revision,
                }
                for index, message, revision in (
                    (1, ten_message_expected, 6),
                    (2, photo_message_expected, 7),
                    (3, maximum_message_expected, 8),
                    (4, later_expected, 10),
                )
            ],
            "users": users,
            "assets": [*emoji_assets, photo_asset],
            "custom_emoji": [emoji_descriptor],
            "documents": documents[1:],
        }
        emoji_response = request(
            bridge.base_url,
            token,
            "POST",
            "/v5/custom-emoji-documents",
            {"custom_emoji_ids": ["7"]},
        )
        assert emoji_response.status == 200
        assert emoji_response.json() == {
            "schema": 5,
            "world_id": world_id,
            "user_id": 1,
            "custom_emoji": [emoji_descriptor],
            "assets": emoji_assets,
        }
        send_command = {
            "request_id": "client-send",
            "chat_id": 1,
            "text": "🙂",
            "entities": [{"type": "custom_emoji", "offset": 0, "length": 2, "custom_emoji_id": 7}],
        }
        sent = request(bridge.base_url, token, "POST", "/v5/messages", send_command)
        expected_client_message = {
            "id": 5,
            "chat_id": 1,
            "sender_id": 1,
            "date": 1_700_000_000,
            "text": "🙂",
            "entities": [
                {"type": "custom_emoji", "offset": 0, "length": 2, "custom_emoji_id": "7"}
            ],
        }
        send_response = {
            "schema": 5,
            "world_id": world_id,
            "user_id": 1,
            "send": {
                "request_id": "client-send",
                "position": 5,
                "message": expected_client_message,
            },
            "users": users,
            "custom_emoji": [emoji_descriptor],
            "assets": emoji_assets,
            "message_revision": 11,
            "documents": [],
        }
        assert sent.status == 200 and sent.json() == send_response
        assert request(bridge.base_url, token, "POST", "/v5/messages", send_command).json() == (
            send_response
        )
        assert_binary(
            request(bridge.base_url, token, "GET", "/v5/documents/2"),
            small.data,
            "application/octet-stream",
        )
        assert_binary(
            request(bridge.base_url, token, "GET", "/v5/documents/10"),
            ten.data,
            "text/plain",
        )
        assert_binary(
            request(bridge.base_url, token, "GET", f"/v5/documents/{2**63 - 1}"),
            maximum.data,
            "application/pdf",
        )
        assert_binary(
            request(bridge.base_url, token, "GET", "/v5/assets/3"),
            photo_data,
            "image/png",
        )
    with ClientBridge(directory) as reopened:
        assert_binary(
            request(reopened.base_url, token, "GET", f"/v5/documents/{2**63 - 1}"),
            maximum.data,
            "application/pdf",
        )
        assert (
            request(reopened.base_url, token, "GET", f"/v5/callbacks/{callback_id}").json()
            == callback_response
        )


def test_v5_document_download_auth_syntax_isolation_and_request_limits(tmp_path: Path) -> None:
    directory = tmp_path / "world"
    with World.create(directory, seed=104, now=5) as world:
        user = world.create_user(first_name="Ada")
        other = world.create_user(first_name="Other")
        bot = world.create_user(first_name="Bot", is_bot=True)
        chat = world.open_private_chat(user_id=user["id"], bot_id=bot["id"])
        token = world.issue_client_token(user["id"])
        other_token = world.issue_client_token(other["id"])
        upload = DocumentUpload(b"private", "../private.txt")
        world.send_document(
            chat_id=chat["id"],
            sender_id=bot["id"],
            document={"media": "attach://private"},
            uploads={"private": upload},
            reply_markup={"inline_keyboard": [[{"text": "Tap", "callback_data": "tap"}]]},
        )
        seed_document(world, 2, DocumentUpload(b"ungranted", "ungranted.bin"))
        before = list(world._connection.iterdump())
    with World.create(tmp_path / "other-world", seed=105, now=5) as other_world:
        other_world.create_user(first_name="Ada")
        foreign_token = other_world.issue_client_token(1)
    unavailable = {
        "schema": 5,
        "error": {"code": "document_unavailable", "message": "Document is unavailable"},
    }
    unauthorized = {
        "schema": 5,
        "error": {"code": "unauthorized", "message": "Client capability required"},
    }
    with ClientBridge(directory) as bridge:
        for denied_token, document_id in (
            (other_token, "1"),
            (token, "2"),
            (token, "3"),
        ):
            denied = request(bridge.base_url, denied_token, "GET", f"/v5/documents/{document_id}")
            assert denied.status == 404 and denied.json() == unavailable
            assert "Location" not in denied.headers and denied.will_close
        for bad_token in (None, "invalid", foreign_token):
            denied = request(bridge.base_url, bad_token, "GET", "/v5/documents/1")
            assert denied.status == 401 and denied.json() == unauthorized
        duplicate = duplicate_authorization_get(bridge.base_url, token)
        assert duplicate.status == 401 and duplicate.json() == unauthorized
        for value in ("", "0", "-1", "+1", "01", "1.0", "9223372036854775808", "private.txt"):
            rejected = request(bridge.base_url, token, "GET", f"/v5/documents/{value}")
            assert rejected.status == 400
            assert rejected.json() == {
                "schema": 5,
                "error": {"code": "invalid_request", "message": "Invalid document ID"},
            }
        for path in (
            "/v5/documents/extra/1",
            "/v5/documents//1",
            "/v5/documents/1/",
        ):
            rejected = request(bridge.base_url, token, "GET", path)
            assert rejected.status == 400
            assert rejected.json() == {
                "schema": 5,
                "error": {"code": "invalid_request", "message": "Invalid document ID"},
            }
        for headers, path in (
            ({}, "/v5/documents/1?download=true"),
            ({}, "/v5/documents/1?download="),
            ({"Range": "bytes=0-1"}, "/v5/documents/1"),
            ({"Transfer-Encoding": "chunked"}, "/v5/documents/1"),
        ):
            rejected = request(bridge.base_url, token, "GET", path, extra_headers=headers)
            assert rejected.status == 400 and rejected.json()["schema"] == 5
        assert_binary(
            request(bridge.base_url, token, "GET", "/v5/documents/1?"),
            upload.data,
            "text/plain",
        )
        post = request(bridge.base_url, token, "POST", "/v5/documents/1", {})
        assert post.status == 404
        assert post.json() == {
            "schema": 5,
            "error": {"code": "unsupported", "message": "Unknown client bridge operation"},
        }
        missing_asset = request(bridge.base_url, token, "GET", "/v5/assets/999")
        assert missing_asset.status == 404
        assert missing_asset.json() == {
            "schema": 5,
            "error": {"code": "asset_unavailable", "message": "Asset is unavailable"},
        }
        missing_emoji = request(
            bridge.base_url,
            token,
            "POST",
            "/v5/custom-emoji-documents",
            {"custom_emoji_ids": ["7"]},
        )
        assert missing_emoji.status == 404
        assert missing_emoji.json() == unavailable
        for framing in (
            [("Content-Type", "application/json")],
            [
                ("Content-Type", "application/json"),
                ("Content-Length", "2"),
                ("Content-Length", "2"),
            ],
            [
                ("Content-Type", "application/json"),
                ("Content-Length", "2"),
                ("Transfer-Encoding", "chunked"),
            ],
            [("Content-Type", "application/json"), ("Content-Length", "20000")],
        ):
            rejected = unframed_post(bridge.base_url, token, framing)
            assert rejected.status == 400 and rejected.json()["schema"] == 5
        malformed = request(
            bridge.base_url,
            token,
            "POST",
            "/v5/callbacks?unexpected=1",
            {"request_id": "bad", "chat_id": 1, "message_id": 1, "data": "tap"},
        )
        assert malformed.status == 400 and malformed.json()["schema"] == 5
        for body, headers in (
            ({"request_id": "missing"}, {}),
            (
                {
                    "request_id": "extra",
                    "chat_id": 1,
                    "message_id": 1,
                    "data": "tap",
                    "extra": True,
                },
                {},
            ),
            (
                {"request_id": "type", "chat_id": 1, "message_id": 1, "data": "tap"},
                {"Content-Type": "text/plain"},
            ),
        ):
            rejected = request(
                bridge.base_url,
                token,
                "POST",
                "/v5/callbacks",
                body,
                extra_headers=headers,
            )
            assert rejected.status == 400 and rejected.json()["schema"] == 5
        get_query = request(bridge.base_url, token, "GET", "/v5/callbacks/unknown?unexpected=1")
        assert get_query.status == 400 and get_query.json()["schema"] == 5
    with World.open(directory) as world:
        assert list(world._connection.iterdump()) == before
        assert world.history(1) == [
            {
                "id": 1,
                "chat_id": 1,
                "sender_id": 3,
                "date": 5,
                "text": "",
                "reply_markup": {"inline_keyboard": [[{"text": "Tap", "callback_data": "tap"}]]},
                "document": {"document_id": "1"},
            }
        ]
        assert world._connection.execute("SELECT count(*) FROM callbacks").fetchone() == (0,)
        assert world.document_descriptor("1")["file_name"] == "private.txt"


def test_legacy_document_routes_reject_without_callback_mutation(tmp_path: Path) -> None:
    directory = tmp_path / "world"
    with World.create(directory, seed=106, now=9) as world:
        user = world.create_user(first_name="Ada")
        bot = world.create_user(first_name="Bot", is_bot=True)
        chat = world.open_private_chat(user_id=user["id"], bot_id=bot["id"])
        token = world.issue_client_token(user["id"])
        world.send_document(
            chat_id=chat["id"],
            sender_id=bot["id"],
            document={"media": "attach://document"},
            uploads={"document": DocumentUpload(b"legacy guard", "guard.txt")},
            reply_markup={"inline_keyboard": [[{"text": "Tap", "callback_data": "tap"}]]},
        )
        before = list(world._connection.iterdump())
    callback_command = {
        "request_id": "callback",
        "chat_id": 1,
        "message_id": 1,
        "data": "tap",
    }
    with ClientBridge(directory) as bridge:
        for version in (1, 2, 3, 4):
            snapshot = request(bridge.base_url, token, "GET", f"/v{version}/snapshot")
            assert snapshot.status == 400 and snapshot.json()["schema"] == version
        events = request(bridge.base_url, token, "GET", "/v1/events?after=0")
        assert events.status == 400 and events.json()["schema"] == 1
        for version in (2, 3, 4):
            changes = request(bridge.base_url, token, "GET", f"/v{version}/changes?after=0")
            assert changes.status == 400 and changes.json()["schema"] == version
        for version in (1, 3, 4):
            command = callback_command | {"request_id": f"legacy-{version}"}
            rejected = request(bridge.base_url, token, "POST", f"/v{version}/callbacks", command)
            assert rejected.status == 400 and rejected.json()["schema"] == version
        with World.open(directory) as world:
            assert list(world._connection.iterdump()) == before
        created = request(bridge.base_url, token, "POST", "/v5/callbacks", callback_command)
        assert created.status == 200
        callback_id = created.json()["callback"]["id"]
        with World.open(directory) as world:
            after_created = list(world._connection.iterdump())
        for version in (1, 3, 4):
            rejected = request(
                bridge.base_url, token, "GET", f"/v{version}/callbacks/{callback_id}"
            )
            assert rejected.status == 400 and rejected.json()["schema"] == version
        with World.open(directory) as world:
            assert list(world._connection.iterdump()) == after_created
            assert world._connection.execute("SELECT count(*) FROM callbacks").fetchone() == (1,)
