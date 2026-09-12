"""Current message shapes remain usable through Android host interactions."""

from __future__ import annotations

import json
import os
import shutil
import time
from pathlib import Path
from typing import Any

import pytest

from gramlab._android import Android, _inline_fragments, _inline_matches
from gramlab.runner import run
from gramlab.runtime import RuntimeProfile
from gramlab.world import World

ASSETS = Path(__file__).parent / "assets"
KEYBOARD = {"inline_keyboard": [[{"text": "Inspect", "callback_data": "inspect"}]]}

SCENARIO = """import time
from pathlib import Path
from gramlab.scenario import Scenario

lab = Scenario.from_environment()
lab.register_custom_emoji(
    request_id="current-static",
    main=Path("emoji-static.webp").read_bytes(),
    thumbnail=Path("emoji-thumbnail.webp").read_bytes(),
    fallback="👩‍💻",
    custom_emoji_id="7",
)
user = lab.create_user(first_name="Sara")
chat = lab.open_private_chat(user_id=user["id"], bot_id=lab.bots()["current"])
lab.send_message(chat_id=chat["id"], sender_id=user["id"], text="publish current content")
publication_deadline = time.monotonic() + 30
while len(lab.history(chat["id"])) != 4:
    assert time.monotonic() < publication_deadline, "Current messages were not published"
    time.sleep(0.02)
lab.capture_chat(
    chat_id=chat["id"], label="current-messages",
    contains=["Current photo caption", "Current photo credit"],
)
lab.tap_inline_button(chat_id=chat["id"], message_id=2, row=0, column=0)
lab.type_message(chat_id=chat["id"], text="reply after current content")
completion_deadline = time.monotonic() + 30
while len(lab.history(chat["id"])) != 6 or not any(
    event["type"] == "callback.answered" for event in lab.events()
):
    assert time.monotonic() < completion_deadline, "Current interactions did not complete"
    time.sleep(0.02)
"""


def _android(version: int) -> Android:
    return Android(
        RuntimeProfile(bubblewrap="", python="", store_paths=()),
        deadline=time.monotonic() + 5,
        secrets=[],
        bridge_version=version,
    )


def test_plain_multiline_identity_does_not_match_another_messages_first_line() -> None:
    multiline = {"text": "Choose an option\nتأیید"}
    first_line_only = {"text": "Choose an option"}
    native_text = "Choose an option\nتأیید\nReceived at 10:13 PM\n"

    assert _inline_matches(multiline, native_text)
    assert not _inline_matches(first_line_only, native_text)


def _stage_versioned_message(world: World, kind: str) -> tuple[dict[str, Any], int]:
    user = world.create_user(first_name="Sara")
    bot = world.create_user(first_name="Bot", is_bot=True)
    chat = world.open_private_chat(user_id=user["id"], bot_id=bot["id"])
    if kind == "photo":
        world.send_photo(
            chat_id=chat["id"],
            sender_id=bot["id"],
            photo={"type": "photo", "media": "attach://photo"},
            uploads={"photo": (ASSETS / "rich-media/photo-square-16x16.png").read_bytes()},
        )
        return chat, 3
    if kind == "mention":
        mentioned = world.create_user(first_name="Mina")
        world.open_private_chat(user_id=mentioned["id"], bot_id=bot["id"])
        world.send_rich_message(
            chat_id=chat["id"],
            sender_id=bot["id"],
            rich_message={
                "skip_entity_detection": True,
                "blocks": [
                    {
                        "type": "paragraph",
                        "text": {
                            "type": "text_mention",
                            "text": "Mina",
                            "user": {"id": mentioned["id"]},
                        },
                    }
                ],
            },
        )
        return chat, 3
    descriptor = world.register_custom_emoji(
        request_id="static",
        main=(ASSETS / "custom-emoji/emoji-static.webp").read_bytes(),
        thumbnail=(ASSETS / "custom-emoji/emoji-thumbnail.webp").read_bytes(),
        fallback="👩‍💻",
        custom_emoji_id=7,
    )
    world.send_message(
        chat_id=chat["id"],
        sender_id=bot["id"],
        text="👩‍💻",
        entities=[
            {
                "type": "custom_emoji",
                "offset": 0,
                "length": 5,
                "custom_emoji_id": descriptor["custom_emoji_id"],
            }
        ],
    )
    return chat, 4


@pytest.mark.parametrize("kind", ["photo", "mention", "custom_emoji"])
def test_composer_uses_configured_snapshot_for_current_visible_messages(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    directory = tmp_path / "world"
    with World.create(directory, seed=7, now=100) as world:
        chat, version = _stage_versioned_message(world, kind)
        before = world.client_snapshot(chat["user_id"], version=version)
        with pytest.raises(ValueError, match=f"v{version}"):
            world.client_snapshot(chat["user_id"], version=2)

    android = _android(version)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(android, "_open_chat", lambda _chat: "external Android launch")
    monkeypatch.setattr(android, "_wait_ui", lambda _contains: "<hierarchy />")

    def enter(text: str) -> dict[str, Any]:
        with World.open(Path("world")) as current:
            current.send_client_message(
                user_id=chat["user_id"],
                chat_id=chat["id"],
                request_id=f"{kind}-send",
                text=text,
                version=4 if version == 4 else 2,
            )
        return {
            "ok": True,
            "input": "bounded-external-substitute",
            "text_verified": True,
            "send_actions": 1,
            "uid": 2000,
        }

    monkeypatch.setattr(android, "_enter_text", enter)
    observed = android._send_composer_action(chat, "reply", {"text": "reply"})

    with World.open(Path("world")) as world:
        snapshot = world.client_snapshot(chat["user_id"], version=version)
        assert snapshot["message_position"] == before["message_position"] + 1
        assert snapshot["sends"] == observed["sends"]
        assert world.history(chat["id"])[-1] == observed["sends"][0]["message"]
    assert observed["sends"] == [
        {
            "request_id": f"{kind}-send",
            "position": before["message_position"] + 1,
            "message": {
                "id": 2,
                "chat_id": chat["id"],
                "sender_id": chat["user_id"],
                "date": 100,
                "text": "reply",
            },
        }
    ]


def test_start_bot_uses_original_composer_when_stock_overlay_is_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    directory = tmp_path / "world"
    with World.create(directory, seed=7, now=100) as world:
        user = world.create_user(first_name="Sara")
        bot = world.create_user(first_name="Bot", is_bot=True)
        chat = world.open_private_chat(user_id=user["id"], bot_id=bot["id"])

    android = _android(6)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(android, "_open_chat", lambda _chat: "external Android launch")
    composer_ui = (
        '<hierarchy><node text="Bot" package="org.gramlab.android" />'
        '<node text="Message" package="org.gramlab.android" '
        'class="android.widget.EditText" enabled="true" /></hierarchy>'
    )
    monkeypatch.setattr(android, "_wait_ui", lambda _contains, **_options: composer_ui)

    def enter(text: str) -> dict[str, Any]:
        assert text == "/start"
        with World.open(Path("world")) as current:
            current.send_client_message(
                user_id=chat["user_id"],
                chat_id=chat["id"],
                request_id="composer-start",
                text=text,
                version=6,
            )
        return {
            "ok": True,
            "input": "bounded-external-substitute",
            "text_verified": True,
            "send_actions": 1,
            "uid": 2000,
        }

    monkeypatch.setattr(android, "_enter_text", enter)
    observed = android._send_composer_action(chat, None, {"text": "/start"})

    assert observed["android"]["input"]["input"] == "bounded-external-substitute"
    assert observed["sends"][0]["message"]["text"] == "/start"


def test_rich_photo_caption_identity_matches_text_and_credit_and_rejects_ambiguity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with World.create(tmp_path / "world", seed=7, now=100) as world:
        user = world.create_user(first_name="Sara")
        bot = world.create_user(first_name="Bot", is_bot=True)
        chat = world.open_private_chat(user_id=user["id"], bot_id=bot["id"])
        message = world.send_rich_message(
            chat_id=chat["id"],
            sender_id=bot["id"],
            uploads={
                "photo": (ASSETS / "rich-media/photo-square-16x16.png").read_bytes(),
            },
            rich_message={
                "skip_entity_detection": True,
                "blocks": [
                    {
                        "type": "photo",
                        "photo": {"type": "photo", "media": "attach://photo"},
                        "caption": {
                            "text": {"type": "bold", "text": "Caption identity"},
                            "credit": {"type": "italic", "text": "Independent credit"},
                        },
                    }
                ],
            },
            reply_markup=KEYBOARD,
        )

    label = "Caption identity\nIndependent credit\n\nReceived at 10:00 PM\n"
    assert _inline_fragments(message) == ["Caption identity", "Independent credit"]
    assert _inline_matches(message, label)
    assert not _inline_matches(message, "Caption identity\n\nReceived at 10:00 PM\n")

    android = _android(3)
    cell = (
        '<node package="org.gramlab.android" text="'
        + label.replace("\n", "&#10;")
        + '"><node class="android.widget.Button" text="Inspect" /></node>'
    )
    duplicate = "<hierarchy>" + cell * 2 + "</hierarchy>"
    monkeypatch.setattr(android, "_open_chat", lambda _chat: "external Android launch")
    monkeypatch.setattr(android, "_wait_ui", lambda _contains: duplicate)
    with pytest.raises(RuntimeError, match="one accessible match"):
        android._tap_inline_button(chat, message, 0, 0)


def test_ordinary_photo_keyboard_requires_exact_authored_caption_and_rejects_ambiguity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    directory = tmp_path / "world"
    with World.create(directory, seed=7, now=100) as world:
        user = world.create_user(first_name="Sara")
        bot = world.create_user(first_name="Bot", is_bot=True)
        chat = world.open_private_chat(user_id=user["id"], bot_id=bot["id"])
        message = world.send_photo(
            chat_id=chat["id"],
            sender_id=bot["id"],
            photo={"type": "photo", "media": "attach://photo"},
            uploads={
                "photo": (ASSETS / "rich-media/photo-square-16x16.png").read_bytes(),
            },
            caption="PNG ordinary / تصویر معمولی",
            reply_markup=KEYBOARD,
        )
        world.send_photo(
            chat_id=chat["id"],
            sender_id=bot["id"],
            photo={"type": "photo", "media": "attach://other"},
            uploads={
                "other": (ASSETS / "rich-media/photo-square-16x16.png").read_bytes(),
            },
            caption="A distinct authored caption",
            reply_markup=KEYBOARD,
        )

    label = "Photo\nPNG ordinary / تصویر معمولی\nReceived at 10:13 PM\n"
    assert _inline_fragments(message) == ["PNG ordinary / تصویر معمولی"]
    assert _inline_matches(message, label)
    assert not _inline_matches(message, "Photo\nReceived at 10:13 PM\n")
    assert not _inline_matches(message, "Photo\nDifferent caption\nReceived at 10:13 PM\n")

    android = _android(3)
    cell = (
        '<node package="org.gramlab.android" text="'
        + label.replace("\n", "&#10;")
        + '"><node class="android.widget.Button" text="Inspect" bounds="[10,100][90,130]" '
        'clickable="true" enabled="true" /></node>'
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(android, "_open_chat", lambda _chat: "external Android launch")
    monkeypatch.setattr(
        android, "_wait_ui", lambda _contains: "<hierarchy>" + cell + "</hierarchy>"
    )

    class NativeInputReached(Exception):
        pass

    def input_boundary(*_arguments: str, **_keywords: Any) -> Any:
        raise NativeInputReached

    monkeypatch.setattr(android, "_adb", input_boundary)
    with pytest.raises(NativeInputReached):
        android._tap_inline_button(chat, message, 0, 0)

    with World.open(directory) as world:
        world.send_photo(
            chat_id=chat["id"],
            sender_id=bot["id"],
            photo={"type": "photo", "media": "attach://duplicate"},
            uploads={
                "duplicate": (ASSETS / "rich-media/photo-square-16x16.png").read_bytes(),
            },
            caption=message["caption"],
            reply_markup=KEYBOARD,
        )
    with pytest.raises(RuntimeError, match="text is ambiguous"):
        android._tap_inline_button(chat, message, 0, 0)

    message.pop("caption")
    assert _inline_fragments(message) == []
    assert not _inline_matches(message, "Photo\nReceived at 10:13 PM\n")


@pytest.mark.android
def test_public_android_runner_interacts_with_current_photo_mention_and_custom_emoji(
    tmp_path: Path,
) -> None:
    manifest_path = os.environ.get("GRAMLAB_ANDROID_RUNTIME_PROFILE")
    apk = os.environ.get("GRAMLAB_ANDROID_PROBE_APK")
    if manifest_path is None or apk is None or not os.access("/dev/kvm", os.R_OK | os.W_OK):
        pytest.skip("Requires the Android profile, reviewed current APK and accessible KVM")
    project = tmp_path / "project"
    project.mkdir()
    (project / "run.toml").write_text(
        'schema = 1\nmode = "headless-android"\nseed = 7\nnow = 1700000000\ntimeout = 300\n'
        '[scenario]\nentry = "scenario.py"\nfiles = ["scenario.py", "emoji-static.webp", '
        '"emoji-thumbnail.webp"]\n[bots.current]\nentry = "bot.py"\n'
        'files = ["bot.py", "photo.png"]\n'
    )
    (project / "scenario.py").write_text(SCENARIO)
    shutil.copy2("tests/fixtures/current_message_interactions_bot.py", project / "bot.py")
    shutil.copy2(ASSETS / "rich-media/photo-square-16x16.png", project / "photo.png")
    for name in ("emoji-static.webp", "emoji-thumbnail.webp"):
        shutil.copy2(ASSETS / "custom-emoji" / name, project / name)

    output = tmp_path / "run"
    outcome = run(
        project / "run.toml",
        output,
        profile=RuntimeProfile.load(Path(os.environ["GRAMLAB_RUNTIME_PROFILE"])),
        android_profile=RuntimeProfile.load(Path(manifest_path)),
        android_apk=Path(apk),
        bridge_version=4,
    )
    recorded = json.loads((output / "result.json").read_text())
    assert outcome == "passed", recorded
    expected_history = [
        {
            "id": 1,
            "chat_id": 1,
            "sender_id": 2,
            "date": 1700000000,
            "text": "publish current content",
        },
        {
            "id": 2,
            "chat_id": 1,
            "sender_id": 1,
            "date": 1700000000,
            "text": "",
            "rich_message": {
                "blocks": [
                    {
                        "type": "photo",
                        "asset_id": 3,
                        "caption": {
                            "text": {"type": "bold", "text": "Current photo caption"},
                            "credit": {"type": "italic", "text": "Current photo credit"},
                        },
                    }
                ]
            },
            "reply_markup": {
                "inline_keyboard": [[{"text": "Inspect", "callback_data": "inspect-current"}]]
            },
        },
        {
            "id": 3,
            "chat_id": 1,
            "sender_id": 1,
            "date": 1700000000,
            "text": "",
            "rich_message": {
                "blocks": [
                    {
                        "type": "paragraph",
                        "text": {
                            "type": "text_mention",
                            "text": "Mention Bot",
                            "user_id": 1,
                        },
                    }
                ]
            },
        },
        {
            "id": 4,
            "chat_id": 1,
            "sender_id": 1,
            "date": 1700000000,
            "text": "Emoji 👩‍💻",
            "entities": [
                {
                    "type": "custom_emoji",
                    "offset": 6,
                    "length": 5,
                    "custom_emoji_id": "7",
                }
            ],
        },
        {
            "id": 5,
            "chat_id": 1,
            "sender_id": 2,
            "date": 1700000000,
            "text": "reply after current content",
        },
        {
            "id": 6,
            "chat_id": 1,
            "sender_id": 1,
            "date": 1700000000,
            "text": "Current content reply received",
        },
    ]
    assert recorded["histories"] == {"1": expected_history}
    callback_interaction, composer_interaction = recorded["interactions"]
    assert callback_interaction["native"] is True
    assert callback_interaction["callback"]["message"] == expected_history[1]
    assert callback_interaction["callback"]["data"] == "inspect-current"
    assert callback_interaction["android"]["target"]["text"] == "Inspect"
    assert composer_interaction["native"] is True
    assert composer_interaction["sends"] == [
        {
            "request_id": composer_interaction["sends"][0]["request_id"],
            "position": 5,
            "message": expected_history[4],
        }
    ]
    callback_events = [
        event for event in recorded["events"] if event["type"].startswith("callback.")
    ]
    assert [event["type"] for event in callback_events] == [
        "callback.created",
        "callback.answered",
    ]
    expected_callback = {
        "id": callback_interaction["callback"]["id"],
        "user_id": 2,
        "chat_id": 1,
        "message": expected_history[1],
        "data": "inspect-current",
        "chat_instance": callback_interaction["callback"]["chat_instance"],
    }
    assert callback_interaction["callback"] == expected_callback | {"answer": None}
    assert callback_events[0]["data"] == expected_callback
    assert callback_events[1]["data"] == {
        "id": callback_interaction["callback"]["id"],
        "user_id": 2,
        "answer": {"text": "Inspected", "show_alert": False, "cache_time": 0},
    }
    assert recorded["captures"][0]["history"] == expected_history[:4]
    assert recorded["captures"][0]["rendered"] is True
