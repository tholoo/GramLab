"""Two independent conversations with a real bot, inside the private scenario process."""

from typing import Any

from gramlab import Conversation, Message, Scenario

lab = Scenario.from_environment()
bot = lab.bot("echo")
conversations: list[tuple[Conversation, Message, str]] = []
for first_name, language, text in (
    ("Sara", "fa", "سلام hello — نیم‌فاصله 👩🏽‍💻"),
    ("Alex", "en", "Hello from a second conversation"),
):
    chat = lab.conversation(user=lab.user(first_name, language_code=language), bot=bot)
    sent = chat.send(text)
    conversations.append((chat, sent, text))

for chat, sent, text in conversations:
    history = chat.wait_for_messages(2, timeout=10)
    expected: list[dict[str, Any]] = [
        sent.raw,
        {
            "id": 2,
            "chat_id": chat.id,
            "sender_id": bot.id,
            "date": 1700000000,
            "text": "Echo: " + text,
        },
    ]
    if [message.raw for message in history] != expected:
        raise AssertionError("Conversation history differs from the expected exchange")
    chat.capture("chat-" + str(chat.id), contains=[text, "Echo: " + text])
print("Verified two independent conversations, including mixed Persian/English and emoji.")
