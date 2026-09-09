import time

from gramlab.scenario import Scenario

lab = Scenario.from_environment()
user = lab.create_user(first_name="Alex", language_code="en")
chat = lab.open_private_chat(user_id=user["id"], bot_id=lab.bots()["echo"])
lab.send_message(chat_id=chat["id"], sender_id=user["id"], text="Hello!")

deadline = time.monotonic() + 5
while len(lab.history(chat["id"])) < 2:
    if time.monotonic() >= deadline:
        raise TimeoutError("The bot did not reply")
    time.sleep(0.05)

if lab.history(chat["id"])[1]["text"] != "Echo: Hello!":
    raise AssertionError("Unexpected bot reply")
lab.capture_chat(chat_id=chat["id"], label="hello", contains=["Echo: Hello!"])
