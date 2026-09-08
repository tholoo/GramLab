"""Four independent public observations, with clipboard proof terminal in each phase."""

import json
import time
from pathlib import Path
from typing import Any, Protocol, cast

from gramlab.scenario import Scenario


class RichScenario(Protocol):
    def rich_buttons(self, *, chat_id: int, message_id: int) -> dict[str, Any]: ...

    def tap_rich_button(self, *, target_id: str, timeout: float = 180) -> dict[str, Any]: ...


if json.loads(Path("fixture-variant.json").read_text()) != "clipboard-four-phases":
    raise ValueError("Expected the dedicated clipboard phase manifest")
lab = Scenario.from_environment()
rich = cast(RichScenario, lab)
user = lab.create_user(first_name="Sara", language_code="fa")
chat = lab.open_private_chat(user_id=user["id"], bot_id=lab.bots()["targets"])
lab.send_message(chat_id=chat["id"], sender_id=user["id"], text="publish rich targets")
deadline = time.monotonic() + 30
while len(lab.history(chat["id"])) != 3:
    if time.monotonic() >= deadline:
        raise RuntimeError("Clipboard fixture did not publish")
    time.sleep(0.02)


def state() -> dict[str, Any]:
    return {"snapshot": lab.snapshot(), "events": lab.events(), "history": lab.history(chat["id"])}


row = ["blocks", 16, "buttons", 1]
inline = ["blocks", 17, "text", 1, "text", 2, "button"]
plan = [
    ("row_copy", [("row_copy", row)]),
    ("inline_copy", [("inline_copy", inline)]),
    (
        "inline_disabled",
        [("inline_baseline", inline), ("inline_disabled", ["blocks", 17, "text", 2, "button"])],
    ),
    ("row_disabled", [("row_baseline", row), ("row_disabled", ["blocks", 16, "buttons", 2])]),
]
phases = []
for name, actions in plan:
    before = state()
    observation = rich.rich_buttons(chat_id=chat["id"], message_id=2)
    phase: dict[str, Any] = {
        "name": name,
        "observation": observation,
        "before": before,
        "observed": state(),
        "actions": [],
    }
    for action, path in actions:
        target = next(target for target in observation["targets"] if target["path"] == path)
        before = state()
        receipt = rich.tap_rich_button(target_id=target["target_id"])
        phase["actions"].append(
            {"name": action, "receipt": receipt, "before": before, "after": state()}
        )
        if receipt["status"] != "succeeded" or receipt["dispatch"] != "dispatched":
            raise RuntimeError("Clipboard phase action failed; no replacement or retry")
    phase["after"] = state()
    phases.append(phase)

lab.send_message(chat_id=chat["id"], sender_id=user["id"], text="finish rich targets")
deadline = time.monotonic() + 30
while lab.bot_status("targets")["state"] != "exited":
    if time.monotonic() >= deadline:
        raise RuntimeError("Clipboard fixture did not finish")
    time.sleep(0.02)
print(
    json.dumps(
        {"variant": "clipboard-four-phases", "phases": phases, "final": state()}, ensure_ascii=False
    ),
    flush=True,
)
