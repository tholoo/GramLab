"""Public captures recognize photo captions and credits, excluding hidden metadata."""

import json
from pathlib import Path

from test_runner_rich_action_captures import action_project, invoke

BOT = r"""import http.client
import json
import os
from pathlib import Path
from urllib.parse import urlencode, urlsplit

endpoint = urlsplit(os.environ["GRAMLAB_BOT_API"])
token = os.environ["GRAMLAB_BOT_TOKEN"]

def request(method, body, content_type):
    connection = http.client.HTTPConnection("127.0.0.1", endpoint.port, timeout=5)
    try:
        connection.request("POST", f"/bot{token}/{method}", body,
                           {"Content-Type": content_type})
        response = connection.getresponse()
        result = json.loads(response.read())
        assert response.status == 200 and result["ok"], result
        return result["result"]
    finally:
        connection.close()

def call(method, value):
    return request(method, json.dumps(value), "application/json")

updates = call("getUpdates", {"timeout": 5})
chat_id = updates[0]["message"]["chat"]["id"]
boundary = "GramLabPhotoCaptionFixture"
parts = []
for key, value in {"chat_id": str(chat_id), "caption": "Ordinary تصویر"}.items():
    parts.append((f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n'
                  f'\r\n{value}\r\n').encode())
parts.append((f'--{boundary}\r\nContent-Disposition: form-data; name="photo"; '
              'filename="hidden-filename.png"\r\nContent-Type: image/png\r\n\r\n').encode()
             + Path("photo.png").read_bytes() + b"\r\n")
parts.append(f"--{boundary}--\r\n".encode())
photo = request("sendPhoto", b"".join(parts), "multipart/form-data; boundary=" + boundary)
call("sendRichMessage", {
    "chat_id": chat_id,
    "rich_message": {
        "skip_entity_detection": True,
        "blocks": [{
            "type": "photo", "photo": {"type": "photo", "media": photo["photo"][0]["file_id"]},
            "caption": {
                "text": ["Rich ", {"type": "bold", "text": "عکس"}],
                "credit": {"type": "url", "text": "Artist هنرمند", "url": "hidden-credit-url"},
            },
        }],
    },
})
"""

SCENARIO = """import time
from gramlab.scenario import Scenario, ScenarioError

lab = Scenario.from_environment()
user = lab.create_user(first_name="Sara", language_code="fa")
chat = lab.open_private_chat(user_id=user["id"], bot_id=lab.bots()["echo"])
lab.send_message(chat_id=chat["id"], sender_id=user["id"], text="show")
deadline = time.monotonic() + 5
while len(lab.history(chat["id"])) != 3:
    assert time.monotonic() < deadline, "Photo fixture did not publish both messages"
    time.sleep(0.01)
lab.capture_chat(chat_id=chat["id"], label="ordinary", contains=["Ordinary تصویر"])
lab.capture_chat(chat_id=chat["id"], label="rich", contains=["Rich عکس", "Artist هنرمند"])
for index, text in enumerate(("hidden-filename.png", "hidden-credit-url", "Rich عکسArtist هنرمند")):
    try:
        lab.capture_chat(chat_id=chat["id"], label=f"hidden-{index}", contains=[text])
    except ScenarioError as error:
        assert error.code == "invalid_request" and not error.outcome_uncertain
    else:
        raise AssertionError("Photo capture accepted hidden or cross-fragment metadata")
"""


def test_public_captures_preserve_ordinary_and_rich_photo_captions(tmp_path: Path) -> None:
    project = tmp_path / "project"
    manifest = action_project(project, SCENARIO)
    manifest.write_text(
        manifest.read_text().replace('files = ["bot.py"]', 'files = ["bot.py", "photo.png"]')
    )
    (project / "bot.py").write_text(BOT)
    (project / "photo.png").write_bytes(
        Path("tests/assets/rich-media/photo-square-16x16.png").read_bytes()
    )
    output = tmp_path / "run"
    result = invoke(manifest, output)
    assert result.returncode == 0, (
        (output / "result.json").read_text() if output.exists() else result.stderr
    )
    recorded = json.loads((output / "result.json").read_text())
    history = [
        {"id": 1, "chat_id": 1, "sender_id": 2, "date": 1700000000, "text": "show"},
        {
            "id": 2,
            "chat_id": 1,
            "sender_id": 1,
            "date": 1700000000,
            "text": "",
            "photo": {"asset_id": 1},
            "caption": "Ordinary تصویر",
        },
        {
            "id": 3,
            "chat_id": 1,
            "sender_id": 1,
            "date": 1700000000,
            "text": "",
            "rich_message": {
                "blocks": [
                    {
                        "type": "photo",
                        "asset_id": 1,
                        "caption": {
                            "text": ["Rich ", {"type": "bold", "text": "عکس"}],
                            "credit": {
                                "type": "url",
                                "text": "Artist هنرمند",
                                "url": "hidden-credit-url",
                            },
                        },
                    }
                ]
            },
        },
    ]
    assert recorded["outcome"] == "passed"
    assert recorded["histories"] == {"1": history}
    assert recorded["captures"] == [
        {"chat_id": 1, "label": label, "history": history, "rendered": False}
        for label in ("ordinary", "rich")
    ]
