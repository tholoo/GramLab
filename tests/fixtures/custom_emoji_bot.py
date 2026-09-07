"""Contained stdlib bot exercising static and animated custom emoji."""

import hashlib
import http.client
import json
import os
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urlsplit

if Path("/work/world").exists() or Path("/proc/1/root/work/world").exists():
    raise RuntimeError("Fixture bot can see the authoritative World")

endpoint = urlsplit(os.environ["GRAMLAB_BOT_API"])
if endpoint.scheme != "http" or endpoint.hostname != "127.0.0.1" or endpoint.port is None:
    raise ValueError("Requires the explicit loopback Bot API")
token = os.environ["GRAMLAB_BOT_TOKEN"]


def request(
    method: str,
    parameters: dict[str, Any],
    *,
    form: bool = False,
    expect_ok: bool = True,
) -> dict[str, Any]:
    body = (
        urlencode(
            {
                key: json.dumps(value, ensure_ascii=False)
                if isinstance(value, (dict, list))
                else value
                for key, value in parameters.items()
            }
        )
        if form
        else json.dumps(parameters, ensure_ascii=False)
    )
    encoding = "application/x-www-form-urlencoded" if form else "application/json"
    connection = http.client.HTTPConnection("127.0.0.1", endpoint.port, timeout=15)
    try:
        connection.request(
            "POST", f"/bot{token}/{method}", body.encode(), {"Content-Type": encoding}
        )
        response = connection.getresponse()
        result = {"status": response.status, "body": json.loads(response.read())}
    finally:
        connection.close()
    with Path("api.jsonl").open("a") as evidence:
        evidence.write(
            json.dumps(
                {"method": method, "encoding": "form" if form else "json", "response": result},
                ensure_ascii=False,
            )
            + "\n"
        )
    if expect_ok and (result["status"] != 200 or result["body"].get("ok") is not True):
        raise RuntimeError(f"Local Bot API rejected {method}: HTTP {result['status']}")
    return result


def call(method: str, parameters: dict[str, Any], *, form: bool = False) -> Any:
    return request(method, parameters, form=form)["body"]["result"]


def download(sticker: dict[str, Any], key: str, source: str) -> dict[str, Any]:
    item = sticker if key == "main" else sticker["thumbnail"]
    file = call("getFile", {"file_id": item["file_id"]})
    connection = http.client.HTTPConnection("127.0.0.1", endpoint.port, timeout=15)
    try:
        connection.request("GET", f"/file/bot{token}/{file['file_path']}")
        response = connection.getresponse()
        payload = response.read()
        status = response.status
        content_type = response.getheader("Content-Type")
    finally:
        connection.close()
    expected = Path(source).read_bytes()
    if status != 200 or payload != expected:
        raise RuntimeError("Custom emoji download differed from the registered bytes")
    return {
        "get_file": file,
        "content_type": content_type,
        "size": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def emoji_leaf(identifier: str, alternative: str) -> dict[str, Any]:
    return {
        "type": "custom_emoji",
        "custom_emoji_id": identifier,
        "alternative_text": alternative,
    }


def rich(identifier: str) -> dict[str, Any]:
    return {
        "skip_entity_detection": True,
        "blocks": [
            {"type": "paragraph", "text": ["Rich ", emoji_leaf(identifier, "different")]},
            {
                "type": "buttons",
                "buttons": [
                    {
                        "text": ["Badge ", emoji_leaf(identifier, "")],
                        "disabled": {},
                    }
                ],
            },
        ],
    }


updates = call("getUpdates", {})
if len(updates) != 1 or updates[0].get("message", {}).get("text") != "سلام 👩‍💻":
    raise RuntimeError("Expected one static custom-emoji update")

stickers = call("getCustomEmojiStickers", {"custom_emoji_ids": ["1109", "1", "1109"]})
if [item["custom_emoji_id"] for item in stickers] != ["1", "1109"]:
    raise RuntimeError("Custom emoji lookup did not deduplicate and sort")
downloads = {
    "static_main": download(stickers[0], "main", "emoji-static.webp"),
    "static_thumbnail": download(stickers[0], "thumbnail", "emoji-thumbnail.webp"),
    "animated_main": download(stickers[1], "main", "emoji-animated.webm"),
    "animated_thumbnail": download(stickers[1], "thumbnail", "emoji-thumbnail.webp"),
}
ordinary_parameters = {
    "chat_id": 1,
    "text": "Ordinary 👩‍💻",
    "entities": [{"type": "custom_emoji", "offset": 9, "length": 5, "custom_emoji_id": 1}],
    "reply_markup": {
        "inline_keyboard": [[{"text": "Animate / متحرک", "callback_data": "emoji:animate"}]]
    },
}
ordinary = call("sendMessage", ordinary_parameters)
rich_message = call("sendRichMessage", {"chat_id": 1, "rich_message": rich("1")})
noop = request(
    "editMessageText",
    {
        "chat_id": 1,
        "message_id": rich_message["message_id"],
        "rich_message": rich_message["rich_message"] | {"skip_entity_detection": True},
    },
    form=True,
    expect_ok=False,
)
print(
    json.dumps(
        {
            "event": "initial",
            "update": updates[0],
            "stickers": stickers,
            "downloads": downloads,
            "ordinary": ordinary,
            "rich": rich_message,
            "noop": noop,
        },
        ensure_ascii=False,
    ),
    flush=True,
)

if sys.stdin.readline() != "next\n":
    raise RuntimeError("Missing custom emoji callback boundary")
incoming = call("getUpdates", {"offset": updates[0]["update_id"] + 1})
if len(incoming) != 1 or incoming[0].get("callback_query", {}).get("data") != "emoji:animate":
    raise RuntimeError("Expected exactly one custom emoji callback")
callback = incoming[0]["callback_query"]
answer = call(
    "answerCallbackQuery",
    {"callback_query_id": callback["id"], "text": "Animated / متحرک شد"},
)
ordinary_edited = call(
    "editMessageText",
    {
        "chat_id": 1,
        "message_id": ordinary["message_id"],
        "text": ordinary["text"],
        "entities": [{"type": "custom_emoji", "offset": 9, "length": 5, "custom_emoji_id": "1109"}],
    },
)
rich_edited = call(
    "editMessageText",
    {
        "chat_id": 1,
        "message_id": rich_message["message_id"],
        "rich_message": rich("1109"),
    },
    form=True,
)
pending = call("getUpdates", {"offset": incoming[0]["update_id"] + 1})
if pending:
    raise RuntimeError("Unexpected pending bot update")
print(
    json.dumps(
        {
            "event": "edited",
            "update": incoming[0],
            "answer": answer,
            "ordinary": ordinary_edited,
            "rich": rich_edited,
        },
        ensure_ascii=False,
    ),
    flush=True,
)
