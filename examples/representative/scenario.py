"""One semantic scenario shared by simulation and the original Android renderer."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from assets import ANIMATED_EMOJI, EMOJI_THUMBNAIL, STATIC_EMOJI

from gramlab.scenario import Scenario

if Path("/work/world").exists() or Path("/proc/1/root/work/world").exists():
    raise RuntimeError("Representative scenario can see the authoritative World")

lab = Scenario.from_environment()
static = lab.register_custom_emoji(
    request_id="representative-static",
    custom_emoji_id="1",
    main=STATIC_EMOJI,
    thumbnail=EMOJI_THUMBNAIL,
    fallback="👩‍💻",
)
animated = lab.register_custom_emoji(
    request_id="representative-animated",
    custom_emoji_id="1109",
    main=ANIMATED_EMOJI,
    thumbnail=EMOJI_THUMBNAIL,
    fallback="👩‍💻",
)
user = lab.create_user(first_name="Sara", username="sara", language_code="fa")
chat = lab.open_private_chat(user_id=user["id"], bot_id=lab.bots()["representative"])


def wait_history(count: int, phase: str) -> list[dict[str, Any]]:
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        history = lab.history(chat["id"])
        if len(history) == count:
            return history
        if len(history) > count:
            raise RuntimeError(f"Unexpected extra message during {phase}")
        time.sleep(0.02)
    raise RuntimeError(f"Representative bot did not reach {phase}")


start = lab.start_bot_chat(chat_id=chat["id"])
incoming = lab.send_message(
    chat_id=chat["id"],
    sender_id=user["id"],
    text="Incoming 👩‍💻",
    entities=[{"type": "custom_emoji", "offset": 9, "length": 5, "custom_emoji_id": "1"}],
)
initial = wait_history(4, "initial controls")
initial_capture = lab.capture_chat(
    chat_id=chat["id"],
    label="representative-initial",
    contains=["Ordinary سلام", "Auto example.test"],
)

ordinary_action = lab.tap_inline_button(chat_id=chat["id"], message_id=3, row=0, column=0)
wait_history(5, "restart checkpoint")
ordinary_callback = ordinary_action["callback"]
if lab.get_callback(user_id=user["id"], callback_id=ordinary_callback["id"])["answer"] is not None:
    raise RuntimeError("Recovery callback was answered before restart")
first_status = lab.bot_status("representative")
stopped = lab.stop_bot("representative", generation=first_status["generation"])
started = lab.start_bot("representative", generation=stopped["generation"])
deadline = time.monotonic() + 90
ordinary_answer = None
while ordinary_answer is None and time.monotonic() < deadline:
    ordinary_answer = lab.get_callback(user_id=user["id"], callback_id=ordinary_callback["id"])[
        "answer"
    ]
    if ordinary_answer is None:
        time.sleep(0.02)
if ordinary_answer is None or lab.history(chat["id"])[2]["text"] != "Recovered — بازیابی شد ✓":
    raise RuntimeError("Representative callback did not recover")

observation = lab.rich_buttons(chat_id=chat["id"], message_id=4)
by_path = {json.dumps(target["path"]): target for target in observation["targets"]}
row_path = ["blocks", 2, "buttons", 0]
inline_path = ["blocks", 3, "text", "button"]
row_action = lab.tap_rich_button(target_id=by_path[json.dumps(row_path)]["target_id"])
inline_action = lab.tap_rich_button(target_id=by_path[json.dumps(inline_path)]["target_id"])
if row_action["status"] != "succeeded" or inline_action["status"] != "succeeded":
    raise RuntimeError("Representative rich action failed")
deadline = time.monotonic() + 90
while time.monotonic() < deadline:
    current_rich = lab.history(chat["id"])[3].get("rich_message", {})
    answers = [
        lab.get_callback(user_id=user["id"], callback_id=action["effect"]["callback"]["id"])[
            "answer"
        ]
        for action in (row_action, inline_action)
    ]
    if current_rich.get("blocks") == [
        {"type": "paragraph", "text": "Rich callbacks complete / کنش‌های غنی کامل شد"}
    ] and all(answer is not None for answer in answers):
        break
    time.sleep(0.02)
else:
    raise RuntimeError("Representative rich callbacks were not completed")
recovered_capture = lab.capture_chat(
    chat_id=chat["id"],
    label="representative-recovered",
    contains=["Recovered", "Rich callbacks complete"],
)

photos_input = lab.type_message(chat_id=chat["id"], text="publish photos / تصاویر")
photos = wait_history(12, "photo publication")
photo_capture = lab.capture_chat(
    chat_id=chat["id"], label="representative-photos", contains=["Photo album / آلبوم عکس"]
)
documents_input = lab.type_message(chat_id=chat["id"], text="publish documents / اسناد")
documents = wait_history(17, "document publication")
document_capture = lab.capture_chat(
    chat_id=chat["id"],
    label="representative-documents",
    contains=["Document album / آلبوم سند"],
)
restart_capture = lab.capture_chat(
    chat_id=chat["id"],
    label="representative-relaunch",
    contains=["Document album / آلبوم سند"],
)
deadline = time.monotonic() + 90
final_status = lab.bot_status("representative")
while final_status["state"] == "running" and time.monotonic() < deadline:
    time.sleep(0.02)
    final_status = lab.bot_status("representative")
if final_status["state"] != "exited" or final_status["exit_code"] != 0:
    raise RuntimeError("Representative bot did not exit cleanly")

print(
    json.dumps(
        {
            "registrations": [static, animated],
            "user": user,
            "start": start,
            "incoming": incoming,
            "initial_history": initial,
            "initial_capture": initial_capture,
            "ordinary_action": ordinary_action,
            "ordinary_answer": ordinary_answer,
            "bot_lifecycle": [first_status, stopped, started, final_status],
            "rich_observation": observation,
            "rich_actions": [row_action, inline_action],
            "recovered_capture": recovered_capture,
            "photos_input": photos_input,
            "photos": photos[6:12],
            "photo_capture": photo_capture,
            "documents_input": documents_input,
            "documents": documents[13:17],
            "document_capture": document_capture,
            "restart_capture": restart_capture,
            "history": lab.history(chat["id"]),
            "events": lab.events(),
        },
        ensure_ascii=False,
    ),
    flush=True,
)
