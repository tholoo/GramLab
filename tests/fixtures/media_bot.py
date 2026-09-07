"""Contained stdlib bot exercising the complete first local photo profile."""

import hashlib
import http.client
import json
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

if Path("/work/world").exists() or Path("/proc/1/root/work/world").exists():
    raise RuntimeError("Fixture bot can see the authoritative World")

endpoint = urlsplit(os.environ["GRAMLAB_BOT_API"])
if endpoint.scheme != "http" or endpoint.hostname != "127.0.0.1" or endpoint.port is None:
    raise ValueError("Requires the explicit loopback Bot API")
token = os.environ["GRAMLAB_BOT_TOKEN"]
foreign_token = os.environ["GRAMLAB_FOREIGN_BOT_TOKEN"]
scene = json.loads(os.environ["GRAMLAB_MEDIA_SCENE"])
operation_counts: dict[str, int] = {}


def request(
    method: str,
    parameters: dict[str, Any],
    *,
    files: dict[str, tuple[str, bytes, str]] | None = None,
    use_token: str = token,
    expect_ok: bool = True,
) -> dict[str, Any]:
    headers: dict[str, str]
    if files:
        boundary = "gramlab-" + uuid.uuid4().hex
        chunks: list[bytes] = []
        for name, value in parameters.items():
            encoded = (
                json.dumps(value, ensure_ascii=False)
                if isinstance(value, (dict, list))
                else str(value)
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
    connection = http.client.HTTPConnection("127.0.0.1", endpoint.port, timeout=15)
    try:
        connection.request("POST", f"/bot{use_token}/{method}", body, headers)
        response = connection.getresponse()
        result = {"status": response.status, "body": json.loads(response.read())}
    finally:
        connection.close()
    with Path("api.jsonl").open("a") as evidence:
        operation_counts[method] = operation_counts.get(method, 0) + 1
        evidence.write(
            json.dumps(
                {
                    "operation": f"{method}:{operation_counts[method]}",
                    "method": method,
                    "response": result,
                },
                ensure_ascii=False,
            )
            + "\n"
        )
    if (result["status"] == 200 and result["body"].get("ok") is True) != expect_ok:
        raise RuntimeError(f"Unexpected local Bot API result for {method}")
    return result


def download(file_id: str, expected: bytes) -> dict[str, Any]:
    file_result = request("getFile", {"file_id": file_id})["body"]["result"]
    if request("getFile", {"file_id": file_id})["body"]["result"] != file_result:
        raise RuntimeError("Repeated getFile did not preserve the generated path")
    connection = http.client.HTTPConnection("127.0.0.1", endpoint.port, timeout=15)
    try:
        connection.request("GET", f"/file/bot{token}/{file_result['file_path']}")
        response = connection.getresponse()
        payload = response.read()
    finally:
        connection.close()
    if response.status != 200 or payload != expected:
        raise RuntimeError("Downloaded photo differs from the uploaded original")
    return {
        "get_file": file_result,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size": len(payload),
    }


png = Path("photo-square-16x16.png").read_bytes()
jpeg = Path("photo-quadrants-64x48.jpg").read_bytes()
updates = request("getUpdates", {})["body"]["result"]
if len(updates) != 1 or updates[0]["message"]["text"] != "Show local photos":
    raise RuntimeError("Expected the one media scenario request")
chat = updates[0]["message"]["chat"]["id"]
keyboard = {
    "inline_keyboard": [[{"text": "Inspect / بررسی", "callback_data": scene["callback_data"]}]]
}

ordinary = request(
    "sendPhoto",
    {
        "chat_id": chat,
        "photo": "attach://photo",
        "caption": scene["ordinary_caption"],
        "caption_entities": scene["ordinary_entities"],
    },
    files={"photo": ("../نام تصویر.png", png, "application/octet-stream")},
)["body"]["result"]
png_id = ordinary["photo"][0]["file_id"]
ordinary_reuse = request("sendPhoto", {"chat_id": chat, "photo": png_id})["body"]["result"]
rich = request(
    "sendRichMessage",
    {
        "chat_id": chat,
        "rich_message": {
            "blocks": [
                {
                    "type": "photo",
                    "photo": {"type": "photo", "media": "attach://image"},
                    "caption": scene["rich_initial_caption"],
                }
            ],
            "skip_entity_detection": True,
        },
        "reply_markup": keyboard,
    },
    files={"image": ("jpeg-with-untrusted-name.png", jpeg, "image/png")},
)["body"]["result"]
jpeg_id = rich["rich_message"]["blocks"][0]["photo"][0]["file_id"]
rich_reuse = request(
    "sendRichMessage",
    {
        "chat_id": chat,
        "rich_message": {
            "blocks": [{"type": "photo", "photo": {"type": "photo", "media": jpeg_id}}],
            "skip_entity_detection": True,
        },
    },
)["body"]["result"]
malformed = request(
    "sendPhoto",
    {"chat_id": chat, "photo": "attach://broken"},
    files={"broken": ("broken.jpg", jpeg[:-31], "image/jpeg")},
    expect_ok=False,
)
foreign = request(
    "sendPhoto", {"chat_id": 2, "photo": png_id}, use_token=foreign_token, expect_ok=False
)
published = {
    "ordinary": ordinary,
    "ordinary_reuse": ordinary_reuse,
    "rich": rich,
    "rich_reuse": rich_reuse,
    "png_download": download(png_id, png),
    "jpeg_download": download(jpeg_id, jpeg),
    "malformed": malformed,
    "foreign": foreign,
}
print(json.dumps({"event": "published", "value": published}, ensure_ascii=False), flush=True)

if sys.stdin.readline() != "callback\n":
    raise RuntimeError("Missing media callback signal")
offset = updates[0]["update_id"] + 1
deadline = time.monotonic() + 20
while time.monotonic() < deadline:
    incoming = request("getUpdates", {"offset": offset, "timeout": 10})["body"]["result"]
    if not incoming:
        continue
    if (
        len(incoming) != 1
        or incoming[0].get("callback_query", {}).get("data") != scene["callback_data"]
    ):
        raise RuntimeError("Expected exactly one media callback")
    callback = incoming[0]["callback_query"]
    answer = request(
        "answerCallbackQuery",
        {"callback_query_id": callback["id"], "text": "دریافت شد / Received"},
    )["body"]["result"]
    offset = incoming[0]["update_id"] + 1
    print(
        json.dumps(
            {"event": "callback", "update": incoming[0], "answer": answer}, ensure_ascii=False
        ),
        flush=True,
    )
    break
else:
    raise RuntimeError("Media callback did not arrive")

if sys.stdin.readline() != "edit\n":
    raise RuntimeError("Missing media edit signal")
edited = request(
    "editMessageText",
    {
        "chat_id": chat,
        "message_id": rich["message_id"],
        "rich_message": {
            "is_rtl": True,
            "blocks": [
                {
                    "type": "photo",
                    "photo": {"type": "photo", "media": png_id},
                    "caption": scene["rich_edited_caption"],
                }
            ],
            "skip_entity_detection": True,
        },
    },
)["body"]["result"]
if request("getUpdates", {"offset": offset})["body"]["result"] != []:
    raise RuntimeError("Unexpected pending update after media edit")
print(json.dumps({"event": "edited", "value": edited}, ensure_ascii=False), flush=True)
