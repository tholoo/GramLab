"""Bot-owned list checkboxes remain read-only through original input and live edits."""

import hashlib
import json
import os
import shutil
import xml.etree.ElementTree as ET
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pytest
from test_rich_round_trip import stage_rich_scenario

from gramlab.reports import Report, Screenshot, write_report
from gramlab.runtime import RuntimeProfile, Sandbox

pytestmark = pytest.mark.android

INPUT_SCENE = {
    "initial": {
        "blocks": [
            {
                "type": "list",
                "items": [
                    {
                        "blocks": [{"type": "paragraph", "text": "Unchecked task"}],
                        "has_checkbox": True,
                    },
                    {"blocks": [], "has_checkbox": True, "is_checked": True},
                    {
                        "blocks": [{"type": "paragraph", "text": "Checked task"}],
                        "has_checkbox": True,
                        "is_checked": True,
                    },
                    {
                        "blocks": [
                            {
                                "type": "list",
                                "items": [
                                    {
                                        "blocks": [
                                            {"type": "paragraph", "text": "Nested فارسی"},
                                        ],
                                        "type": "A",
                                        "value": 27,
                                    }
                                ],
                            }
                        ]
                    },
                ],
            }
        ]
    },
    "edited": {
        "is_rtl": True,
        "blocks": [
            {
                "type": "list",
                "items": [
                    {
                        "blocks": [{"type": "paragraph", "text": "انجام شد"}],
                        "has_checkbox": True,
                        "is_checked": True,
                    },
                    {"blocks": [], "has_checkbox": True},
                    {"blocks": [{"type": "paragraph", "text": "باز مانده"}], "has_checkbox": True},
                    {
                        "blocks": [
                            {
                                "type": "list",
                                "items": [
                                    {
                                        "blocks": [
                                            {"type": "paragraph", "text": "Nested edited"},
                                        ],
                                        "type": "i",
                                        "value": 4,
                                    }
                                ],
                            }
                        ]
                    },
                ],
            }
        ],
    },
}

EXPECTED_SCENE = {
    "initial": {
        "blocks": [
            {
                "type": "list",
                "items": [
                    {
                        "label": "•",
                        "blocks": [{"type": "paragraph", "text": "Unchecked task"}],
                        "has_checkbox": True,
                    },
                    {"label": "•", "blocks": [], "has_checkbox": True, "is_checked": True},
                    {
                        "label": "•",
                        "blocks": [{"type": "paragraph", "text": "Checked task"}],
                        "has_checkbox": True,
                        "is_checked": True,
                    },
                    {
                        "label": "•",
                        "blocks": [
                            {
                                "type": "list",
                                "items": [
                                    {
                                        "label": "AA.",
                                        "blocks": [
                                            {"type": "paragraph", "text": "Nested فارسی"},
                                        ],
                                        "type": "A",
                                        "value": 27,
                                    }
                                ],
                            }
                        ],
                    },
                ],
            }
        ]
    },
    "edited": {
        "is_rtl": True,
        "blocks": [
            {
                "type": "list",
                "items": [
                    {
                        "label": "•",
                        "blocks": [{"type": "paragraph", "text": "انجام شد"}],
                        "has_checkbox": True,
                        "is_checked": True,
                    },
                    {"label": "•", "blocks": [], "has_checkbox": True},
                    {
                        "label": "•",
                        "blocks": [{"type": "paragraph", "text": "باز مانده"}],
                        "has_checkbox": True,
                    },
                    {
                        "label": "•",
                        "blocks": [
                            {
                                "type": "list",
                                "items": [
                                    {
                                        "label": "iv.",
                                        "blocks": [
                                            {"type": "paragraph", "text": "Nested edited"},
                                        ],
                                        "type": "i",
                                        "value": 4,
                                    }
                                ],
                            }
                        ],
                    },
                ],
            }
        ],
    },
}


def test_bot_list_checkboxes_render_reject_user_mutation_and_follow_bot_edit(
    tmp_path: Path,
) -> None:
    manifest = os.environ.get("GRAMLAB_ANDROID_RUNTIME_PROFILE")
    apk = os.environ.get("GRAMLAB_ANDROID_PROBE_APK")
    if manifest is None or apk is None or not os.access("/dev/kvm", os.R_OK | os.W_OK):
        pytest.skip("Requires the provisioned Android profile, list APK and KVM")
    profile = RuntimeProfile.load(Path(manifest))
    core = RuntimeProfile.load(Path(os.environ["GRAMLAB_RUNTIME_PROFILE"]))
    stage_rich_scenario(tmp_path, core)
    (tmp_path / "rich-scene.json").write_text(json.dumps(INPUT_SCENE))
    shutil.copy2(apk, tmp_path / "client.apk")
    (tmp_path / "emulator-profile.json").write_text(json.dumps(asdict(profile)))
    for name in (
        "emulator_process.py",
        "android_guest.py",
        "android_rich_messages.py",
        "android_list_rendering.py",
    ):
        shutil.copy2(Path("tests/probes") / name, tmp_path / name)
    result = Sandbox(profile).supervise(
        [
            profile.python,
            "/work/android_list_rendering.py",
            profile.executables["emulator"],
            profile.executables["adb"],
            profile.executables["avdmanager"],
            "system-images;android-36;default;x86_64",
        ],
        data=tmp_path,
        kvm=True,
        timeout=300,
    )
    (tmp_path / "list-rendering-result.json").write_text(result.stdout)
    assert result.returncode == 0, result.stderr
    full = json.loads(result.stdout)
    assert full["host_interfaces"] == [[1, "lo"]]
    assert "Accounts: 0" in full["accounts"]
    for family in ("ipv4", "ipv6"):
        assert full["network"][family] == {
            "returncode": 1,
            "stdout": "",
            "stderr": "nc: connect: Network is unreachable\n",
        }
    observed = full["extra_probe"]
    initial: dict[str, Any] = {
        "message_id": 2,
        "from": {"id": 2, "is_bot": True, "first_name": "Echo", "username": "gramlab_echo_bot"},
        "chat": {"id": 1, "type": "private", "first_name": "Sara"},
        "date": 1700000000,
        "rich_message": EXPECTED_SCENE["initial"],
    }
    assert observed["initial"] == initial
    assert observed["edited"] == initial | {
        "edit_date": 1700000005,
        "rich_message": EXPECTED_SCENE["edited"],
    }
    assert observed["history"] == [
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
    ]
    assert observed["pending"] == []
    client = observed["client"]
    for phase in ("initial", "edited"):
        messages = client["codecs"][phase]["messages"]
        assert len(messages) == 2
        assert messages[0]["rich_message"] == EXPECTED_SCENE[phase]
    for launch in client["launches"].values():
        assert "Status: ok" in launch and "LaunchState: COLD" in launch
    for phase in ("edited", "restarted"):
        tree = ET.fromstring(client[phase])  # noqa: S314 — dedicated guest UIAutomator XML
        nodes = [
            node for node in tree.iter("node") if node.get("class") == "android.widget.CheckBox"
        ]
        assert [node.get("checked") for node in nodes] == ["true", "false"]
        assert all(node.get("clickable") == "false" for node in nodes)
    checkbox = observed["checkbox"]
    assert checkbox["before"] == checkbox["after"]
    assert checkbox["world_unchanged"] is True
    assert checkbox["target"]["node"] == checkbox["before"][0]
    assert isinstance(checkbox["menu_dismissed"], bool)
    write_report(
        tmp_path / "report.html",
        Report(
            run_id="rich-list-checkbox-send-edit-restart",
            title="Lists and bot-owned checkboxes in Android",
            mode="headless-android",
            outcome="passed",
            seed=7,
            profile={
                "Android": "Pinned client; AOSP API 36; 320 x 640 at 160 dpi",
                "APK SHA-256": hashlib.sha256(Path(apk).read_bytes()).hexdigest(),
            },
            summary="A local bot sends list checkboxes, edits their state and switches to RTL. "
            "A user tap preserves bot-owned checkbox state and the complete message.",
            evidence={
                "Bot and native observations": observed,
                "Network isolation": full["network"],
            },
            timings={
                name.removesuffix("_seconds"): value * 1000
                for name, value in client["timings"].items()
            },
            screenshots=[
                Screenshot(caption=phase, png=(tmp_path / f"{phase}.png").read_bytes())
                for phase in ("initial", "checkbox-action", "after-checkbox", "edited", "restarted")
            ],
            limitations=[
                "User checkbox editing is unsupported for incoming bot messages.",
                "Empty list items are retained semantically and skipped by the original renderer.",
                "This bounded scene does not cover media or every rich-message block.",
            ],
        ),
    )
