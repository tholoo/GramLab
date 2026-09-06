"""Explicit formatting entities at the public Bot API and durable world boundaries."""

import json
import os
import shutil
from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from test_bot_api import request

from gramlab.bot_api import BotAPIServer
from gramlab.runtime import RuntimeProfile, Sandbox
from gramlab.world import World


def test_nested_utf16_entities_survive_http_history_and_the_client_snapshot(tmp_path: Path) -> None:
    directory = tmp_path / "world"
    text = "😀 سلام bold code"
    entities = [
        {"type": "bold", "offset": 3, "length": 9},
        {"type": "italic", "offset": 8, "length": 4},
        {"type": "code", "offset": 13, "length": 4},
    ]
    with World.create(directory, seed=7, now=100) as world:
        world.create_user(first_name="Alice")
        world.create_user(first_name="Echo", is_bot=True)
        world.open_private_chat(user_id=1, bot_id=2)
        token = world.issue_bot_token(2)
    with BotAPIServer(directory) as server:
        assert request(
            server,
            token,
            "sendMessage",
            {
                "chat_id": 1,
                "text": text,
                "entities": list(reversed(entities)),
            },
        ) == (
            200,
            {
                "ok": True,
                "result": {
                    "message_id": 1,
                    "from": {"id": 2, "is_bot": True, "first_name": "Echo"},
                    "chat": {"id": 1, "type": "private", "first_name": "Alice"},
                    "date": 100,
                    "text": text,
                    "entities": entities,
                },
            },
        )
    expected = {
        "id": 1,
        "chat_id": 1,
        "sender_id": 2,
        "date": 100,
        "text": text,
        "entities": entities,
    }
    with World.open(directory) as world:
        assert world.history(1) == [expected]
        assert world.client_snapshot(1)["messages"] == [expected]
        assert world.events(after=3) == [
            {"sequence": 4, "type": "message.created", "data": expected}
        ]


@pytest.mark.parametrize(
    "kind",
    [
        "bold",
        "italic",
        "underline",
        "strikethrough",
        "spoiler",
        "code",
        "pre",
        "blockquote",
        "expandable_blockquote",
    ],
)
def test_formatting_types_reach_the_bot_update_queue(tmp_path: Path, kind: str) -> None:
    directory = tmp_path / "world"
    entity = {"type": kind, "offset": 0, "length": 9}
    if kind == "pre":
        entity["language"] = "python"
    with World.create(directory, seed=7, now=100) as world:
        world.create_user(first_name="Alice")
        world.create_user(first_name="Echo", is_bot=True)
        world.open_private_chat(user_id=1, bot_id=2)
        token = world.issue_bot_token(2)
        world.send_message(chat_id=1, sender_id=1, text="سلام code", entities=[entity])
    with BotAPIServer(directory) as server:
        assert request(server, token, "getUpdates") == (
            200,
            {
                "ok": True,
                "result": [
                    {
                        "update_id": 1,
                        "message": {
                            "message_id": 1,
                            "from": {"id": 1, "is_bot": False, "first_name": "Alice"},
                            "chat": {"id": 1, "type": "private", "first_name": "Alice"},
                            "date": 100,
                            "text": "سلام code",
                            "entities": [entity],
                        },
                    }
                ],
            },
        )


def test_invalid_entities_cannot_change_state_or_consume_message_ids(tmp_path: Path) -> None:
    directory = tmp_path / "world"
    with World.create(directory, seed=7, now=100) as world:
        world.create_user(first_name="Alice")
        world.create_user(first_name="Echo", is_bot=True)
        world.open_private_chat(user_id=1, bot_id=2)
        token = world.issue_bot_token(2)
        before = world.events()
    invalid = [
        {},
        "bold",
        [None],
        [{}],
        [{"type": "bold", "offset": 0}],
        *[
            [{"type": "bold", "offset": offset, "length": length}]
            for offset, length in [
                (1, 1),
                (0, 1),
                (-1, 2),
                (8, 1),
                (0, 0),
                (0, -1),
                (True, 2),
                (0, True),
                ("0", 2),
                (0, 2.0),
            ]
        ],
        [{"type": "custom_emoji", "offset": 0, "length": 2}],
        [{"type": "bold", "offset": 0, "length": 2, "url": "https://example.com"}],
        [{"type": "pre", "offset": 0, "length": 2, "language": None}],
        [{"type": "pre", "offset": 0, "length": 2, "language": "\ud800"}],
        [{"type": "bold", "offset": 2, "length": 4}, {"type": "italic", "offset": 4, "length": 4}],
        [{"type": "pre", "offset": 2, "length": 4}, {"type": "italic", "offset": 3, "length": 2}],
        [{"type": "bold", "offset": 2, "length": 4}, {"type": "code", "offset": 3, "length": 2}],
        [
            {"type": "blockquote", "offset": 0, "length": 8},
            {"type": "bold", "offset": 2, "length": 6},
            {"type": "expandable_blockquote", "offset": 3, "length": 2},
        ],
    ]
    with BotAPIServer(directory) as server:
        for entities in invalid:
            status, body = request(
                server,
                token,
                "sendMessage",
                {"chat_id": 1, "text": "😀abcdef", "entities": entities},
            )
            assert status == 400, entities
            assert body["ok"] is False
        with World.open(directory) as world:
            assert world.history(1) == []
            assert world.events() == before
        status, body = request(
            server,
            token,
            "sendMessage",
            {
                "chat_id": 1,
                "text": "😀abcdef",
                "entities": [
                    {"type": "blockquote", "offset": 0, "length": 8},
                    {"type": "bold", "offset": 2, "length": 6},
                ],
            },
        )
        assert status == 200
        assert body["result"]["message_id"] == 1


def test_formatting_only_edits_are_atomic_and_omission_removes_entities(tmp_path: Path) -> None:
    directory = tmp_path / "world"
    entity = {"type": "italic", "offset": 2, "length": 3}
    with World.create(directory, seed=7, now=100) as world:
        world.create_user(first_name="Alice")
        world.create_user(first_name="Echo", is_bot=True)
        world.open_private_chat(user_id=1, bot_id=2)
        token = world.issue_bot_token(2)
        world.send_message(
            chat_id=1,
            sender_id=2,
            text="😀abc",
            entities=[{"type": "bold", "offset": 2, "length": 3}],
        )
        world.advance_time(5)
    parameters = {"chat_id": 1, "message_id": 1, "text": "😀abc", "entities": [entity]}
    expected = {
        "message_id": 1,
        "from": {"id": 2, "is_bot": True, "first_name": "Echo"},
        "chat": {"id": 1, "type": "private", "first_name": "Alice"},
        "date": 100,
        "edit_date": 105,
        "text": "😀abc",
        "entities": [entity],
    }
    with BotAPIServer(directory) as server:
        assert request(server, token, "editMessageText", parameters) == (
            200,
            {"ok": True, "result": expected},
        )
        with World.open(directory) as world:
            events = world.events()
            persisted = world.history(1)
            assert world.client_events(1, after=5)["events"] == [
                {"sequence": 6, "type": "message.edited", "data": persisted[0]}
            ]
        assert request(
            server, token, "editMessageText", parameters | {"entities": [entity, entity]}
        ) == (
            400,
            {"ok": False, "error_code": 400, "description": "MESSAGE_NOT_MODIFIED"},
        )
        assert (
            request(
                server,
                token,
                "editMessageText",
                parameters | {"entities": [{"type": "bold", "offset": 1, "length": 1}]},
            )[0]
            == 400
        )
        with World.open(directory) as world:
            assert world.history(1) == persisted
            assert world.events() == events
        del parameters["entities"]
        del expected["entities"]
        assert request(server, token, "editMessageText", parameters) == (
            200,
            {"ok": True, "result": expected},
        )
    with World.open(directory) as world:
        assert world.history(1) == [
            {"id": 1, "chat_id": 1, "sender_id": 2, "date": 100, "edit_date": 105, "text": "😀abc"}
        ]
        assert world.poll_updates(2) == []


@given(
    prefix=st.text(alphabet=["😀", "a", "س", "\u200c", "\u0301", "👩", "\u200d"], max_size=12),
    body=st.text(
        alphabet=["😀", "a", "س", "\u200c", "\u0301", "👩", "\u200d"], min_size=1, max_size=12
    ),
)
@settings(max_examples=40, deadline=None)
def test_valid_utf16_substrings_remain_valid_across_mixed_unicode(prefix: str, body: str) -> None:
    entity = {
        "type": "bold",
        "offset": len(prefix.encode("utf-16-le")) // 2,
        "length": len(body.encode("utf-16-le")) // 2,
    }
    with TemporaryDirectory() as temporary:
        with World.create(Path(temporary) / "world", seed=7, now=100) as world:
            world.create_user(first_name="Alice")
            world.create_user(first_name="Echo", is_bot=True)
            world.open_private_chat(user_id=1, bot_id=2)
            expected = {
                "id": 1,
                "chat_id": 1,
                "sender_id": 1,
                "date": 100,
                "text": prefix + body,
                "entities": [entity],
            }
            assert (
                world.send_message(chat_id=1, sender_id=1, text=prefix + body, entities=[entity])
                == expected
            )
            assert world.poll_updates(2) == [{"update_id": 1, "message": expected}]


def assert_formatted_result(observed, scene) -> None:
    semantic = dict(observed)
    del semantic["client"]
    plain = {
        "message_id": 2,
        "from": {"id": 2, "is_bot": True, "first_name": "Echo", "username": "gramlab_echo_bot"},
        "chat": {"id": 1, "type": "private", "first_name": "Sara"},
        "date": 1700000000,
        "text": scene["text"],
    }
    assert semantic == {
        "plain": plain,
        "formatted": plain | {"edit_date": 1700000005, "entities": scene["entities"]},
        "history": [
            {"id": 1, "chat_id": 1, "sender_id": 1, "date": 1700000000, "text": "Show formatting"},
            {
                "id": 2,
                "chat_id": 1,
                "sender_id": 2,
                "date": 1700000000,
                "edit_date": 1700000005,
                **scene,
            },
        ],
        "pending": [],
    }


def test_real_bot_edits_only_formatting_in_the_shared_scenario(tmp_path: Path) -> None:
    profile = RuntimeProfile.load(Path(os.environ["GRAMLAB_RUNTIME_PROFILE"]))
    shutil.copytree(
        "src/gramlab", tmp_path / "gramlab", ignore=shutil.ignore_patterns("__pycache__")
    )
    (tmp_path / "component-profile.json").write_text(json.dumps(asdict(profile)))
    for name in ("component_bot.py", "formatted_round_trip.py"):
        shutil.copy2(Path("tests/probes") / name, tmp_path / name)
    for name in ("formatted_bot.py", "formatting.json"):
        shutil.copy2(Path("tests/fixtures") / name, tmp_path / name)
    result = Sandbox(profile).supervise(
        [profile.python, "/work/formatted_round_trip.py"], data=tmp_path, timeout=30
    )
    assert result.returncode == 0, result.stderr
    (tmp_path / "formatting-result.json").write_text(result.stdout)
    assert_formatted_result(
        json.loads(result.stdout), json.loads(Path("tests/fixtures/formatting.json").read_text())
    )
