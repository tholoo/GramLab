"""Trusted orchestration executed wholly inside the isolated runtime."""

import json
import os
import subprocess
import sys
from pathlib import Path

from gramlab.bot_api import BotAPIServer
from gramlab.world import World

directory = Path("world")
with World.create(directory, seed=11, now=1700000000) as world:
    world.create_user(first_name="Sara", language_code="fa")
    world.create_user(first_name="Echo", username="gramlab_echo_bot", is_bot=True)
    world.open_private_chat(user_id=1, bot_id=2)
    token = world.issue_bot_token(2)
    world.send_message(chat_id=1, sender_id=1, text="سلام hello")
with BotAPIServer(directory) as server:
    bot = subprocess.run(
        [sys.executable, "echo_bot.py"],
        env={**os.environ, "GRAMLAB_BOT_API": server.base_url, "GRAMLAB_BOT_TOKEN": token},
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert bot.returncode == 0, bot.stderr
    assert token not in bot.stdout + bot.stderr
with World.open(directory) as world:
    print(
        json.dumps(
            {
                "bot": json.loads(bot.stdout),
                "history": world.history(1),
                "pending": world.poll_updates(2),
            }
        )
    )
