"""Public Scenario workflow for residual rich-button acceptance."""

import json
import time
from pathlib import Path
from typing import Any, Protocol, cast

from gramlab.scenario import Scenario, ScenarioError


class RichScenario(Protocol):
    def rich_buttons(self, *, chat_id: int, message_id: int) -> dict[str, Any]: ...

    def tap_rich_button(self, *, target_id: str, timeout: float = 180) -> dict[str, Any]: ...


mode = json.loads(Path("fixture-mode.json").read_text())
if mode not in ("simulation-only", "headless-android"):
    raise ValueError("Unknown residual fixture mode")
lab = Scenario.from_environment()
rich = cast(RichScenario, lab)
user = lab.create_user(first_name="Sara", language_code="fa")
chat = lab.open_private_chat(user_id=user["id"], bot_id=lab.bots()["residual"])
lab.send_message(chat_id=chat["id"], sender_id=user["id"], text="publish residual controls")

deadline = time.monotonic() + 30
while len(lab.history(chat["id"])) != 2:
    if time.monotonic() >= deadline:
        raise RuntimeError("Residual fixture did not publish")
    time.sleep(0.02)

paths: dict[str, list[str | int]] = {
    "clipped": ["blocks", 4, "buttons", 0],
    "rtl_callback": ["blocks", 16, "buttons", 0],
    "copy": ["blocks", 16, "buttons", 1],
    "lost_reply_callback": ["blocks", 17, "text", 1, "text", "button"],
}


def state() -> dict[str, Any]:
    return {
        "snapshot": lab.snapshot(),
        "history": lab.history(chat["id"]),
        "events": lab.events(),
    }


def observe() -> dict[str, Any]:
    return rich.rich_buttons(chat_id=chat["id"], message_id=2)


def select(observation: dict[str, Any], name: str) -> dict[str, Any]:
    matching = [target for target in observation["targets"] if target["path"] == paths[name]]
    if len(matching) != 1:
        raise RuntimeError(f"Residual target is missing or ambiguous: {name}")
    return cast(dict[str, Any], matching[0])


def wait_for_callback_answers(expected: int) -> None:
    deadline = time.monotonic() + 30
    while len([event for event in lab.events() if event["type"] == "callback.answered"]) < expected:
        if time.monotonic() >= deadline:
            raise RuntimeError("Residual callback answer did not arrive")
        time.sleep(0.02)


actions: list[dict[str, Any]] = []
if mode == "simulation-only":
    observation = observe()
    for name in ("rtl_callback", "copy", "lost_reply_callback"):
        target = select(observation, name)
        before = state()
        receipt = rich.tap_rich_button(target_id=target["target_id"])
        repeat = (
            rich.tap_rich_button(target_id=target["target_id"])
            if name == "lost_reply_callback"
            else None
        )
        if name == "rtl_callback":
            wait_for_callback_answers(1)
        elif name == "lost_reply_callback":
            wait_for_callback_answers(2)
        actions.append(
            {
                "name": name,
                "observation": observation,
                "target": target,
                "before": before,
                "receipt": receipt,
                "repeat": repeat,
                "after": state(),
            }
        )
else:
    initial = observe()
    clipped = select(initial, "clipped")
    before = state()
    clipped_receipt = rich.tap_rich_button(target_id=clipped["target_id"])
    actions.append(
        {
            "name": "clipped",
            "observation": initial,
            "target": clipped,
            "before": before,
            "receipt": clipped_receipt,
            "repeat": rich.tap_rich_button(target_id=clipped["target_id"]),
            "after": state(),
        }
    )
    rtl = select(initial, "rtl_callback")
    before = state()
    rtl_receipt = rich.tap_rich_button(target_id=rtl["target_id"])
    wait_for_callback_answers(1)
    actions.append(
        {
            "name": "rtl_callback",
            "observation": initial,
            "target": rtl,
            "before": before,
            "receipt": rtl_receipt,
            "repeat": rich.tap_rich_button(target_id=rtl["target_id"]),
            "after": state(),
        }
    )

    restart_observation = observe()
    old_copy = select(restart_observation, "copy")
    before = state()
    old_receipt = rich.tap_rich_button(target_id=old_copy["target_id"])
    actions.append(
        {
            "name": "restart_old_copy",
            "observation": restart_observation,
            "target": old_copy,
            "before": before,
            "receipt": old_receipt,
            "repeat": rich.tap_rich_button(target_id=old_copy["target_id"]),
            "after": state(),
        }
    )
    fresh_observation = observe()
    fresh_copy = select(fresh_observation, "copy")
    before = state()
    fresh_receipt = rich.tap_rich_button(target_id=fresh_copy["target_id"])
    actions.append(
        {
            "name": "restart_fresh_copy",
            "observation": fresh_observation,
            "target": fresh_copy,
            "before": before,
            "receipt": fresh_receipt,
            "repeat": rich.tap_rich_button(target_id=fresh_copy["target_id"]),
            "after": state(),
        }
    )

    lost_observation = observe()
    lost = select(lost_observation, "lost_reply_callback")
    before = state()
    failure: dict[str, Any] | None = None
    try:
        rich.tap_rich_button(target_id=lost["target_id"])
    except ScenarioError as error:
        failure = {
            "operation": error.operation,
            "code": error.code,
            "outcome_uncertain": error.outcome_uncertain,
            "status": error.status,
        }
    if failure is None:
        raise RuntimeError("The dedicated supervisor did not drop the selected control reply")
    recovered = rich.tap_rich_button(target_id=lost["target_id"])
    wait_for_callback_answers(2)
    actions.append(
        {
            "name": "lost_reply_callback",
            "observation": lost_observation,
            "target": lost,
            "before": before,
            "transport_failure": failure,
            "receipt": recovered,
            "repeat": rich.tap_rich_button(target_id=lost["target_id"]),
            "after": state(),
        }
    )

lab.send_message(chat_id=chat["id"], sender_id=user["id"], text="finish residual controls")
deadline = time.monotonic() + 30
while lab.bot_status("residual")["state"] != "exited":
    if time.monotonic() >= deadline:
        raise RuntimeError("Residual fixture did not finish")
    time.sleep(0.02)

print(
    json.dumps(
        {"mode": mode, "user": user, "chat": chat, "actions": actions, "final": state()},
        ensure_ascii=False,
    ),
    flush=True,
)
