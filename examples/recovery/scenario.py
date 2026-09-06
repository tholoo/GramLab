"""Crash after callback receipt, then recover the same update in either rendering mode."""

import time

from gramlab.scenario import Scenario


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


lab = Scenario.from_environment()
user = lab.create_user(first_name="Sara", language_code="fa")
chat = lab.open_private_chat(user_id=user["id"], bot_id=lab.bots()["recovery"])
lab.send_message(chat_id=chat["id"], sender_id=user["id"], text="سلام hello")
deadline = time.monotonic() + 10
while len(lab.history(chat["id"])) != 2:
    expect(time.monotonic() < deadline, "Keyboard missing")
    time.sleep(0.05)
lab.capture_chat(chat_id=chat["id"], label="before-crash", contains=["Choose recovery"])
action = lab.tap_inline_button(chat_id=chat["id"], message_id=2, row=0, column=0)
callback = action["callback"]
deadline = time.monotonic() + 10
while len(lab.history(chat["id"])) != 3:
    expect(time.monotonic() < deadline, "Bot did not reach its controlled crash point")
    time.sleep(0.05)
expect(
    lab.get_callback(user_id=user["id"], callback_id=callback["id"])["answer"] is None,
    "Callback was acknowledged before the crash",
)
status = lab.bot_status("recovery")
expect(status["state"] == "running" and status["generation"] == 1, "Wrong initial bot state")
stopped = lab.stop_bot("recovery", generation=status["generation"])
expect(stopped["state"] == "stopped" and stopped["generation"] == 1, "Bot did not stop")
expect(lab.bot_status("recovery") == stopped, "Stopped state was not retained")
started = lab.start_bot("recovery", generation=stopped["generation"])
expect(started["state"] == "running" and started["generation"] == 2, "Wrong replacement generation")
deadline = time.monotonic() + 10
while lab.get_callback(user_id=user["id"], callback_id=callback["id"])["answer"] is None:
    expect(time.monotonic() < deadline, "Recovered bot did not answer the pending callback")
    time.sleep(0.05)
expect(lab.history(chat["id"])[1]["text"] == "Recovered — بازیابی شد ✓", "Recovery edit missing")
expect(
    len([event for event in lab.events() if event["type"] == "callback.created"]) == 1,
    "Restart created a second callback",
)
lab.capture_chat(chat_id=chat["id"], label="after-recovery", contains=["Recovered — بازیابی شد ✓"])
