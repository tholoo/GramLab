"""Current semantic messages support public virtual inline-button input."""

import json
import subprocess
import sys
from pathlib import Path

BOT = r"""import http.client
import json
import os
import uuid
from urllib.parse import urlsplit

endpoint = urlsplit(os.environ["GRAMLAB_BOT_API"])
token = os.environ["GRAMLAB_BOT_TOKEN"]

def call(method, parameters, *, photo=None):
    headers = {}
    if photo is None:
        body = json.dumps(parameters, ensure_ascii=False).encode()
        headers["Content-Type"] = "application/json"
    else:
        boundary = "gramlab-" + uuid.uuid4().hex
        chunks = []
        for key, value in parameters.items():
            chunks.append((f"--{boundary}\r\nContent-Disposition: form-data; name=\"{key}\""
                           f"\r\n\r\n{value}\r\n").encode())
        chunks.append((f"--{boundary}\r\nContent-Disposition: form-data; name=\"photo\"; "
                       "filename=\"original.png\"\r\nContent-Type: image/png\r\n\r\n").encode()
                      + photo + b"\r\n")
        chunks.append(f"--{boundary}--\r\n".encode())
        body = b"".join(chunks)
        headers["Content-Type"] = "multipart/form-data; boundary=" + boundary
    connection = http.client.HTTPConnection("127.0.0.1", endpoint.port, timeout=35)
    try:
        connection.request("POST", f"/bot{token}/{method}", body, headers)
        response = connection.getresponse()
        result = json.loads(response.read())
    finally:
        connection.close()
    if response.status != 200 or result.get("ok") is not True:
        raise RuntimeError(f"Bot API rejected {method}")
    return result["result"]

keyboard = lambda data: {"inline_keyboard": [[{"text": data.title(), "callback_data": data}]]}
offset = 0
while True:
    for update in call("getUpdates", {"offset": offset, "timeout": 30}):
        offset = update["update_id"] + 1
        if "message" in update:
            message = update["message"]
            text = message["text"]
            if text == "photo":
                call("sendPhoto", {"chat_id": str(message["chat"]["id"]), "caption": "Photo",
                                    "reply_markup": json.dumps(keyboard("photo"))},
                     photo=open("photo.png", "rb").read())
            elif text == "mention":
                call("sendRichMessage", {"chat_id": message["chat"]["id"],
                     "rich_message": {"skip_entity_detection": True, "blocks": [
                         {"type": "paragraph", "text": ["Mention ", {"type": "text_mention",
                          "text": "Mina", "user": {"id": 2, "first_name": "Ignored"}}]}]},
                     "reply_markup": keyboard("mention")})
            elif text == "emoji":
                call("sendMessage", {"chat_id": message["chat"]["id"], "text": "Emoji 🙂",
                     "entities": [{"type": "custom_emoji", "offset": 6, "length": 2,
                                   "custom_emoji_id": "1"}],
                     "reply_markup": keyboard("emoji")})
        else:
            callback = update["callback_query"]
            data = callback["data"]
            message = callback["message"]
            if data == "photo" and "photo" not in message:
                raise RuntimeError("Photo callback lost its message")
            rich = message.get("rich_message", {}).get("blocks", [{}])[0].get("text", [])
            if data == "mention" and rich[1].get("user", {}).get("id") != 2:
                raise RuntimeError("Mention callback lost its authoritative user")
            if data == "emoji" and message.get("entities", [{}])[0].get("custom_emoji_id") != "1":
                raise RuntimeError("Emoji callback lost its identifier")
            call("answerCallbackQuery", {
                "callback_query_id": callback["id"], "text": "handled:" + data})
"""


SCENARIO = r"""import time
from pathlib import Path
from gramlab.scenario import Scenario, ScenarioError

lab = Scenario.from_environment()
main = Path("emoji-static.webp").read_bytes()
thumb = Path("emoji-thumbnail.webp").read_bytes()
assert lab.register_custom_emoji(request_id="emoji", main=main, thumbnail=thumb,
                                 fallback="🙂")["custom_emoji_id"] == "1"
mina = lab.create_user(first_name="Mina")
user = lab.create_user(first_name="Sara", language_code="fa")
bot = lab.bots()["current"]
known = lab.open_private_chat(user_id=mina["id"], bot_id=bot)
chat = lab.open_private_chat(user_id=user["id"], bot_id=bot)
lab.send_message(chat_id=known["id"], sender_id=mina["id"], text="known")

messages = []
callbacks = []
commands = []
for command in ("photo", "mention", "emoji"):
    before = len(lab.history(chat["id"]))
    commands.append(lab.send_message(chat_id=chat["id"], sender_id=user["id"], text=command))
    deadline = time.monotonic() + 10
    while len(lab.history(chat["id"])) != before + 2:
        assert time.monotonic() < deadline
        time.sleep(0.02)
    message = lab.history(chat["id"])[-1]
    events = lab.events()
    try:
        lab.tap_inline_button(chat_id=chat["id"], message_id=message["id"], row=1, column=0)
    except ScenarioError as error:
        assert error.code == "invalid_request" and not error.outcome_uncertain
    else:
        raise AssertionError("Invalid keyboard row accepted")
    assert lab.events() == events
    interaction = lab.tap_inline_button(
        chat_id=chat["id"], message_id=message["id"], row=0, column=0)
    callback = interaction["callback"]
    assert callback["message"] == message and callback["data"] == command
    deadline = time.monotonic() + 10
    while lab.get_callback(user_id=user["id"], callback_id=callback["id"])["answer"] is None:
        assert time.monotonic() < deadline
        time.sleep(0.02)
    answer = lab.get_callback(user_id=user["id"], callback_id=callback["id"])["answer"]
    assert answer["text"] == "handled:" + command
    messages.append(message)
    callbacks.append(callback)

photo, mention, emoji = messages
assert photo == {"id": photo["id"], "chat_id": chat["id"], "sender_id": bot,
                 "date": 1700000000, "text": "", "photo": {"asset_id": 3},
                 "caption": "Photo",
                 "reply_markup": {"inline_keyboard": [[
                     {"text": "Photo", "callback_data": "photo"}]]}}
assert mention == {"id": mention["id"], "chat_id": chat["id"], "sender_id": bot,
                   "date": 1700000000, "text": "",
                   "rich_message": {"blocks": [{"type": "paragraph", "text": ["Mention ",
                       {"type": "text_mention", "text": "Mina", "user_id": 2}]}]},
                   "reply_markup": {"inline_keyboard": [[
                       {"text": "Mention", "callback_data": "mention"}]]}}
assert emoji == {"id": emoji["id"], "chat_id": chat["id"], "sender_id": bot,
                 "date": 1700000000, "text": "Emoji 🙂",
                 "entities": [{"type": "custom_emoji", "offset": 6, "length": 2,
                               "custom_emoji_id": "1"}],
                 "reply_markup": {"inline_keyboard": [[
                     {"text": "Emoji", "callback_data": "emoji"}]]}}
created = [event for event in lab.events() if event["type"] == "callback.created"]
assert len(created) == 3
assert [event["data"]["data"] for event in created] == ["photo", "mention", "emoji"]
assert [event["data"]["message"] for event in created] == messages
assert [callback["id"] for callback in callbacks] == [event["data"]["id"] for event in created]
assert commands == [
    {"id": command["id"], "chat_id": chat["id"], "sender_id": user["id"],
     "date": 1700000000, "text": text}
    for command, text in zip(commands, ("photo", "mention", "emoji"))
]
assert lab.history(chat["id"]) == [item for pair in zip(commands, messages) for item in pair]
print("current semantic callbacks verified")
"""


def test_contained_scenario_taps_current_semantic_inline_keyboards(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "run.toml").write_text(
        'schema = 1\nmode = "simulation-only"\nseed = 7\nnow = 1700000000\ntimeout = 20\n'
        '[scenario]\nentry = "scenario.py"\nfiles = ["scenario.py", "emoji-static.webp", '
        '"emoji-thumbnail.webp"]\n'
        '[bots.current]\nentry = "bot.py"\nfiles = ["bot.py", "photo.png"]\n'
    )
    (project / "scenario.py").write_text(SCENARIO)
    (project / "bot.py").write_text(BOT)
    assets = Path("tests/assets")
    (project / "photo.png").write_bytes(
        (assets / "rich-media" / "photo-square-16x16.png").read_bytes()
    )
    emoji = assets / "custom-emoji"
    for name in ("emoji-static.webp", "emoji-thumbnail.webp"):
        (project / name).write_bytes((emoji / name).read_bytes())
    output = tmp_path / "run"
    result = subprocess.run(  # noqa: S603 - tested CLI inside the outer network namespace
        [
            sys.executable,
            "-m",
            "gramlab",
            "run",
            str(project / "run.toml"),
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
        timeout=45,
    )
    (tmp_path / "runner.stdout.log").write_text(result.stdout)
    (tmp_path / "runner.stderr.log").write_text(result.stderr)
    assert result.returncode == 0, (output / "result.json").read_text()
    recorded = json.loads((output / "result.json").read_text())
    assert recorded["outcome"] == "passed"
    assert recorded["processes"]["scenario"]["stdout"] == "current semantic callbacks verified\n"
    assert len(recorded["interactions"]) == 3
    assert [item["callback"]["data"] for item in recorded["interactions"]] == [
        "photo",
        "mention",
        "emoji",
    ]
