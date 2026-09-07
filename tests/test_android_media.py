"""Original Android media rendering, loader diagnostics and private cache evidence."""

import hashlib
import json
import os
import shutil
import xml.etree.ElementTree as ET
from collections import Counter
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
    run_native_media(tmp_path, control=False)


def test_unchanged_photo_reuses_original_destination_after_cold_restart(tmp_path: Path) -> None:
    run_native_media(tmp_path, control=True)


def run_native_media(tmp_path: Path, *, control: bool) -> None:
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
    if control:
        (tmp_path / "unchanged-photo-control.json").write_text("{}\n")
    shutil.copy2(apk, tmp_path / "client.apk")
    (tmp_path / "emulator-profile.json").write_text(json.dumps(asdict(profile)))
    for name in (
        "emulator_process.py",
        "android_guest.py",
        "android_media.py",
        "native_asset_proxy.py",
    ):
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
    if control:
        assert_unchanged_observation(tmp_path, full, apk, toolchain)
    else:
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
    assert_cache_lifecycle(client["cache"])

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
    assert_phase_requests(tmp_path, client, final_rows, control=False)

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
            "photo, and verifies original destination cleanup followed by exact JPEG reload "
            "on cold restart. Unchanged-photo destination reuse has a separate control."
            + (" " + acceptance_note if acceptance_note else ""),
            evidence={
                "Semantic round trip": observed,
                "Media loader trace": media_trace,
                "Private cache observations": client["cache"],
                "Native-only asset requests": client["native_requests"],
                "Phase boundaries": client["phases"],
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


def assert_cache_lifecycle(cache: dict[str, Any], *, control: bool = False) -> None:
    """Exact independent original-directory oracle; usable on preserved pre-proxy evidence."""
    image = "/storage/emulated/0/Android/data/org.gramlab.android/files/Telegram/Telegram Images/"
    temporary = "/storage/emulated/0/Android/data/org.gramlab.android/cache/"
    directories = (
        {"initial": {1: {image}}, "restart": {1: {image}}}
        if control
        else {
            "initial": {1: {image}, 2: {image, temporary}},
            "edited": {1: {image, temporary}, 2: {temporary}},
            "restart": {1: {image, temporary}, 2: {image, temporary}},
        }
    )
    assert set(cache) == set(directories)
    for stage, assets in directories.items():
        assert set(cache[stage]) == {f"{asset}_1.jpg" for asset in assets}
        for asset, locations in assets.items():
            source = PNG if asset == 1 else JPEG
            filename = f"{asset}_1.jpg"
            copies = cache[stage][filename]["copies"]
            assert copies == [
                {
                    "path": directory + filename,
                    "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                    "size": source.stat().st_size,
                }
                for directory in sorted(locations)
            ]


def assert_phase_requests(
    tmp_path: Path, client: dict[str, Any], rows: list[dict[str, Any]], *, control: bool
) -> None:
    expected = (
        {"initial": {1: 1}, "restart": {1: 0}}
        if control
        else {"initial": {1: 1, 2: 2}, "edited": {1: 1, 2: 0}, "restart": {1: 0, 2: 1}}
    )
    assert set(client["phases"]) == set(expected)
    assert client["partials"] == {stage: [] for stage in expected}
    requests = client["native_requests"]
    assert json.loads((tmp_path / "native-asset-requests.json").read_text()) == requests
    assert [r["sequence"] for r in requests] == list(range(1, len(requests) + 1))
    assert all(r["phase"] in expected for r in requests)
    for request in requests:
        assert set(request) == {
            "sequence",
            "phase",
            "asset_id",
            "status",
            "bytes",
            "started_ns",
            "finished_ns",
            "error",
        }
        assert request["asset_id"] in expected[request["phase"]]
        assert request["status"] == 200 and request["error"] is None
        assert request["finished_ns"] >= request["started_ns"] > 0
        assert request["bytes"] == (PNG if request["asset_id"] == 1 else JPEG).stat().st_size
    end = 0
    for stage, counts in expected.items():
        phase = client["phases"][stage]
        assert set(phase) == {"trace_start", "trace_end", "media_start"}
        assert type(phase["trace_start"]) is type(phase["trace_end"]) is int
        assert 0 <= phase["trace_start"] < phase["trace_end"] <= len(rows)
        assert phase["trace_start"] == end
        assert phase["media_start"] == sum(
            r.get("event", "").startswith("media_") for r in rows[:end]
        )
        end = phase["trace_end"]
        assert json.loads((tmp_path / f"{stage}-cache.json").read_text()) == client["cache"][stage]
        assert json.loads((tmp_path / f"{stage}-partials.json").read_text()) == []
        selected = rows[phase["trace_start"] : end]
        assert selected
        assert any(
            r.get("event") == ("events_applied" if stage == "edited" else "initialized")
            for r in selected
        )
        for event in ("media_load_start", "media_load_success"):
            assert Counter(r["asset_id"] for r in selected if r.get("event") == event) == Counter(
                {k: v for k, v in counts.items() if v}
            )
        assert Counter(r["asset_id"] for r in requests if r["phase"] == stage) == Counter(
            {k: v for k, v in counts.items() if v}
        )
        media = [r for r in selected if r.get("event", "").startswith("media_")]
        assert not any(r["event"] in ("media_load_failure", "media_load_cancel") for r in media)
        for row in media:
            assert set(row) == {"event", "asset_id", "cache_file", "file_size", "digest_ok"}
            assert row["asset_id"] in counts
            assert row["cache_file"] == f"{row['asset_id']}_1.jpg"
            assert row["file_size"] == (PNG if row["asset_id"] == 1 else JPEG).stat().st_size
            if row["event"] in ("media_load_success", "media_cache_hit"):
                assert row["digest_ok"] is True
    assert end == len(rows)
    assert client["media_trace"] == [r for r in rows if r.get("event", "").startswith("media_")]


def assert_unchanged_snapshot(snapshot: dict[str, Any]) -> None:
    """Complete independent fixture envelope shared with the guarded real-HTTP check."""
    assert snapshot["messages"] == [
        {
            "id": 1,
            "chat_id": 1,
            "sender_id": 2,
            "date": 1700000000,
            "text": "",
            "photo": {"asset_id": 1},
            "caption": "PNG ordinary / تصویر معمولی",
        }
    ]
    assert snapshot["assets"] == [
        {
            "asset_id": 1,
            "mime_type": "image/png",
            "file_size": PNG.stat().st_size,
            "sha256": hashlib.sha256(PNG.read_bytes()).hexdigest(),
            "width": 16,
            "height": 16,
        }
    ]
    assert snapshot == {
        "schema": 3,
        "world_id": snapshot["world_id"],
        "user_id": 1,
        "users": [
            {"id": 1, "is_bot": False, "first_name": "Sara", "language_code": "fa"},
            {"id": 2, "is_bot": True, "first_name": "Echo", "username": "gramlab_echo_bot"},
        ],
        "chats": [{"id": 1, "type": "private", "user_id": 1, "bot_id": 2}],
        "messages": snapshot["messages"],
        "assets": snapshot["assets"],
        "sends": [],
        "message_revisions": [{"chat_id": 1, "message_id": 1, "revision": 4}],
        "cursor": 4,
        "now": 1700000000,
        "message_position": 1,
    }


def assert_unchanged_observation(
    tmp_path: Path, full: dict[str, Any], apk: str, toolchain: dict[str, Any]
) -> None:
    assert_isolation(full)
    observed = full["extra_probe"]
    snapshot = observed["snapshot"]
    assert snapshot == observed["restarted_snapshot"]
    assert_unchanged_snapshot(snapshot)
    client = observed["client"]
    assert_cache_lifecycle(client["cache"], control=True)
    rows = [json.loads(line) for line in (tmp_path / "final-trace.jsonl").read_text().splitlines()]
    assert sum(r.get("event") == "initialized" for r in rows) == 2
    assert_phase_requests(tmp_path, client, rows, control=True)
    assert (
        set(client["captures"])
        == set(client["launches"])
        == set(client["bindings"])
        == {"initial", "restart"}
    )
    assert client["bindings"]["initial"]["pid"] != client["bindings"]["restart"]["pid"]
    assert set(client["control_frames"]) == {"initial", "restart"}
    for stage in ("initial", "restart"):
        frame = client["control_frames"][stage]
        assert (
            frame["viewport_left"]
            <= frame["target_left"]
            < frame["target_right"]
            <= frame["viewport_right"]
        )
        assert (
            frame["viewport_top"]
            <= frame["target_top"]
            < frame["target_bottom"]
            <= frame["viewport_bottom"]
        )
        assert (
            "Status: ok" in client["launches"][stage]
            and "LaunchState: COLD" in client["launches"][stage]
        )
        xml = client["captures"][stage]
        assert "PNG ordinary / تصویر معمولی" in labels(xml)
        assert (tmp_path / f"{stage}.xml").read_text() == xml
        binding = client["bindings"][stage]
        assert binding == json.loads((tmp_path / f"{stage}-binding.json").read_text())
        assert binding["schema"] == 1 and binding["nonce"] == "unchanged-" + stage
        assert (
            binding["world_id"] == snapshot["world_id"]
            and binding["user_id"] == 1
            and binding["peer_id"] == 2
        )
        assert (
            binding["available"] is True and binding["reason"] is None and binding["generation"] > 0
        )
        assert 0 <= binding["observed_uptime_ms"] - binding["uptime_ms"] <= 1000
        assert len(binding["messages"]) == 1
        message = binding["messages"][0]
        assert message["message_id"] == 1 and message["has_image"] is True
        assert message["image_key"].startswith("1_1@")
        image = message["image_bounds"]
        visible = message["visible_bounds"]
        assert visible[0] <= image[0] < image[2] <= visible[2]
        assert visible[1] <= image[1] < image[3] <= visible[3]
        assert (tmp_path / f"{stage}.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
        assert (tmp_path / f"{stage}.png").stat().st_size > 1024
    assert "Accounts: 0" in client["accounts"]
    write_report(
        tmp_path / "report.html",
        Report(
            run_id="unchanged-photo-cold-restart",
            title="Unchanged original photo destination reuse",
            mode="headless-android",
            outcome="passed",
            seed=23,
            profile={
                "APK SHA-256": hashlib.sha256(Path(apk).read_bytes()).hexdigest(),
                "Android SDK": str(toolchain["sdk"]["platform"]),
                "Display": "320 x 640 at 160 dpi",
            },
            summary="One unchanged ordinary PNG retains its exact original image-directory bytes "
            "across a COLD process restart. The original ImageReceiver loads the photo without "
            "a new native asset GET.",
            evidence={
                "World and native observations": observed,
                "Network isolation": full["network"],
                "Emulator filesystem": full["emulator_filesystem"],
                "Guest fingerprint": full["fingerprint"],
            },
            screenshots=tuple(
                Screenshot(caption=stage, png=(tmp_path / f"{stage}.png").read_bytes())
                for stage in ("initial", "restart")
            ),
            limitations=(
                "The retained original screenshots require visual inspection.",
                "This control covers one unchanged ordinary photo and its selected destination; "
                "edited rich photos have separate original cleanup behavior.",
            ),
        ),
    )
