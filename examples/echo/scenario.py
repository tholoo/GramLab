"""Two independent conversations with a real bot, inside the private scenario process."""

import time

from gramlab.scenario import Scenario

lab = Scenario.from_environment()
bot_id = lab.bots()["echo"]
conversations = []
for first_name, language, text in (
    ("Sara", "fa", "سلام hello — نیم‌فاصله 👩🏽‍💻"),
    ("Alex", "en", "Hello from a second conversation"),
):
    user = lab.create_user(first_name=first_name, language_code=language)
    chat = lab.open_private_chat(user_id=user["id"], bot_id=bot_id)
    sent = lab.send_message(chat_id=chat["id"], sender_id=user["id"], text=text)
    conversations.append((chat, sent, text))

deadline = time.monotonic() + 10
for chat, sent, text in conversations:
    while len(lab.history(chat["id"])) < 2:
        if time.monotonic() >= deadline:
            raise TimeoutError("The bot did not reply to both conversations")
        time.sleep(0.02)
    expected = [
        sent,
        {
            "id": 2,
            "chat_id": chat["id"],
            "sender_id": bot_id,
            "date": 1700000000,
            "text": "Echo: " + text,
        },
    ]
    if lab.history(chat["id"]) != expected:
        raise AssertionError("Conversation history differs from the expected exchange")
    lab.capture_chat(
        chat_id=chat["id"], label="chat-" + str(chat["id"]), contains=[text, "Echo: " + text]
    )
print("Verified two independent conversations, including mixed Persian/English and emoji.")
