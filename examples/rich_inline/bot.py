"""Ordinary HTTP Bot API consumer, using only Python's standard library."""

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


replies: dict[int, dict[str, Any]] = {}
offset = 0
keyboard = {
    "inline_keyboard": [
        [
            {"text": "Cancel", "callback_data": "cancel"},
            {"text": "Confirm", "callback_data": "wrong"},
        ],
        [{"text": "Confirm", "callback_data": "confirm"}],
    ]
}
while True:
    for update in call("getUpdates", {"offset": offset, "timeout": 30}):
        if "message" in update:
            message = update["message"]
            reply = call(
                "sendRichMessage",
                {
                    "chat_id": message["chat"]["id"],
                    "rich_message": {
                        "blocks": [
                            {"type": "heading", "size": 2, "text": "Rich choice"},
                            {
                                "type": "table",
                                "cells": [
                                    [
                                        {"text": "زبان", "align": "left", "valign": "middle"},
                                        {"text": "English", "align": "left", "valign": "middle"},
                                    ]
                                ],
                                "is_bordered": True,
                            },
                            {
                                "type": "paragraph",
                                "text": [
                                    "Choose ",
                                    {"type": "bold", "text": "an option"},
                                    " — تأیید",
                                ],
                            },
                        ],
                        "skip_entity_detection": True,
                    },
                    "reply_markup": keyboard,
                },
            )
            replies[message["chat"]["id"]] = reply
        else:
            callback = update["callback_query"]
            if callback["message"] != replies[callback["message"]["chat"]["id"]]:
                raise AssertionError("Callback did not retain the complete sent rich message")
            call(
                "editMessageText",
                {
                    "chat_id": callback["message"]["chat"]["id"],
                    "message_id": callback["message"]["message_id"],
                    "rich_message": {
                        "blocks": [
                            {
                                "type": "paragraph",
                                "text": "Selected: " + callback["data"] + " ✓ — انجام شد",
                            }
                        ],
                        "is_rtl": True,
                        "skip_entity_detection": True,
                    },
                },
            )
            call("answerCallbackQuery", {"callback_query_id": callback["id"], "text": "Done"})
        offset = update["update_id"] + 1
