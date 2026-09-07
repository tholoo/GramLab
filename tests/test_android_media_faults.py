"""Original Android rejects controlled photo faults and retries only after restart."""

import hashlib
import json
import os
import shutil
import xml.etree.ElementTree as ET
from dataclasses import asdict
from pathlib import Path

import pytest
from test_android_quoted_code import assert_isolation

from gramlab.reports import Report, Screenshot, write_report
from gramlab.runtime import RuntimeProfile, Sandbox

pytestmark = pytest.mark.android
FAULTS = ("truncate", "corrupt", "redirect", "missing")
PHOTO = Path("tests/assets/rich-media/photo-quadrants-64x48.jpg")


def test_original_photo_failures_leave_no_bytes_and_cold_restart_recovers(
    tmp_path: Path,
) -> None:
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
    shutil.copy2(apk, tmp_path / "client.apk")
    shutil.copy2(
        "tests/assets/rich-media/photo-quadrants-64x48.jpg",
        tmp_path / "photo-quadrants-64x48.jpg",
    )
    shutil.copytree(
        "src/gramlab", tmp_path / "gramlab", ignore=shutil.ignore_patterns("__pycache__")
    )
    (tmp_path / "emulator-profile.json").write_text(json.dumps(asdict(profile)))
    for name in (
        "emulator_process.py",
        "android_guest.py",
        "media_transfer_server.py",
        "android_media_faults.py",
    ):
        shutil.copy2(Path("tests/probes") / name, tmp_path / name)
    result = Sandbox(profile).supervise(
        [
            profile.python,
            "/work/android_media_faults.py",
            profile.executables["emulator"],
            profile.executables["adb"],
            profile.executables["avdmanager"],
            image_package,
        ],
        data=tmp_path,
        kvm=True,
        timeout=600,
    )
    (tmp_path / "media-fault-result.json").write_text(result.stdout)
    (tmp_path / "media-fault-stderr.log").write_text(result.stderr)
    assert result.returncode == 0, result.stderr
    full = json.loads(result.stdout)
    assert_isolation(full)
    observed = full["extra_probe"]
    assert set(observed["cases"]) == set(FAULTS)
    assert "Accounts: 0" in observed["accounts"]
    expected = {
        "size": PHOTO.stat().st_size,
        "sha256": hashlib.sha256(PHOTO.read_bytes()).hexdigest(),
    }
    assert observed["photo"] == expected

    screenshots = []
    for fault in FAULTS:
        case = observed["cases"][fault]
        before_assets = [
            request for request in case["requests_before_retry"] if request["operation"] == "asset"
        ]
        assert before_assets
        assert all(
            request == {"operation": "asset", "asset_id": 1, "fault": fault}
            for request in before_assets
        )
        assert not any(
            row["event"] in ("media_load_success", "media_cache_hit")
            for row in case["failed_trace"]
        )
        failures = [
            row
            for row in case["failed_trace"]
            if row["event"] == "media_load_failure" and row["asset_id"] == 1
        ]
        assert failures
        assert all(row["cache_file"] == "1_1.jpg" and row["digest_ok"] is False for row in failures)
        assert case["failed_files"] == []

        all_assets = [request for request in case["requests"] if request["operation"] == "asset"]
        assert all_assets[: len(before_assets)] == before_assets
        assert all_assets[len(before_assets) :] == [
            {"operation": "asset", "asset_id": 1, "fault": "complete"}
        ]
        successes = [
            row
            for row in case["recovered_trace"]
            if row["event"] == "media_load_success" and row["asset_id"] == 1
        ]
        assert successes
        assert all(
            row["cache_file"] == "1_1.jpg"
            and row["file_size"] == expected["size"]
            and row["digest_ok"] is True
            for row in successes
        )
        assert len(case["recovered_files"]) == 1
        recovered = case["recovered_files"][0]
        assert Path(recovered["path"]).name == "1_1.jpg"
        assert recovered["size"] == expected["size"]
        assert recovered["sha256"] == expected["sha256"]

        for stage in ("failed", "recovered"):
            capture = case[f"{stage}_capture"]
            assert (tmp_path / capture["png"]).read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
            xml = ET.fromstring(capture["xml"])  # noqa: S314 — dedicated guest UI XML
            labels = "\n".join(node.get("text", "") for node in xml.iter("node"))
            assert "Fault recovery / بازیابی تصویر" in labels
            screenshots.append(
                Screenshot(caption=f"{fault}-{stage}", png=(tmp_path / capture["png"]).read_bytes())
            )
        assert (tmp_path / case["failed_capture"]["png"]).read_bytes() != (
            tmp_path / case["recovered_capture"]["png"]
        ).read_bytes()

    write_report(
        tmp_path / "report.html",
        Report(
            run_id="media-fault-restart-recovery",
            title="Original Android photo failure and retry",
            mode="headless-android",
            outcome="passed",
            seed=17,
            profile={
                "Android SDK": str(toolchain["sdk"]["platform"]),
                "System image": image_package,
                "Display": "320 x 640 at 160 dpi",
            },
            summary="Truncated, corrupt, redirected and missing local photos fail without cache "
            "publication, then load only after an explicitly enabled cold-restart retry.",
            evidence={
                "Fault cases": observed["cases"],
                "Expected photo": expected,
                "Network isolation": full["network"],
                "Emulator filesystem": full["emulator_filesystem"],
            },
            screenshots=tuple(screenshots),
            limitations=(
                "This fixture covers response faults and restart retry; cancellation and a late "
                "old transfer after edit remain separate acceptance work.",
            ),
        ),
    )
