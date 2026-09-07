"""Public semantic captures preserve canonical custom-emoji alternatives."""

import json
import subprocess
import sys
from pathlib import Path

RICH_INPUT = {
    "skip_entity_detection": True,
    "blocks": [
        {
            "type": "paragraph",
            "text": [
                "Prefix ",
                {
                    "type": "custom_emoji",
                    "custom_emoji_id": "7",
                    "alternative_text": "diamond alternate",
                },
                " suffix",
            ],
        },
        {
            "type": "blockquote",
            "blocks": [
                {
                    "type": "buttons",
                    "buttons": [
                        {
                            "text": [
                                "Button ",
                                [
                                    {
                                        "type": "custom_emoji",
                                        "custom_emoji_id": "7",
                                        "alternative_text": "",
                                    },
                                    "middle ",
                                ],
                                {
                                    "type": "custom_emoji",
                                    "custom_emoji_id": "7",
                                    "alternative_text": "button alternate",
                                },
                            ],
                            "callback_data": "pick:diamond",
                        }
                    ],
                }
            ],
        },
    ],
}

BOT = r"""import http.client
import json
import os
from urllib.parse import urlsplit

endpoint = urlsplit(os.environ["GRAMLAB_BOT_API"])
token = os.environ["GRAMLAB_BOT_TOKEN"]

def call(method, parameters):
    connection = http.client.HTTPConnection("127.0.0.1", endpoint.port, timeout=5)
    try:
        connection.request(
            "POST",
            f"/bot{token}/{method}",
            json.dumps(parameters, ensure_ascii=False),
            {"Content-Type": "application/json"},
        )
        response = connection.getresponse()
        body = json.loads(response.read())
        if response.status != 200 or not body["ok"]:
            raise RuntimeError(f"Local Bot API rejected custom emoji scene: {body}")
        return body["result"]
    finally:
        connection.close()

updates = call("getUpdates", {"timeout": 5})
chat_id = updates[0]["message"]["chat"]["id"]
call("sendRichMessage", {"chat_id": chat_id, "rich_message": json.loads(__RICH__)})
"""

SCENARIO = r"""import time
from pathlib import Path
from gramlab.scenario import Scenario, ScenarioError

lab = Scenario.from_environment()
assert lab.register_custom_emoji(
    request_id="static",
    main=Path("emoji-static.webp").read_bytes(),
    thumbnail=Path("emoji-thumbnail.webp").read_bytes(),
    fallback="CATALOG-FALLBACK",
    custom_emoji_id="7",
)["custom_emoji_id"] == "7"
user = lab.create_user(first_name="Sara")
chat = lab.open_private_chat(user_id=user["id"], bot_id=lab.bots()["echo"])
lab.send_message(
    chat_id=chat["id"],
    sender_id=user["id"],
    text="Request entity-token source",
    entities=[{
        "type": "bold", "offset": 8, "length": 12,
    }],
)
deadline = time.monotonic() + 5
while len(lab.history(chat["id"])) != 2:
    assert time.monotonic() < deadline, "Custom emoji rich message missing"
    time.sleep(0.01)

captured = lab.capture_chat(
    chat_id=chat["id"],
    label="custom-emoji",
    contains=[
        "Request entity-token source",
        "Prefix diamond alternate suffix",
        "Button middle button alternate",
    ],
)
assert captured["history"] == lab.history(chat["id"])
try:
    lab.capture_chat(
        chat_id=chat["id"], label="fallback-is-absent", contains=["CATALOG-FALLBACK"],
    )
except ScenarioError as error:
    assert error.code == "invalid_request" and not error.outcome_uncertain
else:
    raise AssertionError("Capture inferred catalog fallback instead of canonical alternative text")
"""


def _project(directory: Path) -> Path:
    directory.mkdir()
    manifest = directory / "run.toml"
    manifest.write_text(
        "schema = 1\nseed = 7\nnow = 1700000000\ntimeout = 10\n"
        '[scenario]\nentry = "scenario.py"\n'
        'files = ["scenario.py", "emoji-static.webp", "emoji-thumbnail.webp"]\n'
        '[bots.echo]\nentry = "bot.py"\nfiles = ["bot.py"]\n'
    )
    (directory / "scenario.py").write_text(SCENARIO)
    encoded = repr(json.dumps(RICH_INPUT, ensure_ascii=False))
    (directory / "bot.py").write_text(BOT.replace("__RICH__", encoded))
    fixture = Path("tests/assets/custom-emoji")
    for name in ("emoji-static.webp", "emoji-thumbnail.webp"):
        (directory / name).write_bytes((fixture / name).read_bytes())
    return manifest


def _invoke(manifest: Path, output: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - actual public CLI argv inside the network guard
        [sys.executable, "-m", "gramlab", "run", str(manifest), "--output", str(output)],
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_public_capture_preserves_custom_emoji_alternatives_and_history(tmp_path: Path) -> None:
    output = tmp_path / "run"
    result = _invoke(_project(tmp_path / "project"), output)
    assert result.returncode == 0, (
        (output / "result.json").read_text() if output.exists() else result.stderr
    )

    canonical_rich = {
        "blocks": [
            {
                "type": "paragraph",
                "text": [
                    "Prefix ",
                    {
                        "type": "custom_emoji",
                        "custom_emoji_id": "7",
                        "alternative_text": "diamond alternate",
                    },
                    " suffix",
                ],
            },
            {
                "type": "blockquote",
                "blocks": [
                    {
                        "type": "buttons",
                        "buttons": [
                            {
                                "text": [
                                    "Button ",
                                    [
                                        {
                                            "type": "custom_emoji",
                                            "custom_emoji_id": "7",
                                            "alternative_text": "",
                                        },
                                        "middle ",
                                    ],
                                    {
                                        "type": "custom_emoji",
                                        "custom_emoji_id": "7",
                                        "alternative_text": "button alternate",
                                    },
                                ],
                                "callback_data": "pick:diamond",
                            }
                        ],
                    }
                ],
            },
        ]
    }
    history = [
        {
            "id": 1,
            "chat_id": 1,
            "sender_id": 2,
            "date": 1700000000,
            "text": "Request entity-token source",
            "entities": [{"type": "bold", "offset": 8, "length": 12}],
        },
        {
            "id": 2,
            "chat_id": 1,
            "sender_id": 1,
            "date": 1700000000,
            "text": "",
            "rich_message": canonical_rich,
        },
    ]
    recorded = json.loads((output / "result.json").read_text())
    assert recorded["outcome"] == "passed"
    assert recorded["histories"] == {"1": history}
    assert recorded["captures"] == [
        {
            "chat_id": 1,
            "label": "custom-emoji",
            "history": history,
            "rendered": False,
        }
    ]
