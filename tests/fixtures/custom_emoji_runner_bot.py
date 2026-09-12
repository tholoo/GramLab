"""Contained Bot API peer for the public bridge-v5 custom-emoji workflow."""

from __future__ import annotations

import hashlib
import http.client
import json
import os
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urlsplit

if Path("/work/world").exists() or Path("/proc/1/root/work/world").exists():
    raise RuntimeError("Fixture bot can see the authoritative World")

endpoint = urlsplit(os.environ["GRAMLAB_BOT_API"])
if endpoint.scheme != "http" or endpoint.hostname != "127.0.0.1" or endpoint.port is None:
    raise ValueError("Requires the explicit loopback Bot API")
token = os.environ["GRAMLAB_BOT_TOKEN"]
records: list[dict[str, Any]] = []


def request(method: str, parameters: dict[str, Any], *, form: bool = False) -> Any:
    if form:
        body = urlencode(
            {
                key: json.dumps(value, ensure_ascii=False)
                if isinstance(value, (dict, list))
                else value
                for key, value in parameters.items()
            }
        ).encode()
        content_type = "application/x-www-form-urlencoded"
    else:
        body = json.dumps(parameters, ensure_ascii=False).encode()
        content_type = "application/json"
    connection = http.client.HTTPConnection("127.0.0.1", endpoint.port, timeout=15)
    try:
        connection.request(
            "POST",
            f"/bot{token}/{method}",
            body,
            {"Content-Type": content_type},
        )
        response = connection.getresponse()
        status = response.status
        decoded = json.loads(response.read())
    finally:
        connection.close()
    record = {
        "method": method,
        "encoding": "form" if form else "json",
        "parameters": parameters,
        "status": status,
        "body": decoded,
    }
    records.append(record)
    if status != 200 or decoded.get("ok") is not True:
        raise RuntimeError(f"Local Bot API rejected {method}")
    return decoded["result"]


def download(sticker: dict[str, Any], member: str, source: str) -> dict[str, Any]:
    selected = sticker if member == "main" else sticker["thumbnail"]
    file = request("getFile", {"file_id": selected["file_id"]})
    connection = http.client.HTTPConnection("127.0.0.1", endpoint.port, timeout=15)
    try:
        connection.request("GET", f"/file/bot{token}/{file['file_path']}")
        response = connection.getresponse()
        payload = response.read()
        observed = {
            "status": response.status,
            "content_type": response.getheader("Content-Type"),
            "content_length": response.getheader("Content-Length"),
            "cache_control": response.getheader("Cache-Control"),
            "size": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
    finally:
        connection.close()
    expected = Path(source).read_bytes()
    if observed["status"] != 200 or payload != expected:
        raise RuntimeError("Custom emoji download differed from registered bytes")
    return {"get_file": file, **observed}


def emoji(identifier: str, alternative: str) -> dict[str, Any]:
    return {
        "type": "custom_emoji",
        "custom_emoji_id": identifier,
        "alternative_text": alternative,
    }


def rich(identifier: str) -> dict[str, Any]:
    return {
        "skip_entity_detection": True,
        "blocks": [
            {"type": "paragraph", "text": ["Rich / غنی ", emoji(identifier, "RICH-ALT")]},
            {
                "type": "buttons",
                "buttons": [
                    {
                        "text": ["Badge / نشان ", emoji(identifier, "BUTTON-ALT")],
                        "disabled": {},
                    }
                ],
            },
        ],
    }


deadline = time.monotonic() + 30
updates: list[dict[str, Any]] = []
while not updates and time.monotonic() < deadline:
    updates = request("getUpdates", {"timeout": 10})
if len(updates) != 1 or updates[0].get("message", {}).get("text") != "Incoming 👩‍💻":
    raise RuntimeError("Expected one incoming custom-emoji update")

stickers = request("getCustomEmojiStickers", {"custom_emoji_ids": ["1109", "1", "1109"]})
if [item["custom_emoji_id"] for item in stickers] != ["1", "1109"]:
    raise RuntimeError("Custom emoji lookup did not deduplicate and sort")
downloads = {
    "static_main": download(stickers[0], "main", "emoji-static.webp"),
    "static_thumbnail": download(stickers[0], "thumbnail", "emoji-thumbnail.webp"),
    "animated_main": download(stickers[1], "main", "emoji-animated.webm"),
    "animated_thumbnail": download(stickers[1], "thumbnail", "emoji-thumbnail.webp"),
}
chat_id = updates[0]["message"]["chat"]["id"]
ordinary = request(
    "sendMessage",
    {
        "chat_id": chat_id,
        "text": "Ordinary 👩‍💻",
        "entities": [{"type": "custom_emoji", "offset": 9, "length": 5, "custom_emoji_id": 1}],
        "reply_markup": {
            "inline_keyboard": [[{"text": "Animate / متحرک", "callback_data": "emoji:animate"}]]
        },
    },
)
rich_message = request("sendRichMessage", {"chat_id": chat_id, "rich_message": rich("1")})
print(
    json.dumps(
        {
            "event": "initial",
            "update": updates[0],
            "stickers": stickers,
            "downloads": downloads,
            "ordinary": ordinary,
            "rich": rich_message,
        },
        ensure_ascii=False,
    ),
    flush=True,
)

offset = updates[0]["update_id"] + 1
deadline = time.monotonic() + 180
callback_update: dict[str, Any] | None = None
while callback_update is None and time.monotonic() < deadline:
    incoming = request("getUpdates", {"offset": offset, "timeout": 10})
    if not incoming:
        continue
    if len(incoming) != 1 or incoming[0].get("callback_query", {}).get("data") != "emoji:animate":
        raise RuntimeError("Expected one custom-emoji callback")
    callback_update = incoming[0]
if callback_update is None:
    raise RuntimeError("Custom-emoji callback did not arrive")
callback = callback_update["callback_query"]
if callback["message"] != ordinary:
    raise RuntimeError("Custom-emoji callback lost its frozen static message")

answer = request(
    "answerCallbackQuery",
    {"callback_query_id": callback["id"], "text": "Animated / متحرک شد"},
)
ordinary_edited = request(
    "editMessageText",
    {
        "chat_id": chat_id,
        "message_id": ordinary["message_id"],
        "text": ordinary["text"],
        "entities": [
            {
                "type": "custom_emoji",
                "offset": 9,
                "length": 5,
                "custom_emoji_id": "1109",
            }
        ],
    },
)
rich_edited = request(
    "editMessageText",
    {
        "chat_id": chat_id,
        "message_id": rich_message["message_id"],
        "rich_message": rich("1109"),
    },
    form=True,
)
pending = request("getUpdates", {"offset": callback_update["update_id"] + 1})
if pending:
    raise RuntimeError("Unexpected update after custom-emoji edit")
print(
    json.dumps(
        {
            "event": "edited",
            "update": callback_update,
            "answer": answer,
            "ordinary": ordinary_edited,
            "rich": rich_edited,
            "api": records,
        },
        ensure_ascii=False,
    ),
    flush=True,
)
