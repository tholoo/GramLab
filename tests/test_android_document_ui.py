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

    source_path = Path(pointer["source_provenance"])
    expected_source_digest = pointer["source_provenance_sha256"]
    if (
        not isinstance(expected_source_digest, str)
        or _digest(source_path) != expected_source_digest
    ):
        raise ValueError("Android source provenance digest does not match its pointer")
    chain: list[dict[str, Any]] = []
    expected_count = len(series)
    while True:
        source = _json_object(source_path)
        if source.get("patches") != expected_count:
            raise ValueError("Android source provenance patch count is discontinuous")
        expected_patch = patch_digests[expected_count - 1]
        if source.get("patch") != expected_patch:
            raise ValueError("Android source provenance patch digest does not match the series")
        chain.append(
            {
                "patches": expected_count,
                "patch": series[expected_count - 1],
                "sha256": expected_patch,
                "provenance_sha256": _digest(source_path),
            }
        )
        if expected_count == 24:
            break
        previous = source.get("before_provenance")
        previous_digest = source.get("before_provenance_sha256")
        if not isinstance(previous, str) or not isinstance(previous_digest, str):
            raise ValueError("Android source provenance chain ends before its established base")
        source_path = Path(previous)
        if _digest(source_path) != previous_digest:
            raise ValueError("Android source provenance link digest does not match")
        expected_count -= 1

    upstream = _json_object(upstream_lock_path)
    revision = toolchain.get("client", {}).get("revision")
    if upstream.get("clientRevision") != revision:
        raise ValueError("Android toolchain and upstream source lock revisions differ")
    return {
        "pointer_sha256": _digest(pointer_path),
        "apk_sha256": expected_apk,
        "source_provenance_sha256": expected_source_digest,
        "upstream_revision": revision,
        "ordered_patches": [
            {"position": position, "name": name, "sha256": digest}
            for position, (name, digest) in enumerate(zip(series, patch_digests, strict=True), 1)
        ],
        "linked_source_provenance": chain,
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

    source = tmp_path / "source"
    source.mkdir()
    previous = tmp_path / "provenance-24.json"
    previous.write_text(
        json.dumps({"source": str(source), "patches": 24, "patch": digests[23]}) + "\n"
    )
    for position in range(25, 31):
        current = tmp_path / f"provenance-{position}.json"
        current.write_text(
            json.dumps(
                {
                    "source": str(source),
                    "patches": position,
                    "patch": digests[position - 1],
                    "before_provenance": str(previous),
                    "before_provenance_sha256": hashlib.sha256(previous.read_bytes()).hexdigest(),
                }
            )
            + "\n"
        )
        previous = current

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
                "source_provenance": str(previous),
                "source_provenance_sha256": hashlib.sha256(previous.read_bytes()).hexdigest(),
            }
        )
        + "\n"
    )
    revision = "62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c"
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
    assert [row["patches"] for row in verified["linked_source_provenance"]] == list(
        range(30, 23, -1)
    )

    apk.write_bytes(b"unreviewed apk")
    with pytest.raises(ValueError, match="APK"):
        verify_android_build_provenance(
            apk, pointer, toolchain, series_path=series, upstream_lock_path=upstream
        )
    apk.write_bytes(b"reviewed apk")
    delivery = patches / names[-1]
    delivery.write_bytes(b"changed delivery patch\n")
    with pytest.raises(ValueError, match="patch digest"):
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
        "reused",
        "restart-bottom",
        "restart-top",
    }
    for name, xml in client["captures"].items():
        assert (tmp_path / f"{name}.xml").read_text() == xml
        png = (tmp_path / f"{name}.png").read_bytes()
        assert png.startswith(b"\x89PNG\r\n\x1a\n") and len(png) > 1024
    initial = visible_labels(client["captures"]["initial"])
    downloaded = visible_labels(client["captures"]["downloaded"])
    reused = visible_labels(client["captures"]["reused"])
    restarted = visible_labels(client["captures"]["restart-bottom"]) + visible_labels(
        client["captures"]["restart-top"]
    )
    for labels in (initial, downloaded, restarted):
        assert SCENE["file_name"] in labels
        assert SCENE["caption"] in labels
        assert SCENE["button_text"] in labels
    assert SCENE["reuse_caption"] in reused and SCENE["file_name"] in reused
    assert SCENE["reuse_caption"] in restarted

    assert set(client["launches"]) == {"initial", "restart"}
    for launch in client["launches"].values():
        assert "Status: ok" in launch and "LaunchState: COLD" in launch
    assert "Accounts: 0" in client["accounts"]
    assert set(client["taps"]) == {"download", "callback"}
    for tap in client["taps"].values():
        left, top, right, bottom = tap["bounds"]
        assert 0 <= left < right <= 320 and 0 <= top < bottom <= 640
    assert client["taps"]["download"]["label"] == SCENE["file_name"]
    assert client["taps"]["download"]["requests_before"] >= 0
    assert (
        client["taps"]["download"]["requests_after"] > client["taps"]["download"]["requests_before"]
    )
    assert client["taps"]["callback"]["label"] == SCENE["button_text"]

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
        assert row["phase"] in {"initial", "reused", "restart"}
        assert row["method"] in {"GET", "POST"}
        assert row["path"] in allowed or row["path"].startswith(
            ("/v5/changes?", "/v5/callbacks/", "/v5/assets/", "/v5/documents/")
        )
        assert row["status"] == 200 and row["error"] is None
        assert row["bytes"] >= 0
        assert row["finished_ns"] >= row["started_ns"] > 0
    document_requests = [row for row in requests if row["kind"] == "document"]
    assert len(document_requests) == 1
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
        }
    ]
    assert (
        client["taps"]["download"]["requests_before"]
        < document_requests[0]["sequence"]
        <= client["taps"]["download"]["requests_after"]
    )
    assert any(row["path"] == "/v5/custom-emoji-documents" for row in requests)
    assert any(row["kind"] == "asset" and row["identifier"] in {"1", "2"} for row in requests)

    trace = client["trace"]
    assert [
        json.loads(line) for line in (tmp_path / "final-trace.jsonl").read_text().splitlines()
    ] == trace
    ordinary = [row for row in trace if row.get("document_id") == "1"]
    assert ordinary
    for row in ordinary:
        assert set(row) == {"event", "document_id", "cache_file", "file_size", "digest_ok"}
        assert row["event"] in DOCUMENT_EVENTS
        assert row["cache_file"] == "-1_-1.pdf"
        assert row["file_size"] == len(DOCUMENT_BYTES)
        assert "asset_id" not in row
    assert not any(row["event"] in {"media_load_failure", "media_load_cancel"} for row in ordinary)
    assert any(row["event"] == "media_load_start" for row in ordinary)
    assert any(
        row["event"] == "media_load_success" and row["digest_ok"] is True for row in ordinary
    )

    phases = client["phases"]
    assert list(phases) == ["initial", "reused", "restart"]
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
    for name in ("reused", "restart"):
        phase = phases[name]
        assert not any(
            row["kind"] == "document"
            for row in requests[phase["request_start"] : phase["request_end"]]
        )

    digest = hashlib.sha256(DOCUMENT_BYTES).hexdigest()
    destination = (
        "/storage/emulated/0/Android/data/org.gramlab.android/files/Telegram/"
        f"Telegram Files/{SCENE['file_name']}"
    )
    assert set(client["cache"]) == {"downloaded", "reused", "restart"}
    for name, value in client["cache"].items():
        assert value["partials"] == []
        assert {row["path"] for row in value["copies"]} >= {destination}
        assert all(
            row["sha256"] == digest and row["size"] == len(DOCUMENT_BYTES)
            for row in value["copies"]
        ), name
        assert json.loads((tmp_path / f"{name}-cache.json").read_text()) == value

    apk_digest = hashlib.sha256(apk.read_bytes()).hexdigest()
    assert hashlib.sha256((tmp_path / "client.apk").read_bytes()).hexdigest() == apk_digest
    profile_digest = hashlib.sha256(manifest.read_bytes()).hexdigest()
    write_report(
        report_path or tmp_path / "report.html",
        Report(
            run_id="ordinary-document-download-callback-restart",
            title="Ordinary document in the original Android renderer",
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
                "A contained real bot sends a forced PDF with formatted bilingual content and "
                "an original callback keyboard. The original client downloads exact bytes, "
                "creates the callback, renders file-ID reuse, and retains the conversation and "
                "saved destination through a cold restart."
                + (" " + acceptance_note if acceptance_note else "")
            ),
            evidence={
                "Semantic Bot API and World round trip": observed,
                "Native bridge requests": requests,
                "Original media trace": ordinary,
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
                    "reused",
                    "restart-bottom",
                    "restart-top",
                )
            ),
            limitations=(
                "The retained original screenshots still require visual inspection.",
                "This fixture covers an explicitly forced non-image PDF; default classification, "
                "albums, document edits and external viewer behavior remain outside this run.",
            ),
        ),
    )
