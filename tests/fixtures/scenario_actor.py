"""Independent programmable scenario consumer, with no world/database imports."""

import json
import socket
import sys
import time
from pathlib import Path

from gramlab.scenario import Scenario

scenario = Scenario.from_environment()


readable = []
for name in (
    "/work/world/world.sqlite3",
    "/proc/1/root/work/world/world.sqlite3",
    "/work/bot/echo_bot.py",
    "/proc/1/root/work/bot/echo_bot.py",
):
    if Path(name).exists():
        readable.append(name)
with socket.socket() as connection:
    connection.settimeout(1)
    try:
        connection.connect(("192.0.2.1", 443))
    except OSError as error:
        external_errno = error.errno
    else:
        external_errno = None
alice = scenario.create_user(first_name="Sara", language_code="fa")
echo = scenario.create_user(first_name="Echo", username="gramlab_echo_bot", is_bot=True)
chat = scenario.open_private_chat(user_id=alice["id"], bot_id=echo["id"])
print(
    json.dumps(
        {
            "ready": True,
            "readable": readable,
            "interfaces": [name for _, name in socket.if_nameindex()],
            "external_errno": external_errno,
        }
    ),
    flush=True,
)
if sys.stdin.readline() != "go\n":
    raise RuntimeError("Missing scenario start signal")
scenario.send_message(chat_id=chat["id"], sender_id=alice["id"], text="سلام hello")
deadline = time.monotonic() + 10
while True:
    history = scenario.history(chat["id"])
    if len(history) == 2:
        break
    if time.monotonic() >= deadline:
        raise TimeoutError("The real bot did not reply")
    time.sleep(0.01)
Path("scenario-state.txt").write_text("private scenario state")
print(
    json.dumps({"history": history, "snapshot": scenario.snapshot(), "events": scenario.events()})
)
