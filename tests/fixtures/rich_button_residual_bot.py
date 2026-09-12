"""Contained real Bot API peer for residual rich-button acceptance."""

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
    with Path("api.jsonl").open("a") as evidence:
        evidence.write(json.dumps(record, ensure_ascii=False) + "\n")
    if response.status != 200 or body.get("ok") is not True:
        raise RuntimeError(f"Local Bot API rejected {method}")
    return body["result"]


fillers = [
    {
        "type": "paragraph",
        "text": f"فاصلهٔ مستقل {index} / spacer {index}"
        + ("\ngauge line one\ngauge line two" if index == 5 else ""),
    }
    for index in range(1, 16)
]
rich_message = {
    "skip_entity_detection": True,
    "blocks": [
        {"type": "paragraph", "text": "فارسی از ابتدای ردیف آغاز می‌شود / RTL starts here"},
        *fillers[:3],
        {
            "type": "buttons",
            "buttons": [
                {
                    "text": "لبهٔ نیمه‌پیدا / clipped edge",
                    "callback_data": "must:not-dispatch",
                }
            ],
        },
        *fillers[4:],
        {
            "type": "buttons",
            "buttons": [
                {"text": "تأیید راست‌به‌چپ / RTL confirm", "callback_data": "rtl:confirm"},
                {
                    "text": "کپی مستقل / Copy",
                    "copy_text": {"text": "متن کپی‌شده / copied text"},
                },
            ],
        },
        {
            "type": "paragraph",
            "text": [
                "کنترل تو در تو: ",
                {
                    "type": "bold",
                    "text": {
                        "type": "button",
                        "button": {
                            "text": "پاسخ گم‌شده / Lost reply",
                            "callback_data": "lost:reply",
                        },
                    },
                },
            ],
        },
        {
            "type": "details",
            "summary": "جزئیات بسته / closed details",
            "blocks": [{"type": "paragraph", "text": "No control in this closed body"}],
        },
    ],
}

updates = call("getUpdates", {"timeout": 10})
if len(updates) != 1 or updates[0]["message"]["text"] != "publish residual controls":
    raise RuntimeError("Expected the residual-control publication request")
chat_id = updates[0]["message"]["chat"]["id"]
published = call("sendRichMessage", {"chat_id": chat_id, "rich_message": rich_message})
print(json.dumps({"event": "published", "message": published}, ensure_ascii=False), flush=True)

offset = updates[0]["update_id"] + 1
callbacks: list[dict[str, Any]] = []
finished = False
deadline = time.monotonic() + 900
while time.monotonic() < deadline and not finished:
    for update in call("getUpdates", {"offset": offset, "timeout": 10}):
        offset = update["update_id"] + 1
        callback = update.get("callback_query")
        if callback is not None:
            callbacks.append(callback)
            call(
                "answerCallbackQuery",
                {"callback_query_id": callback["id"], "text": "ثبت شد / recorded"},
            )
        elif update.get("message", {}).get("text") == "finish residual controls":
            finished = True

if not finished:
    raise RuntimeError("Residual-control scenario did not finish")
if call("getUpdates", {"offset": offset}) != []:
    raise RuntimeError("Unexpected update after residual-control completion")
print(
    json.dumps({"event": "finished", "callbacks": callbacks, "api": records}, ensure_ascii=False),
    flush=True,
)
