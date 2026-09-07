"""Complete canonical button projection and rejection through Android's real serializer."""

import json
import os
import shutil
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pytest

from gramlab.runtime import RuntimeProfile, Sandbox

pytestmark = pytest.mark.android


def test_canonical_buttons_survive_native_serialization_and_reject_malformed_snapshots(
    tmp_path: Path,
) -> None:
    manifest = os.environ.get("GRAMLAB_ANDROID_RUNTIME_PROFILE")
    apk = os.environ.get("GRAMLAB_ANDROID_PROBE_APK")
    if manifest is None or apk is None or not os.access("/dev/kvm", os.R_OK | os.W_OK):
        pytest.skip("Requires the Android profile, button codec APK and accessible KVM")
    profile = RuntimeProfile.load(Path(manifest))
    toolchain = json.loads(Path("clients/android/toolchain.json").read_text())
    image_package = (
        f"system-images;android-{toolchain['sdk']['platform']};"
        f"{toolchain['runtime']['imageType']};{toolchain['runtime']['abi']}"
    )
    shutil.copy2(apk, tmp_path / "client.apk")
    shutil.copytree(
        "src/gramlab", tmp_path / "gramlab", ignore=shutil.ignore_patterns("__pycache__")
    )
    fixtures = Path("clients/android/fixtures")
    catalog = json.loads((fixtures / "rich-message-buttons.json").read_text())
    invalid = json.loads((fixtures / "rich-message-invalid-buttons.json").read_text())

    # Authored canonical boundaries: code points and UTF-8 bytes differ for emoji.
    def row(button: dict[str, Any]) -> dict[str, Any]:
        return {"blocks": [{"type": "buttons", "buttons": [button]}]}

    boundaries = [
        {
            "name": "copy-256-codepoints",
            "rich_message": row({"text": "Copy", "copy_text": {"text": "🙂" * 256}}),
        },
        {
            "name": "callback-64-bytes",
            "rich_message": row({"text": "Go", "callback_data": "🙂" * 16}),
        },
        {
            "name": "label-terminal-codepoint",
            "rich_message": row({"text": "a" * 34995 + "🙂", "disabled": {}}),
        },
        {
            "name": "label-direction-leaf-boundary",
            "rich_message": row({"text": ["\u200e", ["\u200f", "\u200c\u200f"]], "disabled": {}}),
        },
    ]
    deep: Any = "x"
    for _ in range(33):
        deep = [deep]
    invalid_buttons: list[tuple[str, dict[str, Any]]] = [
        ("copy-257-codepoints", {"text": "Copy", "copy_text": {"text": "🙂" * 257}}),
        ("callback-65-bytes", {"text": "Go", "callback_data": "🙂" * 16 + "x"}),
        ("label-past-byte-stop", {"text": "a" * 34996 + "x", "disabled": {}}),
        ("depth-budget", {"text": deep, "disabled": {}}),
        ("node-budget", {"text": [""] * 10000, "disabled": {}}),
        ("utf8-budget", {"text": ["س" * 17000] * 2, "disabled": {}}),
    ]
    invalid.extend({"name": name, "rich_message": row(button)} for name, button in invalid_buttons)
    (tmp_path / "button-boundaries.json").write_text(json.dumps(boundaries))
    (tmp_path / "button-catalog.json").write_text(json.dumps(catalog))
    (tmp_path / "invalid-buttons.json").write_text(json.dumps(invalid))
    (tmp_path / "emulator-profile.json").write_text(json.dumps(asdict(profile)))
    for name in ("emulator_process.py", "android_guest.py", "android_rich_button_codec.py"):
        shutil.copy2(Path("tests/probes") / name, tmp_path / name)
    result = Sandbox(profile).supervise(
        [
            profile.python,
            "/work/android_rich_button_codec.py",
            profile.executables["emulator"],
            profile.executables["adb"],
            profile.executables["avdmanager"],
            image_package,
        ],
        data=tmp_path,
        kvm=True,
        timeout=420,
    )
    (tmp_path / "button-result.json").write_text(result.stdout)
    assert result.returncode == 0, result.stderr
    full = json.loads(result.stdout)
    assert full["emulator_filesystem"] == {
        "world_visible": False,
        "bot_visible": False,
        "private_avd_visible": True,
        "same_pid_namespace": False,
        "same_network": True,
    }
    assert "Accounts: 0" in full["accounts"]
    assert full["network"]["local"] == "gramlab-local-reply\n"
    assert full["network"]["local_error"] == ""
    for family in ("ipv4", "ipv6"):
        assert full["network"][family] == {
            "returncode": 1,
            "stdout": "",
            "stderr": "nc: connect: Network is unreachable\n",
        }
    assert full["host_interfaces"] == [[1, "lo"]]
    observed = full["extra_probe"]
    assert observed["baseline"]["returncode"] == 0, observed["baseline"]
    assert observed["catalog"]["returncode"] == 0, observed["catalog"]
    expected = observed["baseline"]["result"]
    expected["messages"][0]["text"] = ""
    expected["messages"][0]["rich_message"] = catalog
    assert observed["catalog"]["result"] == expected
    for case in boundaries:
        actual = observed["boundaries"][case["name"]]
        assert actual["returncode"] == 0, actual
        expected["messages"][0]["rich_message"] = case["rich_message"]
        assert actual["result"] == expected
    assert observed["rejections"] == {
        case["name"]: {
            "returncode": 2,
            "result": {"error": "GRAMLAB_BRIDGE_INVALID_RICH_MESSAGE"},
        }
        for case in invalid
    }
