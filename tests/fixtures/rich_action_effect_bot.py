"""Real HTTP bot for original copy/disabled effects; clipboard state belongs to Android."""

import http.client
import json
import os
import sys
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
            raise RuntimeError(f"Local rich-effect API rejected {method}")
        return body["result"]
    finally:
        connection.close()


updates = call("getUpdates", {})
if len(updates) != 1 or updates[0]["message"]["text"] != "Show rich effects":
    raise RuntimeError("Expected the single scenario request")
initial = call(
    "sendRichMessage",
    {
        "chat_id": updates[0]["message"]["chat"]["id"],
        "rich_message": {
            "blocks": [
                {
                    "type": "buttons",
                    "buttons": [{"text": "Copy code", "copy_text": {"text": "GramLab-copy-73Q9"}}],
                },
                {
                    "type": "paragraph",
                    "text": [
                        "Choose: ",
                        {"type": "button", "button": {"text": "Unavailable", "disabled": {}}},
                    ],
                },
            ],
            "skip_entity_detection": True,
        },
    },
)
offset = updates[0]["update_id"] + 1
if call("getUpdates", {"offset": offset}) != []:
    raise RuntimeError("Unexpected update before rich effects")
print(json.dumps({"event": "ready", "initial": initial}), flush=True)
# The supervisor bounds lifetime; the controller releases this barrier after actual guest work.
if sys.stdin.readline() != "finish\n":
    raise RuntimeError("Missing explicit fixture completion")
if call("getUpdates", {"offset": offset}) != []:
    raise RuntimeError("Copy or disabled input unexpectedly produced a bot update")
print(json.dumps({"event": "finished", "updates": []}), flush=True)
