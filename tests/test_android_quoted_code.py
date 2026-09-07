"""Independent native nesting guard and real-bot quoted-code rendering evidence."""

import hashlib
import json
import os
import shutil
import xml.etree.ElementTree as ET
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pytest
from test_quoted_code_round_trip import SCENE, assert_scenario, stage_scenario

from gramlab.reports import Report, Screenshot, write_report
from gramlab.runtime import RuntimeProfile, Sandbox

pytestmark = pytest.mark.android

USERS = [
    {
        "id": 1,
        "first_name": "Sara",
        "self": True,
        "bot": False,
        "username": None,
        "language_code": "fa",
        "phone": None,
    },
    {
        "id": 2,
        "first_name": "Echo",
        "self": False,
        "bot": True,
        "username": "gramlab_echo_bot",
        "language_code": None,
        "phone": None,
    },
]


def assert_isolation(full: dict[str, Any]) -> None:
    assert full["host_interfaces"] == [[1, "lo"]]
    assert "Accounts: 0" in full["accounts"]
    assert full["emulator_filesystem"] == {
        "world_visible": False,
        "bot_visible": False,
        "private_avd_visible": True,
        "same_pid_namespace": False,
        "same_network": True,
    }
    assert full["network"]["local"] == "gramlab-local-reply\n"
    assert full["network"]["local_error"] == ""
    for family in ("ipv4", "ipv6"):
        assert full["network"][family] == {
            "returncode": 1,
            "stdout": "",
            "stderr": "nc: connect: Network is unreachable\n",
        }


def run_probe(directory: Path, module: str) -> tuple[dict[str, Any], str]:
    manifest = os.environ.get("GRAMLAB_ANDROID_RUNTIME_PROFILE")
    apk = os.environ.get("GRAMLAB_ANDROID_PROBE_APK")
    if manifest is None or apk is None or not os.access("/dev/kvm", os.R_OK | os.W_OK):
        pytest.skip("Requires the provisioned Android profile, normal APK and KVM")
    profile = RuntimeProfile.load(Path(manifest))
    core = RuntimeProfile.load(Path(os.environ["GRAMLAB_RUNTIME_PROFILE"]))
    stage_scenario(directory, core)
    shutil.copy2(apk, directory / "client.apk")
    (directory / "emulator-profile.json").write_text(json.dumps(asdict(profile)))
    for name in (
        "emulator_process.py",
        "android_guest.py",
        "android_rich_messages.py",
        "android_quoted_code.py",
        "android_quoted_code_codec.py",
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
    (directory / "quoted-native-result.json").write_text(result.stdout)
    (directory / "quoted-native-stderr.log").write_text(result.stderr)
    assert result.returncode == 0, result.stderr
    full = json.loads(result.stdout)
    assert_isolation(full)
    return full["extra_probe"], apk


def codec_cases() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for quote in ("blockquote", "expandable_blockquote"):
        for code in ("code", "pre"):
            for equal in (False, True):
                offset, length = (0, 8) if equal else (2, 4)
                quoted = {"type": quote, "offset": 0, "length": 8}
                inner = {"type": code, "offset": offset, "length": length}
                if code == "pre":
                    inner["language"] = "python"
                expected = [
                    {
                        "kind": "TL_messageEntityBlockquote",
                        "offset": 0,
                        "length": 8,
                        "collapsed": quote == "expandable_blockquote",
                    },
                    {
                        "kind": "TL_messageEntityCode" if code == "code" else "TL_messageEntityPre",
                        "offset": offset,
                        "length": length,
                        **({"language": "python"} if code == "pre" else {}),
                    },
                ]
                for reverse in (False, True):
                    cases.append(
                        {
                            "name": f"{quote}-{code}-{equal}-{reverse}",
                            "content": {
                                "text": "😀abCDyz",
                                "entities": [inner, quoted] if reverse else [quoted, inner],
                            },
                            "expected": expected,
                        }
                    )
    invalid = {
        "equal-quote-style-code": [
            {"type": "blockquote", "offset": 0, "length": 8},
            {"type": "bold", "offset": 0, "length": 8},
            {"type": "code", "offset": 0, "length": 8},
        ],
        "equal-code-style-quote": [
            {"type": "code", "offset": 0, "length": 8},
            {"type": "bold", "offset": 0, "length": 8},
            {"type": "blockquote", "offset": 0, "length": 8},
        ],
        "style-parent-code": [
            {"type": "bold", "offset": 0, "length": 8},
            {"type": "code", "offset": 2, "length": 4},
        ],
        "style-outside-quote": [
            {"type": "bold", "offset": 0, "length": 8},
            {"type": "blockquote", "offset": 2, "length": 6},
            {"type": "code", "offset": 3, "length": 3},
        ],
        "style-inside-quote": [
            {"type": "blockquote", "offset": 0, "length": 8},
            {"type": "italic", "offset": 2, "length": 6},
            {"type": "pre", "offset": 3, "length": 3},
        ],
        "quote-inside-code": [
            {"type": "code", "offset": 0, "length": 8},
            {"type": "blockquote", "offset": 2, "length": 4},
        ],
        "code-inside-pre": [
            {"type": "pre", "offset": 0, "length": 8},
            {"type": "code", "offset": 2, "length": 4},
        ],
        "crossing": [
            {"type": "blockquote", "offset": 0, "length": 5},
            {"type": "code", "offset": 3, "length": 4},
        ],
        "nested-quotes": [
            {"type": "blockquote", "offset": 0, "length": 8},
            {"type": "expandable_blockquote", "offset": 2, "length": 4},
        ],
        "surrogate-split": [
            {"type": "blockquote", "offset": 0, "length": 8},
            {"type": "code", "offset": 1, "length": 4},
        ],
        "code-language": [{"type": "code", "offset": 2, "length": 4, "language": "python"}],
        "pre-language-type": [{"type": "pre", "offset": 2, "length": 4, "language": 7}],
        "unsupported": [{"type": "custom_emoji", "offset": 0, "length": 2}],
        "empty-range": [{"type": "code", "offset": 2, "length": 0}],
    }
    cases.extend(
        {"name": name, "content": {"text": "😀abCDyz", "entities": entities}, "expected": None}
        for name, entities in invalid.items()
    )
    return cases


def test_native_quoted_code_codec_and_independent_rejections(tmp_path: Path) -> None:
    cases = codec_cases()
    (tmp_path / "quoted-code-cases.json").write_text(json.dumps(cases))
    observed, _ = run_probe(tmp_path, "android_quoted_code_codec")
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
        actual = observed["cases"][case["name"]]
        if case["expected"] is None:
            assert actual == {
                "returncode": 2,
                "result": {"error": "GRAMLAB_BRIDGE_INVALID_DATA"},
            }, case["name"]
        else:
            message = baseline["messages"][0] | {
                "text": case["content"]["text"],
                "entities": case["expected"],
            }
            assert actual == {"returncode": 0, "result": baseline | {"messages": [message]}}, case[
                "name"
            ]


def validate_render_result(tmp_path: Path, observed: dict[str, Any], apk: str) -> None:
    assert_scenario(observed)
    client = observed["client"]
    expected_entities = {
        "initial": [
            {"kind": "TL_messageEntityBlockquote", "offset": 0, "length": 15, "collapsed": False},
            {"kind": "TL_messageEntityCode", "offset": 8, "length": 7},
            {"kind": "TL_messageEntityBlockquote", "offset": 16, "length": 17, "collapsed": True},
            {"kind": "TL_messageEntityPre", "offset": 25, "length": 8, "language": "python"},
        ],
        "edited": [
            {"kind": "TL_messageEntityBlockquote", "offset": 0, "length": 12, "collapsed": True},
            {"kind": "TL_messageEntityCode", "offset": 6, "length": 6},
            {"kind": "TL_messageEntityBlockquote", "offset": 13, "length": 19, "collapsed": False},
            {"kind": "TL_messageEntityPre", "offset": 24, "length": 8, "language": "python"},
        ],
    }
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
                    "text": SCENE[phase]["text"],
                    "entities": expected_entities[phase],
                },
                {
                    "id": 1,
                    "sender_id": 1,
                    "recipient_id": 2,
                    "out": True,
                    "date": 1700000000,
                    "text": "Show quoted code",
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
        expected = (
            ("Code", "alpha()", "print(1)") if phase == "initial" else ("کد", "beta()", "print(2)")
        )
        assert all(fragment in labels for fragment in expected)
        assert (tmp_path / f"{phase}.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert "Accounts: 0" in client["accounts"]
    events = [
        json.loads(line) for line in (tmp_path / "edited-trace.jsonl").read_text().splitlines()
    ]
    assert any(event["event"] == "events_applied" for event in events)
    write_report(
        tmp_path / "report.html",
        Report(
            run_id="quoted-code-send-edit-restart",
            title="Quoted code in original Android",
            mode="headless-android",
            outcome="passed",
            seed=7,
            profile={
                "Android": "Pinned client; AOSP API 36; 320 x 640 at 160 dpi",
                "APK SHA-256": hashlib.sha256(Path(apk).read_bytes()).hexdigest(),
            },
            summary="A real local bot sends quoted code and preformatted text, edits the text "
            "and quote kinds, then the original Android client restarts. Complete API, World "
            "and native serializer observations accompany the original captures.",
            evidence={
                "initial": observed["initial"],
                "edited": observed["edited"],
                "events": observed["events"],
                "native": client["codecs"],
            },
            limitations=(
                "HTML parsing and quote expansion gestures are not established by this fixture.",
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


def test_real_bot_quoted_code_renders_edits_and_restarts(tmp_path: Path) -> None:
    observed, apk = run_probe(tmp_path, "android_quoted_code")
    validate_render_result(tmp_path, observed, apk)
