import http.client
import io
import json
from pathlib import Path
from urllib.parse import urlsplit

from PIL import Image

from gramlab.client_bridge import ClientBridge
from gramlab.world import World


def test_v3_snapshot_changes_asset_and_old_version_rejection(tmp_path: Path) -> None:
    data_out = io.BytesIO()
    Image.new("RGB", (2, 3), "red").save(data_out, "JPEG")
    data = data_out.getvalue()
    directory = tmp_path / "world"
    with World.create(directory, seed=1, now=4) as world:
        user = world.create_user(first_name="Ada")
        bot = world.create_user(first_name="Bot", is_bot=True)
        chat = world.open_private_chat(user_id=user["id"], bot_id=bot["id"])
        token = world.issue_client_token(user["id"])
        world.send_photo(
            chat_id=chat["id"],
            sender_id=bot["id"],
            photo={"type": "photo", "media": "attach://p"},
            uploads={"p": data},
        )
    headers = {"Authorization": f"Bearer {token}"}
    with ClientBridge(directory) as server:
        url = urlsplit(server.base_url)
        connection = http.client.HTTPConnection(url.hostname, url.port, timeout=5)
        connection.request("GET", "/v3/snapshot", headers=headers)
        response = connection.getresponse()
        snapshot = json.loads(response.read())
        assert response.status == 200 and snapshot["schema"] == 3
        assert snapshot["assets"][0]["mime_type"] == "image/jpeg"
        assert snapshot["message_revisions"][0]["revision"] == snapshot["cursor"]
        connection.request("GET", "/v3/changes?after=0", headers=headers)
        changes = json.loads(connection.getresponse().read())
        assert changes["changes"][0]["revision"] == snapshot["cursor"]
        assert changes["assets"] == snapshot["assets"]
        assert changes["users"] == snapshot["users"]
        connection.request("GET", "/v2/snapshot", headers=headers)
        rejected = connection.getresponse()
        assert rejected.status == 400 and json.loads(rejected.read())["schema"] == 2
        connection.request("GET", "/v3/assets/1", headers=headers)
        asset = connection.getresponse()
        assert asset.status == 200 and asset.read() == data
        assert asset.getheader("Cache-Control") == "no-store"
        connection.close()


def test_v3_asset_grants_are_persona_and_world_scoped(tmp_path: Path) -> None:
    directory = tmp_path / "world"
    with World.create(directory, seed=1, now=1) as world:
        user = world.create_user(first_name="Ada")
        other = world.create_user(first_name="Lin")
        bot = world.create_user(first_name="Bot", is_bot=True)
        chat = world.open_private_chat(user_id=user["id"], bot_id=bot["id"])
        token = world.issue_client_token(other["id"])
        output = io.BytesIO()
        Image.new("RGB", (1, 1)).save(output, "PNG")
        world.send_photo(
            chat_id=chat["id"],
            sender_id=bot["id"],
            photo={"type": "photo", "media": "attach://p"},
            uploads={"p": output.getvalue()},
        )
    with ClientBridge(directory) as server:
        url = urlsplit(server.base_url)
        connection = http.client.HTTPConnection(url.hostname, url.port, timeout=5)
        connection.request("GET", "/v3/assets/1", headers={"Authorization": f"Bearer {token}"})
        response = connection.getresponse()
        assert response.status == 404
        assert json.loads(response.read()) == {
            "schema": 3,
            "error": {"code": "asset_unavailable", "message": "Asset is unavailable"},
        }


def test_v3_callback_freezes_media_dependencies_and_revision(tmp_path: Path) -> None:
    directory = tmp_path / "world"
    with World.create(directory, seed=1, now=3) as world:
        user = world.create_user(first_name="Ada")
        bot = world.create_user(first_name="Bot", is_bot=True)
        chat = world.open_private_chat(user_id=user["id"], bot_id=bot["id"])
        token = world.issue_client_token(user["id"])
        output = io.BytesIO()
        Image.new("RGB", (2, 2)).save(output, "PNG")
        message = world.send_photo(
            chat_id=chat["id"],
            sender_id=bot["id"],
            photo={"type": "photo", "media": "attach://p"},
            uploads={"p": output.getvalue()},
            reply_markup={"inline_keyboard": [[{"text": "Tap", "callback_data": "media"}]]},
        )
        revision = world.client_snapshot(user["id"], version=3)["message_revisions"][0]["revision"]
    command = json.dumps(
        {
            "request_id": "tap-1",
            "chat_id": chat["id"],
            "message_id": message["id"],
            "data": "media",
        }
    ).encode()
    with ClientBridge(directory) as server:
        url = urlsplit(server.base_url)
        connection = http.client.HTTPConnection(url.hostname, url.port, timeout=5)
        connection.request(
            "POST",
            "/v3/callbacks",
            body=command,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Content-Length": str(len(command)),
            },
        )
        response = connection.getresponse()
        result = json.loads(response.read())
        assert response.status == 200
        assert set(result) == {
            "schema",
            "world_id",
            "user_id",
            "callback",
            "users",
            "assets",
            "message_revision",
        }
        assert result["message_revision"] == revision
        assert result["assets"][0]["asset_id"] == 1
        assert [entry["id"] for entry in result["users"]] == [user["id"], bot["id"]]
