"""Shared real-bot scene; simulation verifies content without claiming clipboard effects."""

import json
import selectors
from collections.abc import Callable
from pathlib import Path
from typing import Any

from component_bot import FixtureBot

from gramlab.bot_api import BotAPIServer
from gramlab.client_bridge import ClientBridge
from gramlab.world import World


def state() -> dict[str, Any]:
    with World.open(Path("world")) as world:
        return {
            "snapshot": world.client_snapshot(1, version=2),
            "events": world.events(),
            "history": world.history(1),
            "pending": world.poll_updates(2),
        }


def run(
    show: Callable[[dict[str, Any]], str] | None = None,
    observe: Callable[[], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    # Native consumer owns its unchanged-scene restart; shared observe expects a bot edit.
    directory = Path("world")
    with World.create(directory, seed=21, now=1700000000) as world:
        world.create_user(first_name="Sara", language_code="en")
        world.create_user(first_name="Echo", username="gramlab_echo_bot", is_bot=True)
        world.open_private_chat(user_id=1, bot_id=2)
        world.send_message(chat_id=1, sender_id=1, text="Show rich effects")
        token, capability = world.issue_bot_token(2), world.issue_client_token(1)
        world_id = world.world_id
    client: dict[str, Any] = {}
    with BotAPIServer(directory) as server, ClientBridge(directory) as bridge:
        with FixtureBot("rich_action_effect_bot.py").start(
            {"GRAMLAB_BOT_API": server.base_url, "GRAMLAB_BOT_TOKEN": token}
        ) as bot:
            assert bot.stdout is not None
            with selectors.DefaultSelector() as ready:
                ready.register(bot.stdout, selectors.EVENT_READ)
                if not ready.select(timeout=10):
                    raise RuntimeError("Real bot did not send the rich-effect message")
            initial = json.loads(bot.stdout.readline())
            before = state()
            transcript_before = Path("bot/api.jsonl").read_text()
            if show is not None:
                client["initial"] = show(
                    {
                        "endpoint": bridge.base_url,
                        "capability": capability,
                        "world_id": world_id,
                        "user_id": 1,
                    }
                )
            after = state()
            transcript_after = Path("bot/api.jsonl").read_text()
            if after != before or transcript_after != transcript_before:
                raise RuntimeError("Client-only rich effects changed World or bot API state")
            stdout, stderr = bot.communicate(input="finish\n", timeout=15)
            if bot.returncode != 0 or stderr:
                raise RuntimeError("Rich-effect bot failed; inspect retained API evidence")
            finished = json.loads(stdout)
    final = state()
    result = {
        "mode": "simulation" if show is None else "native-input",
        "world_id": world_id,
        "initial": initial,
        "finished": finished,
        "before": before,
        "after": after,
        "final": final,
        "client": client,
        "api": [json.loads(line) for line in Path("bot/api.jsonl").read_text().splitlines()],
    }
    evidence = json.dumps(result)
    if token in evidence or capability in evidence:
        raise RuntimeError("Rich-effect evidence contains a capability")
    Path("effect-round-trip.json").write_text(evidence)
    return result


if __name__ == "__main__":
    print(json.dumps(run()))
