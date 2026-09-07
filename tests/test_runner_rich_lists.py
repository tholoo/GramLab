"""Public rich-list consumers retain canonical callback and capture evidence."""

import json
import os
import re
import shutil
from pathlib import Path
from typing import Any

import pytest

from gramlab.runner import run
from gramlab.runtime import RuntimeProfile

USER_MESSAGE = {
    "id": 1,
    "chat_id": 1,
    "sender_id": 2,
    "date": 1700000000,
    "text": "Show lists",
}
INITIAL_MESSAGE = {
    "id": 2,
    "chat_id": 1,
    "sender_id": 1,
    "date": 1700000000,
    "text": "",
    "rich_message": {
        "blocks": [
            {
                "type": "list",
                "items": [
                    {
                        "label": "a.",
                        "blocks": [{"type": "paragraph", "text": "سلام hello"}],
                        "type": "a",
                        "value": 1,
                    },
                    {
                        "label": "B.",
                        "blocks": [
                            {
                                "type": "paragraph",
                                "text": "راهنمای کوتاه English wraps onto a second line",
                            },
                            {
                                "type": "list",
                                "items": [
                                    {
                                        "label": "•",
                                        "blocks": [
                                            {
                                                "type": "paragraph",
                                                "text": "تو در تو nested",
                                            }
                                        ],
                                        "has_checkbox": True,
                                        "is_checked": True,
                                    },
                                    {
                                        "label": "•",
                                        "blocks": [{"type": "paragraph", "text": "Pending"}],
                                        "has_checkbox": True,
                                    },
                                ],
                            },
                            {
                                "type": "details",
                                "summary": "More",
                                "blocks": [
                                    {
                                        "type": "paragraph",
                                        "text": "Initial hidden detail",
                                    }
                                ],
                            },
                        ],
                        "type": "A",
                        "value": 2,
                    },
                    {
                        "label": "iii.",
                        "blocks": [{"type": "paragraph", "text": "سه roman"}],
                        "type": "i",
                        "value": 3,
                    },
                    {"label": "AA.", "blocks": [], "type": "A", "value": 27},
                ],
            }
        ]
    },
    "reply_markup": {
        "inline_keyboard": [
            [
                {"text": "Keep", "callback_data": "keep"},
                {"text": "Apply", "callback_data": "wrong"},
            ],
            [{"text": "Apply", "callback_data": "rtl-edit"}],
        ]
    },
}
EDITED_MESSAGE = {
    "id": 2,
    "chat_id": 1,
    "sender_id": 1,
    "date": 1700000000,
    "text": "",
    "edit_date": 1700000000,
    "rich_message": {
        "blocks": [
            {
                "type": "list",
                "items": [
                    {
                        "label": "•",
                        "blocks": [{"type": "paragraph", "text": "ویرایش راست‌به‌چپ RTL"}],
                    },
                    {
                        "label": "•",
                        "blocks": [
                            {"type": "paragraph", "text": "مرحله nested"},
                            {
                                "type": "list",
                                "items": [
                                    {
                                        "label": "IV.",
                                        "blocks": [{"type": "paragraph", "text": "چهار IV"}],
                                        "type": "I",
                                        "value": 4,
                                    },
                                    {
                                        "label": "5.",
                                        "blocks": [{"type": "paragraph", "text": "پنج decimal"}],
                                        "type": "1",
                                        "value": 5,
                                    },
                                ],
                            },
                        ],
                    },
                ],
            }
        ],
        "is_rtl": True,
    },
}
EXPECTED_WORLD = {
    "schema": 1,
    "seed": 7,
    "now": 1700000000,
    "users": [
        {"id": 1, "is_bot": True, "first_name": "lists"},
        {"id": 2, "is_bot": False, "first_name": "Sara", "language_code": "fa"},
    ],
    "chats": [{"id": 1, "type": "private", "user_id": 2, "bot_id": 1}],
}
EXPECTED_EVENTS = [
    {
        "sequence": 1,
        "type": "user.created",
        "data": {"is_bot": True, "first_name": "lists", "id": 1},
    },
    {
        "sequence": 2,
        "type": "user.created",
        "data": {
            "is_bot": False,
            "first_name": "Sara",
            "language_code": "fa",
            "id": 2,
        },
    },
    {
        "sequence": 3,
        "type": "chat.created",
        "data": {"id": 1, "type": "private", "user_id": 2, "bot_id": 1},
    },
    {"sequence": 4, "type": "message.created", "data": USER_MESSAGE},
    {"sequence": 5, "type": "message.created", "data": INITIAL_MESSAGE},
    {
        "sequence": 6,
        "type": "callback.created",
        "data": {
            "id": "<callback>",
            "user_id": 2,
            "chat_id": 1,
            "message": INITIAL_MESSAGE,
            "data": "rtl-edit",
            "chat_instance": "<world-scoped-chat>",
        },
    },
    {"sequence": 7, "type": "message.edited", "data": EDITED_MESSAGE},
    {
        "sequence": 8,
        "type": "callback.answered",
        "data": {
            "id": "<callback>",
            "user_id": 2,
            "answer": {"text": "Lists updated", "show_alert": False, "cache_time": 0},
        },
    },
]


def project(directory: Path) -> Path:
    directory.mkdir()
    for name in ("run.toml", "bot.py", "scenario.py"):
        shutil.copy2(Path("examples/rich_lists") / name, directory / name)
    return directory / "run.toml"


def require_android() -> None:
    profile = os.environ.get("GRAMLAB_ANDROID_RUNTIME_PROFILE")
    apk = os.environ.get("GRAMLAB_ANDROID_PROBE_APK")
    if profile is None or apk is None or not os.access("/dev/kvm", os.R_OK | os.W_OK):
        pytest.skip("Requires the provisioned Android profile, list-capable APK and KVM")


def execute(manifest: Path, output: Path, *, native: bool) -> dict[str, Any]:
    source = manifest.read_text()
    if native:
        source = source.replace('mode = "simulation-only"', 'mode = "headless-android"').replace(
            "timeout = 20", "timeout = 300"
        )
    manifest.write_text(source)
    run(
        manifest,
        output,
        profile=RuntimeProfile.load(Path(os.environ["GRAMLAB_RUNTIME_PROFILE"])),
        android_profile=RuntimeProfile.load(Path(os.environ["GRAMLAB_ANDROID_RUNTIME_PROFILE"]))
        if native
        else None,
        android_apk=Path(os.environ["GRAMLAB_ANDROID_PROBE_APK"]) if native else None,
    )
    recorded: dict[str, Any] = json.loads((output / "result.json").read_text())
    return recorded


def normalized_events(result: dict[str, Any]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = json.loads(json.dumps(result["events"]))
    for event in events:
        if event["type"].startswith("callback."):
            event["data"]["id"] = "<callback>"
            if "chat_instance" in event["data"]:
                event["data"]["chat_instance"] = "<world-scoped-chat>"
    return events


def verify(result: dict[str, Any], *, native: bool) -> None:
    assert result["outcome"] == "passed", result
    assert result["world"] == EXPECTED_WORLD
    assert result["histories"] == {"1": [USER_MESSAGE, EDITED_MESSAGE]}
    expected_captures = [
        {
            "chat_id": 1,
            "label": "before-tap",
            "history": [USER_MESSAGE, INITIAL_MESSAGE],
            "rendered": native,
        },
        {
            "chat_id": 1,
            "label": "after-edit",
            "history": [USER_MESSAGE, EDITED_MESSAGE],
            "rendered": native,
        },
        {
            "chat_id": 1,
            "label": "cold-reopen",
            "history": [USER_MESSAGE, EDITED_MESSAGE],
            "rendered": native,
        },
    ]
    if native:
        assert [
            {key: capture[key] for key in ("chat_id", "label", "history", "rendered")}
            for capture in result["captures"]
        ] == expected_captures
    else:
        assert result["captures"] == expected_captures
    assert normalized_events(result) == EXPECTED_EVENTS

    assert len(result["interactions"]) == 1
    interaction = result["interactions"][0]
    assert {key: interaction[key] for key in ("chat_id", "message_id", "row", "column")} == {
        "chat_id": 1,
        "message_id": 2,
        "row": 1,
        "column": 0,
    }
    assert interaction["native"] is native
    callback = interaction["callback"]
    assert callback["message"] == INITIAL_MESSAGE
    assert {key: callback[key] for key in ("user_id", "chat_id", "data")} == {
        "user_id": 2,
        "chat_id": 1,
        "data": "rtl-edit",
    }
    # Native observation may follow the real bot's answer; the scenario and complete
    # event comparison above independently require the final answer in either mode.
    assert callback["answer"] in (
        None,
        {"text": "Lists updated", "show_alert": False, "cache_time": 0},
    )
    assert re.fullmatch(r"[0-9a-f-]{36}", callback["id"])
    assert re.fullmatch(r"[0-9a-f]{64}", callback["chat_instance"])
    assert result["processes"]["bot:lists"] == {
        "exit_code": None,
        "stopped_by_runner": True,
        "stopped_by_scenario": False,
        "generation": 1,
        "stdout": "",
        "stdout_complete": False,
        "stderr": "",
        "stderr_complete": False,
    }
    assert result["processes"]["scenario"]["exit_code"] == 0
    assert "callback edit through two cold launches" in result["processes"]["scenario"]["stdout"]
    if native:
        assert interaction["android"]["target"]["text"] == "Apply"
        assert interaction["android"]["target"]["class"] == "android.widget.Button"


def test_rich_lists_real_bot_callback_edit_and_cold_reopen(tmp_path: Path) -> None:
    manifest = project(tmp_path / "project")
    result = execute(manifest, tmp_path / "run", native=False)
    verify(result, native=False)
    assert not list((tmp_path / "run").glob("captures/*.png"))
    report = (tmp_path / "run/report.html").read_text()
    assert "راهنمای کوتاه English wraps onto a second line" in report
    assert "ویرایش راست‌به‌چپ RTL" in report


@pytest.mark.android
def test_rich_lists_native_callback_matches_simulation(tmp_path: Path) -> None:
    require_android()
    manifest = project(tmp_path / "project")
    simulation = execute(manifest, tmp_path / "simulation", native=False)
    verify(simulation, native=False)
    android = execute(manifest, tmp_path / "android", native=True)
    verify(android, native=True)
    assert simulation["world"] == android["world"]
    assert simulation["histories"] == android["histories"]
    assert normalized_events(simulation) == normalized_events(android)
    for capture in android["captures"]:
        assert "Accounts: 0" in capture["android"]["accounts"]
        assert "Status: ok" in capture["android"]["launch"]
        assert (
            (tmp_path / "android/captures" / (capture["label"] + ".png"))
            .read_bytes()
            .startswith(b"\x89PNG\r\n\x1a\n")
        )
    assert android["android"]["network"]["ipv4"] != 0
    assert android["android"]["network"]["ipv6"] != 0
    report = (tmp_path / "android/report.html").read_text()
    assert report.count("data:image/png;base64,") == 3
    assert "gramlab-client_" not in report and "gramlab-control_" not in report


@pytest.mark.android
def test_rich_lists_offscreen_metadata_duplicate_rejects_before_input(tmp_path: Path) -> None:
    require_android()
    manifest = project(tmp_path / "project")
    scenario = manifest.parent / "scenario.py"
    with scenario.open("a") as script:
        script.write(
            """
from gramlab.scenario import ScenarioError
lab.send_message(chat_id=chat["id"], sender_id=user["id"], text="Show lists")
deadline = time.monotonic() + 10
while len(lab.history(chat["id"])) != 4:
    expect(time.monotonic() < deadline, "List competitor missing")
    time.sleep(0.05)
for index in range(30):
    lab.send_message(chat_id=chat["id"], sender_id=lab.bots()["lists"], text=f"Spacer {index}")
lab.send_message(chat_id=chat["id"], sender_id=user["id"], text="Duplicate lists")
deadline = time.monotonic() + 10
while len(lab.history(chat["id"])) != 36:
    expect(time.monotonic() < deadline, "Metadata duplicate missing")
    time.sleep(0.05)
duplicate = lab.history(chat["id"])[-1]
lab.capture_chat(
    chat_id=chat["id"],
    label="before-ambiguous",
    contains=["سلام hello", "Pending", "More"],
)
before = lab.events()
try:
    lab.tap_inline_button(chat_id=chat["id"], message_id=duplicate["id"], row=1, column=0)
except ScenarioError as error:
    expect(error.code == "server_error" and error.outcome_uncertain, "Wrong native failure")
else:
    raise AssertionError("Indistinguishable list metadata was accepted")
expect(lab.events() == before, "Ambiguous list input caused a world mutation")
"""
        )
    result = execute(manifest, tmp_path / "android", native=True)
    assert result["outcome"] == "failed" and result["failure"] == "interaction_failed", result
    assert result["processes"]["scenario"]["exit_code"] == 0
    assert result["android"]["input_failure"] == "Inline message text is ambiguous in this chat"
    assert len(result["interactions"]) == 2
    assert result["interactions"][1]["failure"] == "RuntimeError"
    callbacks = [event for event in result["events"] if event["type"] == "callback.created"]
    assert len(callbacks) == 1 and callbacks[0]["data"]["data"] == "rtl-edit"

    competitor = result["histories"]["1"][3]["rich_message"]["blocks"][0]["items"]
    duplicate = result["histories"]["1"][-1]["rich_message"]["blocks"][0]["items"]
    assert [(item["label"], item.get("type"), item.get("value")) for item in competitor] == [
        ("a.", "a", 1),
        ("B.", "A", 2),
        ("iii.", "i", 3),
        ("AA.", "A", 27),
    ]
    assert [(item["label"], item.get("type"), item.get("value")) for item in duplicate] == [
        ("A.", "A", 1),
        ("b.", "a", 2),
        ("III.", "I", 3),
        ("99.", "1", 99),
    ]
    competitor_nested = competitor[1]["blocks"][1]["items"]
    duplicate_nested = duplicate[1]["blocks"][1]["items"]
    assert all("has_checkbox" not in item for item in competitor)
    assert all("has_checkbox" not in item for item in duplicate)
    assert all(item["has_checkbox"] is True for item in competitor_nested)
    assert all(item["has_checkbox"] is True for item in duplicate_nested)
    assert competitor_nested[0]["is_checked"] is True
    assert "is_checked" not in duplicate_nested[0]
    assert "is_checked" not in competitor_nested[1]
    assert duplicate_nested[1]["is_checked"] is True
    assert competitor[3]["blocks"] == duplicate[3]["blocks"] == []
    assert competitor[1]["blocks"][2] == {
        "type": "details",
        "summary": "More",
        "blocks": [{"type": "paragraph", "text": "Initial hidden detail"}],
    }
    assert duplicate[1]["blocks"][2] == {
        "type": "details",
        "summary": "More",
        "blocks": [{"type": "paragraph", "text": "Duplicate hidden detail"}],
    }
    assert [capture["label"] for capture in result["captures"]] == [
        "before-tap",
        "after-edit",
        "cold-reopen",
        "before-ambiguous",
    ]
    assert (tmp_path / "android/report.html").read_text().count("data:image/png;base64,") == 4
