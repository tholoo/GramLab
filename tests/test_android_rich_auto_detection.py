"""Collectable original-Android codec case for generated rich-text nodes."""

import json
import os
import shutil
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pytest
from test_android_quoted_code import USERS, assert_isolation

from gramlab.runtime import RuntimeProfile, Sandbox

pytestmark = pytest.mark.android


def node(kind: str, text: Any) -> dict[str, Any]:
    return {"type": kind, "text": text}


def cases() -> list[dict[str, Any]]:
    all_nodes = [
        node("mention", "@alpha"),
        node("hashtag", "#آزمایش_۱۲"),
        node("cashtag", "$GRAM"),
        node("bot_command", "/start@detector_bot"),
        node("bank_card_number", "4111 1111 1111 1111"),
    ]
    result = [
        {
            "name": "all-five-original-constructors",
            "content": {
                "text": "",
                "rich_message": {
                    "blocks": [
                        {
                            "type": "paragraph",
                            "text": [
                                all_nodes[0],
                                " ",
                                {"type": "bold", "text": all_nodes[1:]},
                            ],
                        }
                    ]
                },
            },
            "valid": True,
        }
    ]
    for kind in ("mention", "hashtag", "cashtag", "bot_command", "bank_card_number"):
        for label, malformed in (
            ("missing-text", {"type": kind}),
            ("numeric-text", node(kind, 7)),
            ("unknown-field", node(kind, "x") | {"extra": True}),
        ):
            result.append(
                {
                    "name": f"{kind}-{label}",
                    "content": {
                        "text": "",
                        "rich_message": {"blocks": [{"type": "paragraph", "text": malformed}]},
                    },
                    "valid": False,
                }
            )
    return result


def test_original_codec_projects_generated_rich_text_nodes(tmp_path: Path) -> None:
    manifest = os.environ.get("GRAMLAB_ANDROID_RUNTIME_PROFILE")
    apk = os.environ.get("GRAMLAB_ANDROID_PROBE_APK")
    if manifest is None or apk is None or not os.access("/dev/kvm", os.R_OK | os.W_OK):
        pytest.skip("Requires the Android profile, patch-0031 APK and accessible KVM")
    profile = RuntimeProfile.load(Path(manifest))
    toolchain = json.loads(Path("clients/android/toolchain.json").read_text())
    image_package = (
        f"system-images;android-{toolchain['sdk']['platform']};"
        f"{toolchain['runtime']['imageType']};{toolchain['runtime']['abi']}"
    )
    authored = cases()
    (tmp_path / "message-codec-cases.json").write_text(json.dumps(authored))
    shutil.copy2(apk, tmp_path / "client.apk")
    shutil.copytree(
        "src/gramlab", tmp_path / "gramlab", ignore=shutil.ignore_patterns("__pycache__")
    )
    (tmp_path / "emulator-profile.json").write_text(json.dumps(asdict(profile)))
    for name in (
        "emulator_process.py",
        "android_guest.py",
        "android_message_codec.py",
        "android_rich_auto_detection.py",
    ):
        shutil.copy2(Path("tests/probes") / name, tmp_path / name)
    result = Sandbox(profile).supervise(
        [
            profile.python,
            "/work/android_rich_auto_detection.py",
            profile.executables["emulator"],
            profile.executables["adb"],
            profile.executables["avdmanager"],
            image_package,
        ],
        data=tmp_path,
        kvm=True,
        timeout=420,
    )
    (tmp_path / "rich-auto-detection-codec-result.json").write_text(result.stdout)
    (tmp_path / "rich-auto-detection-codec-stderr.log").write_text(result.stderr)
    assert result.returncode == 0, result.stderr
    full = json.loads(result.stdout)
    assert_isolation(full)
    observed = full["extra_probe"]
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
    assert set(observed["cases"]) == {case["name"] for case in authored}
    for case in authored:
        expected = (
            {
                "returncode": 0,
                "result": baseline | {"messages": [baseline["messages"][0] | case["content"]]},
            }
            if case["valid"]
            else {
                "returncode": 2,
                "result": {"error": "GRAMLAB_BRIDGE_INVALID_RICH_MESSAGE"},
            }
        )
        assert observed["cases"][case["name"]] == expected, case["name"]
