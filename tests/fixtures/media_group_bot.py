"""Contained stdlib bot for the public atomic-media-group workflow."""

from __future__ import annotations

import http.client
import json
import os
import time
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

if Path("/work/world").exists() or Path("/proc/1/root/work/world").exists():
    raise RuntimeError("Album fixture bot can see the authoritative World")

_endpoint = urlsplit(os.environ["GRAMLAB_BOT_API"])
if _endpoint.scheme != "http" or _endpoint.hostname != "127.0.0.1" or _endpoint.port is None:
    raise ValueError("Album fixture requires the explicit loopback Bot API")
_token = os.environ["GRAMLAB_BOT_TOKEN"]


def call(
    method: str,
    parameters: dict[str, Any],
    *,
    files: dict[str, tuple[str, bytes, str]] | None = None,
    expect_ok: bool = True,
) -> dict[str, Any]:
    if files:
        boundary = "gramlab-" + uuid.uuid4().hex
        chunks: list[bytes] = []
        for name, value in parameters.items():
            encoded = (
                json.dumps(value, ensure_ascii=False) if isinstance(value, list) else str(value)
            )
            chunks.extend(
                [
                    (
                        f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n'
                    ).encode(),
                    encoded.encode(),
                    b"\r\n",
                ]
            )
        for name, (filename, payload, content_type) in files.items():
            chunks.extend(
                [
                    (
                        f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"; '
                        f'filename="{filename}"\r\nContent-Type: {content_type}\r\n\r\n'
                    ).encode(),
                    payload,
                    b"\r\n",
                ]
            )
        chunks.append(f"--{boundary}--\r\n".encode())
        body = b"".join(chunks)
        headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
    else:
        body = json.dumps(parameters, ensure_ascii=False).encode()
        headers = {"Content-Type": "application/json"}
    connection = http.client.HTTPConnection("127.0.0.1", _endpoint.port, timeout=15)
    try:
        connection.request("POST", f"/bot{_token}/{method}", body, headers)
        response = connection.getresponse()
        envelope = {"status": response.status, "body": json.loads(response.read())}
    finally:
        connection.close()
    succeeded = envelope["status"] == 200 and envelope["body"].get("ok") is True
    if succeeded != expect_ok:
        raise RuntimeError(f"Album Bot API call failed: {method}")
    return envelope


def next_text(offset: int, expected: str) -> tuple[int, dict[str, Any]]:
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        updates = call("getUpdates", {"offset": offset, "timeout": 10})["body"]["result"]
        if not updates:
            continue
        if len(updates) != 1 or updates[0].get("message", {}).get("text") != expected:
            raise RuntimeError("Album bot received an unexpected trigger")
        return updates[0]["update_id"] + 1, updates[0]
    raise RuntimeError("Album bot trigger deadline expired")


offset, start = next_text(0, "/start")
chat_id = start["message"]["chat"]["id"]
photo_media = [
    {
        "type": "photo",
        "media": "attach://photo_one",
        "caption": "Album 👩‍💻",
        "caption_entities": [
            {
                "type": "custom_emoji",
                "offset": 6,
                "length": 5,
                "custom_emoji_id": "1109",
            }
        ],
    },
    {"type": "photo", "media": "attach://photo_two"},
]
photos = call(
    "sendMediaGroup",
    {"chat_id": chat_id, "media": photo_media},
    files={
        "photo_one": ("photo-one.png", Path("photo-one.png").read_bytes(), "image/png"),
        "photo_two": ("photo-two.jpg", Path("photo-two.jpg").read_bytes(), "image/jpeg"),
    },
)
photo_message = photos["body"]["result"][0]
grouped_edit_rejections = [
    call(
        "editMessageCaption",
        {"chat_id": chat_id, "message_id": photo_message["message_id"], "caption": "reject"},
        expect_ok=False,
    ),
    call(
        "editMessageMedia",
        {
            "chat_id": chat_id,
            "message_id": photo_message["message_id"],
            "media": {"type": "photo", "media": photo_message["photo"][-1]["file_id"]},
        },
        expect_ok=False,
    ),
]
print(
    json.dumps(
        {
            "event": "photo_group",
            "trigger": start,
            "response": photos,
            "grouped_edit_rejections": grouped_edit_rejections,
        }
    ),
    flush=True,
)

offset, trigger = next_text(offset, "documents / اسناد")
document_media = [
    {"type": "document", "media": "attach://first", "caption": "First / نخست"},
    {"type": "document", "media": "attach://second", "caption": "Second / دوم"},
]
documents = call(
    "sendMediaGroup",
    {"chat_id": chat_id, "media": document_media},
    files={
        "first": ("first-album.txt", Path("first-document.bin").read_bytes(), "text/plain"),
        "second": (
            "second-album.pdf",
            Path("second-document.bin").read_bytes(),
            "application/pdf",
        ),
    },
)
print(
    json.dumps({"event": "document_group", "trigger": trigger, "response": documents}),
    flush=True,
)
