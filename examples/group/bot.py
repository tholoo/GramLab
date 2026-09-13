"""Small standard-library bot demonstrating a group command and callback."""

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


offset = 0
while True:
    for update in call("getUpdates", {"offset": offset, "timeout": 30}):
        if "message" in update:
            message = update["message"]
            owner = call(
                "getChatMember",
                {"chat_id": message["chat"]["id"], "user_id": 2},
            )
            if owner["status"] != "creator":
                raise RuntimeError("Unexpected group creator")
            call(
                "sendRichMessage",
                {
                    "chat_id": message["chat"]["id"],
                    "rich_message": {
                        "skip_entity_detection": True,
                        "blocks": [
                            {"type": "heading", "size": 2, "text": "Group choice"},
                            {"type": "paragraph", "text": "Ready for the group"},
                            {
                                "type": "buttons",
                                "buttons": [
                                    {
                                        "text": "Continue",
                                        "style": "primary",
                                        "callback_data": "continue",
                                    }
                                ],
                            },
                        ],
                    },
                },
            )
        else:
            callback = update["callback_query"]
            call(
                "editMessageText",
                {
                    "chat_id": callback["message"]["chat"]["id"],
                    "message_id": callback["message"]["message_id"],
                    "text": "Continued for the group",
                },
            )
            call("answerCallbackQuery", {"callback_query_id": callback["id"], "text": "Done"})
        offset = update["update_id"] + 1
