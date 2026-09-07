"""Trusted startup/arrival orchestration inside the existing offline runtime."""

import json
import selectors
from pathlib import Path

from component_bot import FixtureBot

from gramlab.bot_api import BotAPIServer
from gramlab.world import World

directory = Path("world")
with World.create(directory, seed=11, now=1700000000) as world:
    world.create_user(first_name="Sara", language_code="fa")
    world.create_user(first_name="Echo", username="gramlab_echo_bot", is_bot=True)
    world.open_private_chat(user_id=1, bot_id=2)
    token = world.issue_bot_token(2)
    world.send_message(chat_id=1, sender_id=1, text="old pending command")
    before = world.client_snapshot(1, version=2)

with BotAPIServer(directory) as server:
    with FixtureBot("polling_startup_bot.py").start(
        {"GRAMLAB_BOT_API": server.base_url, "GRAMLAB_BOT_TOKEN": token}
    ) as bot:
        assert bot.stdout is not None
        with selectors.DefaultSelector() as ready:
            ready.register(bot.stdout, selectors.EVENT_READ)
            if not ready.select(timeout=10):
                raise RuntimeError("Bot did not complete polling startup")
        line = bot.stdout.readline()
        if not line:
            _, stderr = bot.communicate(timeout=10)
            if token in stderr:
                raise RuntimeError("Bot failure contained a capability")
            raise RuntimeError(f"Bot exited before polling startup: {stderr}")
        startup = json.loads(line)
        with World.open(directory) as world:
            after_reset = world.client_snapshot(1, version=2)
            pending_after_reset = world.poll_updates(2)
            world.send_message(chat_id=1, sender_id=1, text="سلام 😀")
        stdout, stderr = bot.communicate(input="continue\n", timeout=10)
        assert token not in line + stdout + stderr
        assert bot.returncode == 0, stderr
        completed = json.loads(stdout)

with World.open(directory) as world:
    print(
        json.dumps(
            {
                "startup": startup,
                "completed": completed,
                "before": before,
                "after_reset": after_reset,
                "pending_after_reset": pending_after_reset,
                "history": world.history(1),
                "pending": world.poll_updates(2),
                "events": world.events(),
                "snapshot": world.client_snapshot(1, version=2),
            }
        )
    )
