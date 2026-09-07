"""Independent local HTTP bot for the explicitly selected rich-action input experiment."""

import http.client
import json
import os
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

if Path("/work/world").exists() or Path("/proc/1/root/work/world").exists():
    raise RuntimeError("Fixture bot can see the authoritative world")
endpoint = urlsplit(os.environ["GRAMLAB_BOT_API"])
if endpoint.scheme != "http" or endpoint.hostname != "127.0.0.1" or endpoint.port is None:
    raise ValueError("Requires the explicit loopback Bot API")
token = os.environ["GRAMLAB_BOT_TOKEN"]


def call(method: str, parameters: dict[str, Any]) -> Any:
    connection = http.client.HTTPConnection("127.0.0.1", endpoint.port, timeout=10)
    try:
        connection.request(
            "POST",
            f"/bot{token}/{method}",
            json.dumps(parameters),
            {"Content-Type": "application/json"},
        )
        response = connection.getresponse()
        body = json.loads(response.read())
        with Path("api.jsonl").open("a") as evidence:
            evidence.write(
                json.dumps({"method": method, "parameters": parameters, "response": body}) + "\n"
            )
        if response.status != 200 or body.get("ok") is not True:
            raise RuntimeError(f"Local rich-action API rejected {method}")
        return body["result"]
    finally:
        connection.close()


updates = call("getUpdates", {})
if len(updates) != 1 or updates[0]["message"]["text"] != "Show rich actions":
    raise RuntimeError("Expected the single scenario request")
chat = updates[0]["message"]["chat"]["id"]
initial = call(
    "sendRichMessage",
    {
        "chat_id": chat,
        "rich_message": {
            "blocks": [
                {"type": "buttons", "buttons": [{"text": "Row action", "callback_data": "row:1"}]},
                {
                    "type": "paragraph",
                    "text": [
                        "Choose: ",
                        {
                            "type": "button",
                            "button": {"text": "Inline action", "callback_data": "inline:1"},
                        },
                    ],
                },
            ],
            "skip_entity_detection": True,
        },
    },
)
offset = updates[0]["update_id"] + 1
if call("getUpdates", {"offset": offset}) != []:
    raise RuntimeError("Unexpected update before rich actions")
print(json.dumps({"event": "ready", "initial": initial}), flush=True)
count = 0
deadline = time.monotonic() + 240
while time.monotonic() < deadline:
    updates = call("getUpdates", {"offset": offset, "timeout": 5})
    if not updates:
        continue
    if len(updates) != 1 or "callback_query" not in updates[0]:
        raise RuntimeError("Expected exactly one native action at a time")
    update = updates[0]
    callback = update["callback_query"]
    if count >= 2 or callback["data"] != ("row:1", "inline:1")[count]:
        raise RuntimeError("Unexpected or extra rich callback")
    if callback["message"] != initial:
        raise RuntimeError("Callback did not retain the actual initial message")
    answer = call("answerCallbackQuery", {"callback_query_id": callback["id"]})
    edited = None
    if count == 1:
        edited = call(
            "editMessageText",
            {
                "chat_id": chat,
                "message_id": initial["message_id"],
                "rich_message": {
                    "blocks": [{"type": "paragraph", "text": "Rich actions complete"}],
                    "skip_entity_detection": True,
                },
            },
        )
    offset = update["update_id"] + 1
    if call("getUpdates", {"offset": offset}) != []:
        raise RuntimeError("Unexpected update after rich callback")
    print(
        json.dumps({"event": "action", "update": update, "answer": answer, "edited": edited}),
        flush=True,
    )
    count += 1
    if count == 2:
        break
else:
    raise RuntimeError("Rich action fixture timed out")
