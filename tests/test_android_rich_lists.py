"""Complete canonical list projection and rejection through Android's real serializer."""

import json
import os
import shutil
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pytest

from gramlab.runtime import RuntimeProfile, Sandbox

pytestmark = pytest.mark.android


def test_canonical_lists_survive_native_serialization_and_reject_malformed_snapshots(
    tmp_path: Path,
) -> None:
    manifest = os.environ.get("GRAMLAB_ANDROID_RUNTIME_PROFILE")
    apk = os.environ.get("GRAMLAB_ANDROID_PROBE_APK")
    if manifest is None or apk is None or not os.access("/dev/kvm", os.R_OK | os.W_OK):
        pytest.skip("Requires the Android profile, list codec APK and accessible KVM")
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
    catalog = json.loads((fixtures / "rich-message-lists.json").read_text())
    invalid = json.loads((fixtures / "rich-message-invalid-lists.json").read_text())
    # Deliberately exceed each independent whole-tree budget with valid list shapes.
    item = {"label": "•", "blocks": [{"type": "paragraph", "text": "x"}]}
    deep: dict[str, Any] = {"type": "paragraph", "text": "x"}
    for _ in range(12):
        deep = {"type": "list", "items": [{"label": "•", "blocks": [deep]}]}
    invalid.extend(
        [
            {"name": "depth-budget", "rich_message": {"blocks": [deep]}},
            {
                "name": "node-budget",
                "rich_message": {"blocks": [{"type": "list", "items": [item] * 1500}]},
            },
            {
                "name": "utf8-budget",
                "rich_message": {
                    "blocks": [
                        {
                            "type": "list",
                            "items": [
                                {
                                    "label": "•",
                                    "blocks": [{"type": "paragraph", "text": "س" * 32768}],
                                }
                            ],
                        }
                    ]
                },
            },
        ]
    )
    (tmp_path / "list-catalog.json").write_text(json.dumps(catalog))
    (tmp_path / "invalid-lists.json").write_text(json.dumps(invalid))
    (tmp_path / "emulator-profile.json").write_text(json.dumps(asdict(profile)))
    for name in ("emulator_process.py", "android_guest.py", "android_rich_lists.py"):
        shutil.copy2(Path("tests/probes") / name, tmp_path / name)
    result = Sandbox(profile).supervise(
        [
            profile.python,
            "/work/android_rich_lists.py",
            profile.executables["emulator"],
            profile.executables["adb"],
            profile.executables["avdmanager"],
            image_package,
        ],
        data=tmp_path,
        kvm=True,
        timeout=420,
    )
    (tmp_path / "list-result.json").write_text(result.stdout)
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
    assert observed["rejections"] == {
        case["name"]: {
            "returncode": 2,
            "result": {"error": "GRAMLAB_BRIDGE_INVALID_RICH_MESSAGE"},
        }
        for case in invalid
    }
