"""A contained real bot begins polling before the virtual user supplies its message."""

import json
import time
from pathlib import Path

from component_bot import FixtureBot

from gramlab.bot_api import BotAPIServer
from gramlab.world import World

directory = Path("world")
with World.create(directory, seed=7, now=100) as world:
    world.create_user(first_name="Alice")
    world.create_user(first_name="Echo", is_bot=True)
    world.open_private_chat(user_id=1, bot_id=2)
    world.send_message(chat_id=1, sender_id=1, text="readiness sentinel")
    token = world.issue_bot_token(2)
with BotAPIServer(directory) as server:
    with FixtureBot("echo_bot.py").start(
        {
            "GRAMLAB_BOT_API": server.base_url,
            "GRAMLAB_BOT_TOKEN": token,
            "GRAMLAB_BOT_OFFSET": "2",
        }
    ) as bot:
        deadline = time.monotonic() + 5
        while True:
            if bot.poll() is not None:
                raise RuntimeError("Bot exited before waiting for the virtual user")
            with World.open(directory) as world:
                if not world.poll_updates(2):
                    world.send_message(chat_id=1, sender_id=1, text="سلام after polling")
                    break
            if time.monotonic() >= deadline:
                raise RuntimeError("Bot did not acknowledge the readiness sentinel")
            time.sleep(0.01)
        stdout, stderr = bot.communicate(timeout=5)
        assert bot.returncode == 0, stderr
        assert token not in stdout + stderr
with World.open(directory) as world:
    print(
        json.dumps(
            {
                "bot": json.loads(stdout),
                "history": world.history(1),
                "pending": world.poll_updates(2),
            }
        )
    )
