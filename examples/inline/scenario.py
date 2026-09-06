"""Identical semantic scenario with virtual or actual Android button input."""

import time

from gramlab.scenario import Scenario


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


lab = Scenario.from_environment()
user = lab.create_user(first_name="Sara", language_code="fa")
chat = lab.open_private_chat(user_id=user["id"], bot_id=lab.bots()["inline"])
lab.send_message(chat_id=chat["id"], sender_id=user["id"], text="سلام hello")
deadline = time.monotonic() + 10
while len(lab.history(chat["id"])) != 2:
    expect(time.monotonic() < deadline, "Bot keyboard missing")
    time.sleep(0.05)
message = lab.history(chat["id"])[1]
lab.capture_chat(chat_id=chat["id"], label="before-tap", contains=[message["text"]])
interaction = lab.tap_inline_button(chat_id=chat["id"], message_id=message["id"], row=1, column=0)
callback = interaction["callback"]
expect(callback["data"] == "confirm" and callback["message"] == message, "Wrong keyboard cell")
expect(callback["user_id"] == user["id"] and callback["chat_id"] == chat["id"], "Wrong persona")
deadline = time.monotonic() + 10
while lab.get_callback(user_id=user["id"], callback_id=callback["id"])["answer"] is None:
    expect(time.monotonic() < deadline, "Bot callback answer missing")
    time.sleep(0.05)
expect(
    lab.history(chat["id"])[1]
    == {
        "id": message["id"],
        "chat_id": chat["id"],
        "sender_id": lab.bots()["inline"],
        "date": 1700000000,
        "edit_date": 1700000000,
        "text": "Selected: confirm ✓",
    },
    "Unexpected bot edit",
)
lab.capture_chat(chat_id=chat["id"], label="after-edit", contains=["Selected: confirm ✓"])
