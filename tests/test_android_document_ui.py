"""Original Android acceptance for the forced ordinary-document lifecycle."""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pytest
from test_android_quoted_code import assert_isolation
from test_document_round_trip import (
    DOCUMENT_BYTES,
    PHOTO,
    REPLACEMENT_DOCUMENT_BYTES,
    SCENE,
    assert_document_scenario,
    stage_document_scenario,
)

from gramlab.reports import Report, Screenshot, write_report
from gramlab.runtime import RuntimeProfile, Sandbox

sys.path.insert(0, str(Path("tests/probes").resolve()))
from android_document_ui import FAILURE_TEXT_LIMIT, retain_failure_evidence
from android_document_ui import TRACE as TRACE_PATH

DOCUMENT_EVENTS = {
    "media_load_start",
    "media_load_coalesced",
    "media_load_success",
    "media_load_failure",
    "media_load_cancel",
    "media_cache_hit",
}


def test_document_callback_taps_follow_the_current_keyboard() -> None:
    from document_round_trip import CALLBACK_TAPS

    assert CALLBACK_TAPS == (
        ("initial", "Reuse / استفاده دوباره"),
        ("photo", "Replace with photo / عکس"),
        ("photo_caption", "Edit photo caption / زیرنویس"),
        ("document_final", "Replace with D2 / سند دوم"),
    )


def visible_labels(xml: str) -> str:
    root = ET.fromstring(xml)  # noqa: S314 — dedicated guest UIAutomator output
    return "\n".join(
        value
        for node in root.iter("node")
        for value in (node.get("text", ""), node.get("content-desc", ""))
        if value
    )


def _digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _json_object(path: Path) -> dict[str, Any]:
    if not path.is_file() or path.stat().st_size > 2 * 1024 * 1024:
        raise ValueError("Android provenance input is missing or oversized")
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError("Android provenance input must be an object")
    return value


def verify_android_build_provenance(
    apk: Path,
    pointer_path: Path,
    toolchain: dict[str, Any],
    *,
    series_path: Path = Path("clients/android/patches/series"),
    upstream_lock_path: Path = Path("clients/android/upstream-lock.json"),
) -> dict[str, Any]:
    """Bind an APK to the existing coordinator pointer and linked source records."""
    pointer = _json_object(pointer_path)
    required = {
        "sha256",
        "apk",
        "experimental",
        "patches",
        "source_provenance",
        "source_provenance_sha256",
    }
    if not required <= set(pointer) or pointer["experimental"] is not False:
        raise ValueError("Android APK pointer is incomplete or experimental")
    pointer_apk = Path(pointer["apk"])
    expected_apk = pointer["sha256"]
    if not isinstance(expected_apk, str) or _digest(apk) != expected_apk:
        raise ValueError("Supplied Android APK does not match its pointer")
    if not pointer_apk.is_file() or _digest(pointer_apk) != expected_apk:
        raise ValueError("Android APK pointer does not identify retained matching bytes")

    series = [
        line.strip()
        for line in series_path.read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if (
        pointer["patches"] != len(series)
        or len(series) < 30
        or series[29] != "0030-ordinary-document-delivery.patch"
        or any(Path(name).name != name for name in series)
    ):
        raise ValueError("Android APK pointer does not cover the current ordered patch series")
    patch_digests = [_digest(series_path.parent / name) for name in series]
    ordered_patches = [
        {"position": position, "name": name, "sha256": digest}
        for position, (name, digest) in enumerate(zip(series, patch_digests, strict=True), 1)
    ]

    source_path = Path(pointer["source_provenance"])
    expected_source_digest = pointer["source_provenance_sha256"]
    if (
        not isinstance(expected_source_digest, str)
        or _digest(source_path) != expected_source_digest
    ):
        raise ValueError("Android source provenance digest does not match its pointer")
    source = _json_object(source_path)
    if "upstream_revision" not in source or "ordered_patches" not in source:
        raise ValueError("Android source provenance lacks complete pinned source fields")
    if source.get("patches") != len(series) or source.get("patch") != patch_digests[-1]:
        raise ValueError("Android source provenance does not describe the complete patch series")
    if source["ordered_patches"] != ordered_patches:
        raise ValueError("Android source provenance ordered patch digests do not match the series")
    upstream = _json_object(upstream_lock_path)
    revision = toolchain.get("client", {}).get("revision")
    if source["upstream_revision"] != revision or upstream.get("clientRevision") != revision:
        raise ValueError("Android source provenance, toolchain and upstream lock revisions differ")
    return {
        "pointer_sha256": _digest(pointer_path),
        "apk_sha256": expected_apk,
        "source_provenance_sha256": expected_source_digest,
        "upstream_revision": revision,
        "ordered_patches": ordered_patches,
    }


def test_failure_evidence_is_bounded_redacted_and_complete(tmp_path: Path) -> None:
    capability = "gramlab-client_" + "s" * 43
    calls: list[tuple[str, ...]] = []

    def guest(*arguments: str, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        del kwargs
        calls.append(arguments)
        if arguments[0] == "pull":
            Path(arguments[-1]).write_bytes(b"\x89PNG\r\n\x1a\nfixture")
        if arguments[-1] == "/data/local/tmp/document-ui-failure.xml":
            output = f'<hierarchy token="{capability}" />'
        elif arguments[-1] == TRACE_PATH:
            output = json.dumps({"event": "media_load_failure", "secret": capability}) + "\n"
        elif arguments[0] == "logcat":
            output = capability + "\n" + "x" * (FAILURE_TEXT_LIMIT + 100)
        else:
            output = ""
        return subprocess.CompletedProcess(arguments, 0, output, "")

    retained = retain_failure_evidence(
        guest,
        lambda: [{"sequence": 1, "error": capability}],
        capability,
        "download",
        "stale-ui",
        directory=tmp_path,
    )
    assert (tmp_path / "download-failure.png").read_bytes().startswith(b"\x89PNG")
    for name in ("xml", "trace", "logcat", "requests"):
        evidence = retained[name]
        raw = (tmp_path / evidence["path"]).read_bytes()
        assert len(raw) == evidence["bytes"] <= FAILURE_TEXT_LIMIT
        assert capability.encode() not in raw
    ledger = json.loads((tmp_path / retained["requests"]["path"]).read_text())
    assert ledger == {"dropped": 0, "requests": [{"sequence": 1, "error": "[REDACTED]"}]}
    assert retained["logcat"]["truncated"] is True
    assert retained["screenshot"] == {
        "path": "download-failure.png",
        "capture_returncode": 0,
        "pull_returncode": 0,
    }
    assert json.loads((tmp_path / "download-failure-evidence.json").read_text()) == retained
    assert calls[:2] == [
        ("shell", "screencap", "-p", "/data/local/tmp/document-ui-failure.png"),
        (
            "pull",
            "/data/local/tmp/document-ui-failure.png",
            str(tmp_path / "download-failure.png"),
        ),
    ]


def test_apk_provenance_binds_delivery_patch_apk_and_upstream(tmp_path: Path) -> None:
    patches = tmp_path / "patches"
    patches.mkdir()
    names = [f"{position:04d}-fixture.patch" for position in range(1, 30)] + [
        "0030-ordinary-document-delivery.patch"
    ]
    digests = []
    for position, name in enumerate(names, 1):
        body = f"patch {position}\n".encode()
        (patches / name).write_bytes(body)
        digests.append(hashlib.sha256(body).hexdigest())
    series = patches / "series"
    series.write_text("\n".join(names) + "\n")

    revision = "62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c"
    ordered = [
        {"position": position, "name": name, "sha256": digest}
        for position, (name, digest) in enumerate(zip(names, digests, strict=True), 1)
    ]
    source_provenance = tmp_path / "source-provenance.json"
    source_record = {
        "patches": 30,
        "patch": digests[-1],
        "upstream_revision": revision,
        "ordered_patches": ordered,
    }
    source_provenance.write_text(json.dumps(source_record) + "\n")
    apk = tmp_path / "client.apk"
    apk.write_bytes(b"reviewed apk")
    apk_digest = hashlib.sha256(apk.read_bytes()).hexdigest()
    pointer = tmp_path / "apk.json"
    pointer.write_text(
        json.dumps(
            {
                "sha256": apk_digest,
                "apk": str(apk),
                "experimental": False,
                "patches": 30,
                "source_provenance": str(source_provenance),
                "source_provenance_sha256": hashlib.sha256(
                    source_provenance.read_bytes()
                ).hexdigest(),
            }
        )
        + "\n"
    )
    upstream = tmp_path / "upstream.json"
    upstream.write_text(json.dumps({"clientRevision": revision}) + "\n")
    toolchain = {"client": {"revision": revision}}

    verified = verify_android_build_provenance(
        apk,
        pointer,
        toolchain,
        series_path=series,
        upstream_lock_path=upstream,
    )
    assert verified["apk_sha256"] == apk_digest
    assert verified["upstream_revision"] == revision
    assert verified["ordered_patches"][-1] == {
        "position": 30,
        "name": "0030-ordinary-document-delivery.patch",
        "sha256": digests[-1],
    }
    assert verified["ordered_patches"] == ordered

    apk.write_bytes(b"unreviewed apk")
    with pytest.raises(ValueError, match="APK"):
        verify_android_build_provenance(
            apk, pointer, toolchain, series_path=series, upstream_lock_path=upstream
        )
    apk.write_bytes(b"reviewed apk")
    first = patches / names[0]
    first.write_bytes(b"changed pre24 patch\n")
    with pytest.raises(ValueError, match="ordered patch digests"):
        verify_android_build_provenance(
            apk, pointer, toolchain, series_path=series, upstream_lock_path=upstream
        )
    first.write_bytes(b"patch 1\n")
    delivery = patches / names[-1]
    delivery.write_bytes(b"changed delivery patch\n")
    with pytest.raises(ValueError, match=r"patch series|ordered patch digests"):
        verify_android_build_provenance(
            apk, pointer, toolchain, series_path=series, upstream_lock_path=upstream
        )
    delivery.write_bytes(b"patch 30\n")
    with pytest.raises(ValueError, match="upstream"):
        verify_android_build_provenance(
            apk,
            pointer,
            {"client": {"revision": "0" * 40}},
            series_path=series,
            upstream_lock_path=upstream,
        )
    incomplete = dict(source_record)
    del incomplete["ordered_patches"]
    source_provenance.write_text(json.dumps(incomplete) + "\n")
    pointer_record = json.loads(pointer.read_text())
    pointer_record["source_provenance_sha256"] = hashlib.sha256(
        source_provenance.read_bytes()
    ).hexdigest()
    pointer.write_text(json.dumps(pointer_record) + "\n")
    with pytest.raises(ValueError, match="lacks complete pinned source fields"):
        verify_android_build_provenance(
            apk, pointer, toolchain, series_path=series, upstream_lock_path=upstream
        )


@pytest.mark.android
def test_original_document_download_callback_reuse_and_restart(tmp_path: Path) -> None:
    manifest = os.environ.get("GRAMLAB_ANDROID_RUNTIME_PROFILE")
    apk = os.environ.get("GRAMLAB_ANDROID_PROBE_APK")
    if manifest is None or apk is None or not os.access("/dev/kvm", os.R_OK | os.W_OK):
        pytest.skip("Requires the Android profile, reviewed delivery104 APK and accessible KVM")
    pointer = os.environ.get("GRAMLAB_ANDROID_APK_PROVENANCE")
    if pointer is None:
        pytest.fail("A reviewed coordinator APK/source provenance pointer is required")
    toolchain = json.loads(Path("clients/android/toolchain.json").read_text())
    provenance = verify_android_build_provenance(Path(apk), Path(pointer), toolchain)
    profile = RuntimeProfile.load(Path(manifest))
    core = RuntimeProfile.load(Path(os.environ["GRAMLAB_RUNTIME_PROFILE"]))
    image_package = (
        f"system-images;android-{toolchain['sdk']['platform']};"
        f"{toolchain['runtime']['imageType']};{toolchain['runtime']['abi']}"
    )
    stage_document_scenario(tmp_path, core)
    shutil.copy2(apk, tmp_path / "client.apk")
    (tmp_path / "emulator-profile.json").write_text(json.dumps(asdict(profile)))
    for name in ("emulator_process.py", "android_guest.py", "android_document_ui.py"):
        shutil.copy2(Path("tests/probes") / name, tmp_path / name)
    result = Sandbox(profile).supervise(
        [
            profile.python,
            "/work/android_document_ui.py",
            profile.executables["emulator"],
            profile.executables["adb"],
            profile.executables["avdmanager"],
            image_package,
        ],
        data=tmp_path,
        kvm=True,
        timeout=480,
    )
    (tmp_path / "document-ui-native-result.json").write_text(result.stdout)
    (tmp_path / "document-ui-native-stderr.log").write_text(result.stderr)
    assert result.returncode == 0, result.stderr
    assert_android_document_observation(
        tmp_path,
        json.loads(result.stdout),
        Path(apk),
        Path(manifest),
        toolchain,
        image_package,
        provenance,
    )


def assert_android_document_observation(
    tmp_path: Path,
    full: dict[str, Any],
    apk: Path,
    manifest: Path,
    toolchain: dict[str, Any],
    image_package: str,
    provenance: dict[str, Any],
    *,
    acceptance_note: str = "",
    report_path: Path | None = None,
) -> None:
    """Validate retained native evidence without rerunning or replacing the guest."""
    assert_isolation(full)
    observed = full["extra_probe"]
    assert_document_scenario(observed)
    client = observed["client"]["observed"]

    assert set(client["captures"]) == {
        "initial",
        "downloaded",
        "document_caption",
        "photo",
        "photo_caption",
        "document_final",
        "restart-bottom",
        "restart-top",
    }
    for name, xml in client["captures"].items():
        assert (tmp_path / f"{name}.xml").read_text() == xml
        png = (tmp_path / f"{name}.png").read_bytes()
        assert png.startswith(b"\x89PNG\r\n\x1a\n") and len(png) > 1024
    initial = visible_labels(client["captures"]["initial"])
    downloaded = visible_labels(client["captures"]["downloaded"])
    document_caption = visible_labels(client["captures"]["document_caption"])
    photo = visible_labels(client["captures"]["photo"])
    photo_caption = visible_labels(client["captures"]["photo_caption"])
    document_final = visible_labels(client["captures"]["document_final"])
    restarted = visible_labels(client["captures"]["restart-bottom"]) + visible_labels(
        client["captures"]["restart-top"]
    )
    for labels in (initial, downloaded):
        assert SCENE["file_name"] in labels
        assert SCENE["caption"] in labels
        assert SCENE["button_text"] in labels
    assert SCENE["file_name"] in document_caption
    assert SCENE["edit_sequence"][0]["caption"] in document_caption
    assert SCENE["edit_sequence"][0]["button_text"] in document_caption
    assert SCENE["edit_sequence"][1]["caption"] in photo
    assert SCENE["edit_sequence"][1]["button_text"] in photo
    assert SCENE["edit_sequence"][2]["caption"] in photo_caption
    assert SCENE["edit_sequence"][2]["button_text"] in photo_caption
    assert SCENE["replacement_file_name"] in document_final
    assert SCENE["edit_sequence"][3]["caption"] in document_final
    assert SCENE["edit_sequence"][3]["button_text"] in document_final
    assert SCENE["replacement_file_name"] in restarted
    assert SCENE["reuse_caption"] in restarted and SCENE["file_name"] in restarted

    assert set(client["launches"]) == {"initial", "restart"}
    for launch in client["launches"].values():
        assert "Status: ok" in launch and "LaunchState: COLD" in launch
    assert "Accounts: 0" in client["accounts"]
    assert set(client["taps"]) == {
        "download",
        "document_caption",
        "photo",
        "photo_caption",
        "document_final",
        "replacement-download",
    }
    for tap in client["taps"].values():
        left, top, right, bottom = tap["bounds"]
        assert 0 <= left < right <= 320 and 0 <= top < bottom <= 640
    assert client["taps"]["download"]["label"] == SCENE["file_name"]
    assert client["taps"]["download"]["requests_before"] >= 0
    assert (
        client["taps"]["download"]["requests_after"] > client["taps"]["download"]["requests_before"]
    )
    assert client["taps"]["document_caption"]["label"] == SCENE["button_text"]
    for index, name in enumerate(("photo", "photo_caption", "document_final")):
        assert client["taps"][name]["label"] == SCENE["edit_sequence"][index]["button_text"]
    assert client["taps"]["replacement-download"]["label"] == SCENE["replacement_file_name"]

    requests = client["requests"]
    assert json.loads((tmp_path / "native-document-ui-requests.json").read_text()) == requests
    assert [row["sequence"] for row in requests] == list(range(1, len(requests) + 1))
    allowed = {
        "/v5/snapshot",
        "/v5/callbacks",
        "/v5/messages",
        "/v5/custom-emoji-documents",
    }
    for row in requests:
        assert set(row) == {
            "sequence",
            "phase",
            "method",
            "path",
            "kind",
            "identifier",
            "status",
            "bytes",
            "started_ns",
            "finished_ns",
            "error",
        }
        assert row["phase"] in {
            "initial",
            "document_caption",
            "photo",
            "photo_caption",
            "document_final",
            "restart",
        }
        assert row["method"] in {"GET", "POST"}
        assert row["path"] in allowed or row["path"].startswith(
            ("/v5/changes?", "/v5/callbacks/", "/v5/assets/", "/v5/documents/")
        )
        assert row["status"] == 200 and row["error"] is None
        assert row["bytes"] >= 0
        assert row["finished_ns"] >= row["started_ns"] > 0
    document_requests = [row for row in requests if row["kind"] == "document"]
    assert len(document_requests) == 2
    assert document_requests == [
        {
            "sequence": document_requests[0]["sequence"],
            "phase": "initial",
            "method": "GET",
            "path": "/v5/documents/1",
            "kind": "document",
            "identifier": "1",
            "status": 200,
            "bytes": len(DOCUMENT_BYTES),
            "started_ns": document_requests[0]["started_ns"],
            "finished_ns": document_requests[0]["finished_ns"],
            "error": None,
        },
        {
            "sequence": document_requests[1]["sequence"],
            "phase": "document_final",
            "method": "GET",
            "path": "/v5/documents/2",
            "kind": "document",
            "identifier": "2",
            "status": 200,
            "bytes": len(REPLACEMENT_DOCUMENT_BYTES),
            "started_ns": document_requests[1]["started_ns"],
            "finished_ns": document_requests[1]["finished_ns"],
            "error": None,
        },
    ]
    assert (
        client["taps"]["download"]["requests_before"]
        < document_requests[0]["sequence"]
        <= client["taps"]["download"]["requests_after"]
    )
    assert (
        client["taps"]["replacement-download"]["requests_before"]
        < document_requests[1]["sequence"]
        <= client["taps"]["replacement-download"]["requests_after"]
    )
    assert any(row["path"] == "/v5/custom-emoji-documents" for row in requests)
    assert any(row["kind"] == "asset" and row["identifier"] in {"1", "2"} for row in requests)
    photo_requests = [
        row for row in requests if row["kind"] == "asset" and row["identifier"] == "3"
    ]
    assert len(photo_requests) == 1
    assert (
        photo_requests[0]["phase"] == "photo" and photo_requests[0]["bytes"] == PHOTO.stat().st_size
    )

    bindings = client["photo_bindings"]
    assert list(bindings) == ["photo", "photo_caption"]
    previous_generation = 0
    pid = None
    identity_keys = ("schema", "nonce", "world_id", "user_id", "peer_id")
    for name, binding in bindings.items():
        assert binding == json.loads((tmp_path / f"{name}-binding.json").read_text())
        observed_identity = {key: binding[key] for key in identity_keys}
        assert observed_identity == {
            "schema": 2,
            "nonce": "standalone-media-edit-p1",
            "world_id": observed["world_id"],
            "user_id": 1,
            "peer_id": 2,
        }
        assert binding["available"] is True and binding["reason"] is None
        assert binding["generation"] > previous_generation
        previous_generation = binding["generation"]
        assert 0 <= binding["observed_uptime_ms"] - binding["uptime_ms"] <= 1000
        pid = binding["pid"] if pid is None else pid
        assert binding["pid"] == pid
        assert len(binding["messages"]) == 1
        message = binding["messages"][0]
        assert message["message_id"] == 2
        assert message["kind"] == "ordinary" and message["asset_id"] == 3
        assert message["has_image"] is True and message["image_key"].startswith("3_1@")
        image = message["image_bounds"]
        visible = message["visible_bounds"]
        assert visible[0] <= image[0] < image[2] <= visible[2]
        assert visible[1] <= image[1] < image[3] <= visible[3]

    trace = client["trace"]
    assert [
        json.loads(line) for line in (tmp_path / "final-trace.jsonl").read_text().splitlines()
    ] == trace
    ordinary = [row for row in trace if row.get("document_id") in {"1", "2"}]
    assert ordinary
    for row in ordinary:
        assert set(row) == {"event", "document_id", "cache_file", "file_size", "digest_ok"}
        assert row["event"] in DOCUMENT_EVENTS
        assert row["cache_file"] == ("-1_-1.pdf" if row["document_id"] == "1" else "-2_-2.pdf")
        assert row["file_size"] == (
            len(DOCUMENT_BYTES) if row["document_id"] == "1" else len(REPLACEMENT_DOCUMENT_BYTES)
        )
        assert "asset_id" not in row
    assert not any(row["event"] in {"media_load_failure", "media_load_cancel"} for row in ordinary)
    assert any(row["event"] == "media_load_start" for row in ordinary)
    assert any(
        row["event"] == "media_load_success" and row["digest_ok"] is True for row in ordinary
    )
    photo_trace = [row for row in trace if row.get("asset_id") == 3]
    assert photo_trace and all(row["cache_file"] == "3_1.jpg" for row in photo_trace)
    assert any(
        row["event"] == "media_load_success" and row["digest_ok"] is True for row in photo_trace
    )

    phases = client["phases"]
    assert list(phases) == [
        "initial",
        "document_caption",
        "photo",
        "photo_caption",
        "document_final",
        "restart",
    ]
    trace_end = request_end = 0
    for name in phases:
        phase = phases[name]
        assert set(phase) == {"trace_start", "trace_end", "request_start", "request_end"}
        assert phase["trace_start"] == trace_end
        assert phase["request_start"] == request_end
        assert phase["trace_start"] <= phase["trace_end"] <= len(trace)
        assert phase["request_start"] <= phase["request_end"] <= len(requests)
        trace_end = phase["trace_end"]
        request_end = phase["request_end"]
    assert trace_end == len(trace) and request_end == len(requests)
    for name in ("document_caption", "photo_caption", "restart"):
        phase = phases[name]
        assert not any(
            row["kind"] == "document"
            for row in requests[phase["request_start"] : phase["request_end"]]
        )

    initial_destination = (
        "/storage/emulated/0/Android/data/org.gramlab.android/files/Telegram/"
        f"Telegram Files/{SCENE['file_name']}"
    )
    final_destination = (
        "/storage/emulated/0/Android/data/org.gramlab.android/files/Telegram/Telegram Files/"
        + SCENE["replacement_file_name"]
    )
    expected_bytes = {
        SCENE["file_name"]: DOCUMENT_BYTES,
        "-1_-1.pdf": DOCUMENT_BYTES,
        "3_1.jpg": PHOTO.read_bytes(),
        SCENE["replacement_file_name"]: REPLACEMENT_DOCUMENT_BYTES,
        "-2_-2.pdf": REPLACEMENT_DOCUMENT_BYTES,
    }
    assert set(client["cache"]) == {
        "downloaded",
        "document_caption",
        "photo",
        "photo_caption",
        "document_final",
        "restart",
    }
    for name, value in client["cache"].items():
        assert value["partials"] == []
        paths = {row["path"] for row in value["copies"]}
        basenames = {Path(str(path)).name for path in paths}
        assert paths >= {initial_destination}
        assert basenames >= {SCENE["file_name"], "-1_-1.pdf"}
        assert all(
            row["size"] == len(expected_bytes[Path(str(row["path"])).name])
            and row["sha256"]
            == hashlib.sha256(expected_bytes[Path(str(row["path"])).name]).hexdigest()
            for row in value["copies"]
        ), name
        assert json.loads((tmp_path / f"{name}-cache.json").read_text()) == value
    for name in ("photo", "photo_caption"):
        assert "3_1.jpg" in {Path(str(row["path"])).name for row in client["cache"][name]["copies"]}
    for name in ("downloaded", "document_caption"):
        assert SCENE["replacement_file_name"] not in {
            Path(str(row["path"])).name for row in client["cache"][name]["copies"]
        }
    for name in ("document_final", "restart"):
        paths = {row["path"] for row in client["cache"][name]["copies"]}
        assert paths >= {
            initial_destination,
            final_destination,
        }
        assert {Path(str(path)).name for path in paths} >= {
            SCENE["replacement_file_name"],
            "-2_-2.pdf",
        }
        assert "3_1.jpg" not in {Path(str(path)).name for path in paths}

    apk_digest = hashlib.sha256(apk.read_bytes()).hexdigest()
    assert hashlib.sha256((tmp_path / "client.apk").read_bytes()).hexdigest() == apk_digest
    profile_digest = hashlib.sha256(manifest.read_bytes()).hexdigest()
    write_report(
        report_path or tmp_path / "report.html",
        Report(
            run_id="standalone-media-edits-original-android",
            title="Standalone media edits in the original Android renderer",
            mode="headless-android",
            outcome="passed",
            seed=105,
            profile={
                "Upstream Android revision": str(toolchain["client"]["revision"]),
                "Android version": str(toolchain["client"]["version"]),
                "System image": image_package,
                "Guest fingerprint": str(full["fingerprint"]),
                "Patched source provenance SHA-256": str(provenance["source_provenance_sha256"]),
                "Runtime profile SHA-256": profile_digest,
                "APK SHA-256": apk_digest,
            },
            summary=(
                "A contained real bot drives four callbacks through D1 caption editing, P1 photo "
                "replacement and caption editing, and final forced D2 replacement. The original "
                "client renders each transition, transfers exact media, cleans the replaced photo, "
                "and retains final state plus unchanged D1 reuse through a cold restart."
                + (" " + acceptance_note if acceptance_note else "")
            ),
            evidence={
                "Semantic Bot API and World round trip": observed,
                "Native bridge requests": requests,
                "Original media trace": ordinary,
                "Original P1 receiver bindings": bindings,
                "Saved destinations": client["cache"],
                "Phase boundaries": phases,
                "Network isolation": full["network"],
                "Emulator filesystem": full["emulator_filesystem"],
                "Android toolchain": toolchain,
                "Reviewed APK and source provenance": provenance,
                "Graphics": full["graphics"],
            },
            timings={"native document probe": full["extra_probe_seconds"] * 1000},
            screenshots=tuple(
                Screenshot(caption=name, png=(tmp_path / f"{name}.png").read_bytes())
                for name in (
                    "initial",
                    "downloaded",
                    "document_caption",
                    "photo",
                    "photo_caption",
                    "document_final",
                    "restart-bottom",
                    "restart-top",
                )
            ),
            limitations=(
                "The retained original screenshots still require visual inspection.",
                "Default classification, albums and external viewer behavior remain outside "
                "this run.",
            ),
        ),
    )
