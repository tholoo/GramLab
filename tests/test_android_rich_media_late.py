"""Original rich receiver keeps its edit while an old shared transfer completes."""

import hashlib
import json
import os
import shutil
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pytest
from test_android_quoted_code import assert_isolation

from gramlab.reports import Report, Screenshot, write_report
from gramlab.runtime import RuntimeProfile, Sandbox

pytestmark = pytest.mark.android

ASSETS = (
    (1, "photo-square-16x16.png", "image/png", 16, 16),
    (2, "photo-landscape-48x12.png", "image/png", 48, 12),
    (3, "photo-quadrants-64x48.jpg", "image/jpeg", 64, 48),
)


def expected_assets() -> list[dict[str, Any]]:
    values = []
    for asset_id, name, mime, width, height in ASSETS:
        source = Path("tests/assets/rich-media") / name
        values.append(
            {
                "asset_id": asset_id,
                "mime_type": mime,
                "file_size": source.stat().st_size,
                "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "width": width,
                "height": height,
            }
        )
    return values


def asset_requests(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in rows if row["operation"] == "asset"]


def test_original_rich_photo_edit_allows_old_shared_completion(tmp_path: Path) -> None:
    manifest = os.environ.get("GRAMLAB_ANDROID_RUNTIME_PROFILE")
    apk = os.environ.get("GRAMLAB_ANDROID_PROBE_APK")
    if manifest is None or apk is None or not os.access("/dev/kvm", os.R_OK | os.W_OK):
        pytest.skip("Requires Android profile, reviewed schema-2 observation APK and KVM")
    profile = RuntimeProfile.load(Path(manifest))
    toolchain = json.loads(Path("clients/android/toolchain.json").read_text())
    image_package = (
        f"system-images;android-{toolchain['sdk']['platform']};"
        f"{toolchain['runtime']['imageType']};{toolchain['runtime']['abi']}"
    )
    shutil.copy2(apk, tmp_path / "client.apk")
    for _, name, _, _, _ in ASSETS:
        shutil.copy2(Path("tests/assets/rich-media") / name, tmp_path / name)
    shutil.copytree(
        "src/gramlab", tmp_path / "gramlab", ignore=shutil.ignore_patterns("__pycache__")
    )
    (tmp_path / "emulator-profile.json").write_text(json.dumps(asdict(profile)))
    for name in (
        "emulator_process.py",
        "android_guest.py",
        "media_transfer_server.py",
        "android_rich_media_late.py",
    ):
        shutil.copy2(Path("tests/probes") / name, tmp_path / name)
    result = Sandbox(profile).supervise(
        [
            profile.python,
            "/work/android_rich_media_late.py",
            profile.executables["emulator"],
            profile.executables["adb"],
            profile.executables["avdmanager"],
            image_package,
        ],
        data=tmp_path,
        kvm=True,
        timeout=600,
    )
    (tmp_path / "rich-photo-late-result.json").write_text(result.stdout)
    (tmp_path / "rich-photo-late-stderr.log").write_text(result.stderr)
    assert result.returncode == 0, result.stderr
    full = json.loads(result.stdout)
    assert_late_completion(tmp_path, full, apk, toolchain, image_package)


def assert_late_completion(
    tmp_path: Path, full: dict[str, Any], apk: str, toolchain: dict[str, Any], image_package: str
) -> None:
    assert_isolation(full)
    observed = full["extra_probe"]
    expected = expected_assets()
    assert observed["assets"] == expected
    assert "Accounts: 0" in observed["accounts"]
    case = observed["case"]
    assert "failure" not in case, json.dumps(case.get("failure"), indent=2)
    assert "evidence_failure" not in case, json.dumps(case.get("evidence_failure"), indent=2)
    assert case["targets"] == [
        {"message_id": 1, "kind": "rich", "asset_ids": [2, 3]},
        {"message_id": 2, "kind": "ordinary", "asset_ids": [2]},
    ]
    assert 0 <= case["release_elapsed"] < 4.8
    assert case["released_at"] > case["partial_sent_at"]
    assert [row["asset_id"] for row in case["loading"]["messages"]] == [2, 2]
    assert not any(row["has_image"] for row in case["loading"]["messages"])
    rich_loading, ordinary_loading = case["loading"]["messages"]
    # Original rich full images pass a null filter; only ordinary receivers append @size.
    assert rich_loading["image_key"] == "2_1"
    assert ordinary_loading["image_key"].startswith("2_1@")
    assert rich_loading["progress"] is None and rich_loading["progress_icon"] is None
    assert ordinary_loading["progress_icon"] == 3
    assert case["edited_snapshot"]["messages"][0]["rich_message"]["blocks"] == [
        {"type": "photo", "asset_id": 1},
        {"type": "photo", "asset_id": 3},
    ]
    assert case["edited_snapshot"]["messages"][1]["photo"] == {"asset_id": 2}
    assert case["changes"] == {
        "schema": 3,
        "world_id": "rich-photo-late",
        "user_id": 1,
        "head": 3,
        "now": 1700000000,
        "users": case["edited_snapshot"]["users"],
        "assets": [expected[2]],
        "changes": [
            {
                "position": 3,
                "type": "message.edited",
                "revision": 6,
                "data": case["edited_snapshot"]["messages"][0],
            }
        ],
    }
    assert case["edited_snapshot"]["message_revisions"] == [
        {"chat_id": 1, "message_id": 1, "revision": 6},
        {"chat_id": 1, "message_id": 2, "revision": 5},
    ]
    before = case["bound_c"]["messages"]
    assert [(row["kind"], row["asset_id"], row["has_image"]) for row in before] == [
        ("rich", 3, True),
        ("ordinary", 2, False),
    ]
    assert before[0]["image_key"] == "3_1"
    assert case["post_release"]
    for sample in case["post_release"] + [case["completed"], case["stable"]]:
        rich, ordinary = sample["messages"]
        assert rich["asset_id"] == 3 and rich["has_image"] is True
        assert rich["image_key"] == "3_1"
        assert ordinary["asset_id"] == 2
        assert ordinary["image_key"].startswith("2_1@")
    assert case["completed"]["messages"][1]["has_image"] is True
    assert case["stable"]["messages"][1]["has_image"] is True
    requests = asset_requests(case["requests"])
    assert {row["asset_id"] for row in requests} == {1, 2, 3}
    auxiliary = [row for row in requests if row["asset_id"] == 1]
    assert 1 <= len(auxiliary) <= 2
    assert all(row["fault"] == "complete" for row in auxiliary)
    assert Counter(
        (row["asset_id"], row["fault"]) for row in requests if row["asset_id"] != 1
    ) == Counter({(2, "gated"): 1, (3, "complete"): 1})
    trace = case["trace"]
    for row in trace:
        assert set(row) == {"event", "asset_id", "cache_file", "file_size", "digest_ok"}
        assert row["asset_id"] in (1, 2, 3)
        assert row["cache_file"] == f"{row['asset_id']}_1.jpg"
        assert row["event"] not in ("media_load_failure", "media_load_cancel")
    for asset_id, count in ((1, len(auxiliary)), (2, 1), (3, 1)):
        for event in ("media_load_start", "media_load_success"):
            assert (
                sum(row["event"] == event and row["asset_id"] == asset_id for row in trace) == count
            )
    assert sum(row["event"] == "media_load_success" and row["asset_id"] == 2 for row in trace) == 1
    assert any(row["event"] == "media_load_coalesced" and row["asset_id"] == 2 for row in trace)
    assert not any(row["event"] == "media_load_cancel" and row["asset_id"] == 2 for row in trace)
    assert any(row["event"] == "media_load_success" and row["asset_id"] == 3 for row in trace)
    final_files = case["files"]
    assert not any(Path(row["path"]).name.endswith(".part") for row in final_files)
    assert {Path(row["path"]).name for row in final_files} == {"1_1.jpg", "2_1.jpg", "3_1.jpg"}
    for row in final_files:
        asset_id = int(Path(row["path"]).name.split("_")[0])
        base = "/storage/emulated/0/Android/data/org.gramlab.android/"
        assert row["path"] in {
            base + f"cache/{asset_id}_1.jpg",
            base + f"files/Telegram/Telegram Images/{asset_id}_1.jpg",
        }
        assert row["size"] == expected[asset_id - 1]["file_size"]
        assert row["sha256"] == expected[asset_id - 1]["sha256"]

    guards = observed["guards"]
    expected_guards = {
        "not-object",
        "wrong-schema",
        "extra-field",
        "targets-scalar",
        "targets-empty",
        "target-extra",
        "message-bool",
        "kind-invalid",
        "ids-scalar",
        "ids-empty",
        "id-zero",
        "id-bool",
        "id-duplicate",
        "message-duplicate",
        "wrong-asset",
        "ambiguous",
        "missing-message",
        "wrong-kind",
    }
    assert set(guards) == expected_guards
    failures = {name: guard["failure"] for name, guard in guards.items() if "failure" in guard}
    assert not failures, json.dumps(failures, indent=2)
    unavailable = {
        "wrong-asset": "unsupported_photo",
        "ambiguous": "ambiguous_photo",
        "missing-message": "message_not_unique_or_visible",
        "wrong-kind": "asset_mismatch",
    }
    for name, guard in guards.items():
        if name in unavailable:
            assert guard["sample"]["available"] is False
            assert guard["sample"]["reason"] == unavailable[name]
            assert {
                key: guard["sample"][key]
                for key in ("schema", "nonce", "world_id", "user_id", "peer_id")
            } == {
                "schema": 2,
                "nonce": name,
                "world_id": "rich-photo-guard",
                "user_id": 1,
                "peer_id": 2,
            }
        else:
            assert guard["sample"] is None
            assert any(row["event"] == "startup_rejected" for row in guard["trace"])
            assert not any(row["event"] == "initialized" for row in guard["trace"])
            assert not asset_requests(guard["requests"])

    screenshots = tuple(
        Screenshot(caption=Path(name).stem, png=(tmp_path / name).read_bytes())
        for name in case["captures"]
    )
    assert len(screenshots) == 4
    assert all(image.png.startswith(b"\x89PNG\r\n\x1a\n") for image in screenshots)
    write_report(
        tmp_path / "report-rich-photo-late.html",
        Report(
            run_id="rich-photo-late-completion",
            title="Original rich photo late completion",
            mode="headless-android",
            outcome="passed",
            seed=17,
            profile={
                "Android SDK": str(toolchain["sdk"]["platform"]),
                "System image": image_package,
                "Display": "320 x 640 at 160 dpi",
                "Theme": "Original app default light theme",
                "Fonts": "Pinned AOSP system fonts",
                "APK SHA-256": hashlib.sha256(Path(apk).read_bytes()).hexdigest(),
            },
            summary="An edited original rich receiver remains bound to C while its old shared "
            "B transfer completes in the ordinary receiver.",
            evidence={
                "Late completion": case,
                "Schema-2 guards": guards,
                "Expected assets": expected,
                "Network isolation": full["network"],
                "Emulator filesystem": full["emulator_filesystem"],
                "Guest fingerprint": full["fingerprint"],
                "Graphics": full["graphics"],
            },
            screenshots=screenshots,
            limitations=(
                "This relies on the unchanged leading rich photo preventing original "
                "whole-message cleanup. Ordinary photo edits retain their separately "
                "observed global cancellation behavior. The private observer does not "
                "expose every render frame or a public atomic input API.",
            ),
        ),
    )
