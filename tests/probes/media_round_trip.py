"""Real multipart bot scenario shared by simulation and original-client acceptance."""

import hashlib
import http.client
import json
import selectors
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from component_bot import FixtureBot

from gramlab.bot_api import BotAPIServer
from gramlab.client_bridge import ClientBridge
from gramlab.world import World


def run(
    show: Callable[[dict[str, Any]], str] | None = None,
    observe: Callable[[], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    directory = Path("world")
    scene = json.loads(Path("media-scene.json").read_text())
    fixture = FixtureBot("media_bot.py")
    for asset in ("photo-square-16x16.png", "photo-quadrants-64x48.jpg"):
        shutil.copy2(asset, fixture.data / asset)
    with World.create(directory, seed=23, now=1700000000) as world:
        world.create_user(first_name="Sara", language_code="fa")
        world.create_user(first_name="Echo", username="gramlab_echo_bot", is_bot=True)
        world.create_user(first_name="Other", username="other_media_bot", is_bot=True)
        world.open_private_chat(user_id=1, bot_id=2)
        world.open_private_chat(user_id=1, bot_id=3)
        world.send_message(chat_id=1, sender_id=1, text="Show local photos")
        token = world.issue_bot_token(2)
        foreign_token = world.issue_bot_token(3)
        capability = world.issue_client_token(1)
        world_id = world.world_id

    client_results: dict[str, Any] = {}
    records: dict[str, Any] = {}

    def configuration(bridge: ClientBridge, stage: str) -> dict[str, Any]:
        return {
            "endpoint": bridge.base_url,
            "capability": capability,
            "world_id": world_id,
            "user_id": 1,
            "bridge_version": 3,
            "stage": stage,
        }

    def bridge_json(
        bridge: ClientBridge, path: str, body: dict[str, Any] | None = None
    ) -> tuple[int, dict[str, Any]]:
        endpoint = urlsplit(bridge.base_url)
        connection = http.client.HTTPConnection("127.0.0.1", endpoint.port, timeout=10)
        try:
            connection.request(
                "POST" if body is not None else "GET",
                path,
                json.dumps(body) if body is not None else None,
                {"Authorization": "Bearer " + capability, "Content-Type": "application/json"},
            )
            response = connection.getresponse()
            return response.status, dict(json.loads(response.read()))
        finally:
            connection.close()

    def bridge_asset(bridge: ClientBridge, asset_id: int) -> dict[str, Any]:
        endpoint = urlsplit(bridge.base_url)
        connection = http.client.HTTPConnection("127.0.0.1", endpoint.port, timeout=10)
        try:
            connection.request(
                "GET",
                f"/v3/assets/{asset_id}",
                headers={"Authorization": "Bearer " + capability},
            )
            response = connection.getresponse()
            payload = response.read()
            return {
                "status": response.status,
                "content_type": response.getheader("Content-Type"),
                "content_length": response.getheader("Content-Length"),
                "cache_control": response.getheader("Cache-Control"),
                "connection": response.getheader("Connection"),
                "sha256": hashlib.sha256(payload).hexdigest(),
                "size": len(payload),
            }
        finally:
            connection.close()

    def read_record(bot: Any, expected: str) -> dict[str, Any]:
        assert bot.stdout is not None
        with selectors.DefaultSelector() as ready:
            ready.register(bot.stdout, selectors.EVENT_READ)
            if not ready.select(timeout=20):
                raise RuntimeError(f"Media bot did not reach {expected}")
        line = bot.stdout.readline()
        if not line:
            _, stderr = bot.communicate(timeout=5)
            raise RuntimeError(f"Media bot exited before {expected}: {stderr}")
        value = dict(json.loads(line))
        if value.get("event") != expected:
            raise RuntimeError(f"Expected {expected}, received another bot event")
        return value

    environment = {
        "GRAMLAB_BOT_API": "",
        "GRAMLAB_BOT_TOKEN": token,
        "GRAMLAB_FOREIGN_BOT_TOKEN": foreign_token,
        "GRAMLAB_MEDIA_SCENE": json.dumps(scene, ensure_ascii=False),
    }
    with BotAPIServer(directory) as server, ClientBridge(directory) as bridge:
        environment["GRAMLAB_BOT_API"] = server.base_url
        with fixture.start(environment) as bot:
            records["published"] = read_record(bot, "published")["value"]
            initial_snapshot = bridge_json(bridge, "/v3/snapshot")[1]
            initial_changes = bridge_json(bridge, "/v3/changes?after=0&limit=100")[1]
            assert bridge_json(bridge, "/v1/snapshot")[0] == 400
            if show is not None:
                client_results["initial"] = show(configuration(bridge, "initial"))

            rich_message_id = records["published"]["rich"]["message_id"]
            with World.open(directory) as world:
                world.advance_time(5)
            callback_status, callback_created = bridge_json(
                bridge,
                "/v3/callbacks",
                {
                    "request_id": "media-tap-1",
                    "chat_id": 1,
                    "message_id": rich_message_id,
                    "data": scene["callback_data"],
                },
            )
            if callback_status != 200:
                raise RuntimeError("v3 media callback creation failed")
            records["callback"] = read_record(bot, "callback")
            callback_id = callback_created["callback"]["id"]
            callback_after = bridge_json(bridge, f"/v3/callbacks/{callback_id}")[1]

            assert bot.stdin is not None
            bot.stdin.write("edit\n")
            bot.stdin.flush()
            records["edited"] = read_record(bot, "edited")["value"]
            _, stderr = bot.communicate(timeout=10)
            if bot.returncode != 0 or stderr:
                raise RuntimeError("Media bot failed after its edit")
            edited_snapshot = bridge_json(bridge, "/v3/snapshot")[1]
            edited_changes = bridge_json(bridge, "/v3/changes?after=0&limit=100")[1]
            assets_after_edit = {
                str(asset["asset_id"]): bridge_asset(bridge, asset["asset_id"])
                for asset in edited_snapshot["assets"]
            }
            if show is not None:
                client_results["edited"] = show(configuration(bridge, "edited"))

    with BotAPIServer(directory) as reopened_server, ClientBridge(directory) as reopened_bridge:
        restarted_snapshot = bridge_json(reopened_bridge, "/v3/snapshot")[1]
        restarted_changes = bridge_json(reopened_bridge, "/v3/changes?after=0&limit=100")[1]
        restarted_callback = bridge_json(reopened_bridge, f"/v3/callbacks/{callback_id}")[1]
        assets_after_restart = {
            str(asset["asset_id"]): bridge_asset(reopened_bridge, asset["asset_id"])
            for asset in restarted_snapshot["assets"]
        }
        if show is not None:
            client_results["restart"] = show(configuration(reopened_bridge, "restart"))
        if observe is not None:
            client_results["observed"] = observe()
        # Ensure the restarted Bot API authenticates the same durable identities too.
        environment["GRAMLAB_BOT_API"] = reopened_server.base_url

    with World.open(directory) as world:
        result = {
            "world_id": world_id,
            "bot": records,
            "history": world.history(1),
            "events": world.events(),
            "pending": world.poll_updates(2),
            "v3": {
                "initial_snapshot": initial_snapshot,
                "initial_changes": initial_changes,
                "callback_created": callback_created,
                "callback_after": callback_after,
                "edited_snapshot": edited_snapshot,
                "edited_changes": edited_changes,
                "restarted_snapshot": restarted_snapshot,
                "restarted_changes": restarted_changes,
                "restarted_callback": restarted_callback,
                "assets_after_edit": assets_after_edit,
                "assets_after_restart": assets_after_restart,
            },
            "api": [json.loads(line) for line in Path("bot/api.jsonl").read_text().splitlines()],
            "client": client_results,
        }
    serialized = json.dumps(result)
    if token in serialized or foreign_token in serialized or capability in serialized:
        raise RuntimeError("Media evidence contains a capability")
    Path("media-round-trip.json").write_text(serialized)
    return result


if __name__ == "__main__":
    print(json.dumps(run()))
