"""Public scenario shared by semantic and original rich-target acceptance."""

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
user = lab.create_user(first_name="Sara", language_code="fa")
chat = lab.open_private_chat(user_id=user["id"], bot_id=lab.bots()["targets"])
lab.send_message(chat_id=chat["id"], sender_id=user["id"], text="publish rich targets")


def wait_for(predicate: Callable[[list[dict[str, Any]]], bool], phase: str) -> list[dict[str, Any]]:
    deadline = time.monotonic() + 30
    while True:
        history = lab.history(chat["id"])
        if predicate(history):
            return history
        if time.monotonic() >= deadline:
            raise RuntimeError(f"Bot did not reach semantic phase: {phase}")
        time.sleep(0.02)


wait_for(lambda history: len(history) == 3, "publication")
observation = rich_lab.rich_buttons(chat_id=chat["id"], message_id=2)
by_path = {json.dumps(target["path"]): target for target in observation["targets"]}
paths: list[list[str | int]] = [
    ["blocks", 16, "buttons", 0],
    ["blocks", 16, "buttons", 1],
    ["blocks", 16, "buttons", 2],
    ["blocks", 17, "text", 1, "text", 0, "button"],
    ["blocks", 17, "text", 1, "text", 2, "button"],
    ["blocks", 17, "text", 2, "button"],
    ["blocks", 18, "blocks", 0, "text", "button"],
    ["blocks", 0, "text", "button"],
]


def target(path: list[str | int]) -> dict[str, Any]:
    return cast(dict[str, Any], by_path[json.dumps(path)])


receipts: dict[str, Any] = {}
states: dict[str, Any] = {}
for name, path in zip(
    (
        "row_callback",
        "row_copy",
        "row_disabled",
        "inline_callback",
        "inline_copy",
        "inline_disabled",
        "hidden",
        "offscreen",
    ),
    paths,
    strict=True,
):
    before = {"snapshot": lab.snapshot(), "events": lab.events()}
    receipt = rich_lab.tap_rich_button(target_id=target(path)["target_id"])
    after = {"snapshot": lab.snapshot(), "events": lab.events()}
    receipts[name] = receipt
    states[name] = {"before": before, "after": after}
receipts["row_callback_repeat"] = rich_lab.tap_rich_button(target_id=target(paths[0])["target_id"])

stale_observation = rich_lab.rich_buttons(chat_id=chat["id"], message_id=2)
lab.send_message(chat_id=chat["id"], sender_id=user["id"], text="same-clock ABA")
wait_for(lambda history: history[-1].get("text") == "ABA complete", "same-clock ABA")
stale_target = next(target for target in stale_observation["targets"] if target["path"] == paths[0])
stale_before = {"snapshot": lab.snapshot(), "events": lab.events()}
stale = rich_lab.tap_rich_button(target_id=stale_target["target_id"])
stale_after = {"snapshot": lab.snapshot(), "events": lab.events()}
stale_repeat = rich_lab.tap_rich_button(target_id=stale_target["target_id"])

unrelated_observation = rich_lab.rich_buttons(chat_id=chat["id"], message_id=2)
lab.send_message(chat_id=chat["id"], sender_id=user["id"], text="edit unrelated")
wait_for(lambda history: history[-1].get("text") == "Unrelated edit complete", "unrelated edit")
unrelated_target = next(
    target for target in unrelated_observation["targets"] if target["path"] == paths[0]
)
unrelated = rich_lab.tap_rich_button(target_id=unrelated_target["target_id"])
unrelated_repeat = rich_lab.tap_rich_button(target_id=unrelated_target["target_id"])

lab.send_message(chat_id=chat["id"], sender_id=user["id"], text="finish rich targets")
finish_deadline = time.monotonic() + 30
while lab.bot_status("targets")["state"] != "exited":
    if time.monotonic() >= finish_deadline:
        raise RuntimeError("Rich-target bot did not exit")
    time.sleep(0.02)

print(
    json.dumps(
        {
            "observation": observation,
            "receipts": receipts,
            "states": states,
            "stale_observation": stale_observation,
            "stale": stale,
            "stale_repeat": stale_repeat,
            "stale_before": stale_before,
            "stale_after": stale_after,
            "unrelated_observation": unrelated_observation,
            "unrelated": unrelated,
            "unrelated_repeat": unrelated_repeat,
            "history": lab.history(chat["id"]),
            "events": lab.events(),
        },
        ensure_ascii=False,
    ),
    flush=True,
)
