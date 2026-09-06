"""Original composer sends commit and reconcile through the actual client."""

import json
import os
import shutil
import xml.etree.ElementTree as ET
from dataclasses import asdict
from pathlib import Path

import pytest
from composer_report import write_composer_report

from gramlab.runtime import RuntimeProfile, Sandbox

pytestmark = pytest.mark.android


def test_actual_composer_sends_equal_unicode_text_as_distinct_messages_and_recovers(
    tmp_path: Path,
) -> None:
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
    for name in (
        "emulator_process.py",
        "component_bot.py",
        "android_guest.py",
        "android_composer.py",
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
    observed = json.loads(result.stdout)["extra_probe"]
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
    assert [2, negative_id, 1] in loss["uncertain"]["messages"]
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
