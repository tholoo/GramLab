"""Original composer sends commit and reconcile through the actual client."""

import json
import os
import shutil
import xml.etree.ElementTree as ET
from dataclasses import asdict
from pathlib import Path

import pytest
from composer_report import write_composer_report, write_live_gap_report

from gramlab.runtime import RuntimeProfile, Sandbox

pytestmark = pytest.mark.android


def run_composer(tmp_path: Path, boundary: str) -> dict:
    manifest, apk = (
        os.environ.get("GRAMLAB_ANDROID_RUNTIME_PROFILE"),
        os.environ.get("GRAMLAB_ANDROID_PROBE_APK"),
    )
    if manifest is None or apk is None or not os.access("/dev/kvm", os.R_OK | os.W_OK):
        pytest.skip("Requires the Android profile, APK and accessible KVM")
    profile = RuntimeProfile.load(Path(manifest))
    core = RuntimeProfile.load(Path(os.environ["GRAMLAB_RUNTIME_PROFILE"]))
    toolchain = json.loads(Path("clients/android/toolchain.json").read_text())
    image_package = (
        f"system-images;android-{toolchain['sdk']['platform']};"
        f"{toolchain['runtime']['imageType']};{toolchain['runtime']['abi']}"
    )
    shutil.copytree(
        "src/gramlab", tmp_path / "gramlab", ignore=shutil.ignore_patterns("__pycache__")
    )
    shutil.copy2(apk, tmp_path / "client.apk")
    shutil.copy2("tests/fixtures/echo_bot.py", tmp_path / "echo_bot.py")
    (tmp_path / "component-profile.json").write_text(json.dumps(asdict(core)))
    (tmp_path / "emulator-profile.json").write_text(json.dumps(asdict(profile)))
    (tmp_path / "interruption.json").write_text(json.dumps({"boundary": boundary}))
    for name in (
        "emulator_process.py",
        "component_bot.py",
        "android_guest.py",
        "android_composer.py",
        "jdwp.py",
        "android_live_gap.py",
    ):
        shutil.copy2(Path("tests/probes") / name, tmp_path / name)
    result = Sandbox(profile).supervise(
        [
            profile.python,
            "/work/android_composer.py",
            profile.executables["emulator"],
            profile.executables["adb"],
            profile.executables["avdmanager"],
            image_package,
        ],
        data=tmp_path,
        kvm=True,
        timeout=300,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)["extra_probe"]


@pytest.mark.parametrize("boundary", ["before_ack", "before_storage"])
def test_actual_composer_sends_equal_unicode_text_as_distinct_messages_and_recovers(
    tmp_path: Path,
    boundary: str,
) -> None:
    observed = run_composer(tmp_path, boundary)
    texts = [
        "composer-baseline",
        "سلام نیم‌فاصله e\u0301 👩🏽‍💻\nhello",
        "سلام نیم‌فاصله e\u0301 👩🏽‍💻\nhello",
    ]
    assert observed["history"] == [
        {"id": 1, "chat_id": 1, "sender_id": 2, "date": 1700000000, "text": "Write a message"},
        *[
            {"id": index + 2, "chat_id": 1, "sender_id": 1, "date": 1700000000, "text": text}
            for index, text in enumerate(texts)
        ],
        *[
            {
                "id": index + 5,
                "chat_id": 1,
                "sender_id": 2,
                "date": 1700000000,
                "text": "Echo: " + text,
            }
            for index, text in enumerate(texts)
        ],
    ]
    assert observed["position"] == 7
    assert [send["position"] for send in observed["sends"]] == [2, 3, 4]
    assert len({send["request_id"] for send in observed["sends"]}) == 3
    assert observed["pending"] == []
    assert (
        observed["inputs"]
        == [
            {
                "ok": True,
                "input": "accessibility",
                "text_verified": True,
                "send_actions": 1,
                "uid": 2000,
            }
        ]
        * 2
    )
    assert len(observed["rejections"]) == 1
    rejection = observed["rejections"][0]
    assert (rejection["ok"], rejection["phase"], rejection["error"]) == (
        False,
        "target",
        "stale_composer",
    )
    assert rejection["target"]["set_selection"]
    assert rejection["target"]["selection_start"] == rejection["target"]["selection_end"] == 0
    for phase in ("stored", "recovered"):
        assert observed[phase]["messages"] == [[2, index, 0] for index in range(1, 8)]
        assert observed[phase]["state"] == [7, 7, 1700000000, 0]
        # The supported profile has no peer read receipts; restarting cannot invent one.
        # Stock storage bit 0 means read, and bit 1 means media read (text has no media).
        assert observed[phase]["outgoing_read_state"] == [[2, 2], [3, 2], [4, 2]]
    assert all("LaunchState: COLD" in launch for launch in observed["launches"])
    assert "Echo:" in observed["restarted"]
    if boundary == "before_ack":
        assert observed["codec"] == {
            "rejected": 17,
            "sends": 2,
            "ack": {
                "id": 1,
                "date": 1700000000,
                "pts": 1,
                "pts_count": 1,
                "out": True,
                "flags": 130,
                "entity": "TL_messageEntityBold",
            },
            "pages": [
                {"type": "TL_updates_differenceSlice", "pts": 1, "seq": 1, "changes": 1},
                {"type": "TL_updates_difference", "pts": 2, "seq": 2, "changes": 1},
            ],
        }
    loss = observed["loss"]
    assert loss["boundary"] == boundary
    assert loss["input"] == observed["inputs"][0]
    assert loss["accepted"]["message"] == {
        "id": 8,
        "chat_id": 1,
        "sender_id": 1,
        "date": 1700000000,
        "text": "lost response بازیابی",
    }
    assert loss["accepted"]["position"] == 8
    correlations = loss["uncertain"]["pending_correlations"]
    assert len(correlations) == 1
    request_id, negative_id, peer = correlations[0]
    assert request_id == loss["accepted"]["request_id"] and negative_id < 0 and peer == 2
    assert loss["uncertain"]["messages"] == [
        [2, negative_id, 1],
        *[[2, index, 0] for index in range(1, 8)],
    ]
    if boundary == "before_storage":
        assert loss["breakpoint"] == {
            "class": "Lorg/telegram/messenger/MessagesStorage;",
            "method": "updateMessageStateAndId",
            "descriptor": "(JJLjava/lang/Integer;IIZII)[J",
            "code_index": 0,
            "suspend_policy": "event_thread",
            "thread_name": "storageQueue_0",
            "arguments": {
                "random_id": int(request_id),
                "dialogId": 2,
                "newId": 8,
                "useQueue": False,
            },
        }
        assert "lost response بازیابی" in loss["acknowledged_ui"]
    assert loss["reconciled"]["messages"] == [[2, index, 0] for index in range(1, 9)]
    assert loss["reconciled"]["pending_correlations"] == []
    assert loss["reconciled"]["state"] == [8, 8, 1700000000, 0]
    assert len(loss["pending_before_bot"]) == 1
    assert loss["pending_before_bot"][0]["message"] == loss["accepted"]["message"]
    assert len(loss["sends"]) == 4 and loss["sends"][-1] == loss["accepted"]
    assert loss["history"] == observed["history"] + [
        loss["accepted"]["message"],
        {
            "id": 9,
            "chat_id": 1,
            "sender_id": 2,
            "date": 1700000000,
            "text": "Echo: lost response بازیابی",
        },
    ]
    assert loss["replied"]["messages"] == [[2, index, 0] for index in range(1, 10)]
    assert loss["replied"]["state"] == [9, 9, 1700000000, 0]
    assert loss["replied"]["outgoing_read_state"] == [[2, 2], [3, 2], [4, 2], [8, 2]]
    assert "LaunchState: COLD" in loss["launch"]
    assert "lost response بازیابی" in loss["recovered_ui"]
    assert "Echo: lost response بازیابی" in loss["reply_ui"]
    for phase, status in (
        ("after-compose", "Not seen"),
        ("after-composer-restart", "Seen"),
        ("after-lost-response-reply", "Seen"),
    ):
        # Pinned ChatActivity marks loaded outgoing bot messages read in memory (line 21015).
        # Preserve that native display policy; it is separate from stored read state above.
        nodes = ET.fromstring((tmp_path / f"{phase}.xml").read_text()).iter("node")  # noqa: S314
        baseline = [
            node.get("text", "")
            for node in nodes
            if node.get("text", "").startswith("composer-baseline\n")
        ]
        assert baseline == [f"composer-baseline\nSent at 10:13 PM, {status}\n"], phase
    for name in ("before-compose", "after-compose", "after-composer-restart"):
        assert (tmp_path / f"{name}.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    write_composer_report(tmp_path)


def test_native_difference_recovers_withheld_messages_without_restart(tmp_path: Path) -> None:
    observed = run_composer(tmp_path, "live_gap")
    verify_live_gap(tmp_path, observed)
    write_live_gap_report(tmp_path)


def verify_live_gap(tmp_path: Path, observed: dict) -> None:
    """Verify fresh or retained observations with the same semantic and UI assertions."""
    texts = [
        "Write a message",
        "delayed message پیام",
        "Echo: delayed message پیام",
        "live gap بازیابی",
        "after recovery ادامه",
        "Echo: live gap بازیابی",
        "Echo: after recovery ادامه",
    ]
    assert observed["history"] == [
        {"id": index, "chat_id": 1, "sender_id": sender, "date": 1700000000, "text": text}
        for index, (sender, text) in enumerate(zip([2, 1, 2, 1, 1, 2, 2], texts, strict=True), 1)
    ]
    assert observed["position"] == 7
    assert [send["position"] for send in observed["sends"]] == [4, 5]
    assert len({send["request_id"] for send in observed["sends"]}) == 2
    assert observed["pending"] == []
    assert observed["stored"]["messages"] == [[2, index, 0] for index in range(1, 8)]
    assert observed["stored"]["state"] == [7, 7, 1700000000, 0]
    assert observed["stored"]["pending_correlations"] == []
    assert (
        observed["inputs"]
        == [
            {
                "ok": True,
                "input": "accessibility",
                "text_verified": True,
                "send_actions": 1,
                "uid": 2000,
            }
        ]
        * 2
    )
    assert len(set(observed["pids"])) == 1
    assert observed["pids"][0].isdigit()
    before = observed["before_trace"]
    recovered = observed["recovered_trace"]
    assert not any(
        row["method"] in ("TL_updates_getDifference", "TL_updates_getState") for row in before
    )
    assert not any(row["event"] == "events_applied" for row in recovered)
    differences = [row for row in recovered if row["method"] == "TL_updates_getDifference"]
    assert [row["event"] for row in differences] == ["request", "response"]
    assert differences[0]["token"] == differences[1]["token"]
    assert sum(row["event"] == "initialized" for row in observed["final_trace"]) == 1
    assert sum(row["event"] == "send_completed" for row in observed["final_trace"]) == 2
    assert observed["differences"] == [
        {
            "after": 1,
            "limit": 1000,
            "cursor": 4,
            "head": 4,
            "positions": [2, 3, 4],
            "status": 200,
        }
    ]
    assert "delayed message" not in observed["withheld_ui"]
    for text in texts[1:4]:
        assert text in observed["recovered_ui"]
    for text in texts[5:]:
        assert text in observed["final_ui"]
    for index, expected_ids in enumerate(([2], [4, 5])):
        transcript = observed["bots"][index]
        polls = [row for row in transcript if row["method"] == "getUpdates"]
        assert [
            row["message"]["message_id"] for row in polls[0]["response"]["result"]
        ] == expected_ids
        assert polls[-1]["response"] == {"ok": True, "result": []}
        assert len([row for row in transcript if row["method"] == "sendMessage"]) == len(
            expected_ids
        )
    # Pinned ChatActivity inserts equal-date arrivals before existing equal-date rows
    # in its reverse list, even when their IDs are older (line 25800). All fixture
    # messages share one world second. Preserve this stock display policy separately
    # from the authoritative ID order asserted above; do not rewrite dates to hide it.
    for name, expected_ids in (
        ("gap-recovered", [1, 4, 2, 3]),
        ("gap-replied", [1, 4, 2, 3, 5, 6, 7]),
    ):
        nodes = ET.fromstring((tmp_path / f"{name}.xml").read_text()).iter("node")  # noqa: S314
        rendered = [
            node.get("text", "").split("\n", 1)[0]
            for node in nodes
            if "\nSent at " in node.get("text", "") or "\nReceived at " in node.get("text", "")
        ]
        assert rendered == [texts[index - 1] for index in expected_ids]
    for name in ("gap-before", "gap-withheld", "gap-recovered", "gap-replied"):
        assert (tmp_path / f"{name}.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
