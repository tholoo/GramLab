"""One real bot scenario supplies simulation and native rich-message evidence."""

import json
import os
import shutil
from dataclasses import asdict
from pathlib import Path
from typing import Any

from gramlab.runtime import RuntimeProfile, Sandbox
from gramlab.world import World


def test_native_catalog_is_canonical_through_real_world(tmp_path: Path) -> None:
    """Catch stale native catalog expectations before paying for a guest boot."""
    catalog = json.loads(Path("clients/android/fixtures/rich-message.json").read_text())
    with World.create(tmp_path / "catalog-world", seed=17, now=1700000000) as world:
        world.create_user(first_name="Sara", language_code="fa")
        world.create_user(first_name="Echo", username="gramlab_echo_bot", is_bot=True)
        world.open_private_chat(user_id=1, bot_id=2)
        message = world.send_rich_message(
            chat_id=1, sender_id=2, rich_message=catalog | {"skip_entity_detection": True}
        )
        expected = {
            "id": 1,
            "chat_id": 1,
            "sender_id": 2,
            "date": 1700000000,
            "text": "",
            "rich_message": catalog,
        }
        assert message == expected
        assert world.history(1) == [expected]
        assert world.client_snapshot(1, version=2)["messages"] == [expected]


def stage_rich_scenario(directory: Path, core: RuntimeProfile) -> None:
    shutil.copytree(
        "src/gramlab", directory / "gramlab", ignore=shutil.ignore_patterns("__pycache__")
    )
    (directory / "component-profile.json").write_text(json.dumps(asdict(core)))
    for name in ("component_bot.py", "rich_round_trip.py"):
        shutil.copy2(Path("tests/probes") / name, directory / name)
    for name in ("rich_bot.py", "rich-scene.json"):
        shutil.copy2(Path("tests/fixtures") / name, directory / name)


def assert_rich_scenario(observed: dict[str, Any]) -> None:
    scene = json.loads(Path("tests/fixtures/rich-scene.json").read_text())
    initial = {
        "message_id": 2,
        "from": {"id": 2, "is_bot": True, "first_name": "Echo", "username": "gramlab_echo_bot"},
        "chat": {"id": 1, "type": "private", "first_name": "Sara"},
        "date": 1700000000,
        "rich_message": scene["initial"],
    }
    assert {key: value for key, value in observed.items() if key != "client"} == {
        "initial": initial,
        "edited": initial | {"edit_date": 1700000005, "rich_message": scene["edited"]},
        "history": [
            {"id": 1, "chat_id": 1, "sender_id": 1, "date": 1700000000, "text": "Show rich blocks"},
            {
                "id": 2,
                "chat_id": 1,
                "sender_id": 2,
                "date": 1700000000,
                "edit_date": 1700000005,
                "text": "",
                "rich_message": scene["edited"],
            },
        ],
        "pending": [],
    }


def test_real_bot_sends_and_edits_structured_rich_content(tmp_path: Path) -> None:
    profile = RuntimeProfile.load(Path(os.environ["GRAMLAB_RUNTIME_PROFILE"]))
    stage_rich_scenario(tmp_path, profile)
    result = Sandbox(profile).supervise(
        [profile.python, "/work/rich_round_trip.py"], data=tmp_path, timeout=30
    )
    (tmp_path / "rich-result.json").write_text(result.stdout)
    assert result.returncode == 0, result.stderr
    assert_rich_scenario(json.loads(result.stdout))
