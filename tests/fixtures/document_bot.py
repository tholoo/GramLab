"""Contained stdlib bot exercising the explicit forced-document lifecycle."""

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
scene = json.loads(os.environ["GRAMLAB_DOCUMENT_SCENE"])
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
    operation_counts[method] = operation_counts.get(method, 0) + 1
    with Path("api.jsonl").open("a") as evidence:
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
    first = request("getFile", {"file_id": file_id})["body"]["result"]
    second = request("getFile", {"file_id": file_id})["body"]["result"]
    if first != second:
        raise RuntimeError("Repeated getFile changed the document path")
    connection = http.client.HTTPConnection("127.0.0.1", endpoint.port, timeout=15)
    try:
        connection.request("GET", f"/file/bot{token}/{first['file_path']}")
        response = connection.getresponse()
        payload = response.read()
        headers = dict(response.getheaders())
    finally:
        connection.close()
    if response.status != 200 or payload != expected:
        raise RuntimeError("Downloaded document differs from its upload")
    return {
        "get_file": first,
        "status": response.status,
        "content_type": headers.get("Content-Type"),
        "content_length": headers.get("Content-Length"),
        "cache_control": headers.get("Cache-Control"),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size": len(payload),
    }


payload = Path("ordinary-document.bin").read_bytes()
updates = request("getUpdates", {})["body"]["result"]
if len(updates) != 1 or updates[0]["message"]["text"] != scene["request_text"]:
    raise RuntimeError("Expected one ordinary-document scenario request")
chat = updates[0]["message"]["chat"]["id"]
keyboard = {
    "inline_keyboard": [[{"text": scene["button_text"], "callback_data": scene["callback_data"]}]]
}
sent = request(
    "sendDocument",
    {
        "chat_id": chat,
        "document": "attach://upload",
        "disable_content_type_detection": "true",
        "caption": scene["caption"],
        "caption_entities": scene["caption_entities"],
        "reply_markup": keyboard,
    },
    files={
        "upload": (scene["upload_name"], payload, "application/octet-stream"),
    },
)["body"]["result"]
file_id = sent["document"]["file_id"]
downloaded = download(file_id, payload)
cross_kind = request("sendPhoto", {"chat_id": chat, "photo": file_id}, expect_ok=False)
foreign = request(
    "sendDocument",
    {"chat_id": chat, "document": file_id},
    use_token=foreign_token,
    expect_ok=False,
)
print(
    json.dumps(
        {
            "event": "published",
            "value": {
                "sent": sent,
                "download": downloaded,
                "cross_kind": cross_kind,
                "foreign": foreign,
            },
        },
        ensure_ascii=False,
    ),
    flush=True,
)

if sys.stdin.readline() != "callback\n":
    raise RuntimeError("Missing document callback signal")
offset = updates[0]["update_id"] + 1
deadline = time.monotonic() + 20
while time.monotonic() < deadline:
    incoming = request("getUpdates", {"offset": offset, "timeout": 10})["body"]["result"]
    if not incoming:
        continue
    callback = incoming[0].get("callback_query", {})
    if len(incoming) != 1 or callback.get("data") != scene["callback_data"]:
        raise RuntimeError("Expected exactly one ordinary-document callback")
    answer = request(
        "answerCallbackQuery",
        {"callback_query_id": callback["id"], "text": scene["answer_text"]},
    )["body"]["result"]
    reused = request(
        "sendDocument",
        {
            "chat_id": chat,
            "document": file_id,
            "caption": scene["reuse_caption"],
        },
    )["body"]["result"]
    offset = incoming[0]["update_id"] + 1
    if request("getUpdates", {"offset": offset})["body"]["result"] != []:
        raise RuntimeError("Unexpected pending update after document reuse")
    print(
        json.dumps(
            {
                "event": "callback",
                "update": incoming[0],
                "answer": answer,
                "reused": reused,
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    break
else:
    raise RuntimeError("Ordinary-document callback did not arrive")
