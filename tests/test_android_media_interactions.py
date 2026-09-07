"""Original UI cancellation and stable photo bindings across out-of-order transfers."""

import hashlib
import json
import os
import shutil
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pytest
from test_android_quoted_code import assert_isolation

from gramlab.reports import Report, Screenshot, write_report
from gramlab.runtime import RuntimeProfile, Sandbox

pytestmark = pytest.mark.android


def asset_requests(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in rows if row["operation"] == "asset"]


def test_original_photo_cancel_retry_shared_consumers_and_late_edit(tmp_path: Path) -> None:
    manifest = os.environ.get("GRAMLAB_ANDROID_RUNTIME_PROFILE")
    apk = os.environ.get("GRAMLAB_ANDROID_PROBE_APK")
    if manifest is None or apk is None or not os.access("/dev/kvm", os.R_OK | os.W_OK):
        pytest.skip("Requires Android profile, reviewed observation APK and accessible KVM")
    profile = RuntimeProfile.load(Path(manifest))
    toolchain = json.loads(Path("clients/android/toolchain.json").read_text())
    image_package = (
        f"system-images;android-{toolchain['sdk']['platform']};"
        f"{toolchain['runtime']['imageType']};{toolchain['runtime']['abi']}"
    )
    shutil.copy2(apk, tmp_path / "client.apk")
    expected = []
    for asset_id, filename, mime, width, height in (
        (1, "photo-wide-48x8.png", "image/png", 48, 8),
        (2, "photo-quadrants-64x48.jpg", "image/jpeg", 64, 48),
    ):
        photo = Path("tests/assets/rich-media") / filename
        shutil.copy2(photo, tmp_path / filename)
        expected.append(
            {
                "asset_id": asset_id,
                "mime_type": mime,
                "file_size": photo.stat().st_size,
                "sha256": hashlib.sha256(photo.read_bytes()).hexdigest(),
                "width": width,
                "height": height,
            }
        )
    shutil.copytree(
        "src/gramlab", tmp_path / "gramlab", ignore=shutil.ignore_patterns("__pycache__")
    )
    (tmp_path / "emulator-profile.json").write_text(json.dumps(asdict(profile)))
    for name in (
        "emulator_process.py",
        "android_guest.py",
        "media_transfer_server.py",
        "android_media_interactions.py",
    ):
        shutil.copy2(Path("tests/probes") / name, tmp_path / name)
    result = Sandbox(profile).supervise(
        [
            profile.python,
            "/work/android_media_interactions.py",
            profile.executables["emulator"],
            profile.executables["adb"],
            profile.executables["avdmanager"],
            image_package,
        ],
        data=tmp_path,
        kvm=True,
        timeout=600,
    )
    (tmp_path / "media-interaction-result.json").write_text(result.stdout)
    (tmp_path / "media-interaction-stderr.log").write_text(result.stderr)
    assert result.returncode == 0, result.stderr
    full = json.loads(result.stdout)
    assert_isolation(full)
    observed = full["extra_probe"]
    assert "Accounts: 0" in observed["accounts"]
    assert observed["assets"] == expected
    assert observed["stale_rejections"] == [
        {
            "from": "cancel-retry",
            "to": "shared-consumer",
            "reason": "Original photo input identity mismatch; no input",
        },
        {
            "from": "shared-consumer",
            "to": "late-edit",
            "reason": "Original photo input identity mismatch; no input",
        },
    ]
    guards = observed["observation_guards"]
    assert set(guards) == {"absent", "wrong-world", "missing-message"}
    assert guards["absent"]["sample"] is None
    assert any(row["event"] == "initialized" for row in guards["absent"]["trace"])
    assert guards["wrong-world"]["sample"] is None
    assert guards["wrong-world"]["trace"][-1]["event"] == "startup_rejected"
    assert not any(row["event"] == "initialized" for row in guards["wrong-world"]["trace"])
    assert not asset_requests(guards["wrong-world"]["requests"])
    missing = guards["missing-message"]["sample"]
    assert missing["available"] is False and missing["messages"] == []
    assert missing["reason"] == "message_not_unique_or_visible"
    assert set(observed["cases"]) == {"cancel-retry", "shared-consumer", "late-edit"}
    gated = {"operation": "asset", "asset_id": 1, "fault": "gated"}
    complete = {"operation": "asset", "asset_id": 1, "fault": "complete"}
    for name, case in observed["cases"].items():
        assert 0 <= case["release_elapsed"] < 4.8
        assert case["released_at"] > case["partial_sent_at"]
        trace = case["final_trace"]
        for row in trace:
            assert set(row) == {"event", "asset_id", "cache_file", "file_size", "digest_ok"}
            assert row["asset_id"] in (1, 2)
            assert row["cache_file"] == f"{row['asset_id']}_1.jpg"
            assert row["event"] != "media_load_failure"
        terminals = [
            row for row in trace if row["event"] in ("media_load_success", "media_load_cancel")
        ]
        success_ids = [row["asset_id"] for row in terminals if row["event"] == "media_load_success"]
        if name == "cancel-retry":
            assert [row["event"] for row in terminals] == [
                "media_load_cancel",
                "media_load_success",
            ]
            assert asset_requests(case["requests_before_retry"]) == [gated]
            assert asset_requests(case["requests"]) == [gated, complete]
            assert case["files_before_retry"] == []
        elif name == "shared-consumer":
            assert [row["event"] for row in terminals] == ["media_load_success"]
            assert asset_requests(case["requests_before_retry"]) == [gated]
            assert asset_requests(case["requests"]) == [gated]
            before = case["shared_binding"]["messages"]
            assert [row["has_image"] for row in before] == [False, True]
            assert before[0]["progress_icon"] == 2
            assert before[1]["image_key"].startswith("1_1@")
        else:
            assert [row["event"] for row in terminals] == [
                "media_load_success",
                "media_load_success",
            ]
            assert success_ids == [2, 1]
            assert asset_requests(case["requests"]) == [gated, complete | {"asset_id": 2}]
            before = case["new_binding"]["messages"]
            assert [row["has_image"] for row in before] == [True, False]
            assert before[0]["image_key"].startswith("2_1@")
            assert case["post_release_bindings"]
            for binding in case["post_release_bindings"]:
                assert binding["messages"][0]["image_key"] == before[0]["image_key"]
                assert binding["messages"][0]["has_image"] is True
            assert case["taps"] == []
        if name != "late-edit":
            assert success_ids == [1]
            assert len(case["taps"]) == 2
            assert [tap["message_id"] for tap in case["taps"]] == [1, 1]
            assert [tap["sample"]["messages"][0]["progress_icon"] for tap in case["taps"]] == [3, 2]
            assert 0 <= case["cancel_elapsed"] < 4.8
        bindings = case["final_binding"]["messages"]
        assert [row["message_id"] for row in bindings] == (
            [1] if name == "cancel-retry" else [1, 2]
        )
        assert all(row["has_image"] and row["progress_icon"] == 4 for row in bindings)
        expected_ids = [2, 1] if name == "late-edit" else [1] * len(bindings)
        for row, asset_id in zip(bindings, expected_ids, strict=True):
            assert row["image_key"].startswith(f"{asset_id}_1@")
        assert {Path(row["path"]).name for row in case["files"]} == {
            f"{asset}_1.jpg" for asset in expected_ids
        }
        assert len(case["files"]) == len(set(expected_ids))
        for row in case["files"]:
            asset = expected[int(Path(row["path"]).name.split("_")[0]) - 1]
            assert row["size"] == asset["file_size"]
            assert row["sha256"] == asset["sha256"]
        for row in terminals:
            if row["event"] == "media_load_success":
                assert row["digest_ok"] is True
                assert row["file_size"] == expected[row["asset_id"] - 1]["file_size"]
        screenshots = tuple(
            Screenshot(caption=Path(path).stem, png=(tmp_path / path).read_bytes())
            for path in case["captures"]
        )
        assert len(screenshots) == 3
        assert all(screenshot.png.startswith(b"\x89PNG\r\n\x1a\n") for screenshot in screenshots)
        write_report(
            tmp_path / f"report-{name}.html",
            Report(
                run_id=f"media-interaction-{name}",
                title=f"Original Android photo: {name}",
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
                summary="Original photo controls and image receivers observed during controlled "
                "local transfers.",
                evidence={
                    "Interaction": case,
                    "Expected assets": expected,
                    "Network isolation": full["network"],
                    "Emulator filesystem": full["emulator_filesystem"],
                    "Guest fingerprint": full["fingerprint"],
                    "Graphics": full["graphics"],
                },
                screenshots=screenshots,
                limitations=(
                    "Shared UI loading does not by itself prove the FileLoader coalescing branch. "
                    "Observation and ordinary input are not an atomic public targeting API.",
                ),
            ),
        )
