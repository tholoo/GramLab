"""Native codec contract for synthetic supergroups."""

import json
import os
import shutil
from dataclasses import asdict
from pathlib import Path

import pytest

from gramlab.runtime import RuntimeProfile, Sandbox

pytestmark = pytest.mark.android


def test_group_identity_title_members_and_messages_survive_native_serialization(
    tmp_path: Path,
) -> None:
    manifest = os.environ.get("GRAMLAB_ANDROID_RUNTIME_PROFILE")
    apk = os.environ.get("GRAMLAB_ANDROID_PROBE_APK")
    if manifest is None or apk is None:
        pytest.skip("Requires the Android profile and built bridge probe APK")
    if not os.access("/dev/kvm", os.R_OK | os.W_OK):
        pytest.skip("Requires an accessible KVM device")
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
    (tmp_path / "emulator-profile.json").write_text(json.dumps(asdict(profile)))
    for name in ("android_guest.py", "android_group_codec.py", "emulator_process.py"):
        shutil.copy2(Path("tests/probes") / name, tmp_path / name)

    result = Sandbox(profile).supervise(
        [
            profile.python,
            "/work/android_group_codec.py",
            profile.executables["emulator"],
            profile.executables["adb"],
            profile.executables["avdmanager"],
            image_package,
        ],
        data=tmp_path,
        kvm=True,
        timeout=240,
    )

    assert result.returncode == 0, result.stderr
    observed = json.loads(result.stdout)["extra_probe"]
    assert observed["returncode"] == 0, observed
    assert json.loads(observed["stdout"]) == {
        "persona": 2,
        "cursor": 6,
        "now": 1_700_000_000,
        "users": [
            {
                "id": 1,
                "first_name": "Mina",
                "self": False,
                "bot": False,
                "username": "mina",
                "language_code": None,
                "phone": None,
            },
            {
                "id": 2,
                "first_name": "Arman",
                "self": True,
                "bot": False,
                "username": "arman",
                "language_code": None,
                "phone": None,
            },
            {
                "id": 3,
                "first_name": "Helper",
                "self": False,
                "bot": True,
                "username": "helper_bot",
                "language_code": None,
                "phone": None,
            },
        ],
        "chats": [
            {
                "id": 4,
                "title": "Study group",
                "megagroup": True,
                "default_send_plain_allowed": True,
                "participants_count": 3,
            }
        ],
        "dialogs": [{"peer_type": "channel", "peer_id": 4, "dialog_id": -4, "top_message": 2}],
        "dialog_message_count": 1,
        "messages": [
            {
                "id": 2,
                "sender_id": 3,
                "recipient_chat_id": 4,
                "dialog_id": -4,
                "out": False,
                "date": 1_700_000_000,
                "text": "Ready for the group",
            },
            {
                "id": 1,
                "sender_id": 2,
                "recipient_chat_id": 4,
                "dialog_id": -4,
                "out": True,
                "date": 1_700_000_000,
                "text": "/game",
            },
        ],
        "history_users": [{"peer_id": -4, "user_ids": [1, 2, 3]}],
        "group_send": {"id": 3, "pts": 3, "pts_count": 1, "date": 1_700_000_000},
        "rejected_group_send_as": "UnsupportedOperationException",
    }
