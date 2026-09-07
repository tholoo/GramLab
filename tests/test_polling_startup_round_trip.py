"""A real isolated bot resets pending delivery and handles only the next arrival."""

import json
import os
import shutil
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Any

from gramlab.runtime import RuntimeProfile, Sandbox


def test_real_bot_discards_old_delivery_then_handles_new_message(tmp_path: Path) -> None:
    profile = RuntimeProfile.load(Path(os.environ["GRAMLAB_RUNTIME_PROFILE"]))
    shutil.copytree(
        "src/gramlab", tmp_path / "gramlab", ignore=shutil.ignore_patterns("__pycache__")
    )
    (tmp_path / "component-profile.json").write_text(json.dumps(asdict(profile)))
    for name in ("component_bot.py", "polling_startup_round_trip.py"):
        shutil.copy2(Path("tests/probes") / name, tmp_path / name)
    shutil.copy2("tests/fixtures/polling_startup_bot.py", tmp_path / "polling_startup_bot.py")
    result = Sandbox(profile).supervise(
        [profile.python, "/work/polling_startup_round_trip.py"], data=tmp_path, timeout=30
    )
    (tmp_path / "startup-result.json").write_text(result.stdout)
    (tmp_path / "startup-stderr.log").write_text(result.stderr)
    assert result.returncode == 0, result.stderr
    observed = json.loads(result.stdout)
    user = {"id": 1, "is_bot": False, "first_name": "Sara", "language_code": "fa"}
    bot = {"id": 2, "is_bot": True, "first_name": "Echo", "username": "gramlab_echo_bot"}
    chat = {"id": 1, "type": "private", "user_id": 1, "bot_id": 2}
    old = {
        "id": 1,
        "chat_id": 1,
        "sender_id": 1,
        "date": 1700000000,
        "text": "old pending command",
    }
    fresh = old | {"id": 2, "text": "سلام 😀"}
    reply = old | {"id": 3, "sender_id": 2, "text": "Ready: سلام 😀"}
    world_id = observed["snapshot"]["world_id"]
    assert str(uuid.UUID(world_id)) == world_id
    before = {
        "schema": 2,
        "world_id": world_id,
        "user_id": 1,
        "cursor": 4,
        "now": 1700000000,
        "users": [user, bot],
        "chats": [chat],
        "messages": [old],
        "message_position": 1,
        "sends": [],
    }
    api_message = {
        "message_id": 2,
        "from": user,
        "chat": {"id": 1, "type": "private", "first_name": "Sara"},
        "date": 1700000000,
        "text": "سلام 😀",
    }

    def entry(method: str, parameters: dict[str, Any], response: Any) -> dict[str, Any]:
        return {
            "method": method,
            "parameters": parameters,
            "status": 200,
            "response": {"ok": True, "result": response},
        }

    startup = [
        entry("getMe", {}, bot),
        entry("deleteWebhook", {"drop_pending_updates": "true"}, True),
        entry("getUpdates", {"timeout": 0}, []),
    ]
    transcript = [
        *startup,
        entry(
            "getUpdates",
            {"timeout": 0, "allowed_updates": ["message", "callback_query"]},
            [{"update_id": 2, "message": api_message}],
        ),
        entry(
            "sendMessage",
            {"chat_id": 1, "text": "Ready: سلام 😀"},
            api_message | {"message_id": 3, "from": bot, "text": "Ready: سلام 😀"},
        ),
        entry("getUpdates", {"offset": 3}, []),
    ]
    assert observed == {
        "startup": {"phase": "ready", "transcript": startup},
        "completed": {"phase": "complete", "transcript": transcript},
        "before": before,
        "after_reset": before,
        "pending_after_reset": [],
        "history": [old, fresh, reply],
        "pending": [],
        "events": [
            {"sequence": 1, "type": "user.created", "data": user},
            {"sequence": 2, "type": "user.created", "data": bot},
            {"sequence": 3, "type": "chat.created", "data": chat},
            {"sequence": 4, "type": "message.created", "data": old},
            {"sequence": 5, "type": "message.created", "data": fresh},
            {"sequence": 6, "type": "message.created", "data": reply},
        ],
        "snapshot": before | {"cursor": 6, "messages": [old, fresh, reply], "message_position": 3},
    }
