"""Independent rich-action scenes cross real Bot API and durable world boundaries."""

import json
import os
from pathlib import Path
from typing import Any

from test_rich_round_trip import stage_rich_scenario

from gramlab.runtime import RuntimeProfile, Sandbox

# Hand-authored from docs/development/rich-buttons-contract.md. Canonical expectations are
# deliberately independent from the input and production normalizer.
INPUT_SCENE = {
    "initial": {
        "blocks": [
            {"type": "heading", "text": "Actions / کنش", "size": 2},
            {"type": "paragraph", "text": "Initial anchor / لنگر"},
            {
                "type": "buttons",
                "buttons": [
                    {
                        "text": ["Go\t", "برو"],
                        "style": "PrImArY",
                        "callback_data": "go:initial",
                    },
                    {
                        "text": "Copy / کپی",
                        "style": "SUCCESS",
                        "copy_text": {"text": "Amber\t42"},
                    },
                ],
            },
            {
                "type": "buttons",
                "align": "left",
                "buttons": [
                    {"text": "Later / بعد", "style": "DANGER", "disabled": {}},
                    {
                        "text": "Link / پیوند",
                        "style": "LINK",
                        "callback_data": "link:initial",
                    },
                ],
            },
            {
                "type": "paragraph",
                "text": [
                    "Inline ",
                    {
                        "type": "button",
                        "button": {"text": "Tap / لمس", "callback_data": "inline:initial"},
                    },
                    " end",
                ],
            },
        ]
    },
    "edited": {
        "is_rtl": True,
        "blocks": [
            {"type": "heading", "text": "ویرایش / Edit", "size": 2},
            {"type": "paragraph", "text": "RTL anchor / لنگر راست"},
            {
                "type": "buttons",
                "align": "right",
                "buttons": [
                    {
                        "text": "تأیید / OK",
                        "style": "PRIMARY",
                        "callback_data": "ok:edited",
                    },
                    {
                        "text": ["کپی ", "نو"],
                        "style": "success",
                        "copy_text": {"text": "متن\tنو"},
                    },
                ],
            },
            {
                "type": "buttons",
                "align": "center",
                "buttons": [
                    {"text": "بسته / Off", "style": "danger", "disabled": {}},
                    {
                        "text": "پیوند / Link",
                        "style": "link",
                        "callback_data": "link:edited",
                    },
                ],
            },
            {
                "type": "paragraph",
                "text": [
                    "درون ",
                    {
                        "type": "button",
                        "button": {"text": "لمس / Tap", "callback_data": "inline:edited"},
                    },
                ],
            },
        ],
    },
}

EXPECTED_SCENE = {
    "initial": {
        "blocks": [
            {"type": "heading", "text": "Actions / کنش", "size": 2},
            {"type": "paragraph", "text": "Initial anchor / لنگر"},
            {
                "type": "buttons",
                "buttons": [
                    {
                        "text": ["Go ", "برو"],
                        "style": "primary",
                        "callback_data": "go:initial",
                    },
                    {
                        "text": "Copy / کپی",
                        "style": "success",
                        "copy_text": {"text": "Amber 42"},
                    },
                ],
            },
            {
                "type": "buttons",
                "buttons": [
                    {"text": "Later / بعد", "style": "danger", "disabled": {}},
                    {
                        "text": "Link / پیوند",
                        "style": "link",
                        "callback_data": "link:initial",
                    },
                ],
                "align": "left",
            },
            {
                "type": "paragraph",
                "text": [
                    "Inline ",
                    {
                        "type": "button",
                        "button": {"text": "Tap / لمس", "callback_data": "inline:initial"},
                    },
                    " end",
                ],
            },
        ]
    },
    "edited": {
        "blocks": [
            {"type": "heading", "text": "ویرایش / Edit", "size": 2},
            {"type": "paragraph", "text": "RTL anchor / لنگر راست"},
            {
                "type": "buttons",
                "buttons": [
                    {
                        "text": "تأیید / OK",
                        "style": "primary",
                        "callback_data": "ok:edited",
                    },
                    {
                        "text": ["کپی ", "نو"],
                        "style": "success",
                        "copy_text": {"text": "متن نو"},
                    },
                ],
                "align": "right",
            },
            {
                "type": "buttons",
                "buttons": [
                    {"text": "بسته / Off", "style": "danger", "disabled": {}},
                    {
                        "text": "پیوند / Link",
                        "style": "link",
                        "callback_data": "link:edited",
                    },
                ],
                "align": "center",
            },
            {
                "type": "paragraph",
                "text": [
                    "درون ",
                    {
                        "type": "button",
                        "button": {"text": "لمس / Tap", "callback_data": "inline:edited"},
                    },
                ],
            },
        ],
        "is_rtl": True,
    },
}


def stage_action_scenario(directory: Path, core: RuntimeProfile) -> None:
    stage_rich_scenario(directory, core)
    (directory / "rich-scene.json").write_text(json.dumps(INPUT_SCENE))
    (directory / "expected-rich-scene.json").write_text(json.dumps(EXPECTED_SCENE))


def assert_action_scenario(observed: dict[str, Any]) -> None:
    initial = {
        "message_id": 2,
        "from": {"id": 2, "is_bot": True, "first_name": "Echo", "username": "gramlab_echo_bot"},
        "chat": {"id": 1, "type": "private", "first_name": "Sara"},
        "date": 1700000000,
        "rich_message": EXPECTED_SCENE["initial"],
    }
    assert {key: value for key, value in observed.items() if key != "client"} == {
        "initial": initial,
        "edited": initial | {"edit_date": 1700000005, "rich_message": EXPECTED_SCENE["edited"]},
        "history": [
            {"id": 1, "chat_id": 1, "sender_id": 1, "date": 1700000000, "text": "Show rich blocks"},
            {
                "id": 2,
                "chat_id": 1,
                "sender_id": 2,
                "date": 1700000000,
                "edit_date": 1700000005,
                "text": "",
                "rich_message": EXPECTED_SCENE["edited"],
            },
        ],
        "pending": [],
    }


def test_real_bot_sends_edits_and_reopens_complete_rich_actions(tmp_path: Path) -> None:
    profile = RuntimeProfile.load(Path(os.environ["GRAMLAB_RUNTIME_PROFILE"]))
    stage_action_scenario(tmp_path, profile)
    result = Sandbox(profile).supervise(
        [profile.python, "/work/rich_round_trip.py"], data=tmp_path, timeout=30
    )
    (tmp_path / "rich-action-result.json").write_text(result.stdout)
    (tmp_path / "rich-action-stderr.log").write_text(result.stderr)
    assert result.returncode == 0, result.stderr
    assert_action_scenario(json.loads(result.stdout))
