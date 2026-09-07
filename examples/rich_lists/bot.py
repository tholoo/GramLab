"""Ordinary local HTTP bot for the rich-list callback example."""

import copy
import http.client
import json
import os
from typing import Any
from urllib.parse import urlsplit

endpoint = urlsplit(os.environ["GRAMLAB_BOT_API"])
if endpoint.scheme != "http" or endpoint.hostname != "127.0.0.1" or endpoint.port is None:
    raise ValueError("An explicit local Bot API endpoint is required")
token = os.environ["GRAMLAB_BOT_TOKEN"]


def call(method: str, parameters: dict[str, Any]) -> Any:
    connection = http.client.HTTPConnection("127.0.0.1", endpoint.port, timeout=35)
    try:
        connection.request(
            "POST",
            f"/bot{token}/{method}",
            json.dumps(parameters),
            {"Content-Type": "application/json"},
        )
        response = connection.getresponse()
        body = json.loads(response.read())
        if response.status != 200 or not body["ok"]:
            raise RuntimeError(f"Bot API rejected {method}")
        return body["result"]
    finally:
        connection.close()


initial: dict[str, Any] = {
    "blocks": [
        {
            "type": "list",
            "items": [
                {
                    "blocks": [{"type": "paragraph", "text": "سلام hello"}],
                    "type": "a",
                    "value": 1,
                },
                {
                    "blocks": [
                        {
                            "type": "paragraph",
                            "text": "راهنمای کوتاه English wraps onto a second line",
                        },
                        {
                            "type": "list",
                            "items": [
                                {
                                    "blocks": [{"type": "paragraph", "text": "تو در تو nested"}],
                                    "has_checkbox": True,
                                    "is_checked": True,
                                },
                                {
                                    "blocks": [{"type": "paragraph", "text": "Pending"}],
                                    "has_checkbox": True,
                                },
                            ],
                        },
                        {
                            "type": "details",
                            "summary": "More",
                            "blocks": [{"type": "paragraph", "text": "Initial hidden detail"}],
                        },
                    ],
                    "type": "A",
                    "value": 2,
                },
                {
                    "blocks": [{"type": "paragraph", "text": "سه roman"}],
                    "type": "i",
                    "value": 3,
                },
                {"blocks": [], "type": "A", "value": 27},
            ],
        }
    ],
    "skip_entity_detection": True,
}
edited: dict[str, Any] = {
    "blocks": [
        {
            "type": "list",
            "items": [
                {
                    "blocks": [
                        {"type": "paragraph", "text": "ویرایش راست‌به‌چپ RTL"},
                    ]
                },
                {
                    "blocks": [
                        {"type": "paragraph", "text": "مرحله nested"},
                        {
                            "type": "list",
                            "items": [
                                {
                                    "blocks": [{"type": "paragraph", "text": "چهار IV"}],
                                    "type": "I",
                                    "value": 4,
                                },
                                {
                                    "blocks": [{"type": "paragraph", "text": "پنج decimal"}],
                                    "type": "1",
                                    "value": 5,
                                },
                            ],
                        },
                    ]
                },
            ],
        }
    ],
    "is_rtl": True,
    "skip_entity_detection": True,
}
duplicate = copy.deepcopy(initial)
duplicate_items = duplicate["blocks"][0]["items"]
duplicate_items[0]["type"] = "A"
duplicate_items[1]["type"] = "a"
duplicate_nested_items = duplicate_items[1]["blocks"][1]["items"]
del duplicate_nested_items[0]["is_checked"]
duplicate_nested_items[1]["is_checked"] = True
duplicate_items[1]["blocks"][2]["blocks"][0]["text"] = "Duplicate hidden detail"
duplicate_items[2]["type"] = "I"
duplicate_items[3].update({"type": "1", "value": 99})

keyboard: dict[str, Any] = {
    "inline_keyboard": [
        [
            {"text": "Keep", "callback_data": "keep"},
            {"text": "Apply", "callback_data": "wrong"},
        ],
        [{"text": "Apply", "callback_data": "rtl-edit"}],
    ]
}
replies: dict[int, dict[str, Any]] = {}
offset = 0
while True:
    for update in call("getUpdates", {"offset": offset, "timeout": 30}):
        if "message" in update:
            message = update["message"]
            if message["text"] not in {"Show lists", "Duplicate lists"}:
                raise ValueError("Unknown scenario command")
            rich_message = duplicate if message["text"] == "Duplicate lists" else initial
            reply = call(
                "sendRichMessage",
                {
                    "chat_id": message["chat"]["id"],
                    "rich_message": rich_message,
                    "reply_markup": keyboard,
                },
            )
            replies[message["chat"]["id"]] = reply
        else:
            callback = update["callback_query"]
            chat_id = callback["message"]["chat"]["id"]
            if callback["message"] != replies[chat_id]:
                raise AssertionError("Callback did not retain the complete sent list message")
            if callback["data"] != "rtl-edit":
                raise AssertionError("Scenario selected the wrong callback payload")
            call(
                "editMessageText",
                {
                    "chat_id": chat_id,
                    "message_id": callback["message"]["message_id"],
                    "rich_message": edited,
                },
            )
            call(
                "answerCallbackQuery",
                {
                    "callback_query_id": callback["id"],
                    "text": "Lists updated",
                },
            )
        offset = update["update_id"] + 1
