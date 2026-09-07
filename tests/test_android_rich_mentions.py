"""Original live mention edits, ordinary inline taps and persisted removal."""

import hashlib
import json
import os
import shutil
import xml.etree.ElementTree as ET
from dataclasses import asdict
from pathlib import Path

import pytest
from test_android_quoted_code import USERS, assert_isolation
from test_rich_mentions_round_trip import assert_scenario, rich_content, stage_scenario

from gramlab.reports import Report, Screenshot, write_report
from gramlab.runtime import RuntimeProfile, Sandbox

pytestmark = pytest.mark.android
PHASES = ("initial", "edited", "removed", "restarted")
NATIVE_A = {
    "id": 3,
    "first_name": "Arman",
    "self": False,
    "bot": False,
    "username": "arman_local",
    "language_code": "fa",
    "phone": None,
}
NATIVE_B = {
    "id": 4,
    "first_name": "Mina",
    "self": False,
    "bot": False,
    "username": "mina_local",
    "language_code": "en",
    "phone": None,
}


def test_real_bot_mentions_render_first_disclosure_remove_and_cold_restart(tmp_path: Path) -> None:
    manifest = os.environ.get("GRAMLAB_ANDROID_RUNTIME_PROFILE")
    apk = os.environ.get("GRAMLAB_ANDROID_PROBE_APK")
    if manifest is None or apk is None or not os.access("/dev/kvm", os.R_OK | os.W_OK):
        pytest.skip("Requires the reviewed mention APK, provisioned Android profile and KVM")
    profile = RuntimeProfile.load(Path(manifest))
    stage_scenario(tmp_path, RuntimeProfile.load(Path(os.environ["GRAMLAB_RUNTIME_PROFILE"])))
    shutil.copy2(apk, tmp_path / "client.apk")
    (tmp_path / "emulator-profile.json").write_text(json.dumps(asdict(profile)))
    for name in ("emulator_process.py", "android_guest.py", "android_rich_mentions.py"):
        shutil.copy2(Path("tests/probes") / name, tmp_path / name)
    toolchain = json.loads(Path("clients/android/toolchain.json").read_text())
    package = (
        f"system-images;android-{toolchain['sdk']['platform']};"
        f"{toolchain['runtime']['imageType']};{toolchain['runtime']['abi']}"
    )
    result = Sandbox(profile).supervise(
        [
            profile.python,
            "/work/android_rich_mentions.py",
            profile.executables["emulator"],
            profile.executables["adb"],
            profile.executables["avdmanager"],
            package,
        ],
        data=tmp_path,
        kvm=True,
        timeout=420,
    )
    (tmp_path / "rich-mentions-native-result.json").write_text(result.stdout)
    (tmp_path / "rich-mentions-native-stderr.log").write_text(result.stderr)
    assert result.returncode == 0, result.stderr
    full = json.loads(result.stdout)
    assert_isolation(full)
    observed = full["extra_probe"]
    assert_scenario(observed)
    client = observed["client"]
    assert set(client["codecs"]) == set(PHASES)
    assert set(client["launches"]) == {"initial", "restarted"}
    assert set(client["taps"]) == {"initial", "edited"}
    assert "Accounts: 0" in client["accounts"]
    for launch in client["launches"].values():
        assert "Status: ok" in launch and "LaunchState: COLD" in launch
    for phase in PHASES:
        users = USERS + (
            [NATIVE_A] if phase == "initial" else [NATIVE_B] if phase == "edited" else []
        )
        expected_codec = {
            "persona": 1,
            "cursor": 9 if phase == "initial" else 13 if phase == "edited" else 17,
            "now": 1700000000
            if phase == "initial"
            else 1700000005
            if phase == "edited"
            else 1700000010,
            "users": users,
            "dialogs": [{"peer_id": 2, "top_message": 2}],
            "dialog_message_count": 1,
            "history_users": [{"peer_id": 2, "user_ids": [user["id"] for user in users]}],
            "messages": [
                {
                    "id": 2,
                    "sender_id": 2,
                    "recipient_id": 1,
                    "out": False,
                    "date": 1700000000,
                    "text": "",
                    "rich_message": rich_content(phase),
                },
                {
                    "id": 1,
                    "sender_id": 1,
                    "recipient_id": 2,
                    "out": True,
                    "date": 1700000000,
                    "text": "Show explicit mentions",
                },
            ],
        }
        assert client["codecs"][phase] == expected_codec
        assert (tmp_path / f"{phase}.xml").read_text() == client[phase]
        ui = ET.fromstring(client[phase])  # noqa: S314 — dedicated guest UIAutomator output
        labels = "\n".join(
            node.get("text", "") + node.get("content-desc", "") for node in ui.iter("node")
        )
        required = (
            ("Explicit mention A", "Arman", "آرمان", "Mention B / نفر بعد")
            if phase == "initial"
            else (
                ("Explicit mention B", "Mina", "مینا", "Remove mention / حذف نام")
                if phase == "edited"
                else ("Mentions removed", "No named user", "اشاره حذف شد")
            )
        )
        assert all(text in labels for text in required), phase
        forbidden = (
            ("Mina", "Explicit mention B")
            if phase == "initial"
            else (
                ("Arman", "Explicit mention A")
                if phase == "edited"
                else (
                    "Explicit mention A",
                    "Explicit mention B",
                    "Mention B / نفر بعد",
                    "Remove mention / حذف نام",
                )
            )
        )
        assert all(text not in labels for text in forbidden), phase
        assert "Forged" not in labels and "forged" not in labels
        assert (tmp_path / f"{phase}.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    for phase, label in (
        ("initial", "Mention B / نفر بعد"),
        ("edited", "Remove mention / حذف نام"),
    ):
        tap = client["taps"][phase]
        assert 0 < tap["x"] < 320 and 0 < tap["y"] < 640
        assert label in tap["node"].get("text", "") + tap["node"].get("content-desc", "")
    traces = {
        phase: [
            json.loads(line)
            for line in (tmp_path / f"{phase}-trace.jsonl").read_text().splitlines()
        ]
        for phase in PHASES
    }
    for phase in ("edited", "removed"):
        assert sum(event["event"] == "events_applied" for event in traces[phase]) >= (
            1 if phase == "edited" else 2
        )
    final_trace = [json.loads(line) for line in client["trace"].splitlines()]
    assert sum(event["event"] == "initialized" for event in final_trace) == 2
    assert not any(
        event["event"] in ("startup_rejected", "bridge_failure", "event_error")
        for event in final_trace
    )
    write_report(
        tmp_path / "report.html",
        Report(
            run_id="rich-mentions-original-callback-edit-remove-restart",
            title="Explicit mentions in original Android",
            mode="headless-android",
            outcome="passed",
            seed=29,
            profile={
                "Android": "Pinned client; AOSP API 36; 320 x 640 at 160 dpi",
                "APK SHA-256": hashlib.sha256(Path(apk).read_bytes()).hexdigest(),
            },
            summary="A real bot mentions contact A, original inline taps edit to newly "
            "disclosed contact B "
            "and then remove mentions, and the original client restarts with the final content.",
            evidence={
                "bot": observed["bot"],
                "snapshots": observed["snapshots"],
                "callbacks": observed["callbacks"],
                "changes": observed["changes"],
                "events": observed["events"],
                "native": client["codecs"],
                "taps": client["taps"],
            },
            limitations=(
                "Structured explicit mentions only. Mention navigation and automatic detection "
                "are not exercised; custom emoji, rich-button target APIs and Mini Apps "
                "remain separate.",
                "Snapshots and serialized envelopes establish identity dependencies; "
                "controller ordering "
                "also relies on the reviewed original update path, not an injected observer.",
            ),
            timings={
                name.removesuffix("_seconds"): value * 1000
                for name, value in client["timings"].items()
            },
            screenshots=tuple(
                Screenshot(png=(tmp_path / f"{phase}.png").read_bytes(), caption=phase)
                for phase in PHASES
            ),
        ),
    )
