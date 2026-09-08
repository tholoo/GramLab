"""Contained bot for current-message Android interaction acceptance."""

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
token = os.environ["GRAMLAB_BOT_TOKEN"]


def call(method: str, parameters: dict[str, Any], *, photo: bytes | None = None) -> Any:
    if photo is None:
        body = json.dumps(parameters, ensure_ascii=False).encode()
        content_type = "application/json"
    else:
        boundary = "GramLabCurrentMessageBoundary"
        parts: list[bytes] = []
        for name, value in parameters.items():
            encoded = (
                json.dumps(value, ensure_ascii=False) if isinstance(value, dict) else str(value)
            )
            parts.append(
                (
                    f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n'
                    f"{encoded}\r\n"
                ).encode()
            )
        parts.extend(
            [
                (
                    f'--{boundary}\r\nContent-Disposition: form-data; name="photo"; '
                    'filename="current.png"\r\nContent-Type: image/png\r\n\r\n'
                ).encode()
                + photo
                + b"\r\n",
                f"--{boundary}--\r\n".encode(),
            ]
        )
        body = b"".join(parts)
        content_type = "multipart/form-data; boundary=" + boundary
    connection = http.client.HTTPConnection("127.0.0.1", endpoint.port, timeout=15)
    try:
        connection.request("POST", f"/bot{token}/{method}", body, {"Content-Type": content_type})
        response = connection.getresponse()
        result = json.loads(response.read())
    finally:
        connection.close()
    if response.status != 200 or result.get("ok") is not True:
        raise RuntimeError(f"Local Bot API rejected {method}")
    return result["result"]


updates = call("getUpdates", {"timeout": 10})
if len(updates) != 1 or updates[0]["message"]["text"] != "publish current content":
    raise RuntimeError("Expected the current-message publication request")
chat_id = updates[0]["message"]["chat"]["id"]
rich = call(
    "sendRichMessage",
    {
        "chat_id": chat_id,
        "rich_message": {
            "skip_entity_detection": True,
            "blocks": [
                {
                    "type": "photo",
                    "photo": {"type": "photo", "media": "attach://photo"},
                    "caption": {
                        "text": {"type": "bold", "text": "Current photo caption"},
                        "credit": {"type": "italic", "text": "Current photo credit"},
                    },
                }
            ],
        },
        "reply_markup": {
            "inline_keyboard": [[{"text": "Inspect", "callback_data": "inspect-current"}]]
        },
    },
    photo=Path("photo.png").read_bytes(),
)
call(
    "sendRichMessage",
    {
        "chat_id": chat_id,
        "rich_message": {
            "skip_entity_detection": True,
            "blocks": [
                {
                    "type": "paragraph",
                    "text": {
                        "type": "text_mention",
                        "text": "Mention Bot",
                        "user": {"id": 1},
                    },
                }
            ],
        },
    },
)
call(
    "sendMessage",
    {
        "chat_id": chat_id,
        "text": "Emoji 👩‍💻",
        "entities": [{"type": "custom_emoji", "offset": 6, "length": 5, "custom_emoji_id": "7"}],
    },
)
print(json.dumps({"event": "published", "rich": rich}), flush=True)

offset = updates[0]["update_id"] + 1
callback = None
reply = None
deadline = time.monotonic() + 300
while time.monotonic() < deadline and (callback is None or reply is None):
    incoming = call("getUpdates", {"offset": offset, "timeout": 10})
    for update in incoming:
        offset = update["update_id"] + 1
        if "callback_query" in update:
            callback = update["callback_query"]
            if callback["data"] != "inspect-current":
                raise RuntimeError("Unexpected callback data")
            call(
                "answerCallbackQuery",
                {"callback_query_id": callback["id"], "text": "Inspected"},
            )
        elif update.get("message", {}).get("text") == "reply after current content":
            reply = call(
                "sendMessage",
                {"chat_id": chat_id, "text": "Current content reply received"},
            )
if callback is None or reply is None:
    raise RuntimeError("Current-message interactions did not both arrive")
print(json.dumps({"event": "completed", "callback": callback, "reply": reply}), flush=True)
