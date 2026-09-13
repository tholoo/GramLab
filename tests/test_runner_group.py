"""The generic group example exercises a real contained Bot API consumer."""

import json
import os
from pathlib import Path

from gramlab.runner import run
from gramlab.runtime import RuntimeProfile


def test_group_example_proves_membership_delivery_callback_and_edit(tmp_path: Path) -> None:
    output = tmp_path / "run"
    assert (
        run(
            Path("examples/group/run.toml"),
            output,
            profile=RuntimeProfile.load(Path(os.environ["GRAMLAB_RUNTIME_PROFILE"])),
        )
        == "passed"
    ), (output / "result.json").read_text()
    result = json.loads((output / "result.json").read_text())
    group = result["world"]["chats"][0]
    assert group == {
        "id": -1,
        "type": "supergroup",
        "title": "Study group",
        "members": [
            {"user_id": 1, "status": "member"},
            {"user_id": 2, "status": "creator"},
            {"user_id": 3, "status": "member"},
        ],
    }
    assert [message["text"] for message in result["histories"]["-1"]] == [
        "/game",
        "Continued for the group",
        "after restart",
        "Ready for the group",
    ]
    assert result["interactions"][0]["callback"]["user_id"] == 3
    assert [record["operation"] for record in result["lifecycle"]] == [
        "stop_bot",
        "start_bot",
    ]
    assert [capture["label"] for capture in result["captures"]] == [
        "group-before",
        "group-after",
        "group-restarted",
    ]
