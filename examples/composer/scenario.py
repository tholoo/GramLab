"""Actual composer input and equal-text sends, with the same semantic simulation contract."""

import time
from typing import Any

from gramlab.scenario import Scenario

lab = Scenario.from_environment()
bot_id = lab.bots()["echo"]
user = lab.create_user(first_name="Sara", language_code="fa")
chat = lab.open_private_chat(user_id=user["id"], bot_id=bot_id)
lab.capture_chat(chat_id=chat["id"], label="before-input", contains=[])
started = lab.start_bot_chat(chat_id=chat["id"])
start_message = {
    "id": 1,
    "chat_id": chat["id"],
    "sender_id": user["id"],
    "date": 1700000000,
    "text": "/start",
}
if len(started["sends"]) != 1 or started["sends"][0]["message"] != start_message:
    raise AssertionError("Start Bot did not produce the ordinary /start message")
history: list[dict[str, Any]] = [
    start_message,
    {
        "id": 2,
        "chat_id": chat["id"],
        "sender_id": bot_id,
        "date": 1700000000,
        "text": "Echo: /start",
    },
]
deadline = time.monotonic() + 10
while len(lab.history(chat["id"])) < 2:
    if time.monotonic() >= deadline:
        raise TimeoutError("Bot reply missing after Start Bot")
    time.sleep(0.02)
if lab.history(chat["id"]) != history:
    raise AssertionError("Started conversation differs from the expected exchange")
unicode_input = " **سلام 👩🏽‍💻**\nhello "
unicode_message = {
    "text": "سلام 👩🏽‍💻\nhello",
    "entities": [{"type": "bold", "offset": 0, "length": 12}],
}
receipts = []
for raw, message in (
    (unicode_input, unicode_message),
    (unicode_input, unicode_message),
    (
        "before `code` and __italic__",
        {
            "text": "before code and italic",
            "entities": [
                {"type": "code", "offset": 7, "length": 4},
                {"type": "italic", "offset": 16, "length": 6},
            ],
        },
    ),
):
    record = lab.type_message(chat_id=chat["id"], text=raw)
    expected = {
        "id": len(history) + 1,
        "chat_id": chat["id"],
        "sender_id": user["id"],
        "date": 1700000000,
        **message,
    }
    if len(record["sends"]) != 1:
        raise AssertionError("Composer did not accept exactly one message")
    receipt = record["sends"][0]
    if receipt["message"] != expected or receipt["position"] != len(history) + 1:
        raise AssertionError("Composer receipt differs from expected text, entities or position")
    receipts.append(receipt)
    history.extend(
        [
            expected,
            {
                "id": len(history) + 2,
                "chat_id": chat["id"],
                "sender_id": bot_id,
                "date": 1700000000,
                "text": "Echo: " + str(message["text"]),
            },
        ]
    )
    deadline = time.monotonic() + 10
    while len(lab.history(chat["id"])) < len(history):
        if time.monotonic() >= deadline:
            raise TimeoutError("Bot reply missing after composer input")
        time.sleep(0.02)
    if lab.history(chat["id"]) != history:
        raise AssertionError("Full conversation differs from the expected composer exchange")
    if len(receipts) == 1:
        lab.capture_chat(
            chat_id=chat["id"], label="first-send", contains=["سلام", "Echo:", "hello"]
        )
if len({receipt["request_id"] for receipt in receipts}) != 3:
    raise AssertionError("Separate composer actions reused a send identity")
lab.capture_chat(
    chat_id=chat["id"], label="after-input", contains=["before code and italic", "Echo:"]
)
print(
    "Verified Start Bot, original composer semantics, distinct equal-text sends "
    "and four bot replies."
)
