"""Independently authored complete rich-link semantics for a real HTTP bot."""

import json
import os
import shutil
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Any

from gramlab.runtime import RuntimeProfile, Sandbox

SCENE = json.loads(Path("tests/fixtures/rich-links-scene.json").read_text())
USER = {"id": 1, "is_bot": False, "first_name": "Sara", "language_code": "fa"}
BOT = {"id": 2, "is_bot": True, "first_name": "Echo", "username": "gramlab_echo_bot"}
CHAT = {"id": 1, "type": "private", "user_id": 1, "bot_id": 2}
REQUEST = {
    "id": 1,
    "chat_id": 1,
    "sender_id": 1,
    "date": 1700000000,
    "text": "Show linked content",
}


def stage_scenario(directory: Path, core: RuntimeProfile) -> None:
    shutil.copytree(
        "src/gramlab", directory / "gramlab", ignore=shutil.ignore_patterns("__pycache__")
    )
    (directory / "component-profile.json").write_text(json.dumps(asdict(core)))
    (directory / "rich-scene.json").write_text(json.dumps(SCENE))
    shutil.copy2("tests/fixtures/rich_bot.py", directory / "rich_bot.py")
    for name in ("component_bot.py", "rich_round_trip.py", "rich_links_round_trip.py"):
        shutil.copy2(Path("tests/probes") / name, directory / name)


def assert_scenario(observed: dict[str, Any]) -> None:
    first = {
        "id": 2,
        "chat_id": 1,
        "sender_id": 2,
        "date": 1700000000,
        "text": "",
        "rich_message": SCENE["initial"],
    }
    edited = first | {"rich_message": SCENE["edited"], "edit_date": 1700000005}
    api = {
        "message_id": 2,
        "from": BOT,
        "chat": {"id": 1, "type": "private", "first_name": "Sara"},
        "date": 1700000000,
    }
    world_id = observed["snapshot"]["world_id"]
    assert str(uuid.UUID(world_id)) == world_id
    assert {key: value for key, value in observed.items() if key != "client"} == {
        "initial": api | {"rich_message": SCENE["initial"]},
        "edited": api | {"edit_date": 1700000005, "rich_message": SCENE["edited"]},
        "history": [REQUEST, edited],
        "pending": [],
        "events": [
            {"sequence": 1, "type": "user.created", "data": USER},
            {"sequence": 2, "type": "user.created", "data": BOT},
            {"sequence": 3, "type": "chat.created", "data": CHAT},
            {"sequence": 4, "type": "message.created", "data": REQUEST},
            {"sequence": 5, "type": "message.created", "data": first},
            {"sequence": 6, "type": "clock.advanced", "data": {"now": 1700000005}},
            {"sequence": 7, "type": "message.edited", "data": edited},
        ],
        "snapshot": {
            "schema": 2,
            "world_id": world_id,
            "user_id": 1,
            "cursor": 7,
            "now": 1700000005,
            "users": [USER, BOT],
            "chats": [CHAT],
            "messages": [REQUEST, edited],
            "message_position": 3,
            "sends": [],
        },
    }


def test_real_bot_sends_and_edits_structured_links(tmp_path: Path) -> None:
    profile = RuntimeProfile.load(Path(os.environ["GRAMLAB_RUNTIME_PROFILE"]))
    stage_scenario(tmp_path, profile)
    result = Sandbox(profile).supervise(
        [profile.python, "/work/rich_links_round_trip.py"], data=tmp_path, timeout=30
    )
    (tmp_path / "rich-links-result.json").write_text(result.stdout)
    (tmp_path / "rich-links-stderr.log").write_text(result.stderr)
    assert result.returncode == 0, result.stderr
    assert_scenario(json.loads(result.stdout))
