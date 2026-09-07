"""Original UI cancellation, shared receivers and ordinary-edit global cleanup."""

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
    assert_interaction_observation(tmp_path, full, apk, toolchain, image_package, expected)


def assert_interaction_observation(
    tmp_path: Path,
    full: dict[str, Any],
    apk: str,
    toolchain: dict[str, Any],
    image_package: str,
    expected: list[dict[str, Any]],
    *,
    acceptance_note: str = "",
    report_suffix: str = "",
) -> None:
    assert_isolation(full)
    observed = full["extra_probe"]
    assert "Accounts: 0" in observed["accounts"]
    failures = {
        name: case["failure"] for name, case in observed["cases"].items() if "failure" in case
    }
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
    for name, case in observed["cases"].items():
        if "failure" not in case:
            assert_interaction_case(
                tmp_path,
                name,
                case,
                expected,
                full,
                apk,
                toolchain,
                image_package,
                acceptance_note=acceptance_note,
                report_path=tmp_path / f"report-{name}{report_suffix}.html",
            )
    assert not failures, json.dumps(failures, indent=2)


def assert_interaction_case(
    tmp_path: Path,
    name: str,
    case: dict[str, Any],
    expected: list[dict[str, Any]],
    full: dict[str, Any],
    apk: str,
    toolchain: dict[str, Any],
    image_package: str,
    *,
    acceptance_note: str = "",
    report_path: Path | None = None,
) -> None:
    assert "failure" not in case
    gated = {"operation": "asset", "asset_id": 1, "fault": "gated"}
    complete = {"operation": "asset", "asset_id": 1, "fault": "complete"}
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
        assert asset_requests(case["requests"]) == [gated]
        before = case["shared_binding"]["messages"]
        assert [row["has_image"] for row in before] == [False, True]
        assert before[0]["progress_icon"] == 4
        assert before[0]["progress"] == 1
        assert any(row["event"] == "media_load_coalesced" for row in trace)
        assert before[1]["image_key"].startswith("1_1@")
    else:
        assert Counter((row["event"], row["asset_id"]) for row in terminals) == Counter(
            {("media_load_success", 2): 1, ("media_load_cancel", 1): 1}
        )
        assert success_ids == [2]
        assert any(row["event"] == "media_load_coalesced" for row in trace)
        assert case["response_finished"] is True
        assert asset_requests(case["requests"]) == [gated, complete | {"asset_id": 2}]
        before = case["new_binding"]["messages"]
        assert [row["has_image"] for row in before] == [True, False]
        assert before[0]["image_key"].startswith("2_1@")
        assert len(case["post_release_bindings"]) == 2
        for binding in case["post_release_bindings"]:
            assert binding["messages"][0]["image_key"] == before[0]["image_key"]
            assert binding["messages"][0]["has_image"] is True
            assert binding["messages"][1]["image_key"].startswith("1_1@")
            assert binding["messages"][1]["has_image"] is False
        assert (
            case["post_release_bindings"][1]["generation"]
            > case["post_release_bindings"][0]["generation"]
        )
        assert case["taps"] == []
    if name != "late-edit":
        assert success_ids == [1]
        count = 2 if name == "cancel-retry" else 1
        assert len(case["taps"]) == count
        assert [tap["message_id"] for tap in case["taps"]] == [1] * count
        assert [tap["sample"]["messages"][0]["progress_icon"] for tap in case["taps"]] == [3, 2][
            :count
        ]
        assert all(not row["has_image"] for row in case["loading"]["messages"])
        assert [row["progress_icon"] for row in case["canceled"]["messages"]] == (
            [2] if name == "cancel-retry" else [2, 3]
        )
        assert 0 <= case["cancel_elapsed"] < 4.8
    bindings = case["final_binding"]["messages"]
    assert [row["message_id"] for row in bindings] == ([1] if name == "cancel-retry" else [1, 2])
    assert [row["has_image"] for row in bindings] == (
        [False, True]
        if name == "shared-consumer"
        else [True, False]
        if name == "late-edit"
        else [True]
    )
    assert [row["progress_icon"] for row in bindings] == (
        [4, 3] if name == "late-edit" else [4] * len(bindings)
    )
    expected_ids = [2, 1] if name == "late-edit" else [1] * len(bindings)
    for row, asset_id in zip(bindings, expected_ids, strict=True):
        assert row["image_key"].startswith(f"{asset_id}_1@")
    cached_ids = {2} if name == "late-edit" else set(expected_ids)
    assert {Path(row["path"]).name for row in case["files"]} == {
        f"{asset}_1.jpg" for asset in cached_ids
    }
    assert len(case["files"]) == len(cached_ids)
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
        report_path or tmp_path / f"report-{name}.html",
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
            "local transfers." + (" " + acceptance_note if acceptance_note else ""),
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
                "Observation and ordinary input are not an atomic public targeting API. "
                "Ordinary photo replacement invokes original global cleanup: the unchanged "
                "shared cell retains its loading control without a bitmap after cancellation. "
                "Actual old-transfer completion after edit requires the separate rich-photo case.",
            ),
        ),
    )
