"""One bot/world history for simulation-only and offline Android cache recovery."""

import json
import selectors
from collections.abc import Callable
from pathlib import Path
from typing import Any

from component_bot import FixtureBot

from gramlab.bot_api import BotAPIServer
from gramlab.client_bridge import ClientBridge
from gramlab.world import World


def run(
    suspend: Callable[[dict[str, Any]], str] | None = None,
    recover: Callable[[], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    directory = Path("world")
    with World.create(directory, seed=7, now=1700000000) as world:
        world.create_user(first_name="Sara", language_code="fa")
        world.create_user(first_name="Echo", username="gramlab_echo_bot", is_bot=True)
        world.open_private_chat(user_id=1, bot_id=2)
        world.send_message(chat_id=1, sender_id=1, text="Check recovery")
        token = world.issue_bot_token(2)
        configuration = {
            "capability": world.issue_client_token(1),
            "world_id": world.world_id,
            "user_id": 1,
        }
    client: dict[str, Any] = {}
    with BotAPIServer(directory) as server, ClientBridge(directory) as bridge:
        with FixtureBot("recovery_bot.py").start(
            {"GRAMLAB_BOT_API": server.base_url, "GRAMLAB_BOT_TOKEN": token}
        ) as bot:
            assert bot.stdout is not None
            with selectors.DefaultSelector() as ready:
                ready.register(bot.stdout, selectors.EVENT_READ)
                if not ready.select(timeout=10):
                    raise RuntimeError("Bot did not send its original replies")
            before = json.loads(bot.stdout.readline())
            if suspend is not None:
                client["before"] = suspend(configuration | {"endpoint": bridge.base_url})
            with World.open(directory) as world:
                world.advance_time(5)
            stdout, stderr = bot.communicate(input="edit\n", timeout=10)
            assert bot.returncode == 0, stderr
            assert token not in stdout + stderr
            after = json.loads(stdout)
        # Retain the real HTTP exchange even if Android recovery later fails.
        Path("bot-exchange.json").write_text(json.dumps({"before": before, "after": after}))
        if recover is not None:
            client.update(recover())
    with World.open(directory) as world:
        return {
            "before": before,
            "after": after,
            "client": client,
            "history": world.history(1),
            "pending": world.poll_updates(2),
        }


if __name__ == "__main__":
    print(json.dumps(run()))
