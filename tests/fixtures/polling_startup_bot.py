"""Ordinary HTTP polling consumer with an explicit test-only startup barrier."""

import http.client
import json
import os
import sys
from typing import Any
from urllib.parse import urlencode, urlsplit

endpoint = urlsplit(os.environ["GRAMLAB_BOT_API"])
if endpoint.scheme != "http" or endpoint.hostname != "127.0.0.1":
    raise ValueError("This fixture requires its explicit local Bot API endpoint")
token = os.environ["GRAMLAB_BOT_TOKEN"]
transcript: list[dict[str, Any]] = []


def call(method: str, parameters: dict[str, Any], *, form: bool = False) -> Any:
    connection = http.client.HTTPConnection("127.0.0.1", endpoint.port, timeout=10)
    try:
        connection.request(
            "POST",
            f"/bot{token}/{method}",
            urlencode(parameters) if form else json.dumps(parameters),
            {"Content-Type": ("application/x-www-form-urlencoded" if form else "application/json")},
        )
        response = connection.getresponse()
        body = json.loads(response.read())
        transcript.append(
            {
                "method": method,
                "parameters": parameters,
                "status": response.status,
                "response": body,
            }
        )
        if response.status != 200 or not body["ok"]:
            raise RuntimeError(f"Local Bot API rejected {method}: HTTP {response.status}")
        return body["result"]
    finally:
        connection.close()


call("getMe", {})
call("deleteWebhook", {"drop_pending_updates": "true"}, form=True)
call("getUpdates", {"timeout": 0})
print(json.dumps({"phase": "ready", "transcript": transcript}), flush=True)
if sys.stdin.readline() != "continue\n":
    raise RuntimeError("Missing explicit scenario continuation")
updates = call("getUpdates", {"timeout": 0, "allowed_updates": ["message", "callback_query"]})
for update in updates:
    message = update["message"]
    call("sendMessage", {"chat_id": message["chat"]["id"], "text": "Ready: " + message["text"]})
if updates:
    call("getUpdates", {"offset": updates[-1]["update_id"] + 1})
print(json.dumps({"phase": "complete", "transcript": transcript}))
