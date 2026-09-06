"""Independent programmable scenario consumer, with no world/database imports."""

import http.client
import json
import os
import socket
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

endpoint = urlsplit(os.environ["GRAMLAB_CONTROL_ENDPOINT"])
if endpoint.scheme != "http" or endpoint.hostname != "127.0.0.1":
    raise ValueError("Requires the explicit local control endpoint")
world_id = os.environ["GRAMLAB_WORLD_ID"]


def call(operation: str, **parameters: Any) -> Any:
    connection = http.client.HTTPConnection("127.0.0.1", endpoint.port, timeout=5)
    try:
        connection.request(
            "POST",
            "/v1/world",
            json.dumps(
                {
                    "schema": 1,
                    "world_id": world_id,
                    "operation": operation,
                    "parameters": parameters,
                }
            ),
            {
                "Content-Type": "application/json",
                "Authorization": "Bearer " + os.environ["GRAMLAB_CONTROL_CAPABILITY"],
            },
        )
        response = connection.getresponse()
        result = json.loads(response.read())
        if response.status != 200 or result["world_id"] != world_id or result["schema"] != 1:
            raise RuntimeError("World control rejected the scenario action")
        return result["result"]
    finally:
        connection.close()


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
alice = call("create_user", first_name="Sara", language_code="fa")
echo = call("create_user", first_name="Echo", username="gramlab_echo_bot", is_bot=True)
chat = call("open_private_chat", user_id=alice["id"], bot_id=echo["id"])
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
call("send_message", chat_id=chat["id"], sender_id=alice["id"], text="سلام hello")
deadline = time.monotonic() + 10
while True:
    history = call("history", chat_id=chat["id"])
    if len(history) == 2:
        break
    if time.monotonic() >= deadline:
        raise TimeoutError("The real bot did not reply")
    time.sleep(0.01)
Path("scenario-state.txt").write_text("private scenario state")
print(json.dumps({"history": history, "snapshot": call("snapshot"), "events": call("events")}))
