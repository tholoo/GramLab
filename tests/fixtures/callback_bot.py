"""Independent real Bot API consumer with a controlled interruption point for recovery tests."""

import http.client
import json
import os
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

if Path("/work/world").exists() or Path("/proc/1/root/work/world").exists():
    raise RuntimeError("Bot must not have filesystem access to the authoritative world")
launches = Path("launch-count")
launches.write_text(str(int(launches.read_text()) + 1 if launches.exists() else 1))

endpoint = urlsplit(os.environ["GRAMLAB_BOT_API"])
if endpoint.scheme != "http" or endpoint.hostname != "127.0.0.1" or endpoint.port is None:
    raise ValueError("This fixture requires its explicit local Bot API endpoint")
token = os.environ["GRAMLAB_BOT_TOKEN"]


def call(method: str, parameters: dict[str, Any]) -> Any:
    connection = http.client.HTTPConnection("127.0.0.1", endpoint.port, timeout=5)
    try:
        connection.request(
            "POST",
            f"/bot{token}/{method}",
            json.dumps(parameters),
            {"Content-Type": "application/json"},
        )
        response = connection.getresponse()
        body = json.loads(response.read())
        print(
            json.dumps({"method": method, "parameters": parameters, "response": body}), flush=True
        )
        if response.status != 200 or not body["ok"]:
            raise RuntimeError(f"Local Bot API rejected {method}")
        return body["result"]
    finally:
        connection.close()


call("getMe", {})
offset = 0
deadline = time.monotonic() + 30
while time.monotonic() < deadline:
    updates = call("getUpdates", {"offset": offset})
    for update in updates:
        if "message" in update:
            call(
                "sendMessage",
                {
                    "chat_id": update["message"]["chat"]["id"],
                    "text": "سلام hello — choose",
                    "reply_markup": {
                        "inline_keyboard": [[{"text": "تأیید ✓", "callback_data": "confirm"}]]
                    },
                },
            )
            offset = update["update_id"] + 1
            call("getUpdates", {"offset": offset})
            print(json.dumps({"event": "prompt_ready"}), flush=True)
        elif "callback_query" in update:
            callback = update["callback_query"]
            if callback["data"] != "confirm":
                raise RuntimeError("Unexpected action in callback scenario")
            print(json.dumps({"event": "callback_received", "id": callback["id"]}), flush=True)
            if os.environ.get("GRAMLAB_BOT_PAUSE_ON_CALLBACK") == "1":
                if sys.stdin.readline().strip() != "continue":
                    raise RuntimeError("Callback pause interrupted")
            call(
                "editMessageText",
                {
                    "chat_id": callback["message"]["chat"]["id"],
                    "message_id": callback["message"]["message_id"],
                    "text": "تأیید شد ✓",
                    "reply_markup": {"inline_keyboard": []},
                },
            )
            call("answerCallbackQuery", {"callback_query_id": callback["id"], "text": "انجام شد ✓"})
            call("getUpdates", {"offset": update["update_id"] + 1})
            print(json.dumps({"event": "completed"}), flush=True)
            raise SystemExit(0)
        else:
            raise RuntimeError("Unexpected update in callback scenario")
    time.sleep(0.1)
raise RuntimeError("Callback scenario timed out")
