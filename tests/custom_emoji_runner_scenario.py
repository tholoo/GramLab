"""Public scenario shared by simulation and original custom-emoji acceptance."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from gramlab.scenario import Scenario

if Path("/work/world").exists() or Path("/proc/1/root/work/world").exists():
    raise RuntimeError("Scenario can see the authoritative World")

lab = Scenario.from_environment()
static = lab.register_custom_emoji(
    request_id="runner-static",
    custom_emoji_id="1",
    main=Path("emoji-static.webp").read_bytes(),
    thumbnail=Path("emoji-thumbnail.webp").read_bytes(),
    fallback="👩‍💻",
)
animated = lab.register_custom_emoji(
    request_id="runner-animated",
    custom_emoji_id="1109",
    main=Path("emoji-animated.webm").read_bytes(),
    thumbnail=Path("emoji-thumbnail.webp").read_bytes(),
    fallback="👩‍💻",
)
assert static == {
    "custom_emoji_id": "1",
    "fallback": "👩‍💻",
    "free": True,
    "needs_repainting": False,
    "main_asset_id": 1,
    "thumbnail_asset_id": 2,
    "duration_ms": 0,
}
assert animated == {
    "custom_emoji_id": "1109",
    "fallback": "👩‍💻",
    "free": True,
    "needs_repainting": False,
    "main_asset_id": 3,
    "thumbnail_asset_id": 2,
    "duration_ms": 1000,
}

user = lab.create_user(first_name="Sara", language_code="fa")
bot = lab.bots()["emoji"]
chat = lab.open_private_chat(user_id=user["id"], bot_id=bot)
incoming = lab.send_message(
    chat_id=chat["id"],
    sender_id=user["id"],
    text="Incoming 👩‍💻",
    entities=[{"type": "custom_emoji", "offset": 9, "length": 5, "custom_emoji_id": "1"}],
)


def wait_for_messages(phase: str, identifiers: tuple[str, str]) -> list[dict[str, Any]]:
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        history = lab.history(chat["id"])
        if len(history) == 3:
            ordinary, rich = history[1:]
            ordinary_id = ordinary.get("entities", [{}])[0].get("custom_emoji_id")
            rich_id = (
                rich.get("rich_message", {})
                .get("blocks", [{}])[0]
                .get("text", [{}, {}])[1]
                .get("custom_emoji_id")
            )
            if (ordinary_id, rich_id) == identifiers:
                return history
        time.sleep(0.02)
    raise RuntimeError(f"Bot did not reach the {phase} custom-emoji state")


initial_history = wait_for_messages("initial", ("1", "1"))
initial_capture = lab.capture_chat(
    chat_id=chat["id"],
    label="custom-emoji-initial",
    contains=["Incoming", "Ordinary", "Rich"],
)
lab.advance_time(5)
interaction = lab.tap_inline_button(
    chat_id=chat["id"], message_id=initial_history[1]["id"], row=0, column=0
)
callback = interaction["callback"]
assert callback["message"] == initial_history[1]
assert callback["data"] == "emoji:animate" and callback["answer"] is None

final_history = wait_for_messages("edited", ("1109", "1109"))
deadline = time.monotonic() + 30
answer = None
while answer is None and time.monotonic() < deadline:
    answer = lab.get_callback(user_id=user["id"], callback_id=callback["id"])["answer"]
    if answer is None:
        time.sleep(0.02)
if answer is None:
    raise RuntimeError("Bot did not answer the custom-emoji callback")
assert answer == {"text": "Animated / متحرک شد", "show_alert": False, "cache_time": 0}

edited_capture = lab.capture_chat(
    chat_id=chat["id"],
    label="custom-emoji-edited",
    contains=["Incoming", "Ordinary", "Rich"],
)
relaunch_capture = lab.capture_chat(
    chat_id=chat["id"],
    label="custom-emoji-relaunch",
    contains=["Incoming", "Ordinary", "Rich"],
)
deadline = time.monotonic() + 30
bot_status = lab.bot_status("emoji")
while bot_status["state"] == "running" and time.monotonic() < deadline:
    time.sleep(0.02)
    bot_status = lab.bot_status("emoji")
if bot_status != {
    "name": "emoji",
    "generation": 1,
    "state": "exited",
    "exit_code": 0,
}:
    raise RuntimeError("Custom-emoji bot did not exit cleanly")
print(
    json.dumps(
        {
            "static": static,
            "animated": animated,
            "incoming": incoming,
            "initial_history": initial_history,
            "initial_capture": initial_capture,
            "interaction": interaction,
            "answer": answer,
            "edited_capture": edited_capture,
            "relaunch_capture": relaunch_capture,
            "final_history": final_history,
            "events": lab.events(),
        },
        ensure_ascii=False,
    ),
    flush=True,
)
