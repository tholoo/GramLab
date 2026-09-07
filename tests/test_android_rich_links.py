"""Independent native metadata validation and original rich-link rendering."""

import hashlib
import json
import os
import shutil
import xml.etree.ElementTree as ET
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pytest
from test_android_quoted_code import USERS, assert_isolation
from test_rich_links_round_trip import SCENE, assert_scenario, stage_scenario

from gramlab.reports import Report, Screenshot, write_report
from gramlab.runtime import RuntimeProfile, Sandbox

pytestmark = pytest.mark.android


def run_probe(directory: Path, module: str) -> tuple[dict[str, Any], str]:
    manifest = os.environ.get("GRAMLAB_ANDROID_RUNTIME_PROFILE")
    apk = os.environ.get("GRAMLAB_ANDROID_PROBE_APK")
    if manifest is None or apk is None or not os.access("/dev/kvm", os.R_OK | os.W_OK):
        pytest.skip("Requires the provisioned Android profile, normal APK and KVM")
    profile = RuntimeProfile.load(Path(manifest))
    stage_scenario(directory, RuntimeProfile.load(Path(os.environ["GRAMLAB_RUNTIME_PROFILE"])))
    shutil.copy2(apk, directory / "client.apk")
    (directory / "emulator-profile.json").write_text(json.dumps(asdict(profile)))
    for name in (
        "emulator_process.py",
        "android_guest.py",
        "android_rich_messages.py",
        "android_rich_links.py",
        "android_message_codec.py",
    ):
        shutil.copy2(Path("tests/probes") / name, directory / name)
    toolchain = json.loads(Path("clients/android/toolchain.json").read_text())
    package = (
        f"system-images;android-{toolchain['sdk']['platform']};"
        f"{toolchain['runtime']['imageType']};{toolchain['runtime']['abi']}"
    )
    result = Sandbox(profile).supervise(
        [
            profile.python,
            f"/work/{module}.py",
            profile.executables["emulator"],
            profile.executables["adb"],
            profile.executables["avdmanager"],
            package,
        ],
        data=directory,
        kvm=True,
        timeout=420,
    )
    (directory / "rich-links-native-result.json").write_text(result.stdout)
    (directory / "rich-links-native-stderr.log").write_text(result.stderr)
    assert result.returncode == 0, result.stderr
    full = json.loads(result.stdout)
    assert_isolation(full)
    return full["extra_probe"], apk


def codec_cases() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []

    def add(name: str, rich: dict[str, Any], *, valid: bool) -> None:
        cases.append({"name": name, "content": {"text": "", "rich_message": rich}, "valid": valid})

    for phase in ("initial", "edited"):
        add(phase, SCENE[phase], valid=True)
    for kind, metadata in (
        ("url", "https://example.invalid/path"),
        ("email_address", "team@example.invalid"),
        ("phone_number", "+12025550123"),
    ):
        for label, value in (("address", metadata), ("empty", ""), ("arbitrary", "not an address")):
            add(
                f"{kind}-{label}",
                {
                    "blocks": [
                        {
                            "type": "paragraph",
                            "text": {
                                "type": kind,
                                "text": ["A😀", {"type": "code", "text": "ب"}],
                                kind: value,
                            },
                        }
                    ]
                },
                valid=True,
            )
        base: dict[str, Any] = {"type": kind, "text": "Visible label", kind: metadata}
        malformed = {
            "missing": {key: value for key, value in base.items() if key != kind},
            "null": base | {kind: None},
            "number": base | {kind: 123},
            "boolean": base | {kind: True},
            "array": base | {kind: []},
            "object": base | {kind: {}},
            "extra": base | {"unexpected": "field"},
            "bad-text": base | {"text": 4},
        }
        for name, text in malformed.items():
            add(f"{kind}-{name}", {"blocks": [{"type": "paragraph", "text": text}]}, valid=False)
    add(
        "cached-page-field",
        {
            "blocks": [
                {
                    "type": "paragraph",
                    "text": {"type": "url", "text": "Page", "url": "", "webpage_id": 1},
                }
            ]
        },
        valid=False,
    )
    add(
        "unknown-type",
        {
            "blocks": [
                {"type": "paragraph", "text": {"type": "text_link", "text": "Page", "url": ""}}
            ]
        },
        valid=False,
    )
    return cases


def test_original_codec_preserves_rich_links_and_rejects_malformed_metadata(tmp_path: Path) -> None:
    cases = codec_cases()
    (tmp_path / "message-codec-cases.json").write_text(json.dumps(cases))
    observed, _ = run_probe(tmp_path, "android_message_codec")
    baseline: dict[str, Any] = {
        "persona": 1,
        "cursor": 4,
        "now": 1700000000,
        "users": USERS,
        "dialogs": [{"peer_id": 2, "top_message": 1}],
        "dialog_message_count": 1,
        "messages": [
            {
                "id": 1,
                "sender_id": 2,
                "recipient_id": 1,
                "out": False,
                "date": 1700000000,
                "text": "Codec transport baseline",
            }
        ],
    }
    assert observed["baseline"] == {"returncode": 0, "result": baseline}
    assert set(observed["cases"]) == {case["name"] for case in cases}
    for case in cases:
        expected = (
            {
                "returncode": 0,
                "result": baseline | {"messages": [baseline["messages"][0] | case["content"]]},
            }
            if case["valid"]
            else {"returncode": 2, "result": {"error": "GRAMLAB_BRIDGE_INVALID_DATA"}}
        )
        assert observed["cases"][case["name"]] == expected, case["name"]


def test_real_bot_rich_links_render_edit_and_survive_cold_restart(tmp_path: Path) -> None:
    observed, apk = run_probe(tmp_path, "android_rich_links")
    assert_scenario(observed)
    client = observed["client"]
    assert set(client["codecs"]) == {"initial", "edited"}
    for phase, cursor, now in (("initial", 5, 1700000000), ("edited", 7, 1700000005)):
        assert client["codecs"][phase] == {
            "persona": 1,
            "cursor": cursor,
            "now": now,
            "users": USERS,
            "dialogs": [{"peer_id": 2, "top_message": 2}],
            "dialog_message_count": 1,
            "messages": [
                {
                    "id": 2,
                    "sender_id": 2,
                    "recipient_id": 1,
                    "out": False,
                    "date": 1700000000,
                    "text": "",
                    "rich_message": SCENE[phase],
                },
                {
                    "id": 1,
                    "sender_id": 1,
                    "recipient_id": 2,
                    "out": True,
                    "date": 1700000000,
                    "text": "Show linked content",
                },
            ],
        }
    assert set(client["launches"]) == {"initial", "restarted"}
    for launch in client["launches"].values():
        assert "Status: ok" in launch and "LaunchState: COLD" in launch
    for phase in ("initial", "edited", "restarted"):
        assert (tmp_path / f"{phase}.xml").read_text() == client[phase]
        ui = ET.fromstring(client[phase])  # noqa: S314 — dedicated guest UIAutomator output
        labels = "\n".join(node.get("text", "") for node in ui.iter("node"))
        required = (
            ("Guide", "Email team", "Call team")
            if phase == "initial"
            else ("New guide", "New email", "New phone")
        )
        assert all(fragment in labels for fragment in required)
        assert all(
            hidden not in labels
            for hidden in (
                "hidden-url",
                "hidden-email",
                "+12025550123",
                "not an address",
                "not a phone number",
            )
        )
        assert (tmp_path / f"{phase}.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert "Accounts: 0" in client["accounts"]
    events = [
        json.loads(line) for line in (tmp_path / "edited-trace.jsonl").read_text().splitlines()
    ]
    assert any(event["event"] == "events_applied" for event in events)
    write_report(
        tmp_path / "report.html",
        Report(
            run_id="rich-link-send-edit-restart",
            title="Structured links in original Android",
            mode="headless-android",
            outcome="passed",
            seed=7,
            profile={
                "Android": "Pinned client; AOSP API 36; 320 x 640 at 160 dpi",
                "APK SHA-256": hashlib.sha256(Path(apk).read_bytes()).hexdigest(),
            },
            summary="A real bot sends nested URL, email and phone labels, edits their text "
            "and metadata, then the original Android client restarts.",
            evidence={
                "initial": observed["initial"],
                "edited": observed["edited"],
                "events": observed["events"],
                "native": client["codecs"],
            },
            limitations=(
                "Link navigation, automatic entity detection and cached web pages "
                "are not established by this fixture.",
            ),
            timings={
                name.removesuffix("_seconds"): seconds * 1000
                for name, seconds in client["timings"].items()
            },
            screenshots=tuple(
                Screenshot(png=(tmp_path / f"{phase}.png").read_bytes(), caption=phase)
                for phase in ("initial", "edited", "restarted")
            ),
        ),
    )
