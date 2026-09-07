"""Capture the same rich-list callback flow in simulation and Android modes."""

import time

from gramlab.scenario import Scenario


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


lab = Scenario.from_environment()
user = lab.create_user(first_name="Sara", language_code="fa")
chat = lab.open_private_chat(user_id=user["id"], bot_id=lab.bots()["lists"])
lab.send_message(chat_id=chat["id"], sender_id=user["id"], text="Show lists")
deadline = time.monotonic() + 10
while len(lab.history(chat["id"])) != 2:
    expect(time.monotonic() < deadline, "Bot list message missing")
    time.sleep(0.05)
message = lab.history(chat["id"])[1]
lab.capture_chat(
    chat_id=chat["id"],
    label="before-tap",
    contains=[
        "سلام hello",
        "راهنمای کوتاه English wraps",
        "تو در تو nested",
        "More",
        "سه roman",
    ],
)
interaction = lab.tap_inline_button(chat_id=chat["id"], message_id=message["id"], row=1, column=0)
callback = interaction["callback"]
expect(callback["data"] == "rtl-edit" and callback["message"] == message, "Wrong callback")
expect(callback["user_id"] == user["id"] and callback["chat_id"] == chat["id"], "Wrong persona")
deadline = time.monotonic() + 10
while True:
    answer = lab.get_callback(user_id=user["id"], callback_id=callback["id"])["answer"]
    history = lab.history(chat["id"])
    if answer is not None and history[1].get("edit_date") is not None:
        break
    expect(time.monotonic() < deadline, "Bot list edit or callback answer missing")
    time.sleep(0.05)
expect(
    answer == {"text": "Lists updated", "show_alert": False, "cache_time": 0},
    "Unexpected callback answer",
)
for label in ("live-edit", "cold-reopen"):
    lab.capture_chat(
        chat_id=chat["id"],
        label=label,
        contains=["ویرایش راست‌به‌چپ RTL", "مرحله nested", "چهار IV", "پنج decimal"],
    )
print("Rich lists retained through callback edit and cold reopen")
