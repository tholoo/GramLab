"""Shared simulation/Android scenario for a real bot's structured rich-message send and edit."""

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
    show: Callable[[dict[str, Any]], str] | None = None,
    observe: Callable[[], dict[str, Any]] | None = None,
    *,
    bot_fixture: str = "rich_bot.py",
    request_text: str = "Show rich blocks",
) -> dict[str, Any]:
    directory = Path("world")
    with World.create(directory, seed=7, now=1700000000) as world:
        world.create_user(first_name="Sara", language_code="fa")
        world.create_user(first_name="Echo", username="gramlab_echo_bot", is_bot=True)
        world.open_private_chat(user_id=1, bot_id=2)
        world.send_message(chat_id=1, sender_id=1, text=request_text)
        token = world.issue_bot_token(2)
        capability = world.issue_client_token(1)
        world_id = world.world_id
    client: dict[str, Any] = {}
    with BotAPIServer(directory) as server, ClientBridge(directory) as bridge:
        with FixtureBot(bot_fixture).start(
            {
                "GRAMLAB_BOT_API": server.base_url,
                "GRAMLAB_BOT_TOKEN": token,
                "GRAMLAB_RICH_SCENE": Path("rich-scene.json").read_text(),
            }
        ) as bot:
            assert bot.stdout is not None
            with selectors.DefaultSelector() as ready:
                ready.register(bot.stdout, selectors.EVENT_READ)
                if not ready.select(timeout=10):
                    raise RuntimeError("Bot did not send the initial rich message")
            line = bot.stdout.readline()
            if not line:
                _, stderr = bot.communicate(timeout=10)
                if token in stderr:
                    raise RuntimeError("Bot failure contained a capability")
                raise RuntimeError(f"Rich bot exited before sending: {stderr}")
            initial = json.loads(line)
            if show is not None:
                client["initial"] = show(
                    {
                        "endpoint": bridge.base_url,
                        "capability": capability,
                        "world_id": world_id,
                        "user_id": 1,
                    }
                )
            with World.open(directory) as world:
                world.advance_time(5)
            stdout, stderr = bot.communicate(input="edit\n", timeout=10)
            assert bot.returncode == 0, stderr
            edited = json.loads(stdout)
            assert token not in stdout + stderr
        if observe is not None:
            client.update(observe())
    with World.open(directory) as world:
        return {
            "initial": initial,
            "edited": edited,
            "client": client,
            "history": world.history(1),
            "pending": world.poll_updates(2),
        }


if __name__ == "__main__":
    print(json.dumps(run()))
