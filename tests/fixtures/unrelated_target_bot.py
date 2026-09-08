"""Contained real Bot API peer for unrelated rich-target edit acceptance."""

import http.client
import json
import os
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

if Path("/work/world").exists() or Path("/proc/1/root/work/world").exists():
    raise RuntimeError("Fixture bot can see the authoritative World")

endpoint = urlsplit(os.environ["GRAMLAB_BOT_API"])
if endpoint.scheme != "http" or endpoint.hostname != "127.0.0.1" or endpoint.port is None:
    raise ValueError("Requires the explicit loopback Bot API")
token = os.environ["GRAMLAB_BOT_TOKEN"]
records: list[dict[str, Any]] = []


def call(method: str, parameters: dict[str, Any]) -> Any:
    connection = http.client.HTTPConnection("127.0.0.1", endpoint.port, timeout=15)
    try:
        connection.request(
            "POST",
            f"/bot{token}/{method}",
            json.dumps(parameters, ensure_ascii=False).encode(),
            {"Content-Type": "application/json"},
        )
        response = connection.getresponse()
        body = json.loads(response.read())
    finally:
        connection.close()
    record = {"method": method, "parameters": parameters, "status": response.status, "body": body}
    records.append(record)
    if response.status != 200 or body.get("ok") is not True:
        raise RuntimeError(f"Local Bot API rejected {method}")
    return body["result"]


target_initial = {
    "skip_entity_detection": True,
    "blocks": [
        {"type": "paragraph", "text": "Stable target / هدف ثابت"},
        {
            "type": "buttons",
            "buttons": [
                {"text": "Confirm / تأیید", "callback_data": "stable:confirm"},
            ],
        },
    ],
}
target_edited = {
    "skip_entity_detection": True,
    "blocks": [
        {"type": "paragraph", "text": "Changed target / هدف تغییرکرده"},
        {
            "type": "buttons",
            "buttons": [
                {"text": "Changed / تغییر", "callback_data": "changed:confirm"},
            ],
        },
    ],
}
unrelated_initial = {
    "skip_entity_detection": True,
    "blocks": [{"type": "paragraph", "text": "Unrelated alpha / حالت الف"}],
}
unrelated_edited = {
    "skip_entity_detection": True,
    "blocks": [{"type": "paragraph", "text": "Unrelated bravo / حالت ب"}],
}

updates = call("getUpdates", {"timeout": 10})
if len(updates) != 1 or updates[0]["message"]["text"] != "publish stable target":
    raise RuntimeError("Expected the rendered-chat publication request")
rendered_chat_id = updates[0]["message"]["chat"]["id"]
target = call("sendRichMessage", {"chat_id": rendered_chat_id, "rich_message": target_initial})
unrelated = call(
    "sendRichMessage", {"chat_id": rendered_chat_id, "rich_message": unrelated_initial}
)
print(json.dumps({"event": "published", "target": target, "unrelated": unrelated}), flush=True)

offset = updates[0]["update_id"] + 1
callbacks: list[dict[str, Any]] = []
control_chat_id: int | None = None
deadline = time.monotonic() + 900
finished = False
while time.monotonic() < deadline and not finished:
    for update in call("getUpdates", {"offset": offset, "timeout": 10}):
        offset = update["update_id"] + 1
        if "callback_query" in update:
            callback = update["callback_query"]
            callbacks.append(callback)
            call(
                "answerCallbackQuery",
                {"callback_query_id": callback["id"], "text": "Confirmed / تأیید شد"},
            )
            continue
        message = update.get("message", {})
        text = message.get("text")
        chat_id = message.get("chat", {}).get("id")
        if text in {"edit unrelated", "edit target", "finish proof"}:
            if chat_id == rendered_chat_id:
                raise RuntimeError("Control commands must use the separate private chat")
            if control_chat_id is None:
                control_chat_id = chat_id
            if chat_id != control_chat_id:
                raise RuntimeError("Control chat changed during the proof")
        if text == "edit unrelated":
            call(
                "editMessageText",
                {
                    "chat_id": rendered_chat_id,
                    "message_id": unrelated["message_id"],
                    "rich_message": unrelated_edited,
                },
            )
            call("sendMessage", {"chat_id": control_chat_id, "text": "unrelated edit acknowledged"})
        elif text == "edit target":
            call(
                "editMessageText",
                {
                    "chat_id": rendered_chat_id,
                    "message_id": target["message_id"],
                    "rich_message": target_edited,
                },
            )
            call("sendMessage", {"chat_id": control_chat_id, "text": "target edit acknowledged"})
        elif text == "finish proof":
            finished = True

if not finished:
    raise RuntimeError("Unrelated-target scenario did not finish")
if call("getUpdates", {"offset": offset}) != []:
    raise RuntimeError("Unexpected update after proof completion")
print(
    json.dumps({"event": "finished", "callbacks": callbacks, "api": records}, ensure_ascii=False),
    flush=True,
)
