"""Complete independent semantic and API expectations for a contained mention bot."""

import hashlib
import json
import os
import shutil
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Any

from gramlab.runtime import RuntimeProfile, Sandbox

USER = {"id": 1, "is_bot": False, "first_name": "Sara", "language_code": "fa"}
BOT = {"id": 2, "is_bot": True, "first_name": "Echo", "username": "gramlab_echo_bot"}
A = {
    "id": 3,
    "is_bot": False,
    "first_name": "Arman",
    "username": "arman_local",
    "language_code": "fa",
}
B = {
    "id": 4,
    "is_bot": False,
    "first_name": "Mina",
    "username": "mina_local",
    "language_code": "en",
}
CHAT = {"id": 1, "type": "private", "user_id": 1, "bot_id": 2}
REQUEST = {
    "id": 1,
    "chat_id": 1,
    "sender_id": 1,
    "date": 1700000000,
    "text": "Show explicit mentions",
}
KEYBOARDS = {
    "initial": {
        "inline_keyboard": [[{"text": "Mention B / نفر بعد", "callback_data": "mention:b"}]]
    },
    "edited": {
        "inline_keyboard": [
            [{"text": "Remove mention / حذف نام", "callback_data": "mention:remove"}]
        ]
    },
}
NOOP = {
    "status": 400,
    "body": {"ok": False, "error_code": 400, "description": "MESSAGE_NOT_MODIFIED"},
}
ANSWER = {"text": "Changed / تغییر کرد", "show_alert": False, "cache_time": 0}


def rich_content(phase: str, *, public: bool = False) -> dict[str, Any]:
    """Independent oracle literals; the bot does not import this test module."""
    if phase == "initial":
        identity = {"user": A} if public else {"user_id": 3}
        return {
            "is_rtl": True,
            "blocks": [
                {"type": "heading", "size": 2, "text": "Explicit mention A"},
                {
                    "type": "paragraph",
                    "text": [
                        "Winner: ",
                        {
                            "type": "text_mention",
                            "text": ["آرمان ", {"type": "bold", "text": "Arman"}],
                            **identity,
                        },
                        " / ",
                        {"type": "italic", "text": "سلام hello"},
                    ],
                },
            ],
        }
    if phase == "edited":
        identity = {"user": B} if public else {"user_id": 4}
        return {
            "is_rtl": True,
            "blocks": [
                {"type": "heading", "size": 2, "text": "Explicit mention B"},
                {
                    "type": "paragraph",
                    "text": [
                        "Next: ",
                        {
                            "type": "text_mention",
                            "text": {"type": "underline", "text": ["مینا ", "Mina"]},
                            **identity,
                        },
                        {"type": "text_mention", "text": "", **identity},
                    ],
                },
            ],
        }
    assert phase in ("removed", "restarted")
    return {
        "blocks": [
            {"type": "heading", "size": 2, "text": "Mentions removed"},
            {"type": "paragraph", "text": "No named user / اشاره حذف شد"},
        ]
    }


def message(phase: str, *, public: bool = False) -> dict[str, Any]:
    result: dict[str, Any] = (
        {
            "message_id": 2,
            "from": BOT,
            "chat": {"id": 1, "type": "private", "first_name": "Sara"},
            "date": 1700000000,
        }
        if public
        else {"id": 2, "chat_id": 1, "sender_id": 2, "date": 1700000000, "text": ""}
    )
    result["rich_message"] = rich_content(phase, public=public)
    if phase in KEYBOARDS:
        result["reply_markup"] = KEYBOARDS[phase]
    if phase != "initial":
        result["edit_date"] = 1700000005 if phase == "edited" else 1700000010
    return result


def snapshot(world_id: str, phase: str) -> dict[str, Any]:
    revision = {"initial": 9, "edited": 13, "removed": 17, "restarted": 17}[phase]
    return {
        "schema": 3,
        "world_id": world_id,
        "user_id": 1,
        "cursor": revision,
        "now": 1700000000
        if phase == "initial"
        else 1700000005
        if phase == "edited"
        else 1700000010,
        "users": [USER, BOT, A]
        if phase == "initial"
        else [USER, BOT, B]
        if phase == "edited"
        else [USER, BOT],
        "chats": [CHAT],
        "messages": [REQUEST, message(phase)],
        "message_position": 2 if phase == "initial" else 3 if phase == "edited" else 4,
        "sends": [],
        "assets": [],
        "message_revisions": [
            {"chat_id": 1, "message_id": 1, "revision": 8},
            {"chat_id": 1, "message_id": 2, "revision": revision},
        ],
    }


def stage_scenario(directory: Path, core: RuntimeProfile) -> None:
    shutil.copytree(
        "src/gramlab", directory / "gramlab", ignore=shutil.ignore_patterns("__pycache__")
    )
    (directory / "component-profile.json").write_text(json.dumps(asdict(core)))
    shutil.copy2("tests/fixtures/rich_mentions_bot.py", directory / "rich_mentions_bot.py")
    for name in ("component_bot.py", "rich_mentions_round_trip.py"):
        shutil.copy2(Path("tests/probes") / name, directory / name)


def assert_scenario(observed: dict[str, Any]) -> None:
    world_id = observed["world_id"]
    assert str(uuid.UUID(world_id)) == world_id
    ids = {
        phase: observed["callbacks"][phase + "_created"]["callback"]["id"]
        for phase in ("edited", "removed")
    }
    assert len(set(ids.values())) == 2
    assert all(str(uuid.UUID(value)) == value for value in ids.values())
    chat_instance = hashlib.sha256(f"{world_id}:1".encode()).hexdigest()
    request_api = {
        "message_id": 1,
        "from": USER,
        "chat": {"id": 1, "type": "private", "first_name": "Sara"},
        "date": 1700000000,
        "text": "Show explicit mentions",
    }
    initial_update = {"update_id": 1, "message": request_api}
    updates: dict[str, Any] = {}
    callbacks: dict[str, Any] = {}
    receipts: dict[str, Any] = {}
    for phase, previous, data, update_id, revision, users in (
        ("edited", "initial", "mention:b", 2, 9, [USER, BOT, A]),
        ("removed", "edited", "mention:remove", 3, 13, [USER, BOT, B]),
    ):
        callbacks[phase] = {
            "id": ids[phase],
            "user_id": 1,
            "chat_id": 1,
            "message": message(previous),
            "data": data,
            "chat_instance": chat_instance,
        }
        updates[phase] = {
            "update_id": update_id,
            "callback_query": {
                "id": ids[phase],
                "from": USER,
                "message": message(previous, public=True),
                "chat_instance": chat_instance,
                "data": data,
            },
        }
        base = {
            "schema": 3,
            "world_id": world_id,
            "user_id": 1,
            "users": users,
            "assets": [],
            "message_revision": revision,
        }
        receipts[phase + "_created"] = base | {"callback": callbacks[phase] | {"answer": None}}
        for suffix in ("answered", "restarted"):
            receipts[phase + "_" + suffix] = base | {
                "callback": callbacks[phase] | {"answer": ANSWER}
            }
    bot: dict[str, Any] = {
        "initial": {
            "event": "initial",
            "message": message("initial", public=True),
            "noop": NOOP,
            "update": initial_update,
        }
    }
    for phase in ("edited", "removed"):
        bot[phase] = {
            "event": phase,
            "message": message(phase, public=True),
            "noop": NOOP,
            "update": updates[phase],
            "answer": True,
        }
    events = [
        {"sequence": 1, "type": "user.created", "data": USER},
        {"sequence": 2, "type": "user.created", "data": BOT},
        {"sequence": 3, "type": "user.created", "data": A},
        {"sequence": 4, "type": "user.created", "data": B},
        {"sequence": 5, "type": "chat.created", "data": CHAT},
        {"sequence": 6, "type": "chat.created", "data": CHAT | {"id": 2, "user_id": 3}},
        {"sequence": 7, "type": "chat.created", "data": CHAT | {"id": 3, "user_id": 4}},
        {"sequence": 8, "type": "message.created", "data": REQUEST},
        {"sequence": 9, "type": "message.created", "data": message("initial")},
        {"sequence": 10, "type": "clock.advanced", "data": {"now": 1700000005}},
        {"sequence": 11, "type": "callback.created", "data": callbacks["edited"]},
        {
            "sequence": 12,
            "type": "callback.answered",
            "data": {"id": ids["edited"], "user_id": 1, "answer": ANSWER},
        },
        {"sequence": 13, "type": "message.edited", "data": message("edited")},
        {"sequence": 14, "type": "clock.advanced", "data": {"now": 1700000010}},
        {"sequence": 15, "type": "callback.created", "data": callbacks["removed"]},
        {
            "sequence": 16,
            "type": "callback.answered",
            "data": {"id": ids["removed"], "user_id": 1, "answer": ANSWER},
        },
        {"sequence": 17, "type": "message.edited", "data": message("removed")},
    ]
    changes = [
        {"position": 1, "type": "message.created", "data": REQUEST, "revision": 8},
        {"position": 2, "type": "message.created", "data": message("initial"), "revision": 9},
        {"position": 3, "type": "message.edited", "data": message("edited"), "revision": 13},
        {"position": 4, "type": "message.edited", "data": message("removed"), "revision": 17},
    ]
    change_base = {
        "schema": 3,
        "world_id": world_id,
        "user_id": 1,
        "head": 4,
        "now": 1700000010,
        "assets": [],
    }
    change_responses = {
        "all": change_base | {"cursor": 4, "changes": changes, "users": [USER, BOT, A, B]}
    }
    for name, index, users in (
        ("old_a", 1, [USER, BOT, A]),
        ("old_b", 2, [USER, BOT, B]),
        ("removed", 3, [USER, BOT]),
    ):
        change_responses[name] = change_base | {
            "cursor": index + 1,
            "changes": [changes[index]],
            "users": users,
        }
    api: list[dict[str, Any]] = []

    def success(method: str, value: Any, *, form: bool = False) -> None:
        api.append(
            {
                "method": method,
                "encoding": "form" if form else "json",
                "response": {"status": 200, "body": {"ok": True, "result": value}},
            }
        )

    success("getUpdates", [initial_update])
    success("sendRichMessage", message("initial", public=True))
    api.append({"method": "editMessageText", "encoding": "form", "response": NOOP})
    for phase in ("edited", "removed"):
        success("getUpdates", [updates[phase]])
        success("answerCallbackQuery", True)
        success("editMessageText", message(phase, public=True), form=phase == "edited")
        api.append({"method": "editMessageText", "encoding": "form", "response": NOOP})
        success("getUpdates", [])
    other = {}
    for user, chat_id in ((A, 2), (B, 3)):
        other[str(user["id"])] = {
            "schema": 3,
            "world_id": world_id,
            "user_id": user["id"],
            "cursor": 17,
            "now": 1700000010,
            "users": [BOT, user],
            "chats": [CHAT | {"id": chat_id, "user_id": user["id"]}],
            "messages": [],
            "message_position": 0,
            "sends": [],
            "assets": [],
            "message_revisions": [],
        }
    assert {key: value for key, value in observed.items() if key != "client"} == {
        "world_id": world_id,
        "bot": bot,
        "snapshots": {
            phase: snapshot(world_id, phase)
            for phase in ("initial", "edited", "removed", "restarted")
        },
        "callbacks": receipts,
        "changes": change_responses,
        "history": [REQUEST, message("removed")],
        "events": events,
        "pending": [],
        "other_personas": other,
        "api": api,
    }


def test_real_bot_mentions_disclose_edit_remove_and_preserve_frozen_callbacks(
    tmp_path: Path,
) -> None:
    profile = RuntimeProfile.load(Path(os.environ["GRAMLAB_RUNTIME_PROFILE"]))
    stage_scenario(tmp_path, profile)
    result = Sandbox(profile).supervise(
        [profile.python, "/work/rich_mentions_round_trip.py"], data=tmp_path, timeout=45
    )
    (tmp_path / "rich-mentions-result.json").write_text(result.stdout)
    (tmp_path / "rich-mentions-stderr.log").write_text(result.stderr)
    assert result.returncode == 0, result.stderr
    assert_scenario(json.loads(result.stdout))
