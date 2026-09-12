"""Identical semantic scenario with virtual or actual Android button input."""

from gramlab import Scenario


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


lab = Scenario.from_environment()
chat = lab.conversation(user=lab.user("Sara", language_code="fa"), bot="inline")
chat.send("سلام hello")
message = chat.wait_for_messages(2, timeout=10)[1]
chat.capture("before-tap", contains=[message.text])
callback = message.inline_button(1, 0).tap().callback
expect(callback.data == "confirm" and callback.raw["message"] == message.raw, "Wrong keyboard cell")
expect(callback.user_id == chat.user.id and callback.chat_id == chat.id, "Wrong persona")
callback.wait_until_answered(timeout=10)
expect(
    chat.history()[1].raw
    == {
        "id": message.id,
        "chat_id": chat.id,
        "sender_id": chat.bot.id,
        "date": 1700000000,
        "edit_date": 1700000000,
        "text": "Selected: confirm ✓",
    },
    "Unexpected bot edit",
)
chat.capture("after-edit", contains=["Selected: confirm ✓"])
