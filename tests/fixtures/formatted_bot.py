"""Real Bot API consumer which edits formatting while preserving the message text."""

import http.client
import json
import os
import sys
from typing import Any
from urllib.parse import urlencode, urlsplit

endpoint = urlsplit(os.environ["GRAMLAB_BOT_API"])
if endpoint.scheme != "http" or endpoint.hostname != "127.0.0.1":
    raise ValueError("Requires the explicit local Bot API endpoint")
token = os.environ["GRAMLAB_BOT_TOKEN"]
scene = json.loads(os.environ["GRAMLAB_FORMATTING"])


def call(method: str, parameters: dict[str, Any]) -> Any:
    connection = http.client.HTTPConnection("127.0.0.1", endpoint.port, timeout=35)
    try:
        connection.request(
            "POST",
            f"/bot{token}/{method}",
            urlencode(
                {
                    name: json.dumps(value, ensure_ascii=False)
                    if isinstance(value, (dict, list))
                    else value
                    for name, value in parameters.items()
                }
            ),
            {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"},
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
plain = call("sendMessage", {"chat_id": chat, "text": scene["text"]})
print(json.dumps(plain), flush=True)
if sys.stdin.readline() != "format\n":
    raise RuntimeError("Missing scenario formatting signal")
formatted = call("editMessageText", {"chat_id": chat, "message_id": plain["message_id"], **scene})
if call("getUpdates", {"offset": updates[0]["update_id"] + 1}) != []:
    raise RuntimeError("Unexpected pending update")
print(json.dumps(formatted), flush=True)
