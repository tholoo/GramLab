"""Shared real-bot custom-emoji scenario for semantic and native acceptance."""

import hashlib
import http.client
import json
import selectors
import shutil
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from component_bot import FixtureBot

from gramlab.bot_api import BotAPIServer
from gramlab.client_bridge import ClientBridge
from gramlab.world import World


def run(
    capture: Callable[[str, dict[str, Any]], str] | None = None,
    tap: Callable[[str, str], None] | None = None,
    observe: Callable[[], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    directory = Path("world")
    assets = Path("custom-emoji")
    static = (assets / "emoji-static.webp").read_bytes()
    animated = (assets / "emoji-animated.webm").read_bytes()
    thumbnail = (assets / "emoji-thumbnail.webp").read_bytes()
    with World.create(directory, seed=31, now=1700000000) as world:
        world.create_user(first_name="Sara", language_code="fa")
        world.create_user(first_name="Echo", is_bot=True, username="gramlab_echo_bot")
        world.create_user(first_name="Uninvolved")
        world.open_private_chat(user_id=1, bot_id=2)
        world.register_custom_emoji(
            request_id="static",
            main=static,
            thumbnail=thumbnail,
            fallback="👩‍💻",
            custom_emoji_id=1,
            free=True,
            needs_repainting=False,
        )
        world.register_custom_emoji(
            request_id="animated",
            main=animated,
            thumbnail=thumbnail,
            fallback="👩‍💻",
            custom_emoji_id=1109,
            free=True,
            needs_repainting=False,
        )
        world.send_message(
            chat_id=1,
            sender_id=1,
            text="سلام 👩‍💻",
            entities=[{"type": "custom_emoji", "offset": 5, "length": 5, "custom_emoji_id": 1}],
        )
        token = world.issue_bot_token(2)
        capability = world.issue_client_token(1)
        other_capability = world.issue_client_token(3)
        world_id = world.world_id

    bot_records: dict[str, Any] = {}
    snapshots: dict[str, Any] = {}
    callbacks: dict[str, Any] = {}
    documents: dict[str, Any] = {}
    client: dict[str, Any] = {}

    def read_record(bot: Any, phase: str) -> dict[str, Any]:
        assert bot.stdout is not None
        with selectors.DefaultSelector() as ready:
            ready.register(bot.stdout, selectors.EVENT_READ)
            if not ready.select(timeout=20):
                raise RuntimeError(f"Custom emoji bot did not reach {phase}")
        line = bot.stdout.readline()
        if not line:
            _, stderr = bot.communicate(timeout=5)
            raise RuntimeError(f"Custom emoji bot exited before {phase}: {stderr}")
        result = dict(json.loads(line))
        if result.get("event") != phase:
            raise RuntimeError("Unexpected custom emoji bot phase")
        return result

    def bridge_request(
        bridge: ClientBridge,
        path: str,
        body: dict[str, Any] | None = None,
        *,
        authorization: str = capability,
    ) -> dict[str, Any]:
        endpoint = urlsplit(bridge.base_url)
        connection = http.client.HTTPConnection("127.0.0.1", endpoint.port, timeout=10)
        try:
            connection.request(
                "POST" if body is not None else "GET",
                path,
                json.dumps(body) if body is not None else None,
                {"Authorization": "Bearer " + authorization, "Content-Type": "application/json"},
            )
            response = connection.getresponse()
            return {"status": response.status, "body": json.loads(response.read())}
        finally:
            connection.close()

    def bridge_ok(
        bridge: ClientBridge, path: str, body: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        result = bridge_request(bridge, path, body)
        if result["status"] != 200:
            raise RuntimeError(f"Custom emoji bridge rejected {path}")
        return dict(result["body"])

    def bridge_asset(bridge: ClientBridge, asset_id: int) -> dict[str, Any]:
        endpoint = urlsplit(bridge.base_url)
        connection = http.client.HTTPConnection("127.0.0.1", endpoint.port, timeout=10)
        try:
            connection.request(
                "GET",
                f"/v4/assets/{asset_id}",
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
                "size": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
        finally:
            connection.close()

    configuration: dict[str, Any]
    fixture = FixtureBot("custom_emoji_bot.py")
    for name in ("emoji-static.webp", "emoji-animated.webm", "emoji-thumbnail.webp"):
        shutil.copy2(assets / name, fixture.data / name)
    with BotAPIServer(directory) as server, ClientBridge(directory) as bridge:
        configuration = {
            "endpoint": bridge.base_url,
            "capability": capability,
            "world_id": world_id,
            "user_id": 1,
            "bridge_version": 4,
        }
        with fixture.start({"GRAMLAB_BOT_API": server.base_url, "GRAMLAB_BOT_TOKEN": token}) as bot:
            bot_records["initial"] = read_record(bot, "initial")
            snapshots["initial"] = bridge_ok(bridge, "/v4/snapshot")
            documents["static_initial"] = bridge_request(
                bridge, "/v4/custom-emoji-documents", {"custom_emoji_ids": ["1", "1"]}
            )
            documents["ungranted"] = bridge_request(
                bridge, "/v4/custom-emoji-documents", {"custom_emoji_ids": ["1109"]}
            )
            documents["mixed"] = bridge_request(
                bridge, "/v4/custom-emoji-documents", {"custom_emoji_ids": ["1", "1109"]}
            )
            documents["integer"] = bridge_request(
                bridge, "/v4/custom-emoji-documents", {"custom_emoji_ids": [1]}
            )
            documents["uninvolved_snapshot"] = bridge_request(
                bridge, "/v4/snapshot", authorization=other_capability
            )
            if capture is not None:
                client["initial"] = capture("initial", configuration)

            with World.open(directory) as world:
                world.advance_time(5)
            if tap is None:
                bridge_ok(
                    bridge,
                    "/v4/callbacks",
                    {
                        "request_id": "emoji-edit",
                        "chat_id": 1,
                        "message_id": 2,
                        "data": "emoji:animate",
                    },
                )
            else:
                tap("initial", "Animate / متحرک")
            deadline = time.monotonic() + 10
            callback_id = ""
            while time.monotonic() < deadline:
                with World.open(directory) as world:
                    found = [
                        event["data"]["id"]
                        for event in world.events()
                        if event["type"] == "callback.created"
                        and event["data"]["data"] == "emoji:animate"
                    ]
                if found:
                    if len(found) != 1:
                        raise RuntimeError("Duplicate original custom emoji callback")
                    callback_id = found[0]
                    break
                time.sleep(0.05)
            if not callback_id:
                raise RuntimeError("Original custom emoji button did not publish a callback")
            callbacks["created"] = bridge_ok(bridge, "/v4/callbacks/" + callback_id)
            assert bot.stdin is not None
            bot.stdin.write("next\n")
            bot.stdin.flush()
            bot_records["edited"] = read_record(bot, "edited")
            callbacks["answered"] = bridge_ok(bridge, "/v4/callbacks/" + callback_id)
            snapshots["edited"] = bridge_ok(bridge, "/v4/snapshot")
            documents["both_edited"] = bridge_request(
                bridge,
                "/v4/custom-emoji-documents",
                {"custom_emoji_ids": ["1109", "1", "1109"]},
            )
            documents["assets_edited"] = {
                str(asset_id): bridge_asset(bridge, asset_id) for asset_id in (1, 2, 3)
            }
            changes = {
                "all": bridge_ok(bridge, "/v4/changes?after=0&limit=100"),
                "edited": bridge_ok(bridge, "/v4/changes?after=3&limit=2"),
            }
            if capture is not None:
                client["edited"] = capture("edited", configuration)
            _, stderr = bot.communicate(timeout=5)
            if bot.returncode != 0 or stderr:
                raise RuntimeError("Custom emoji bot failed after edit")

    with BotAPIServer(directory), ClientBridge(directory) as bridge:
        configuration = configuration | {"endpoint": bridge.base_url}
        snapshots["restarted"] = bridge_ok(bridge, "/v4/snapshot")
        callbacks["restarted"] = bridge_ok(bridge, "/v4/callbacks/" + callback_id)
        documents["both_restarted"] = bridge_request(
            bridge,
            "/v4/custom-emoji-documents",
            {"custom_emoji_ids": ["1", "1109"]},
        )
        documents["assets_restarted"] = {
            str(asset_id): bridge_asset(bridge, asset_id) for asset_id in (1, 2, 3)
        }
        if capture is not None:
            client["restarted"] = capture("restarted", configuration)
        if observe is not None:
            client.update(observe())

    with World.open(directory) as world:
        result = {
            "world_id": world_id,
            "bot": bot_records,
            "snapshots": snapshots,
            "callbacks": callbacks,
            "documents": documents,
            "changes": changes,
            "history": world.history(1),
            "events": world.events(),
            "pending": world.poll_updates(2),
            "api": [json.loads(line) for line in Path("bot/api.jsonl").read_text().splitlines()],
            "client": client,
        }
    serialized = json.dumps(result)
    if any(secret in serialized for secret in (token, capability, other_capability)):
        raise RuntimeError("Custom emoji evidence contained a capability")
    return result


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False))
