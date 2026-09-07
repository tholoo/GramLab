"""Complete native projection and rejection oracles for bridge-v3 photos."""

import copy
import hashlib
import json
import os
import shutil
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pytest
from test_android_quoted_code import assert_isolation

from gramlab.runtime import RuntimeProfile, Sandbox

pytestmark = pytest.mark.android

PNG = Path("tests/assets/rich-media/photo-square-16x16.png")
JPEG = Path("tests/assets/rich-media/photo-quadrants-64x48.jpg")
WORLD_ID = "media-codec-world"
USERS = [
    {
        "id": 1,
        "is_bot": False,
        "first_name": "Sara",
        "language_code": "fa",
    },
    {
        "id": 2,
        "is_bot": True,
        "first_name": "Echo",
        "username": "gramlab_echo_bot",
    },
]
NATIVE_USERS = [
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


def descriptor(asset_id: int, source: Path, mime: str, width: int, height: int) -> dict[str, Any]:
    return {
        "asset_id": asset_id,
        "mime_type": mime,
        "file_size": source.stat().st_size,
        "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "width": width,
        "height": height,
    }


PNG_ASSET = descriptor(1, PNG, "image/png", 16, 16)
JPEG_ASSET = descriptor(2, JPEG, "image/jpeg", 64, 48)


def native_photo(asset: dict[str, Any]) -> dict[str, Any]:
    return {
        "asset_id": asset["asset_id"],
        "dc_id": 0,
        "access_hash": 0,
        "file_reference_bytes": 0,
        "size_type": "x",
        "volume_id": asset["asset_id"],
        "local_id": 1,
        "width": asset["width"],
        "height": asset["height"],
        "file_size": asset["file_size"],
    }


def message(message_id: int, **content: Any) -> dict[str, Any]:
    return {
        "id": message_id,
        "chat_id": 1,
        "sender_id": 2,
        "date": 1700000000,
        "text": "",
        **content,
    }


def snapshot(messages: list[dict[str, Any]], assets: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema": 3,
        "world_id": WORLD_ID,
        "user_id": 1,
        "cursor": 20,
        "now": 1700000000,
        "users": USERS,
        "chats": [{"id": 1, "type": "private", "user_id": 1, "bot_id": 2}],
        "messages": messages,
        "message_position": len(messages),
        "sends": [],
        "assets": assets,
        "message_revisions": [
            {"chat_id": 1, "message_id": item["id"], "revision": 10 + index}
            for index, item in enumerate(messages)
        ],
    }


def native_output(messages: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "persona": 1,
        "cursor": 20,
        "now": 1700000000,
        "users": NATIVE_USERS,
        "dialogs": [{"peer_id": 2, "top_message": max(item["id"] for item in messages)}],
        "messages": sorted(messages, key=lambda item: item["id"], reverse=True),
        "dialog_message_count": 1,
    }


def cases() -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    baseline_world = message(1, text="Codec transport baseline")
    baseline_native = {
        "id": 1,
        "sender_id": 2,
        "recipient_id": 1,
        "out": False,
        "date": 1700000000,
        "text": "Codec transport baseline",
    }
    ordinary_world = message(
        1,
        photo={"asset_id": 1},
        caption="PNG ordinary / تصویر معمولی",
        caption_entities=[{"type": "bold", "offset": 0, "length": 3}],
    )
    ordinary_native = {
        "id": 1,
        "sender_id": 2,
        "recipient_id": 1,
        "out": False,
        "date": 1700000000,
        "text": "PNG ordinary / تصویر معمولی",
        "entities": [{"kind": "TL_messageEntityBold", "offset": 0, "length": 3}],
        "native_photo": native_photo(PNG_ASSET),
    }
    rich_content = {
        "blocks": [
            {
                "type": "photo",
                "asset_id": 2,
                "caption": {
                    "text": ["Original ", {"type": "bold", "text": "JPEG"}, " — عکس"],
                    "credit": "GramLab / آزمایشگاه",
                },
            },
            {"type": "photo", "asset_id": 2},
        ],
        "is_rtl": True,
    }
    rich_world = message(1, rich_message=rich_content)
    rich_native_content = rich_content | {"native_photos": [native_photo(JPEG_ASSET)]}
    rich_native = {
        "id": 1,
        "sender_id": 2,
        "recipient_id": 1,
        "out": False,
        "date": 1700000000,
        "text": "",
        "rich_message": rich_native_content,
    }
    mixed_world = [ordinary_world, message(2, rich_message=rich_content)]
    mixed_native = [ordinary_native, rich_native | {"id": 2}]
    valid: list[dict[str, Any]] = [
        {"name": "baseline", "snapshot": snapshot([baseline_world], [])},
        {"name": "ordinary-photo", "snapshot": snapshot([ordinary_world], [PNG_ASSET])},
        {"name": "rich-repeated-photo", "snapshot": snapshot([rich_world], [JPEG_ASSET])},
        {
            "name": "mixed-ordinary-rich",
            "snapshot": snapshot(mixed_world, [PNG_ASSET, JPEG_ASSET]),
        },
    ]
    expected = {
        "baseline": native_output([baseline_native]),
        "ordinary-photo": native_output([ordinary_native]),
        "rich-repeated-photo": native_output([rich_native]),
        "mixed-ordinary-rich": native_output(mixed_native),
    }

    malformed: list[tuple[str, dict[str, Any], str, int]] = []

    def reject(name: str, changed: dict[str, Any], error: str, version: int = 3) -> None:
        malformed.append((name, changed, error, version))

    ordinary = snapshot([ordinary_world], [PNG_ASSET])
    for field in PNG_ASSET:
        changed = copy.deepcopy(ordinary)
        del changed["assets"][0][field]
        reject(f"asset-missing-{field}", changed, "GRAMLAB_BRIDGE_INVALID_DATA")
    changed = copy.deepcopy(ordinary)
    changed["assets"][0]["unexpected"] = True
    reject("asset-unknown-field", changed, "GRAMLAB_BRIDGE_INVALID_DATA")
    for name, update in (
        ("mime", {"mime_type": "image/gif"}),
        ("oversize", {"file_size": 10_000_001}),
        ("zero-width", {"width": 0}),
        ("dimension-sum", {"width": 9999, "height": 2}),
        ("ratio", {"width": 421, "height": 20}),
        ("pixels", {"width": 5001, "height": 5000}),
        ("digest-uppercase", {"sha256": "A" * 64}),
        ("digest-length", {"sha256": "a" * 63}),
    ):
        changed = copy.deepcopy(ordinary)
        changed["assets"][0].update(update)
        reject(f"asset-invalid-{name}", changed, "GRAMLAB_BRIDGE_INVALID_ASSET")
    changed = copy.deepcopy(ordinary)
    changed["assets"] = [JPEG_ASSET, PNG_ASSET]
    reject("assets-unsorted", changed, "GRAMLAB_BRIDGE_INVALID_ASSET")
    changed = copy.deepcopy(ordinary)
    changed["assets"] = [PNG_ASSET, PNG_ASSET]
    reject("assets-duplicate", changed, "GRAMLAB_BRIDGE_INVALID_ASSET")
    changed = copy.deepcopy(ordinary)
    changed["messages"][0]["photo"]["asset_id"] = 2
    reject("ordinary-unknown-asset", changed, "GRAMLAB_BRIDGE_UNKNOWN_ASSET")
    changed = copy.deepcopy(ordinary)
    del changed["messages"][0]["photo"]["asset_id"]
    reject("ordinary-missing-asset-id", changed, "GRAMLAB_BRIDGE_INVALID_DATA")
    changed = snapshot([rich_world], [JPEG_ASSET])
    changed["messages"][0]["rich_message"]["blocks"][0]["asset_id"] = 1
    reject("rich-unknown-asset", changed, "GRAMLAB_BRIDGE_UNKNOWN_ASSET")
    changed = snapshot([rich_world], [JPEG_ASSET])
    del changed["messages"][0]["rich_message"]["blocks"][0]["asset_id"]
    reject("rich-missing-asset-id", changed, "GRAMLAB_BRIDGE_INVALID_DATA")
    for name, field in (("ordinary-photo-extra", "photo"), ("rich-photo-extra", "rich")):
        changed = copy.deepcopy(
            ordinary if field == "photo" else snapshot([rich_world], [JPEG_ASSET])
        )
        target = (
            changed["messages"][0]["photo"]
            if field == "photo"
            else changed["messages"][0]["rich_message"]["blocks"][0]
        )
        target["unexpected"] = 1
        reject(name, changed, "GRAMLAB_BRIDGE_INVALID_DATA")
    version_two = copy.deepcopy(ordinary)
    version_two["schema"] = 2
    version_two.pop("assets")
    version_two.pop("message_revisions")
    reject("media-requires-v3", version_two, "GRAMLAB_BRIDGE_MEDIA_REQUIRES_V3", 2)

    for name, changed, error, version in malformed:
        valid.append({"name": name, "snapshot": changed, "bridge_version": version})
        expected[name] = {"error": error}
    return valid, expected


def test_native_codec_projects_photos_and_rejects_malformed_v3_snapshots(tmp_path: Path) -> None:
    manifest = os.environ.get("GRAMLAB_ANDROID_RUNTIME_PROFILE")
    apk = os.environ.get("GRAMLAB_ANDROID_PROBE_APK")
    if manifest is None or apk is None or not os.access("/dev/kvm", os.R_OK | os.W_OK):
        pytest.skip("Requires the Android profile, reviewed media APK and accessible KVM")
    profile = RuntimeProfile.load(Path(manifest))
    toolchain = json.loads(Path("clients/android/toolchain.json").read_text())
    image_package = (
        f"system-images;android-{toolchain['sdk']['platform']};"
        f"{toolchain['runtime']['imageType']};{toolchain['runtime']['abi']}"
    )
    authored, expected = cases()
    (tmp_path / "media-codec-cases.json").write_text(json.dumps(authored))
    shutil.copy2(apk, tmp_path / "client.apk")
    shutil.copytree(
        "src/gramlab", tmp_path / "gramlab", ignore=shutil.ignore_patterns("__pycache__")
    )
    (tmp_path / "emulator-profile.json").write_text(json.dumps(asdict(profile)))
    for name in ("emulator_process.py", "android_guest.py", "android_media_codec.py"):
        shutil.copy2(Path("tests/probes") / name, tmp_path / name)
    result = Sandbox(profile).supervise(
        [
            profile.python,
            "/work/android_media_codec.py",
            profile.executables["emulator"],
            profile.executables["adb"],
            profile.executables["avdmanager"],
            image_package,
        ],
        data=tmp_path,
        kvm=True,
        timeout=420,
    )
    (tmp_path / "media-codec-result.json").write_text(result.stdout)
    (tmp_path / "media-codec-stderr.log").write_text(result.stderr)
    assert result.returncode == 0, result.stderr
    full = json.loads(result.stdout)
    assert_isolation(full)
    observed = full["extra_probe"]["cases"]
    assert set(observed) == set(expected)
    for name, oracle in expected.items():
        accepted = "error" not in oracle
        assert observed[name] == {
            "returncode": 0 if accepted else 2,
            "result": oracle,
        }, name
