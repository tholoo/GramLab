"""Public scenario for unrelated-edit survival and related-edit rejection."""

import json
import time
from collections.abc import Callable
from typing import Any, Protocol, cast

from gramlab.scenario import Scenario


class RichTargetScenario(Protocol):
    def rich_buttons(self, *, chat_id: int, message_id: int) -> dict[str, Any]: ...

    def tap_rich_button(self, *, target_id: str, timeout: float = 180) -> dict[str, Any]: ...


lab = Scenario.from_environment()
rich_lab = cast(RichTargetScenario, lab)
rendered_user = lab.create_user(first_name="Sara", language_code="fa")
control_user = lab.create_user(first_name="Controller")
bot_id = lab.bots()["unrelated"]
rendered_chat = lab.open_private_chat(user_id=rendered_user["id"], bot_id=bot_id)
control_chat = lab.open_private_chat(user_id=control_user["id"], bot_id=bot_id)
lab.send_message(
    chat_id=rendered_chat["id"], sender_id=rendered_user["id"], text="publish stable target"
)


def wait_for(chat_id: int, predicate: Callable[[list[dict[str, Any]]], bool], phase: str) -> None:
    deadline = time.monotonic() + 30
    while True:
        if predicate(lab.history(chat_id)):
            return
        if time.monotonic() >= deadline:
            raise RuntimeError(f"Bot did not reach semantic phase: {phase}")
        time.sleep(0.02)


wait_for(rendered_chat["id"], lambda history: len(history) == 3, "publication")
initial_rendered = lab.history(rendered_chat["id"])
observation = rich_lab.rich_buttons(chat_id=rendered_chat["id"], message_id=2)
original_target = observation["targets"][0]

lab.send_message(chat_id=control_chat["id"], sender_id=control_user["id"], text="edit unrelated")
wait_for(
    control_chat["id"],
    lambda history: history[-1].get("text") == "unrelated edit acknowledged",
    "unrelated edit acknowledgement",
)
before_success = {"snapshot": lab.snapshot(), "events": lab.events()}
success = rich_lab.tap_rich_button(target_id=original_target["target_id"])
success_repeat = rich_lab.tap_rich_button(target_id=original_target["target_id"])
wait_for(
    control_chat["id"],
    lambda _history: any(event["type"] == "callback.answered" for event in lab.events()),
    "callback answer",
)
after_success = {"snapshot": lab.snapshot(), "events": lab.events()}

related_observation = rich_lab.rich_buttons(chat_id=rendered_chat["id"], message_id=2)
related_target = related_observation["targets"][0]
lab.send_message(chat_id=control_chat["id"], sender_id=control_user["id"], text="edit target")
wait_for(
    control_chat["id"],
    lambda history: history[-1].get("text") == "target edit acknowledged",
    "target edit acknowledgement",
)
before_rejection = {"snapshot": lab.snapshot(), "events": lab.events()}
rejected = rich_lab.tap_rich_button(target_id=related_target["target_id"])
rejected_repeat = rich_lab.tap_rich_button(target_id=related_target["target_id"])
after_rejection = {"snapshot": lab.snapshot(), "events": lab.events()}

lab.send_message(chat_id=control_chat["id"], sender_id=control_user["id"], text="finish proof")
deadline = time.monotonic() + 30
while lab.bot_status("unrelated")["state"] != "exited":
    if time.monotonic() >= deadline:
        raise RuntimeError("Unrelated-target bot did not exit")
    time.sleep(0.02)

print(
    json.dumps(
        {
            "initial_rendered": initial_rendered,
            "observation": observation,
            "original_target_id": original_target["target_id"],
            "success": success,
            "success_repeat": success_repeat,
            "before_success": before_success,
            "after_success": after_success,
            "related_observation": related_observation,
            "rejected": rejected,
            "rejected_repeat": rejected_repeat,
            "before_rejection": before_rejection,
            "after_rejection": after_rejection,
            "rendered_history": lab.history(rendered_chat["id"]),
            "control_history": lab.history(control_chat["id"]),
            "events": lab.events(),
        },
        ensure_ascii=False,
    ),
    flush=True,
)
