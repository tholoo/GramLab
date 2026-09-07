"""Original Android media rendering, loader diagnostics and private cache evidence."""

import hashlib
import json
import os
import shutil
import xml.etree.ElementTree as ET
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pytest
from test_android_quoted_code import assert_isolation
from test_media_round_trip import JPEG, PNG, assert_media_scenario, stage_media_scenario

from gramlab.reports import Report, Screenshot, write_report
from gramlab.runtime import RuntimeProfile, Sandbox

pytestmark = pytest.mark.android


def labels(xml: str) -> str:
    tree = ET.fromstring(xml)  # noqa: S314 — dedicated guest UIAutomator output
    return "\n".join(node.get("text", "") for node in tree.iter("node"))


def test_real_photos_render_edit_cache_and_survive_cold_restart(tmp_path: Path) -> None:
    manifest = os.environ.get("GRAMLAB_ANDROID_RUNTIME_PROFILE")
    apk = os.environ.get("GRAMLAB_ANDROID_PROBE_APK")
    if manifest is None or apk is None or not os.access("/dev/kvm", os.R_OK | os.W_OK):
        pytest.skip("Requires the Android profile, reviewed media APK and accessible KVM")
    profile = RuntimeProfile.load(Path(manifest))
    core = RuntimeProfile.load(Path(os.environ["GRAMLAB_RUNTIME_PROFILE"]))
    toolchain = json.loads(Path("clients/android/toolchain.json").read_text())
    image_package = (
        f"system-images;android-{toolchain['sdk']['platform']};"
        f"{toolchain['runtime']['imageType']};{toolchain['runtime']['abi']}"
    )
    stage_media_scenario(tmp_path, core)
    shutil.copy2(apk, tmp_path / "client.apk")
    (tmp_path / "emulator-profile.json").write_text(json.dumps(asdict(profile)))
    for name in ("emulator_process.py", "android_guest.py", "android_media.py"):
        shutil.copy2(Path("tests/probes") / name, tmp_path / name)
    result = Sandbox(profile).supervise(
        [
            profile.python,
            "/work/android_media.py",
            profile.executables["emulator"],
            profile.executables["adb"],
            profile.executables["avdmanager"],
            image_package,
        ],
        data=tmp_path,
        kvm=True,
        timeout=480,
    )
    (tmp_path / "media-native-result.json").write_text(result.stdout)
    (tmp_path / "media-native-stderr.log").write_text(result.stderr)
    assert result.returncode == 0, result.stderr
    full = json.loads(result.stdout)
    assert_media_observation(tmp_path, full, apk, toolchain)


def assert_media_observation(
    tmp_path: Path,
    full: dict[str, Any],
    apk: str,
    toolchain: dict[str, Any],
    *,
    acceptance_note: str = "",
    report_path: Path | None = None,
) -> None:
    """Validate retained real-guest evidence without rerunning the guest or changing bytes."""
    image_package = (
        f"system-images;android-{toolchain['sdk']['platform']};"
        f"{toolchain['runtime']['imageType']};{toolchain['runtime']['abi']}"
    )
    assert_isolation(full)
    observed = full["extra_probe"]
    assert_media_scenario(observed)
    client = observed["client"]["observed"]

    assert set(client["captures"]) == {"initial-bottom", "initial-top", "edited", "restart"}
    for phase, xml in client["captures"].items():
        assert (tmp_path / f"{phase}.xml").read_text() == xml
        screenshot = (tmp_path / f"{phase}.png").read_bytes()
        assert screenshot.startswith(b"\x89PNG\r\n\x1a\n")
        assert len(screenshot) > 1024
    initial_labels = labels(client["captures"]["initial-bottom"]) + labels(
        client["captures"]["initial-top"]
    )
    assert "PNG ordinary / تصویر معمولی" in initial_labels
    assert "Original JPEG" in initial_labels
    assert "عکس اصلی" in initial_labels
    assert client["framing"]
    final_frame = client["framing"][-1]
    assert final_frame["target_left"] >= final_frame["viewport_left"]
    assert final_frame["target_right"] <= final_frame["viewport_right"]
    assert final_frame["target_top"] >= final_frame["viewport_top"]
    assert final_frame["target_bottom"] <= final_frame["viewport_bottom"]
    final_attempt = final_frame["attempt"]
    for attempt in range(final_attempt + 1):
        assert (tmp_path / f"initial-framing-{attempt}.xml").is_file()
        assert (
            (tmp_path / f"initial-framing-{attempt}.png")
            .read_bytes()
            .startswith(b"\x89PNG\r\n\x1a\n")
        )
        assert (tmp_path / f"initial-framing-{attempt}-structure.json").is_file()
    assert (tmp_path / "initial-top.xml").read_text() == (
        tmp_path / f"initial-framing-{final_attempt}.xml"
    ).read_text()
    assert (tmp_path / "initial-top.png").read_bytes() == (
        tmp_path / f"initial-framing-{final_attempt}.png"
    ).read_bytes()
    for phase in ("edited", "restart"):
        visible = labels(client["captures"][phase])
        assert "ویرایش / Edited" in visible
        assert "new photo" in visible

    expected_cache = {
        "1_1.jpg": {
            "sha256": hashlib.sha256(PNG.read_bytes()).hexdigest(),
            "size": PNG.stat().st_size,
        },
        "2_1.jpg": {
            "sha256": hashlib.sha256(JPEG.read_bytes()).hexdigest(),
            "size": JPEG.stat().st_size,
        },
    }
    assert set(client["cache"]) == {"initial", "edited", "restart"}
    initial_paths: dict[str, list[str]] = {}
    edited_paths: dict[str, list[str]] = {}
    for phase, files in client["cache"].items():
        assert set(files) == set(expected_cache)
        for filename, expected in expected_cache.items():
            copies = files[filename]["copies"]
            assert copies
            paths = []
            for observation in copies:
                assert Path(observation["path"]).name == filename
                assert observation["sha256"] == expected["sha256"]
                assert observation["size"] == expected["size"]
                paths.append(observation["path"])
            assert paths == sorted(set(paths))
            if phase == "initial":
                initial_paths[filename] = paths
            elif phase == "edited":
                # Rich and ordinary receivers select different upstream cache directories.
                # The first rich use may add a copy; existing bytes/locations must survive.
                assert set(initial_paths[filename]) <= set(paths)
                edited_paths[filename] = paths
            else:
                assert paths == edited_paths[filename]

    media_trace = client["media_trace"]
    assert media_trace
    assert all(
        set(row) == {"event", "asset_id", "cache_file", "file_size", "digest_ok"}
        for row in media_trace
    )
    assert not any(
        row["event"] in ("media_load_failure", "media_load_cancel") for row in media_trace
    )
    for asset_id, filename, expected in (
        (1, "1_1.jpg", expected_cache["1_1.jpg"]),
        (2, "2_1.jpg", expected_cache["2_1.jpg"]),
    ):
        matching = [row for row in media_trace if row["asset_id"] == asset_id]
        assert matching
        assert all(row["cache_file"] == filename for row in matching)
        assert all(row["file_size"] == expected["size"] for row in matching)
        assert any(
            row["event"] == "media_load_success" and row["digest_ok"] is True for row in matching
        )
    # Compare within the complete ordered trace. The edited polling trace precedes
    # viewport-driven cache work and cannot mark the cold-restart boundary.
    final_rows = [
        json.loads(line) for line in (tmp_path / "final-trace.jsonl").read_text().splitlines()
    ]
    initializations = [
        index for index, row in enumerate(final_rows) if row.get("event") == "initialized"
    ]
    assert len(initializations) == 2
    assert not any(
        row.get("event") == "media_load_start" for row in final_rows[initializations[1] :]
    )

    assert set(client["launches"]) == {"initial", "restart"}
    for launch in client["launches"].values():
        assert "Status: ok" in launch and "LaunchState: COLD" in launch
    assert "Accounts: 0" in client["accounts"]

    write_report(
        report_path or tmp_path / "report.html",
        Report(
            run_id="media-send-edit-restart",
            title="Local photos in the original Android renderer",
            mode="headless-android",
            outcome="passed",
            seed=23,
            profile={
                "Android SDK": str(toolchain["sdk"]["platform"]),
                "System image": image_package,
                "Display": "320 x 640 at 160 dpi",
                "Theme": "Original app default light theme",
                "Fonts": "Pinned AOSP system fonts",
                "APK SHA-256": hashlib.sha256(Path(apk).read_bytes()).hexdigest(),
            },
            summary="A contained real bot publishes PNG and JPEG photos, edits the primary rich "
            "photo, and the original Android client retains decoded media across cold restart."
            + (" " + acceptance_note if acceptance_note else ""),
            evidence={
                "Semantic round trip": observed,
                "Media loader trace": media_trace,
                "Private cache observations": client["cache"],
                "Network isolation": full["network"],
                "Emulator filesystem": full["emulator_filesystem"],
                "Guest fingerprint": full["fingerprint"],
                "Graphics": full["graphics"],
            },
            timings={
                name.removesuffix("_seconds"): seconds * 1000
                for name, seconds in client["timings"].items()
            },
            screenshots=tuple(
                Screenshot(caption=phase, png=(tmp_path / f"{phase}.png").read_bytes())
                for phase in ("initial-bottom", "initial-top", "edited", "restart")
            ),
            limitations=(
                "Visual decoding requires inspection of the retained original screenshots.",
                "This first profile covers complete PNG/JPEG photos, not albums or documents.",
            ),
        ),
    )
