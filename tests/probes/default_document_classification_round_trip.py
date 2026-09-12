"""Trusted orchestration for the contained default-document classification bot."""

import hashlib
import json
from pathlib import Path
from typing import Any

from component_bot import FixtureBot

from gramlab.bot_api import BotAPIServer
from gramlab.world import World


def run() -> dict[str, Any]:
    directory = Path("world")
    ordinary = b"contained ordinary text document"
    specialized = b"GIF89a contained specialized document"
    with World.create(directory, seed=110, now=1_700_000_000) as world:
        user = world.create_user(first_name="Sara")
        bot = world.create_user(first_name="Files", username="gramlab_files_bot", is_bot=True)
        world.open_private_chat(user_id=user["id"], bot_id=bot["id"])
        token = world.issue_bot_token(bot["id"])

    fixture = FixtureBot("default_document_classification_bot.py")
    (fixture.data / "ordinary.txt").write_bytes(ordinary)
    (fixture.data / "specialized.gif").write_bytes(specialized)
    with BotAPIServer(directory) as server:
        process = fixture.run(
            {"GRAMLAB_BOT_API": server.base_url, "GRAMLAB_BOT_TOKEN": token}, timeout=20
        )
    if process.returncode != 0:
        raise RuntimeError(f"Default-document bot failed: {process.stderr}")
    observed = dict(json.loads(process.stdout))
    with World.open(directory) as world:
        descriptor, stored = world.granted_document(user["id"], "1")
        return {
            "bot": observed,
            "history": world.history(1),
            "events": world.events(),
            "descriptor": descriptor,
            "stored_sha256": hashlib.sha256(stored).hexdigest(),
            "ordinary_sha256": hashlib.sha256(ordinary).hexdigest(),
        }


print(json.dumps(run(), ensure_ascii=True), flush=True)
