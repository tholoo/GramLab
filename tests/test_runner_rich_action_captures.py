"""Public captures treat rich-button labels as visible structured content."""

import json
import os
import subprocess
import sys
from pathlib import Path

INITIAL_INPUT = {
    "skip_entity_detection": True,
    "blocks": [
        {
            "type": "paragraph",
            "text": [
                "Intro ",
                {
                    "type": "button",
                    "button": {
                        "text": ["Inline\t", "Pick"],
                        "style": "PrImArY",
                        "callback_data": "payload:inline",
                    },
                },
                " tail",
            ],
        },
        {
            "type": "buttons",
            "buttons": [
                {
                    "text": ["Copy ", "choice"],
                    "copy_text": {"text": "private copied value"},
                },
                {"text": "Disabled later", "disabled": {}},
                {
                    "text": "Confirm amber",
                    "style": "LINK",
                    "callback_data": "payload:confirm",
                },
            ],
            "align": "right",
        },
    ],
}
EDITED_INPUT = {
    "skip_entity_detection": True,
    "is_rtl": True,
    "blocks": [
        {
            "type": "buttons",
            "buttons": [
                {"text": ["گزینه ", "ویرایش"], "disabled": {}},
                {"text": "Edited copy", "copy_text": {"text": "edited private value"}},
            ],
            "align": "center",
        },
        {
            "type": "paragraph",
            "text": [
                "After ",
                {
                    "type": "button",
                    "button": {"text": "inline edit", "callback_data": "payload:edited"},
                },
            ],
        },
    ],
}
INITIAL_CANONICAL = {
    "blocks": [
        {
            "type": "paragraph",
            "text": [
                "Intro ",
                {
                    "type": "button",
                    "button": {
                        "text": ["Inline ", "Pick"],
                        "style": "primary",
                        "callback_data": "payload:inline",
                    },
                },
                " tail",
            ],
        },
        {
            "type": "buttons",
            "buttons": [
                {
                    "text": ["Copy ", "choice"],
                    "copy_text": {"text": "private copied value"},
                },
                {"text": "Disabled later", "disabled": {}},
                {
                    "text": "Confirm amber",
                    "style": "link",
                    "callback_data": "payload:confirm",
                },
            ],
            "align": "right",
        },
    ]
}
EDITED_CANONICAL = {
    "blocks": EDITED_INPUT["blocks"],
    "is_rtl": True,
}

BOT = r"""import http.client
import json
import os
from urllib.parse import urlencode, urlsplit

endpoint = urlsplit(os.environ["GRAMLAB_BOT_API"])
token = os.environ["GRAMLAB_BOT_TOKEN"]
initial = json.loads(__INITIAL__)
edited = json.loads(__EDITED__)

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
            raise RuntimeError(f"Local Bot API rejected rich action: {body}")
        return body["result"]
    finally:
        connection.close()

offset = 0
message_id = None
while True:
    for update in call("getUpdates", {"offset": offset, "timeout": 10}):
        offset = update["update_id"] + 1
        message = update["message"]
        if message["text"] == "show":
            sent = call("sendRichMessage", {
                "chat_id": message["chat"]["id"],
                "rich_message": initial,
            })
            message_id = sent["message_id"]
        elif message["text"] == "edit":
            call("editMessageText", {
                "chat_id": message["chat"]["id"],
                "message_id": message_id,
                "rich_message": edited,
            })
            raise SystemExit(0)
"""


def action_project(directory: Path, scenario: str) -> Path:
    directory.mkdir()
    (directory / "run.toml").write_text(
        """schema = 1
seed = 7
now = 1700000000
timeout = 10
[scenario]
entry = "scenario.py"
files = ["scenario.py"]
[bots.echo]
entry = "bot.py"
files = ["bot.py"]
"""
    )
    (directory / "scenario.py").write_text(scenario)
    bot = BOT.replace("__INITIAL__", repr(json.dumps(INITIAL_INPUT, ensure_ascii=False))).replace(
        "__EDITED__", repr(json.dumps(EDITED_INPUT, ensure_ascii=False))
    )
    (directory / "bot.py").write_text(bot)
    return directory / "run.toml"


def invoke(manifest: Path, output: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 — actual public CLI argv, no shell
        [sys.executable, "-m", "gramlab", "run", str(manifest), "--output", str(output)],
        capture_output=True,
        text=True,
        timeout=30,
        env=os.environ.copy(),
    )


def test_public_action_captures_use_labels_and_preserve_complete_scenes(tmp_path: Path) -> None:
    scenario = """import time
from gramlab.scenario import Scenario, ScenarioError

lab = Scenario.from_environment()
user = lab.create_user(first_name="Sara", language_code="fa")
chat = lab.open_private_chat(user_id=user["id"], bot_id=lab.bots()["echo"])
lab.send_message(chat_id=chat["id"], sender_id=user["id"], text="show")
deadline = time.monotonic() + 5
while len(lab.history(chat["id"])) != 2:
    assert time.monotonic() < deadline, "Initial rich action missing"
    time.sleep(0.01)

initial = lab.capture_chat(
    chat_id=chat["id"],
    label="initial",
    contains=["Intro Inline Pick tail", "Copy choice", "Disabled later", "Confirm amber"],
)
for index, absent in enumerate((
    "payload:inline", "payload:confirm", "private copied value", "primary", "link", "right",
    "Copy choiceDisabled later", "Disabled laterConfirm amber",
)):
    try:
        lab.capture_chat(chat_id=chat["id"], label=f"rejected-{index}", contains=[absent])
    except ScenarioError as error:
        assert error.code == "invalid_request" and not error.outcome_uncertain
    else:
        raise AssertionError(f"Accepted non-visible action content: {absent}")

lab.send_message(chat_id=chat["id"], sender_id=user["id"], text="edit")
deadline = time.monotonic() + 5
while "edit_date" not in lab.history(chat["id"])[1]:
    assert time.monotonic() < deadline, "Rich action edit missing"
    time.sleep(0.01)
edited = lab.capture_chat(
    chat_id=chat["id"],
    label="after-edit",
    contains=["گزینه ویرایش", "Edited copy", "After inline edit"],
)
cold = lab.capture_chat(
    chat_id=chat["id"], label="cold-semantic", contains=["گزینه ویرایش", "After inline edit"]
)
assert edited["history"] == cold["history"] == lab.history(chat["id"])
"""
    output = tmp_path / "run"
    result = invoke(action_project(tmp_path / "project", scenario), output)
    assert result.returncode == 0, (
        (output / "result.json").read_text() if output.exists() else result.stderr
    )
    recorded = json.loads((output / "result.json").read_text())
    user_show = {"id": 1, "chat_id": 1, "sender_id": 2, "date": 1700000000, "text": "show"}
    initial = {
        "id": 2,
        "chat_id": 1,
        "sender_id": 1,
        "date": 1700000000,
        "text": "",
        "rich_message": INITIAL_CANONICAL,
    }
    edited = {
        **initial,
        "edit_date": 1700000000,
        "rich_message": EDITED_CANONICAL,
    }
    user_edit = {"id": 3, "chat_id": 1, "sender_id": 2, "date": 1700000000, "text": "edit"}
    assert recorded["outcome"] == "passed"
    assert recorded["histories"] == {"1": [user_show, edited, user_edit]}
    assert recorded["captures"] == [
        {"chat_id": 1, "label": "initial", "history": [user_show, initial], "rendered": False},
        {
            "chat_id": 1,
            "label": "after-edit",
            "history": [user_show, edited, user_edit],
            "rendered": False,
        },
        {
            "chat_id": 1,
            "label": "cold-semantic",
            "history": [user_show, edited, user_edit],
            "rendered": False,
        },
    ]
