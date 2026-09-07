"""Independent dirty/canonical fixtures cross real bot HTTP and durable world boundaries."""

# Intentional Persian text exercises Unicode preservation.
# ruff: noqa: RUF001

import json
import os
from pathlib import Path
from typing import Any

from test_rich_round_trip import stage_rich_scenario

from gramlab.runtime import RuntimeProfile, Sandbox

# Hand-authored from docs/development/rich-text-cleaning.md; never derive the oracle
# from these inputs or call the production normalizer to construct expectations.
INPUT_SCENE = {
    "initial": {
        "blocks": [
            {"type": "heading", "text": "Clean\tsta\u202art", "size": 2},
            {
                "type": "paragraph",
                "text": [
                    "Amber\t42 ",
                    {"type": "bold", "text": "A\u030aB\u0333C\u033fD"},
                    " X\u200e\u200f\u200eY\nفارسی می\u200cماند",
                ],
            },
            {"type": "pre", "text": "print\t1", "language": "\u202epy\u030a"},
            {
                "type": "table",
                "caption": "\u2028\u2029",
                "cells": [[{"text": "Value\t7"}]],
            },
        ]
    },
    "edited": {
        "is_rtl": True,
        "blocks": [
            {"type": "heading", "text": "متن\tپا\u202bک", "size": 2},
            {
                "type": "paragraph",
                "text": [
                    "فارسی\tمی\u200cماند ",
                    {"type": "bold", "text": "E\u030aF\u0333G\u033fH"},
                    " R\u200f\u200eL",
                ],
            },
            {"type": "pre", "text": "note\t2", "language": "\u202c\u033f"},
            {
                "type": "table",
                "caption": "جدول\tپاک",
                "cells": [[{"text": "عدد\t۸"}]],
            },
        ],
    },
}

EXPECTED_SCENE = {
    "initial": {
        "blocks": [
            {"type": "heading", "text": "Clean start", "size": 2},
            {
                "type": "paragraph",
                "text": [
                    "Amber 42 ",
                    {"type": "bold", "text": "ABCD"},
                    " X\u200c\u200c\u200eY\nفارسی می\u200cماند",
                ],
            },
            {"type": "pre", "text": "print 1", "language": "py"},
            {
                "type": "table",
                "cells": [[{"text": "Value 7", "align": "left", "valign": "middle"}]],
            },
        ]
    },
    "edited": {
        "is_rtl": True,
        "blocks": [
            {"type": "heading", "text": "متن پاک", "size": 2},
            {
                "type": "paragraph",
                "text": [
                    "فارسی می\u200cماند ",
                    {"type": "bold", "text": "EFGH"},
                    " R\u200c\u200eL",
                ],
            },
            {"type": "pre", "text": "note 2"},
            {
                "type": "table",
                "caption": "جدول پاک",
                "cells": [[{"text": "عدد ۸", "align": "left", "valign": "middle"}]],
            },
        ],
    },
}


def stage_cleaning_scenario(directory: Path, core: RuntimeProfile) -> None:
    stage_rich_scenario(directory, core)
    (directory / "rich-scene.json").write_text(json.dumps(INPUT_SCENE))
    (directory / "expected-rich-scene.json").write_text(json.dumps(EXPECTED_SCENE))


def assert_cleaning_scenario(observed: dict[str, Any]) -> None:
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


def test_real_bot_cleans_rich_send_edit_and_durable_history(tmp_path: Path) -> None:
    profile = RuntimeProfile.load(Path(os.environ["GRAMLAB_RUNTIME_PROFILE"]))
    stage_cleaning_scenario(tmp_path, profile)
    result = Sandbox(profile).supervise(
        [profile.python, "/work/rich_round_trip.py"], data=tmp_path, timeout=30
    )
    (tmp_path / "cleaning-result.json").write_text(result.stdout)
    (tmp_path / "cleaning-stderr.log").write_text(result.stderr)
    assert result.returncode == 0, result.stderr
    assert_cleaning_scenario(json.loads(result.stdout))
