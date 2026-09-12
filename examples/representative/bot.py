"""Contained stdlib Bot API peer for the representative offline workflow."""

from __future__ import annotations

import hashlib
import http.client
import json
import os
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from assets import DEFAULT_DOCUMENT, JPEG, PNG

if Path("/work/world").exists() or Path("/proc/1/root/work/world").exists():
    raise RuntimeError("Representative bot can see the authoritative World")

endpoint = urlsplit(os.environ["GRAMLAB_BOT_API"])
if endpoint.scheme != "http" or endpoint.hostname != "127.0.0.1" or endpoint.port is None:
    raise ValueError("Representative bot requires the explicit loopback Bot API")
token = os.environ["GRAMLAB_BOT_TOKEN"]
state_path = Path("state.json")
state = (
    json.loads(state_path.read_text()) if state_path.exists() else {"generation": 0, "offset": 0}
)
state["generation"] += 1
state_path.write_text(json.dumps(state))


def request(
    method: str,
    parameters: dict[str, Any],
    *,
    files: dict[str, tuple[str, bytes, str]] | None = None,
) -> Any:
    if files:
        boundary = f"gramlab-representative-{state['generation']}-{len(api_records())}"
        chunks: list[bytes] = []
        for name, value in parameters.items():
            encoded = (
                json.dumps(value, ensure_ascii=False)
                if isinstance(value, (dict, list))
                else str(value)
            )
            disposition = f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n'
            chunks.extend([disposition.encode(), encoded.encode(), b"\r\n"])
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
        content_type = f"multipart/form-data; boundary={boundary}"
    else:
        body = json.dumps(parameters, ensure_ascii=False).encode()
        content_type = "application/json"
    connection = http.client.HTTPConnection("127.0.0.1", endpoint.port, timeout=35)
    try:
        connection.request("POST", f"/bot{token}/{method}", body, {"Content-Type": content_type})
        response = connection.getresponse()
        status = response.status
        envelope = json.loads(response.read())
    finally:
        connection.close()
    record = {"method": method, "parameters": parameters, "status": status, "body": envelope}
    with Path("api.jsonl").open("a") as evidence:
        evidence.write(json.dumps(record, ensure_ascii=False) + "\n")
    if status != 200 or envelope.get("ok") is not True:
        raise RuntimeError(f"Representative Bot API rejected {method}")
    return envelope["result"]


def api_records() -> list[dict[str, Any]]:
    if not Path("api.jsonl").exists():
        return []
    return [json.loads(line) for line in Path("api.jsonl").read_text().splitlines()]


def persist_offset(value: int) -> None:
    state["offset"] = value
    state_path.write_text(json.dumps(state))


def download(file_id: str, expected: bytes) -> dict[str, Any]:
    file = request("getFile", {"file_id": file_id})
    connection = http.client.HTTPConnection("127.0.0.1", endpoint.port, timeout=35)
    try:
        connection.request("GET", f"/file/bot{token}/{file['file_path']}")
        response = connection.getresponse()
        payload = response.read()
    finally:
        connection.close()
    if response.status != 200 or payload != expected:
        raise RuntimeError("Representative download differs from uploaded bytes")
    return {"file": file, "size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def emoji(identifier: str, alternative: str) -> dict[str, Any]:
    return {
        "type": "custom_emoji",
        "custom_emoji_id": identifier,
        "alternative_text": alternative,
    }


def initial_rich(user_id: int) -> dict[str, Any]:
    return {
        "blocks": [
            {"type": "paragraph", "text": "Auto example.test @sample_bot"},
            {
                "type": "paragraph",
                "text": [
                    {"type": "url", "text": "Link", "url": "https://example.test/local"},
                    " / ",
                    {"type": "text_mention", "text": "Sara", "user": {"id": user_id}},
                    " / ",
                    emoji("1", "STATIC-ALT"),
                ],
            },
            {
                "type": "buttons",
                "buttons": [
                    {
                        "text": ["Row / ردیف ", emoji("1109", "ANIMATED-BUTTON")],
                        "callback_data": "rich:row",
                    }
                ],
            },
            {
                "type": "paragraph",
                "text": {
                    "type": "button",
                    "button": {
                        "text": ["Inline / درون ", emoji("1", "STATIC-BUTTON")],
                        "callback_data": "rich:inline",
                    },
                },
            },
        ]
    }


def publish_controls(message: dict[str, Any]) -> dict[str, Any]:
    chat_id = message["chat"]["id"]
    ordinary = request(
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": "Ordinary سلام / Hello 👩‍💻",
            "entities": [
                {"type": "custom_emoji", "offset": 22, "length": 5, "custom_emoji_id": "1"}
            ],
            "reply_markup": {
                "inline_keyboard": [
                    [{"text": "Recover / بازیابی", "callback_data": "ordinary:recover"}]
                ]
            },
        },
    )
    rich = request(
        "sendRichMessage",
        {
            "chat_id": chat_id,
            "rich_message": initial_rich(message["from"]["id"]),
        },
    )
    state.update(chat_id=chat_id, ordinary_id=ordinary["message_id"], rich_id=rich["message_id"])
    state_path.write_text(json.dumps(state))
    return {"ordinary": ordinary, "rich": rich}


def publish_photos(chat_id: int) -> dict[str, Any]:
    png = request(
        "sendPhoto",
        {"chat_id": chat_id, "photo": "attach://upload", "caption": "PNG upload / بارگذاری"},
        files={"upload": ("original.png", PNG, "image/png")},
    )
    png_id = png["photo"][0]["file_id"]
    png_reuse = request(
        "sendPhoto", {"chat_id": chat_id, "photo": png_id, "caption": "PNG reuse / استفاده دوباره"}
    )
    jpeg = request(
        "sendPhoto",
        {"chat_id": chat_id, "photo": "attach://upload", "caption": "JPEG upload / بارگذاری"},
        files={"upload": ("original.jpg", JPEG, "image/jpeg")},
    )
    jpeg_id = jpeg["photo"][0]["file_id"]
    jpeg_reuse = request(
        "sendPhoto",
        {"chat_id": chat_id, "photo": jpeg_id, "caption": "JPEG reuse / استفاده دوباره"},
    )
    group = request(
        "sendMediaGroup",
        {
            "chat_id": chat_id,
            "media": [
                {"type": "photo", "media": png_id, "caption": "Photo album / آلبوم عکس"},
                {"type": "photo", "media": jpeg_id},
            ],
        },
    )
    return {
        "png": png,
        "png_reuse": png_reuse,
        "jpeg": jpeg,
        "jpeg_reuse": jpeg_reuse,
        "group": group,
        "downloads": [download(png_id, PNG), download(jpeg_id, JPEG)],
    }


def publish_documents(chat_id: int) -> dict[str, Any]:
    default = request(
        "sendDocument",
        {
            "chat_id": chat_id,
            "document": "attach://upload",
            "caption": "Default document / سند پیش‌فرض",
        },
        files={"upload": ("default.txt", DEFAULT_DOCUMENT, "text/plain")},
    )
    forced = request(
        "sendDocument",
        {
            "chat_id": chat_id,
            "document": "attach://upload",
            "disable_content_type_detection": "true",
            "caption": "Forced document / سند اجباری",
        },
        files={"upload": ("forced-image.png", PNG, "image/png")},
    )
    default_id = default["document"]["file_id"]
    forced_id = forced["document"]["file_id"]
    group = request(
        "sendMediaGroup",
        {
            "chat_id": chat_id,
            "media": [
                {"type": "document", "media": default_id, "caption": "Document album / آلبوم سند"},
                {"type": "document", "media": forced_id},
            ],
        },
    )
    return {
        "default": default,
        "forced": forced,
        "group": group,
        "downloads": [download(default_id, DEFAULT_DOCUMENT), download(forced_id, PNG)],
    }


print(json.dumps({"event": "generation", "generation": state["generation"]}), flush=True)
while True:
    updates = request("getUpdates", {"offset": state["offset"], "timeout": 30})
    for update in updates:
        next_offset = update["update_id"] + 1
        if "message" in update:
            message = update["message"]
            text = message["text"]
            if text == "/start":
                persist_offset(next_offset)
            elif text == "Incoming 👩‍💻":
                controls = publish_controls(message)
                persist_offset(next_offset)
                print(json.dumps({"event": "controls", **controls}, ensure_ascii=False), flush=True)
            elif text == "publish photos / تصاویر":
                photos = publish_photos(message["chat"]["id"])
                persist_offset(next_offset)
                print(
                    json.dumps({"event": "photos", "value": photos}, ensure_ascii=False), flush=True
                )
            elif text == "publish documents / اسناد":
                documents = publish_documents(message["chat"]["id"])
                persist_offset(next_offset)
                print(
                    json.dumps({"event": "documents", "value": documents}, ensure_ascii=False),
                    flush=True,
                )
                print(
                    json.dumps(
                        {
                            "event": "finished",
                            "generation": state["generation"],
                            "api": api_records(),
                        },
                        ensure_ascii=False,
                    ),
                    flush=True,
                )
                raise SystemExit(0)
            else:
                raise RuntimeError(f"Unexpected representative message: {text}")
            continue

        callback = update["callback_query"]
        data = callback["data"]
        if data == "ordinary:recover":
            if state["generation"] == 1:
                Path("received.json").write_text(json.dumps(callback, ensure_ascii=False))
                checkpoint = request(
                    "sendMessage",
                    {
                        "chat_id": callback["message"]["chat"]["id"],
                        "text": "Callback received; restart me / بازیابی",
                    },
                )
                print(json.dumps({"event": "checkpoint", "message": checkpoint}), flush=True)
                while True:
                    time.sleep(60)
            if json.loads(Path("received.json").read_text()) != callback:
                raise RuntimeError("Pending callback changed across representative restart")
            edited = request(
                "editMessageText",
                {
                    "chat_id": callback["message"]["chat"]["id"],
                    "message_id": callback["message"]["message_id"],
                    "text": "Recovered — بازیابی شد ✓",
                },
            )
            answer = request(
                "answerCallbackQuery",
                {"callback_query_id": callback["id"], "text": "Recovered / بازیابی شد"},
            )
            persist_offset(next_offset)
            print(
                json.dumps({"event": "recovered", "edited": edited, "answer": answer}), flush=True
            )
        elif data == "rich:row":
            answer = request("answerCallbackQuery", {"callback_query_id": callback["id"]})
            persist_offset(next_offset)
            print(json.dumps({"event": "rich-row", "answer": answer}), flush=True)
        elif data == "rich:inline":
            edited = request(
                "editMessageText",
                {
                    "chat_id": callback["message"]["chat"]["id"],
                    "message_id": callback["message"]["message_id"],
                    "rich_message": {
                        "blocks": [
                            {
                                "type": "paragraph",
                                "text": "Rich callbacks complete / کنش‌های غنی کامل شد",
                            }
                        ],
                        "skip_entity_detection": True,
                    },
                },
            )
            answer = request("answerCallbackQuery", {"callback_query_id": callback["id"]})
            persist_offset(next_offset)
            print(
                json.dumps(
                    {"event": "rich-inline", "edited": edited, "answer": answer}, ensure_ascii=False
                ),
                flush=True,
            )
        else:
            raise RuntimeError(f"Unexpected representative callback: {data}")
