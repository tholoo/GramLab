"""One rich-message send/edit scenario for semantic and original Android captures."""

import json
import time
from pathlib import Path
from typing import Any

from gramlab.scenario import Scenario

lab = Scenario.from_environment()
scene = json.loads(Path("scene.json").read_text())
user = lab.create_user(first_name="Sara", language_code="fa")
chat = lab.open_private_chat(user_id=user["id"], bot_id=lab.bots()["rich"])


def wait_for_rich(expected: dict[str, Any]) -> None:
    deadline = time.monotonic() + 10
    while True:
        history = lab.history(chat["id"])
        if len(history) >= 2 and history[1].get("rich_message") == expected:
            return
        if time.monotonic() >= deadline:
            raise AssertionError("Bot rich content did not reach the expected state")
        time.sleep(0.05)


lab.send_message(chat_id=chat["id"], sender_id=user["id"], text="Show rich blocks")
wait_for_rich(scene["initial"])
lab.capture_chat(
    chat_id=chat["id"],
    label="initial",
    contains=["Rich blocks", "Hello GramLab", "Language", "۱۲۳", "Original Android rendering"],
)
lab.advance_time(5)
lab.send_message(chat_id=chat["id"], sender_id=user["id"], text="Edit rich blocks")
wait_for_rich(scene["edited"])
for label in ("edited", "restarted"):
    lab.capture_chat(
        chat_id=chat["id"],
        label=label,
        contains=["Rich blocks updated", "GramLab", "زبان", "۴۵۶", "Edited rich message"],
    )
print("Structured send and RTL edit retained in three captures")
