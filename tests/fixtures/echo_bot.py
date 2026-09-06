"""A real, framework-independent Bot API consumer; no GramLab implementation imports."""

import http.client
import json
import os
from typing import Any
from urllib.parse import urlsplit

endpoint = urlsplit(os.environ["GRAMLAB_BOT_API"])
if endpoint.scheme != "http" or endpoint.hostname != "127.0.0.1":
    raise ValueError("This fixture requires its explicit local Bot API endpoint")
token = os.environ["GRAMLAB_BOT_TOKEN"]
transcript: list[dict[str, Any]] = []


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
        transcript.append({"method": method, "parameters": parameters, "response": body})
        if response.status != 200 or not body["ok"]:
            raise RuntimeError(f"Local Bot API rejected {method}")
        return body["result"]
    finally:
        connection.close()


call("getMe", {})
polling: dict[str, Any] = {"timeout": 30}
if "GRAMLAB_BOT_OFFSET" in os.environ:
    polling["offset"] = int(os.environ["GRAMLAB_BOT_OFFSET"])
updates = call("getUpdates", polling)
for update in updates:
    message = update["message"]
    call("sendMessage", {"chat_id": message["chat"]["id"], "text": "Echo: " + message["text"]})
if updates:
    call("getUpdates", {"offset": updates[-1]["update_id"] + 1})
print(json.dumps(transcript))
