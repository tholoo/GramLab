"""Contained real Bot API peer for public rich-target acceptance."""

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


def button(text: Any, **action: Any) -> dict[str, Any]:
    return {"text": text, **action}


filler = [{"type": "paragraph", "text": f"Filler {index} / فاصله {index}"} for index in range(15)]
initial = {
    "skip_entity_detection": True,
    "blocks": [
        {
            "type": "buttons",
            "buttons": [
                button("Same / همان", callback_data="same:payload"),
                button(["Copy / ", "کپی"], copy_text={"text": "row copied / ردیف"}),
                button("Disabled / غیرفعال", disabled={}),
            ],
        },
        {
            "type": "paragraph",
            "text": [
                "Nested / تو در تو ",
                {
                    "type": "bold",
                    "text": [
                        {
                            "type": "button",
                            "button": button("Same / همان", callback_data="same:payload"),
                        },
                        " | ",
                        {
                            "type": "button",
                            "button": button(
                                ["Copy / ", "کپی"], copy_text={"text": "inline copied / درون"}
                            ),
                        },
                    ],
                },
                {
                    "type": "button",
                    "button": button("Disabled inline / غیرفعال", disabled={}),
                },
            ],
        },
        {
            "type": "details",
            "summary": "Hidden / پنهان",
            "blocks": [
                {
                    "type": "paragraph",
                    "text": {
                        "type": "button",
                        "button": button("Hidden callback / پنهان", callback_data="hidden"),
                    },
                }
            ],
        },
        *filler,
        {
            "type": "paragraph",
            "text": {
                "type": "button",
                "button": button("Offscreen callback / دور", callback_data="offscreen"),
            },
        },
    ],
}
alternate = {
    "skip_entity_detection": True,
    "blocks": [{"type": "buttons", "buttons": [button("Temporary", callback_data="temporary")]}],
}
unrelated_initial = {
    "skip_entity_detection": True,
    "blocks": [{"type": "paragraph", "text": "Unrelated A"}],
}
unrelated_edited = {
    "skip_entity_detection": True,
    "blocks": [{"type": "paragraph", "text": "Unrelated B"}],
}

updates = call("getUpdates", {"timeout": 10})
if len(updates) != 1 or updates[0]["message"]["text"] != "publish rich targets":
    raise RuntimeError("Expected the rich-target publication request")
chat_id = updates[0]["message"]["chat"]["id"]
primary = call("sendRichMessage", {"chat_id": chat_id, "rich_message": initial})
unrelated = call("sendRichMessage", {"chat_id": chat_id, "rich_message": unrelated_initial})
print(
    json.dumps(
        {"event": "published", "primary": primary, "unrelated": unrelated}, ensure_ascii=False
    ),
    flush=True,
)

offset = updates[0]["update_id"] + 1
callbacks: list[dict[str, Any]] = []
deadline = time.monotonic() + 900
finished = False
while time.monotonic() < deadline and not finished:
    for update in call("getUpdates", {"offset": offset, "timeout": 10}):
        offset = update["update_id"] + 1
        if "callback_query" in update:
            callback = update["callback_query"]
            callbacks.append(callback)
            continue
        text = update.get("message", {}).get("text")
        if text == "same-clock ABA":
            call(
                "editMessageText",
                {
                    "chat_id": chat_id,
                    "message_id": primary["message_id"],
                    "rich_message": alternate,
                },
            )
            call(
                "editMessageText",
                {"chat_id": chat_id, "message_id": primary["message_id"], "rich_message": initial},
            )
            call("sendMessage", {"chat_id": chat_id, "text": "ABA complete"})
        elif text == "edit unrelated":
            call(
                "editMessageText",
                {
                    "chat_id": chat_id,
                    "message_id": unrelated["message_id"],
                    "rich_message": unrelated_edited,
                },
            )
            call("sendMessage", {"chat_id": chat_id, "text": "Unrelated edit complete"})
        elif text == "finish rich targets":
            finished = True
if not finished:
    raise RuntimeError("Rich-target scenario did not reach its finish message")
for callback in callbacks:
    call(
        "answerCallbackQuery",
        {"callback_query_id": callback["id"], "text": "Observed / مشاهده شد"},
    )
if call("getUpdates", {"offset": offset}) != []:
    raise RuntimeError("Unexpected update after rich-target completion")
print(
    json.dumps({"event": "finished", "callbacks": callbacks, "api": records}, ensure_ascii=False),
    flush=True,
)
