"""Real bot which edits an older reply after the scenario stops its Android observer."""

import http.client
import json
import os
import sys
from typing import Any
from urllib.parse import urlsplit

endpoint = urlsplit(os.environ["GRAMLAB_BOT_API"])
if endpoint.scheme != "http" or endpoint.hostname != "127.0.0.1":
    raise ValueError("Requires the explicit local Bot API endpoint")
token = os.environ["GRAMLAB_BOT_TOKEN"]


def call(method: str, parameters: dict[str, Any]) -> Any:
    connection = http.client.HTTPConnection("127.0.0.1", endpoint.port, timeout=35)
    try:
        connection.request(
            "POST",
            f"/bot{token}/{method}",
            json.dumps(parameters),
            {"Content-Type": "application/json"},
        )
        response = connection.getresponse()
        body = json.loads(response.read())
        if response.status != 200 or not body["ok"]:
            raise RuntimeError(f"Local Bot API rejected {method}")
        return body["result"]
    finally:
        connection.close()


updates = call("getUpdates", {"timeout": 30})
if len(updates) != 1:
    raise RuntimeError("Expected one virtual-user request")
chat = updates[0]["message"]["chat"]["id"]
older = call(
    "sendMessage",
    {
        "chat_id": chat,
        "text": "سلام — original",
        "reply_markup": {
            "inline_keyboard": [[{"text": "Original action", "callback_data": "original"}]]
        },
    },
)
latest = call("sendMessage", {"chat_id": chat, "text": "Previously newest"})
print(json.dumps([older, latest]), flush=True)
if sys.stdin.readline() != "edit\n":
    raise RuntimeError("Missing scenario edit signal")
edited = call(
    "editMessageText",
    {
        "chat_id": chat,
        "message_id": older["message_id"],
        "text": "سلام — corrected 😀",
        "entities": [{"type": "bold", "offset": 7, "length": 9}],
    },
)
newest = call("sendMessage", {"chat_id": chat, "text": "Sent while away"})
if call("getUpdates", {"offset": updates[0]["update_id"] + 1}) != []:
    raise RuntimeError("Unexpected pending update")
print(json.dumps([edited, newest]), flush=True)
