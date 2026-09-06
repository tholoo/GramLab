"""Ordinary HTTP Bot API consumer, using only Python's standard library."""

import http.client
import json
import os
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

endpoint = urlsplit(os.environ["GRAMLAB_BOT_API"])
if endpoint.scheme != "http" or endpoint.hostname != "127.0.0.1" or endpoint.port is None:
    raise ValueError("An explicit local Bot API endpoint is required")
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
            raise RuntimeError(f"Bot API rejected {method}")
        return body["result"]
    finally:
        connection.close()


state_path = Path("state.json")
state = (
    json.loads(state_path.read_text()) if state_path.exists() else {"generation": 0, "offset": 0}
)
state["generation"] += 1
state_path.write_text(json.dumps(state))
print("Bot generation", state["generation"], flush=True)
while True:
    for update in call("getUpdates", {"offset": state["offset"], "timeout": 30}):
        if "message" in update:
            message = update["message"]
            # Commit the subscription before exposing the keyboard as scenario readiness.
            call(
                "getUpdates",
                {"offset": update["update_id"] + 1, "allowed_updates": ["callback_query"]},
            )
            call(
                "sendMessage",
                {
                    "chat_id": message["chat"]["id"],
                    "text": "Choose recovery — بازیابی",
                    "reply_markup": {
                        "inline_keyboard": [[{"text": "Recover", "callback_data": "recover"}]]
                    },
                },
            )
        else:
            callback = update["callback_query"]
            if update["update_id"] != 2:
                raise RuntimeError("Filtered messages consumed update identifiers")
            if state["generation"] == 1:
                Path("received.json").write_text(json.dumps(callback))
                call(
                    "sendMessage",
                    {
                        "chat_id": callback["message"]["chat"]["id"],
                        "text": "Callback received; restart me",
                    },
                )
                while True:
                    time.sleep(60)
            if json.loads(Path("received.json").read_text()) != callback:
                raise RuntimeError("The pending callback changed across restart")
            call(
                "editMessageText",
                {
                    "chat_id": callback["message"]["chat"]["id"],
                    "message_id": callback["message"]["message_id"],
                    "text": "Recovered — بازیابی شد ✓",
                },
            )
            call("answerCallbackQuery", {"callback_query_id": callback["id"], "text": "Recovered"})
        state["offset"] = update["update_id"] + 1
        state_path.write_text(json.dumps(state))
