import http.client
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import pytest

from gramlab.client_bridge import ClientBridge
from gramlab.documents import DocumentUpload
from gramlab.world import World

PHOTO = Path(__file__).parent / "assets" / "rich-media" / "photo-square-16x16.png"
EMOJI = Path(__file__).parent / "assets" / "custom-emoji"


@dataclass(frozen=True, slots=True)
class Response:
    status: int
    body: bytes

    def json(self) -> dict[str, Any]:
        value = json.loads(self.body)
        assert isinstance(value, dict)
        return value


def request(
    base_url: str,
    token: str,
    method: str,
    path: str,
    body: dict[str, Any] | None = None,
) -> Response:
    url = urlsplit(base_url)
    assert url.hostname is not None
    raw = None if body is None else json.dumps(body).encode()
    headers = {"Authorization": f"Bearer {token}"}
    if raw is not None:
        headers["Content-Type"] = "application/json"
    connection = http.client.HTTPConnection(url.hostname, url.port, timeout=10)
    try:
        connection.request(method, path, raw, headers)
        response = connection.getresponse()
        return Response(response.status, response.read())
    finally:
        connection.close()


def setup(path: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], str]:
    with World.create(path, seed=6, now=600) as world:
        user = world.create_user(first_name="Ada")
        bot = world.create_user(first_name="Albums", is_bot=True)
        chat = world.open_private_chat(user_id=user["id"], bot_id=bot["id"])
        token = world.issue_client_token(user["id"])
        return user, bot, chat, token


def test_v6_snapshot_and_changes_preserve_complete_album_topology_and_dependencies(
    tmp_path: Path,
) -> None:
    directory = tmp_path / "world"
    _user, bot, chat, token = setup(directory)
    with World.open(directory) as world:
        first = world.send_message(chat_id=chat["id"], sender_id=bot["id"], text="before")
        album = world.send_media_group(
            chat_id=chat["id"],
            sender_id=bot["id"],
            media=[
                {"type": "photo", "media": "attach://same", "caption": "one"},
                {"type": "photo", "media": "attach://same", "caption": "two"},
                {"type": "photo", "media": "attach://same", "caption": "three"},
            ],
            uploads={"same": PHOTO.read_bytes()},
        )
        last = world.send_message(chat_id=chat["id"], sender_id=bot["id"], text="after")
        asset = world.asset_descriptor(1)
        world_id = world.world_id

    with ClientBridge(directory) as bridge:
        snapshot = request(bridge.base_url, token, "GET", "/v6/snapshot")
        assert snapshot.status == 200
        snapshot_body = snapshot.json()
        assert snapshot_body["schema"] == 6
        assert snapshot_body["world_id"] == world_id
        assert snapshot_body["messages"] == [first, *album, last]
        assert snapshot_body["assets"] == [asset]
        assert snapshot_body["documents"] == []

        page = request(bridge.base_url, token, "GET", "/v6/changes?after=0&limit=2")
        assert page.status == 200
        page_body = page.json()
        assert page_body["cursor"] == 4 and page_body["head"] == 5
        assert [change["data"] for change in page_body["changes"]] == [first, *album]
        assert page_body["assets"] == [asset]
        assert page_body["documents"] == []

        minimum_page = request(bridge.base_url, token, "GET", "/v6/changes?after=1&limit=1")
        assert minimum_page.status == 200
        assert [change["data"] for change in minimum_page.json()["changes"]] == album
        assert minimum_page.json()["cursor"] == 4

        after_group = request(bridge.base_url, token, "GET", "/v6/changes?after=4&limit=1")
        assert after_group.status == 200
        assert [change["data"] for change in after_group.json()["changes"]] == [last]


def test_v6_changes_expansion_unions_dependencies_from_every_document_member(
    tmp_path: Path,
) -> None:
    directory = tmp_path / "world"
    user, bot, chat, token = setup(directory)
    with World.open(directory) as world:
        emoji = world.register_custom_emoji(
            request_id="expanded-page-emoji",
            main=(EMOJI / "emoji-static.webp").read_bytes(),
            thumbnail=(EMOJI / "emoji-thumbnail.webp").read_bytes(),
            fallback="🙂",
            custom_emoji_id=9,
        )
        first = world.send_message(chat_id=chat["id"], sender_id=bot["id"], text="before")
        album = world.send_media_group(
            chat_id=chat["id"],
            sender_id=bot["id"],
            media=[
                {"type": "document", "media": "attach://first"},
                {
                    "type": "document",
                    "media": "attach://second",
                    "caption": "🙂",
                    "caption_entities": [
                        {
                            "type": "custom_emoji",
                            "offset": 0,
                            "length": 2,
                            "custom_emoji_id": "9",
                        }
                    ],
                },
            ],
            uploads={
                "first": DocumentUpload(b"first document", "first.bin"),
                "second": DocumentUpload(b"second document", "second.bin"),
            },
        )
        documents = [world.document_descriptor("1"), world.document_descriptor("2")]
        assets = [
            world.asset_descriptor(emoji["main_asset_id"]),
            world.asset_descriptor(emoji["thumbnail_asset_id"]),
        ]
        assets.sort(key=lambda item: item["asset_id"])
        users = [user, bot]
        world_id = world.world_id

    with ClientBridge(directory) as bridge:
        response = request(bridge.base_url, token, "GET", "/v6/changes?after=0&limit=2")
        assert response.status == 200
        page = response.json()
        assert page["schema"] == 6 and page["world_id"] == world_id
        assert page["user_id"] == user["id"]
        assert page["cursor"] == page["head"] == 3
        assert [change["data"] for change in page["changes"]] == [first, *album]
        assert page["users"] == users
        assert page["assets"] == assets
        assert page["custom_emoji"] == [emoji]
        assert page["documents"] == documents


def test_v6_inside_group_cursor_is_exact_409_and_legacy_routes_reject_without_mutation(
    tmp_path: Path,
) -> None:
    directory = tmp_path / "world"
    _user, bot, chat, token = setup(directory)
    with World.open(directory) as world:
        album = world.send_media_group(
            chat_id=chat["id"],
            sender_id=bot["id"],
            media=[
                {"type": "document", "media": "attach://same"},
                {"type": "document", "media": "attach://same"},
                {"type": "document", "media": "attach://same"},
            ],
            uploads={"same": DocumentUpload(b"album document", "album.txt")},
        )
        before = list(world._connection.iterdump())
    with ClientBridge(directory) as bridge:
        for after in (1, 2):
            response = request(bridge.base_url, token, "GET", f"/v6/changes?after={after}&limit=1")
            assert response.status == 409
            assert response.json() == {
                "schema": 6,
                "error": {
                    "code": "resnapshot_required",
                    "message": "Client cursor splits a media group",
                },
            }
        boundary = request(bridge.base_url, token, "GET", "/v6/changes?after=3&limit=1")
        assert boundary.status == 200 and boundary.json()["changes"] == []
        for version in range(1, 6):
            snapshot = request(bridge.base_url, token, "GET", f"/v{version}/snapshot")
            assert snapshot.status == 400 and snapshot.json()["schema"] == version
        for version in range(2, 6):
            changes = request(bridge.base_url, token, "GET", f"/v{version}/changes?after=0")
            assert changes.status == 400 and changes.json()["schema"] == version
        callback = {
            "request_id": "legacy-album",
            "chat_id": chat["id"],
            "message_id": album[0]["id"],
            "data": "tap",
        }
        for version in (1, 3, 4, 5):
            rejected = request(bridge.base_url, token, "POST", f"/v{version}/callbacks", callback)
            assert rejected.status == 400 and rejected.json()["schema"] == version
    with World.open(directory) as world:
        assert list(world._connection.iterdump()) == before


def test_v6_document_and_asset_routes_keep_v5_topology(tmp_path: Path) -> None:
    directory = tmp_path / "world"
    _user, bot, chat, token = setup(directory)
    with World.open(directory) as world:
        photos = world.send_media_group(
            chat_id=chat["id"],
            sender_id=bot["id"],
            media=[
                {"type": "photo", "media": "attach://p"},
                {"type": "photo", "media": "attach://p"},
            ],
            uploads={"p": PHOTO.read_bytes()},
        )
        documents = world.send_media_group(
            chat_id=chat["id"],
            sender_id=bot["id"],
            media=[
                {"type": "document", "media": "attach://d"},
                {"type": "document", "media": "attach://d"},
            ],
            uploads={"d": DocumentUpload(b"document bytes", "album.bin")},
        )
        asset_id = photos[0]["photo"]["asset_id"]
        document_id = documents[0]["document"]["document_id"]
    with ClientBridge(directory) as bridge:
        asset = request(bridge.base_url, token, "GET", f"/v6/assets/{asset_id}")
        document = request(bridge.base_url, token, "GET", f"/v6/documents/{document_id}")
        assert asset.status == 200 and asset.body == PHOTO.read_bytes()
        assert document.status == 200 and document.body == b"document bytes"


def test_v6_messages_callbacks_and_custom_emoji_document_routes_keep_group_identity(
    tmp_path: Path,
) -> None:
    directory = tmp_path / "world"
    _user, bot, chat, token = setup(directory)
    with World.open(directory) as world:
        world.register_custom_emoji(
            request_id="album-emoji",
            main=(EMOJI / "emoji-static.webp").read_bytes(),
            thumbnail=(EMOJI / "emoji-thumbnail.webp").read_bytes(),
            fallback="🙂",
            custom_emoji_id=7,
        )
        album = world.send_media_group(
            chat_id=chat["id"],
            sender_id=bot["id"],
            media=[
                {
                    "type": "photo",
                    "media": "attach://p",
                    "caption": "🙂",
                    "caption_entities": [
                        {
                            "type": "custom_emoji",
                            "offset": 0,
                            "length": 2,
                            "custom_emoji_id": "7",
                        }
                    ],
                },
                {"type": "photo", "media": "attach://p"},
            ],
            uploads={"p": PHOTO.read_bytes()},
        )
    with ClientBridge(directory) as bridge:
        sent = request(
            bridge.base_url,
            token,
            "POST",
            "/v6/messages",
            {"request_id": "v6-send", "chat_id": chat["id"], "text": "hello"},
        )
        assert sent.status == 200 and sent.json()["schema"] == 6
        emoji = request(
            bridge.base_url,
            token,
            "POST",
            "/v6/custom-emoji-documents",
            {"custom_emoji_ids": ["7"]},
        )
        assert emoji.status == 200 and emoji.json()["schema"] == 6
        assert emoji.json()["custom_emoji"][0]["custom_emoji_id"] == "7"
        callback = request(
            bridge.base_url,
            token,
            "POST",
            "/v6/callbacks",
            {
                "request_id": "v6-callback",
                "chat_id": chat["id"],
                "message_id": album[0]["id"],
                "data": "tap",
            },
        )
        assert callback.status == 200
        callback_body = callback.json()
        assert callback_body["callback"]["message"]["media_group_id"] == "1"
        assert callback_body["documents"] == []
        callback_id = callback_body["callback"]["id"]
        fetched = request(bridge.base_url, token, "GET", f"/v6/callbacks/{callback_id}")
        assert fetched.status == 200 and fetched.json() == callback_body


@pytest.mark.parametrize(
    ("corruption", "route"),
    [
        ("group_id", "/v6/snapshot"),
        ("copied_member", "/v6/snapshot"),
        ("nested_photo", "/v6/snapshot"),
        ("non_object_message", "/v6/snapshot"),
        ("duplicate_revision", "/v6/snapshot"),
        ("gapped_revision", "/v6/snapshot"),
        ("non_object_event", "/v6/changes?after=0"),
        ("invalid_event_json", "/v6/changes?after=0"),
    ],
)
def test_v6_rejects_malformed_persisted_group_state(
    tmp_path: Path, corruption: str, route: str
) -> None:
    directory = tmp_path / "world"
    _user, bot, chat, token = setup(directory)
    with World.open(directory) as world:
        group = world.send_media_group(
            chat_id=chat["id"],
            sender_id=bot["id"],
            media=[
                {"type": "photo", "media": "attach://p"},
                {"type": "photo", "media": "attach://p"},
            ],
            uploads={"p": PHOTO.read_bytes()},
        )
        with world._connection:
            revisions = [
                world._connection.execute(
                    "SELECT revision FROM message_revisions WHERE chat_id=? AND message_id=?",
                    (chat["id"], member["id"]),
                ).fetchone()[0]
                for member in group
            ]
            if corruption == "duplicate_revision":
                world._connection.execute(
                    "UPDATE message_revisions SET revision=? WHERE chat_id=? AND message_id=?",
                    (revisions[0], chat["id"], group[1]["id"]),
                )
            elif corruption == "gapped_revision":
                gapped = world._connection.execute(
                    "INSERT INTO events(type, body) VALUES ('message.created', ?)",
                    (json.dumps(group[1]),),
                ).lastrowid
                world._connection.execute(
                    "UPDATE message_revisions SET revision=? WHERE chat_id=? AND message_id=?",
                    (gapped, chat["id"], group[1]["id"]),
                )
            elif corruption in ("non_object_event", "invalid_event_json"):
                world._connection.execute(
                    "UPDATE events SET body=? WHERE sequence=?",
                    ("[]" if corruption == "non_object_event" else "{", revisions[0]),
                )
            elif corruption == "non_object_message":
                world._connection.execute(
                    "UPDATE messages SET body='[]' WHERE chat_id=? AND id=?",
                    (chat["id"], group[0]["id"]),
                )
                world._connection.execute(
                    "UPDATE events SET body='[]' WHERE sequence=?", (revisions[0],)
                )
            else:
                target = 1 if corruption == "copied_member" else 0
                if corruption == "group_id":
                    corrupted = dict(group[target]) | {"media_group_id": "2"}
                elif corruption == "nested_photo":
                    corrupted = dict(group[target]) | {"photo": {"asset_id": []}}
                else:
                    corrupted = group[0]
                encoded = json.dumps(corrupted)
                world._connection.execute(
                    "UPDATE messages SET body=? WHERE chat_id=? AND id=?",
                    (encoded, chat["id"], group[target]["id"]),
                )
                world._connection.execute(
                    "UPDATE events SET body=? WHERE sequence=?", (encoded, revisions[target])
                )
    with ClientBridge(directory) as bridge:
        response = request(bridge.base_url, token, "GET", route)
        assert response.status == 400
        assert response.json() == {
            "schema": 6,
            "error": {"code": "invalid_request", "message": "Invalid stored media group"},
        }


def test_v6_limit_1000_expands_at_most_nine_group_members(tmp_path: Path) -> None:
    directory = tmp_path / "world"
    _user, bot, chat, _token = setup(directory)
    with World.open(directory) as world:
        for index in range(999):
            world.send_message(chat_id=chat["id"], sender_id=bot["id"], text=f"standalone {index}")
        world.send_media_group(
            chat_id=chat["id"],
            sender_id=bot["id"],
            media=[{"type": "photo", "media": "attach://same"} for _index in range(10)],
            uploads={"same": PHOTO.read_bytes()},
        )
        page = world.client_changes(1, after=0, limit=1000, version=6)
        assert len(page["changes"]) == 1009
        assert page["cursor"] == page["head"] == 1009
