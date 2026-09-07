"""Public scenario captures find link labels without treating destinations as visible."""

import json
from pathlib import Path

from test_rich_links_round_trip import SCENE
from test_runner_rich_action_captures import BOT as BOT_TEMPLATE
from test_runner_rich_action_captures import action_project, invoke


def test_public_rich_link_captures_exclude_destination_metadata(tmp_path: Path) -> None:
    scenario = """import time
from gramlab.scenario import Scenario, ScenarioError

lab = Scenario.from_environment()
user = lab.create_user(first_name="Sara", language_code="fa")
chat = lab.open_private_chat(user_id=user["id"], bot_id=lab.bots()["echo"])
lab.send_message(chat_id=chat["id"], sender_id=user["id"], text="show")
deadline = time.monotonic() + 5
while len(lab.history(chat["id"])) != 2:
    assert time.monotonic() < deadline, "Initial rich links missing"
    time.sleep(0.01)
initial = lab.capture_chat(
    chat_id=chat["id"], label="initial",
    contains=["Visit Guide راهنما", "Email team / Call team"],
)
for index, hidden in enumerate((
    "hidden-url", "hidden-email@example.invalid", "+12025550123", "راهنما" + "Email team",
)):
    try:
        lab.capture_chat(chat_id=chat["id"], label=f"hidden-{index}", contains=[hidden])
    except ScenarioError as error:
        assert error.code == "invalid_request" and not error.outcome_uncertain
    else:
        raise AssertionError("Capture accepted hidden destination or cross-fragment text")
lab.send_message(chat_id=chat["id"], sender_id=user["id"], text="edit")
deadline = time.monotonic() + 5
while "edit_date" not in lab.history(chat["id"])[1]:
    assert time.monotonic() < deadline, "Rich link edit missing"
    time.sleep(0.01)
edited = lab.capture_chat(
    chat_id=chat["id"], label="after-edit",
    contains=["Open New guide راهنمای تازه", "New email ایمیل / New phone تلفن"],
)
for index, hidden in enumerate(("not an address", "not a phone number", "hidden-email")):
    try:
        lab.capture_chat(chat_id=chat["id"], label=f"edited-hidden-{index}", contains=[hidden])
    except ScenarioError as error:
        assert error.code == "invalid_request" and not error.outcome_uncertain
    else:
        raise AssertionError("Capture accepted hidden or stale link metadata")
assert edited["history"] == lab.history(chat["id"])
"""
    project = tmp_path / "project"
    manifest = action_project(project, scenario)
    initial_input = SCENE["initial"] | {"skip_entity_detection": True}
    edited_input = SCENE["edited"] | {"skip_entity_detection": True}
    bot = BOT_TEMPLATE.replace("__INITIAL__", repr(json.dumps(initial_input))).replace(
        "__EDITED__", repr(json.dumps(edited_input))
    )
    (project / "bot.py").write_text(bot)
    output = tmp_path / "run"
    result = invoke(manifest, output)
    assert result.returncode == 0, (
        (output / "result.json").read_text() if output.exists() else result.stderr
    )
    recorded = json.loads((output / "result.json").read_text())
    show = {"id": 1, "chat_id": 1, "sender_id": 2, "date": 1700000000, "text": "show"}
    initial = {
        "id": 2,
        "chat_id": 1,
        "sender_id": 1,
        "date": 1700000000,
        "text": "",
        "rich_message": SCENE["initial"],
    }
    edit = show | {"id": 3, "text": "edit"}
    edited = initial | {"edit_date": 1700000000, "rich_message": SCENE["edited"]}
    assert recorded["outcome"] == "passed"
    assert recorded["histories"] == {"1": [show, edited, edit]}
    assert recorded["captures"] == [
        {"chat_id": 1, "label": "initial", "history": [show, initial], "rendered": False},
        {
            "chat_id": 1,
            "label": "after-edit",
            "history": [show, edited, edit],
            "rendered": False,
        },
    ]
