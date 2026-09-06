"""Public scenario captures assert rich text without flattening retained evidence."""

import json
from pathlib import Path
from typing import cast

from test_runner import invoke, project

RICH_MESSAGE = {
    "blocks": [
        {
            "type": "paragraph",
            "text": [
                "سلام ",
                {"type": "bold", "text": {"type": "italic", "text": "hello"}},
            ],
        },
        {"type": "heading", "size": 2, "text": "Second block"},
        {
            "type": "details",
            "summary": ["خلاصه ", {"type": "underline", "text": "summary"}],
            "blocks": [
                {
                    "type": "blockquote",
                    "blocks": [{"type": "paragraph", "text": "Nested body"}],
                    "credit": ["نویسنده ", {"type": "italic", "text": "Author"}],
                }
            ],
            "is_open": True,
        },
        {
            "type": "table",
            "caption": ["نتیجه ", {"type": "bold", "text": "Scores"}],
            "is_bordered": True,
            "cells": [
                [
                    {"text": ["ردیف ", {"type": "bold", "text": "one"}], "is_header": True},
                    {"text": "Cell two", "align": "right"},
                ]
            ],
        },
        {"type": "pre", "text": "literal payload", "language": "python"},
    ]
}

BOT = r"""import http.client
import json
import os
from urllib.parse import urlencode, urlsplit

endpoint = urlsplit(os.environ["GRAMLAB_BOT_API"])
token = os.environ["GRAMLAB_BOT_TOKEN"]
RICH_MESSAGE = json.loads(__RICH_MESSAGE__)

def call(method, parameters):
    connection = http.client.HTTPConnection("127.0.0.1", endpoint.port, timeout=10)
    try:
        connection.request(
            "POST",
            f"/bot{token}/{method}",
            urlencode({
                key: json.dumps(value, ensure_ascii=False)
                if isinstance(value, (dict, list))
                else value
                for key, value in parameters.items()
            }),
            {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"},
        )
        response = connection.getresponse()
        body = json.loads(response.read())
        if response.status != 200 or not body["ok"]:
            raise RuntimeError("Local Bot API rejected request")
        return body["result"]
    finally:
        connection.close()

offset = 0
handled = 0
while handled != 2:
    updates = call("getUpdates", {"offset": offset, "timeout": 10})
    for update in updates:
        offset = update["update_id"] + 1
        chat_id = update["message"]["chat"]["id"]
        if update["message"]["text"] == "primary":
            rich = RICH_MESSAGE
        else:
            rich = {"blocks": [{"type": "paragraph", "text": "Other chat secret"}]}
        call("sendRichMessage", {
            "chat_id": chat_id,
            "rich_message": {**rich, "skip_entity_detection": True},
        })
        handled += 1
"""


def rich_project(directory: Path, scenario: str) -> Path:
    manifest = cast(Path, project(directory, scenario))
    encoded = repr(json.dumps(RICH_MESSAGE, ensure_ascii=False))
    (directory / "bot.py").write_text(BOT.replace("__RICH_MESSAGE__", encoded))
    return manifest


def test_public_capture_matches_each_rich_fragment_and_preserves_structure(tmp_path: Path) -> None:
    scenario = """import time
from gramlab.scenario import Scenario
lab = Scenario.from_environment()
primary_user = lab.create_user(first_name="Primary")
other_user = lab.create_user(first_name="Other")
bot = lab.bots()["echo"]
primary = lab.open_private_chat(user_id=primary_user["id"], bot_id=bot)
other = lab.open_private_chat(user_id=other_user["id"], bot_id=bot)
lab.send_message(chat_id=primary["id"], sender_id=primary_user["id"], text="primary")
lab.send_message(chat_id=other["id"], sender_id=other_user["id"], text="other")
deadline = time.monotonic() + 5
while len(lab.history(primary["id"])) != 2 or len(lab.history(other["id"])) != 2:
    assert time.monotonic() < deadline
    time.sleep(0.01)
captured = lab.capture_chat(
    chat_id=primary["id"],
    label="rich",
    contains=[
        "سلام hello", "خلاصه summary", "Nested body", "نویسنده Author",
        "نتیجه Scores", "ردیف one", "Cell two", "literal payload",
    ],
)
assert captured["history"] == lab.history(primary["id"])
"""
    output = tmp_path / "run"
    result = invoke(rich_project(tmp_path / "project", scenario), output)
    assert result.returncode == 0, (
        (output / "result.json").read_text() if output.exists() else result.stderr
    )
    recorded = json.loads((output / "result.json").read_text())
    assert recorded["captures"][0]["history"] == recorded["histories"]["1"]
    rich = recorded["captures"][0]["history"][1]["rich_message"]
    assert rich["blocks"][2]["blocks"][0]["credit"][1]["text"] == "Author"
    assert rich["blocks"][3]["cells"][0][1]["align"] == "right"


def test_rich_capture_rejects_non_text_and_cross_fragment_matches_without_new_evidence(
    tmp_path: Path,
) -> None:
    scenario = """import time
from gramlab.scenario import Scenario, ScenarioError
lab = Scenario.from_environment()
primary_user = lab.create_user(first_name="Primary")
other_user = lab.create_user(first_name="Other")
bot = lab.bots()["echo"]
primary = lab.open_private_chat(user_id=primary_user["id"], bot_id=bot)
other = lab.open_private_chat(user_id=other_user["id"], bot_id=bot)
lab.send_message(chat_id=primary["id"], sender_id=primary_user["id"], text="primary")
lab.send_message(chat_id=other["id"], sender_id=other_user["id"], text="other")
deadline = time.monotonic() + 5
while len(lab.history(primary["id"])) != 2 or len(lab.history(other["id"])) != 2:
    assert time.monotonic() < deadline
    time.sleep(0.01)
first = lab.capture_chat(chat_id=primary["id"], label="kept", contains=["سلام hello"])
for index, absent in enumerate((
    "absent", "python", "right", "paragraph", "سلام helloSecond block",
    "ردیف oneCell two", "Other chat secret",
)):
    try:
        lab.capture_chat(chat_id=primary["id"], label=f"rejected-{index}", contains=[absent])
    except ScenarioError as error:
        assert error.code == "invalid_request" and not error.outcome_uncertain
    else:
        raise AssertionError(f"Accepted non-fragment text: {absent}")
assert first["history"] == lab.history(primary["id"])
"""
    output = tmp_path / "run"
    result = invoke(rich_project(tmp_path / "project", scenario), output)
    assert result.returncode == 0, (
        (output / "result.json").read_text() if output.exists() else result.stderr
    )
    recorded = json.loads((output / "result.json").read_text())
    captures = recorded["captures"]
    assert [capture["label"] for capture in captures] == ["kept"]
    assert captures[0]["history"] == recorded["histories"]["1"]
