"""A contained polling Bot API consumer; scenario inputs do not import simulator code."""

import http.client
import json
import os
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urlsplit

endpoint = urlsplit(os.environ["GRAMLAB_BOT_API"])
if endpoint.scheme != "http" or endpoint.hostname != "127.0.0.1":
    raise ValueError("Requires the explicit local Bot API endpoint")
token = os.environ["GRAMLAB_BOT_TOKEN"]


def request(method: str, parameters: dict[str, Any], *, form: bool = False) -> dict[str, Any]:
    body = (
        urlencode(
            {
                key: json.dumps(value, ensure_ascii=False)
                if isinstance(value, (dict, list))
                else value
                for key, value in parameters.items()
            }
        )
        if form
        else json.dumps(parameters, ensure_ascii=False)
    )
    encoding = "application/x-www-form-urlencoded" if form else "application/json"
    connection = http.client.HTTPConnection("127.0.0.1", endpoint.port, timeout=15)
    try:
        connection.request(
            "POST", f"/bot{token}/{method}", body.encode(), {"Content-Type": encoding}
        )
        response = connection.getresponse()
        result = {"status": response.status, "body": json.loads(response.read())}
    finally:
        connection.close()
    with Path("api.jsonl").open("a") as evidence:
        evidence.write(
            json.dumps(
                {"method": method, "encoding": "form" if form else "json", "response": result},
                ensure_ascii=False,
            )
            + "\n"
        )
    return result


def call(method: str, parameters: dict[str, Any], *, form: bool = False) -> Any:
    result = request(method, parameters, form=form)
    if result["status"] != 200 or result["body"].get("ok") is not True:
        raise RuntimeError(f"Local Bot API rejected {method}: HTTP {result['status']}")
    return result["body"]["result"]


def unchanged(message: dict[str, Any]) -> dict[str, Any]:
    # Feed the actual authoritative User output back to the public input boundary.
    parameters = {
        "chat_id": 1,
        "message_id": message["message_id"],
        "rich_message": message["rich_message"] | {"skip_entity_detection": True},
    }
    if "reply_markup" in message:
        parameters["reply_markup"] = message["reply_markup"]
    result = request("editMessageText", parameters, form=True)
    if result != {
        "status": 400,
        "body": {"ok": False, "error_code": 400, "description": "MESSAGE_NOT_MODIFIED"},
    }:
        raise RuntimeError("Returned User content was not a canonical no-op")
    return result


initial_rich = {
    "is_rtl": True,
    "skip_entity_detection": True,
    "blocks": [
        {"type": "heading", "size": 2, "text": "Explicit mention A"},
        {
            "type": "paragraph",
            "text": [
                "Winner: ",
                {
                    "type": "text_mention",
                    "text": ["آرمان ", {"type": "bold", "text": "Arman"}],
                    "user": {"id": 3, "first_name": "Forged", "is_bot": True, "username": "forged"},
                },
                " / ",
                {"type": "italic", "text": "سلام hello"},
            ],
        },
    ],
}
edited_rich = {
    "is_rtl": True,
    "skip_entity_detection": True,
    "blocks": [
        {"type": "heading", "size": 2, "text": "Explicit mention B"},
        {
            "type": "paragraph",
            "text": [
                "Next: ",
                {
                    "type": "text_mention",
                    "text": {"type": "underline", "text": ["مینا ", "Mina"]},
                    "user": {"id": 4},
                },
                {"type": "text_mention", "text": "", "user": {"id": 4}},
            ],
        },
    ],
}
removed_rich = {
    "skip_entity_detection": True,
    "blocks": [
        {"type": "heading", "size": 2, "text": "Mentions removed"},
        {"type": "paragraph", "text": "No named user / اشاره حذف شد"},
    ],
}
keyboard_a = {"inline_keyboard": [[{"text": "Mention B / نفر بعد", "callback_data": "mention:b"}]]}
keyboard_b = {
    "inline_keyboard": [[{"text": "Remove mention / حذف نام", "callback_data": "mention:remove"}]]
}
updates = call("getUpdates", {})
if len(updates) != 1 or updates[0]["message"]["text"] != "Show explicit mentions":
    raise RuntimeError("Expected one virtual-user mention request")
message = call(
    "sendRichMessage", {"chat_id": 1, "rich_message": initial_rich, "reply_markup": keyboard_a}
)
print(
    json.dumps(
        {"event": "initial", "message": message, "noop": unchanged(message), "update": updates[0]},
        ensure_ascii=False,
    ),
    flush=True,
)
offset = updates[0]["update_id"] + 1
for phase, data, rich, keyboard, form in (
    ("edited", "mention:b", edited_rich, keyboard_b, True),
    ("removed", "mention:remove", removed_rich, None, False),
):
    if sys.stdin.readline() != "next\n":
        raise RuntimeError("Missing scenario callback boundary")
    incoming = call("getUpdates", {"offset": offset})
    if len(incoming) != 1 or incoming[0].get("callback_query", {}).get("data") != data:
        raise RuntimeError("Expected exactly one original-button callback")
    callback = incoming[0]["callback_query"]
    answer = call(
        "answerCallbackQuery", {"callback_query_id": callback["id"], "text": "Changed / تغییر کرد"}
    )
    parameters = {"chat_id": 1, "message_id": message["message_id"], "rich_message": rich}
    if keyboard is not None:
        parameters["reply_markup"] = keyboard
    message = call("editMessageText", parameters, form=form)
    noop = unchanged(message)
    offset = incoming[0]["update_id"] + 1
    if call("getUpdates", {"offset": offset}) != []:
        raise RuntimeError("Unexpected pending bot update")
    print(
        json.dumps(
            {
                "event": phase,
                "message": message,
                "noop": noop,
                "update": incoming[0],
                "answer": answer,
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
