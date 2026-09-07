"""Shared real-bot scenario; native mode supplies original screenshots and button input."""

import http.client
import json
import selectors
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
    with World.create(directory, seed=29, now=1700000000) as world:
        world.create_user(first_name="Sara", language_code="fa")
        world.create_user(first_name="Echo", is_bot=True, username="gramlab_echo_bot")
        world.create_user(first_name="Arman", username="arman_local", language_code="fa")
        world.create_user(first_name="Mina", username="mina_local", language_code="en")
        for user in (1, 3, 4):
            world.open_private_chat(user_id=user, bot_id=2)
        world.send_message(chat_id=1, sender_id=1, text="Show explicit mentions")
        token = world.issue_bot_token(2)
        capability = world.issue_client_token(1)
        world_id = world.world_id
    records: dict[str, Any] = {}
    snapshots: dict[str, Any] = {}
    receipts: dict[str, Any] = {}
    client: dict[str, Any] = {}

    def read_record(bot: Any, phase: str) -> dict[str, Any]:
        assert bot.stdout is not None
        with selectors.DefaultSelector() as ready:
            ready.register(bot.stdout, selectors.EVENT_READ)
            if not ready.select(timeout=15):
                raise RuntimeError(f"Mention bot did not reach {phase}")
        line = bot.stdout.readline()
        if not line:
            _, stderr = bot.communicate(timeout=5)
            if token in stderr:
                raise RuntimeError("Bot diagnostic contained a capability")
            raise RuntimeError(f"Mention bot exited before {phase}: {stderr}")
        result = dict(json.loads(line))
        if result.get("event") != phase:
            raise RuntimeError("Unexpected mention bot phase")
        return result

    with BotAPIServer(directory) as server, ClientBridge(directory) as bridge:
        configuration = {
            "endpoint": bridge.base_url,
            "capability": capability,
            "world_id": world_id,
            "user_id": 1,
            "bridge_version": 3,
        }

        def bridge_json(path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
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
                result = dict(json.loads(response.read()))
                if response.status != 200:
                    raise RuntimeError(f"Mention bridge failed: HTTP {response.status}")
                return result
            finally:
                connection.close()

        with FixtureBot("rich_mentions_bot.py").start(
            {
                "GRAMLAB_BOT_API": server.base_url,
                "GRAMLAB_BOT_TOKEN": token,
            }
        ) as bot:
            records["initial"] = read_record(bot, "initial")
            snapshots["initial"] = bridge_json("/v3/snapshot")
            if capture is not None:
                client["initial"] = capture("initial", configuration)
            for phase, previous, label, data in (
                ("edited", "initial", "Mention B / نفر بعد", "mention:b"),
                ("removed", "edited", "Remove mention / حذف نام", "mention:remove"),
            ):
                with World.open(directory) as world:
                    world.advance_time(5)
                if tap is None:
                    bridge_json(
                        "/v3/callbacks",
                        {
                            "request_id": "mentions-" + phase,
                            "chat_id": 1,
                            "message_id": 2,
                            "data": data,
                        },
                    )
                else:
                    tap(previous, label)
                # Bot is paused before polling, making the unacknowledged frozen receipt observable.
                deadline = time.monotonic() + 10
                callback_id = ""
                while time.monotonic() < deadline:
                    with World.open(directory) as world:
                        callbacks = [
                            event["data"]
                            for event in world.events()
                            if event["type"] == "callback.created" and event["data"]["data"] == data
                        ]
                    if callbacks:
                        if len(callbacks) != 1:
                            raise RuntimeError("Duplicate original mention callback")
                        callback_id = callbacks[0]["id"]
                        break
                    time.sleep(0.05)
                if not callback_id:
                    raise RuntimeError("Original mention button did not publish a callback")
                receipts[phase + "_created"] = bridge_json("/v3/callbacks/" + callback_id)
                assert bot.stdin is not None
                bot.stdin.write("next\n")
                bot.stdin.flush()
                records[phase] = read_record(bot, phase)
                receipts[phase + "_answered"] = bridge_json("/v3/callbacks/" + callback_id)
                snapshots[phase] = bridge_json("/v3/snapshot")
                if capture is not None:
                    client[phase] = capture(phase, configuration)
            _, stderr = bot.communicate(timeout=5)
            if bot.returncode != 0 or stderr:
                raise RuntimeError("Mention bot failed after removal")
        snapshots["restarted"] = bridge_json("/v3/snapshot")
        if capture is not None:
            client["restarted"] = capture("restarted", configuration)
        for phase in ("edited", "removed"):
            callback_id = receipts[phase + "_created"]["callback"]["id"]
            receipts[phase + "_restarted"] = bridge_json("/v3/callbacks/" + callback_id)
        changes = {
            "all": bridge_json("/v3/changes?after=0&limit=100"),
            "old_a": bridge_json("/v3/changes?after=1&limit=1"),
            "old_b": bridge_json("/v3/changes?after=2&limit=1"),
            "removed": bridge_json("/v3/changes?after=3&limit=1"),
        }
        if observe is not None:
            client.update(observe())
    with World.open(directory) as world:
        result = {
            "world_id": world_id,
            "bot": records,
            "snapshots": snapshots,
            "callbacks": receipts,
            "changes": changes,
            "history": world.history(1),
            "events": world.events(),
            "pending": world.poll_updates(2),
            "other_personas": {
                str(user): world.client_snapshot(user, version=3) for user in (3, 4)
            },
            "api": [json.loads(line) for line in Path("bot/api.jsonl").read_text().splitlines()],
            "client": client,
        }
    if token in json.dumps(result) or capability in json.dumps(result):
        raise RuntimeError("Mention evidence contained a capability")
    return result


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False))
