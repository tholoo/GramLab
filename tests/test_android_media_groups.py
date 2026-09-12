"""Single-guest original Android album acceptance and independent host oracle."""

from __future__ import annotations

import hashlib
import http.client
import json
import os
import shutil
import sys
import threading
from collections import Counter
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

import pytest
from PIL import Image
from test_android_document_ui import verify_android_build_provenance
from test_android_media_groups_codec import cases as codec_cases
from test_android_quoted_code import assert_isolation

from gramlab.reports import Report, Screenshot, write_report
from gramlab.runtime import RuntimeProfile, Sandbox

sys.path.insert(0, str(Path("tests/probes").resolve()))
from android_media_groups import AlbumProxy

PHOTO_FILES = ("photo-one.png", "photo-two.jpg")
DOCUMENT_FILES = ("first-document.bin", "second-document.bin")
DOCUMENT_NAMES = ("first-album.txt", "second-album.pdf")
CAPTURES = (
    "album-photos",
    "album-documents",
    "album-second-failed",
    "album-final",
    "album-cold",
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_focused_report(
    root: Path,
    full: dict[str, Any],
    observed: dict[str, Any],
    *,
    profile_digest: str,
    apk_digest: str,
    toolchain: dict[str, Any],
    provenance: dict[str, Any],
) -> Path:
    source_digests = {
        name: digest(Path(name))
        for name in (
            "tests/probes/android_media_groups.py",
            "tests/test_android_media_groups.py",
            "clients/android/patches/series",
            "clients/android/toolchain.json",
        )
    }
    return write_report(
        root / "report.html",
        Report(
            run_id="album-native-normal31",
            title="Original Android album retry and cold-cache acceptance",
            mode="headless-android",
            outcome="passed",
            seed=114,
            profile={
                "APK SHA-256": apk_digest,
                "Runtime profile SHA-256": profile_digest,
                "Upstream Android revision": str(provenance["upstream_revision"]),
                "Source provenance SHA-256": str(provenance["source_provenance_sha256"]),
                "Guest fingerprint": str(full["fingerprint"]),
                "Android version": str(toolchain["client"]["version"]),
            },
            summary=(
                "One supervised guest ran the 48-case app-process codec first, then retained "
                "the stock two-photo and two-document album UI, causal radial retry, exact "
                "files, and cold-cache evidence."
            ),
            evidence={
                "Focused result": observed,
                "Network isolation": full["network"],
                "Emulator filesystem": full["emulator_filesystem"],
                "Verified APK and source provenance": provenance,
                "APK and source digests": {"client.apk": apk_digest, **source_digests},
                "Android toolchain": toolchain,
            },
            timings={"focused native probe": full["extra_probe_seconds"] * 1000},
            screenshots=tuple(
                Screenshot(caption=name, png=(root / f"{name}.png").read_bytes())
                for name in CAPTURES
            ),
            limitations=(
                "The original photo collage screenshot still requires manual visual inspection; "
                "the automated oracle binds its caption, loaded assets, geometry, and nonblank "
                "320x640 capture but does not reconstruct or classify the collage layout.",
            ),
        ),
    )


def assert_codec_observation(observed: dict[str, Any]) -> None:
    _authored, expected = codec_cases()
    actual = observed["cases"]
    assert set(actual) == set(expected)
    for name, oracle in expected.items():
        result = actual[name]
        assert result["returncode"] == oracle["returncode"], (name, result)
        if "error" in oracle:
            assert result["result"] == {"error": oracle["error"]}, (name, result)
            continue
        body = result["result"]
        if "messages" in oracle:
            assert body["messages"] == oracle["messages"], name
        if "group_ids" in oracle:
            assert [row["media_group_id"] for row in body["messages"]] == oracle["group_ids"]
        if "application_counts" in oracle:
            envelopes = body["changes"]["envelopes"]
            assert [len(row["updates"]) for row in envelopes] == oracle["application_counts"]
            assert [row["seq"] for row in envelopes] == oracle["application_sequences"]
        if "difference_group_ids" in oracle:
            assert [
                row["message"].get("media_group_id") for row in body["difference"]["updates"]
            ] == oracle["difference_group_ids"]
        if "final_atomic_count" in oracle:
            final = body["changes"]["envelopes"][-1]
            assert (final["atomic_count"], final["seq"]) == (
                oracle["final_atomic_count"],
                oracle["final_sequence"],
            )
        for key in ("send", "callback"):
            if key in oracle:
                assert body[key] == oracle[key]
        if "document_count" in oracle:
            assert len(body["documents"]) == oracle["document_count"]
        if "recovery" in oracle:
            assert body["media_group_resnapshot"] == oracle["recovery"]
        if "paths" in oracle:
            assert [row["path"] for row in result["requests"]] == oracle["paths"]


def assert_focused_observation(root: Path, observed: dict[str, Any]) -> None:
    assert_codec_observation(observed["codec"])
    photos = observed["photos"]
    documents = observed["documents"]
    assert [row["id"] for row in photos] == [1, 2]
    assert [row.get("media_group_id") for row in photos] == ["1", "1"]
    assert [row.get("caption") for row in photos] == ["Album / آلبوم", None]
    assert [row["id"] for row in documents] == [3, 4]
    assert [row.get("media_group_id") for row in documents] == ["2", "2"]
    assert [row.get("caption") for row in documents] == ["First / نخست", "Second / دوم"]
    assert observed["initial_snapshot"]["messages"] == photos
    assert observed["initial_snapshot"]["message_position"] == 2
    assert observed["final_snapshot"]["messages"] == [*photos, *documents]
    assert observed["final_snapshot"]["message_position"] == 4
    changes = observed["live_changes"]
    assert changes["cursor"] == changes["head"] == 4
    assert [row["position"] for row in changes["changes"]] == [3, 4]
    assert [row["data"] for row in changes["changes"]] == documents

    requests = observed["requests"]
    successful_snapshots = [
        row
        for row in requests
        if row["path"] == "/v6/snapshot"
        and row["status"] == 200
        and row["response"]["message_position"] == 2
    ]
    assert len(successful_snapshots) == 1
    assert not [row for row in requests if row["status"] == 409]
    after_two = [
        row
        for row in requests
        if row["path"].startswith("/v6/changes?after=2&") and row["status"] == 200
    ]
    assert after_two
    live_after_two = [
        row for row in after_two if row["response"] == {"cursor": 4, "positions": [3, 4]}
    ]
    assert live_after_two
    assert not [row for row in requests if row["path"].startswith("/v6/changes?after=3&")]
    after_four = [
        row
        for row in requests
        if row["path"].startswith("/v6/changes?after=4&") and row["status"] == 200
    ]
    assert after_four
    assert min(row["sequence"] for row in after_four) > min(
        row["sequence"] for row in live_after_two
    )

    applied = [
        row
        for row in observed["traces"]["all"]
        if row.get("event") == "events_applied" and row.get("method") == "messages"
    ]
    assert len(applied) == 1 and applied[0]["token"] == 2
    assert not [row for row in observed["traces"]["all"] if "resnapshot" in row.get("event", "")]
    assert observed["geometry"]["photo_xml_labels"].count("Album / آلبوم") == 1
    document_bounds = observed["geometry"]["document_bounds"]
    assert len(document_bounds) == 2 and document_bounds[0][1] < document_bounds[1][1]
    assert all(len(row) == 4 and row[0] < row[2] and row[1] < row[3] for row in document_bounds)

    document_requests = [
        row for row in observed["requests"] if row["path"].startswith("/v6/documents/")
    ]
    assert [row["path"] for row in document_requests] == [
        "/v6/documents/1",
        "/v6/documents/2",
        "/v6/documents/2",
    ]
    assert [row["truncated"] for row in document_requests] == [False, True, False]
    assert [row["error"] for row in document_requests] == [None, "truncated_body", None]
    assert Counter(row["path"] for row in document_requests) == Counter(
        {"/v6/documents/1": 1, "/v6/documents/2": 2}
    )
    assert not [
        row for row in observed["cold_requests"] if row["path"].startswith("/v6/documents/")
    ]
    assert len(observed["taps"]) == 3
    assert [row["file_name"] for row in observed["taps"]] == [
        DOCUMENT_NAMES[0],
        DOCUMENT_NAMES[1],
        DOCUMENT_NAMES[1],
    ]
    assert sum(row["event"] == "media_load_success" for row in observed["traces"]["first"]) == 1
    assert (
        sum(row["event"] == "media_load_failure" for row in observed["traces"]["second_failed"])
        == 1
    )
    assert not any(
        row["event"] == "media_load_success" for row in observed["traces"]["second_failed"]
    )
    assert sum(row["event"] == "media_load_failure" for row in observed["traces"]["final"]) == 1
    assert sum(row["event"] == "media_load_success" for row in observed["traces"]["final"]) == 1
    guard = observed["retry_guard"]
    assert guard["request_count"] == 1 and guard["success_count"] == 0
    assert len(guard["samples"]) >= 20
    assert guard["samples"][-1]["observed_ns"] - guard["samples"][0]["observed_ns"] >= 2_000_000_000
    assert {row["request_count"] for row in guard["samples"]} == {1}
    assert {row["success_count"] for row in guard["samples"]} == {0}
    assert document_requests[2]["started_ns"] >= observed["taps"][2]["started_ns"]
    assert observed["failed_inventory"]["partials"] == []

    bodies = [(root / source).read_bytes() for source in DOCUMENT_FILES]
    expected = {hashlib.sha256(body).hexdigest(): len(body) for body in bodies}
    assert [(row["status"], row["bytes"], row["sha256"]) for row in document_requests] == [
        (200, len(bodies[0]), hashlib.sha256(bodies[0]).hexdigest()),
        (
            200,
            max(1, len(bodies[1]) // 2),
            hashlib.sha256(bodies[1][: max(1, len(bodies[1]) // 2)]).hexdigest(),
        ),
        (200, len(bodies[1]), hashlib.sha256(bodies[1]).hexdigest()),
    ]
    expected_files = {
        ("internal", "-1_-1.txt"): (hashlib.sha256(bodies[0]).hexdigest(), len(bodies[0])),
        ("external", "first-album.txt"): (
            hashlib.sha256(bodies[0]).hexdigest(),
            len(bodies[0]),
        ),
        ("internal", "-1_-2.pdf"): (hashlib.sha256(bodies[1]).hexdigest(), len(bodies[1])),
        ("external", "second-album.pdf"): (
            hashlib.sha256(bodies[1]).hexdigest(),
            len(bodies[1]),
        ),
    }
    for inventory in (observed["final_inventory"], observed["cold_inventory"]):
        assert inventory["partials"] == []
        assert {
            (row["scope"], Path(row["path"]).name): (row["sha256"], row["size"])
            for row in inventory["files"]
        } == expected_files
        by_digest = Counter((row["sha256"], row["size"]) for row in inventory["files"])
        for digest, size in expected.items():
            assert by_digest[digest, size] == 2
            scopes = {row["scope"] for row in inventory["files"] if row["sha256"] == digest}
            assert scopes == {"internal", "external"}
    assert set(observed["captures"]) == set(CAPTURES)
    for value in observed["captures"].values():
        assert (root / value["png"]).read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
        assert "<hierarchy" in (root / value["xml"]).read_text()
    with Image.open(root / observed["captures"]["album-photos"]["png"]) as photo_capture:
        assert photo_capture.size == (320, 640)
        assert len(photo_capture.convert("RGB").getcolors(maxcolors=320 * 640) or []) > 16
    assert "Accounts: 0" in observed["accounts"]


def test_album_proxy_truncates_only_the_first_second_document_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = b"second document body"
    monkeypatch.setattr("android_media_groups.socket.if_nameindex", lambda: [(1, "lo")])

    class Upstream(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:
            pass

        def do_GET(self) -> None:
            self.send_response(200)
            self.send_header("Content-Type", "application/pdf")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    capability = "gramlab-client_" + "x" * 43
    with HTTPServer(("127.0.0.1", 0), Upstream) as upstream:
        worker = threading.Thread(target=upstream.serve_forever, daemon=True)
        worker.start()
        try:
            with AlbumProxy(f"http://127.0.0.1:{upstream.server_port}", capability) as proxy:
                bodies = []
                for _ in range(2):
                    connection = http.client.HTTPConnection(
                        "127.0.0.1", int(proxy.base_url.rsplit(":", 1)[1]), timeout=5
                    )
                    try:
                        connection.request(
                            "GET",
                            "/v6/documents/2",
                            headers={"Authorization": "Bearer " + capability},
                        )
                        response = connection.getresponse()
                        try:
                            bodies.append(response.read())
                        except http.client.IncompleteRead as error:
                            bodies.append(error.partial)
                    finally:
                        connection.close()
                requests = proxy.requests()
        finally:
            upstream.shutdown()
            worker.join(timeout=5)
    assert 0 < len(bodies[0]) < len(payload) and bodies[1] == payload
    assert [row["truncated"] for row in requests] == [True, False]
    assert [row["status"] for row in requests] == [200, 200]
    assert [row["bytes"] for row in requests] == [max(1, len(payload) // 2), len(payload)]
    assert [row["sha256"] for row in requests] == [
        hashlib.sha256(payload[: max(1, len(payload) // 2)]).hexdigest(),
        hashlib.sha256(payload).hexdigest(),
    ]
    assert all(row["started_ns"] <= row["finished_ns"] for row in requests)


def test_focused_probe_runs_codec_before_installing_and_launching_ui() -> None:
    source = Path("tests/probes/android_media_groups.py").read_text()
    assert source.index("codec = codec_probe(guest)") < source.index(
        'adb("install", "--no-streaming", "/work/client.apk"'
    )
    assert source.count("main(probe)") == 1
    assert '"bridge_version": 6' in source
    assert 'row.get("event") == "events_applied" and row.get("token") == 2' in source


def test_focused_report_retains_five_original_captures_and_provenance(tmp_path: Path) -> None:
    for name in CAPTURES:
        Image.new("RGB", (320, 640), color=(30, 80, 60)).save(tmp_path / f"{name}.png")
    report = write_focused_report(
        tmp_path,
        {
            "fingerprint": "gramlab",
            "network": {"ipv4": 1, "ipv6": 1},
            "emulator_filesystem": {"isolated": True},
            "extra_probe_seconds": 2.5,
        },
        {"requests": [], "captures": list(CAPTURES)},
        profile_digest="1" * 64,
        apk_digest="2" * 64,
        toolchain={"client": {"version": "normal31"}},
        provenance={
            "upstream_revision": "revision",
            "source_provenance_sha256": "3" * 64,
        },
    )
    rendered = report.read_text()
    assert rendered.count("data:image/png;base64,") == 5
    assert "manual visual inspection" in rendered
    assert "Verified APK and source provenance" in rendered
    assert "Network isolation" in rendered


@pytest.mark.parametrize(
    "fault",
    [
        "group",
        "positions",
        "cursor",
        "retry",
        "partial",
        "cold_get",
        "snapshot",
        "after_three",
        "early_retry",
        "unstable_guard",
        "identity",
        "payload",
        "resnapshot",
    ],
)
def test_focused_oracle_rejects_weakened_native_evidence(
    tmp_path: Path, fault: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Exercise the substantive guard directly while leaving the large codec oracle independent.
    monkeypatch.setattr(sys.modules[__name__], "assert_codec_observation", lambda _value: None)
    for source, body in zip(DOCUMENT_FILES, (b"one", b"two"), strict=True):
        (tmp_path / source).write_bytes(body)
    for name in CAPTURES:
        image = Image.new("RGB", (320, 640))
        image.putdata([(index % 17, index % 13, index % 11) for index in range(320 * 640)])
        image.save(tmp_path / f"{name}.png")
        (tmp_path / f"{name}.xml").write_text("<hierarchy />")
    photos = [
        {"id": 1, "media_group_id": "1", "caption": "Album / آلبوم"},
        {"id": 2, "media_group_id": "1"},
    ]
    documents = [
        {"id": 3, "media_group_id": "2", "caption": "First / نخست"},
        {"id": 4, "media_group_id": "2", "caption": "Second / دوم"},
    ]
    bodies = [(tmp_path / source).read_bytes() for source in DOCUMENT_FILES]
    digests = [hashlib.sha256(body).hexdigest() for body in bodies]
    files = [
        {
            "scope": "internal",
            "path": "./cache4/-1_-1.txt",
            "size": len(bodies[0]),
            "sha256": digests[0],
        },
        {
            "scope": "external",
            "path": "/external/Telegram Files/first-album.txt",
            "size": len(bodies[0]),
            "sha256": digests[0],
        },
        {
            "scope": "internal",
            "path": "./cache4/-1_-2.pdf",
            "size": len(bodies[1]),
            "sha256": digests[1],
        },
        {
            "scope": "external",
            "path": "/external/Telegram Files/second-album.pdf",
            "size": len(bodies[1]),
            "sha256": digests[1],
        },
    ]
    samples = [
        {"observed_ns": index * 100_000_000, "request_count": 1, "success_count": 0}
        for index in range(21)
    ]
    request_defaults = {
        "finished_ns": 50,
        "bytes": 0,
        "sha256": hashlib.sha256(b"").hexdigest(),
        "truncated": False,
        "error": None,
    }
    value: dict[str, Any] = {
        "codec": {},
        "photos": photos,
        "documents": documents,
        "initial_snapshot": {"messages": photos, "message_position": 2},
        "final_snapshot": {"messages": [*photos, *documents], "message_position": 4},
        "live_changes": {
            "cursor": 4,
            "head": 4,
            "changes": [
                {"position": 3, "data": documents[0]},
                {"position": 4, "data": documents[1]},
            ],
        },
        "traces": {
            "all": [{"event": "events_applied", "method": "messages", "token": 2}],
            "first": [{"event": "media_load_success"}],
            "second_failed": [{"event": "media_load_failure"}],
            "final": [
                {"event": "media_load_failure"},
                {"event": "media_load_success"},
            ],
        },
        "geometry": {
            "photo_xml_labels": "Album / آلبوم",
            "document_bounds": [[0, 10, 100, 30], [0, 40, 100, 60]],
        },
        "requests": [
            request_defaults
            | {
                "sequence": 1,
                "path": "/v6/snapshot",
                "started_ns": 0,
                "status": 200,
                "response": {"message_position": 2},
            },
            request_defaults
            | {
                "sequence": 2,
                "path": "/v6/changes?after=2&limit=100",
                "started_ns": 100,
                "status": 200,
                "response": {"cursor": 4, "positions": [3, 4]},
            },
            request_defaults
            | {
                "sequence": 3,
                "path": "/v6/changes?after=4&limit=100",
                "started_ns": 200,
                "status": 200,
                "response": {"cursor": 4, "positions": []},
            },
            request_defaults
            | {
                "sequence": 4,
                "path": "/v6/documents/1",
                "started_ns": 300,
                "status": 200,
                "bytes": len(bodies[0]),
                "sha256": digests[0],
                "response": None,
            },
            request_defaults
            | {
                "sequence": 5,
                "path": "/v6/documents/2",
                "started_ns": 400,
                "status": 200,
                "bytes": max(1, len(bodies[1]) // 2),
                "sha256": hashlib.sha256(bodies[1][: max(1, len(bodies[1]) // 2)]).hexdigest(),
                "truncated": True,
                "error": "truncated_body",
                "response": None,
            },
            request_defaults
            | {
                "sequence": 6,
                "path": "/v6/documents/2",
                "started_ns": 1_100,
                "status": 200,
                "bytes": len(bodies[1]),
                "sha256": digests[1],
                "response": None,
            },
        ],
        "cold_requests": [],
        "taps": [
            {"file_name": DOCUMENT_NAMES[0], "started_ns": 500},
            {"file_name": DOCUMENT_NAMES[1], "started_ns": 600},
            {"file_name": DOCUMENT_NAMES[1], "started_ns": 1_000},
        ],
        "retry_guard": {"request_count": 1, "success_count": 0, "samples": samples},
        "final_inventory": {"partials": [], "files": files},
        "cold_inventory": {"partials": [], "files": files},
        "failed_inventory": {"partials": [], "files": files[:2]},
        "captures": {name: {"png": f"{name}.png", "xml": f"{name}.xml"} for name in CAPTURES},
        "accounts": "Accounts: 0",
    }
    if fault == "group":
        value["documents"][1]["media_group_id"] = "3"
    elif fault == "positions":
        value["final_snapshot"]["message_position"] = 3
    elif fault == "cursor":
        value["live_changes"]["cursor"] = 3
    elif fault == "retry":
        value["requests"].pop()
    elif fault == "partial":
        value["final_inventory"]["partials"] = ["orphan.part"]
    elif fault == "cold_get":
        value["cold_requests"] = [{"path": "/v6/documents/1"}]
    elif fault == "snapshot":
        value["requests"][0]["response"]["message_position"] = 1
    elif fault == "after_three":
        value["requests"][2]["path"] = "/v6/changes?after=3&limit=100"
    elif fault == "early_retry":
        value["requests"][5]["started_ns"] = 999
    elif fault == "unstable_guard":
        value["retry_guard"]["samples"][-1]["request_count"] = 2
    elif fault == "identity":
        value["final_inventory"]["files"][0]["path"] = "./cache4/wrong.txt"
    elif fault == "payload":
        value["requests"][5]["bytes"] -= 1
    else:
        value["traces"]["all"].append({"event": "events_resnapshot"})
    with pytest.raises((AssertionError, KeyError)):
        assert_focused_observation(tmp_path, value)


@pytest.mark.android
def test_actual_album_codec_ui_retry_and_cold_cache_share_one_guest(tmp_path: Path) -> None:
    manifest = os.environ.get("GRAMLAB_ANDROID_RUNTIME_PROFILE")
    client_apk = os.environ.get("GRAMLAB_ANDROID_PROBE_APK")
    codec_apk = os.environ.get("GRAMLAB_ANDROID_MEDIA_GROUPS_CODEC_PROBE_APK")
    provenance_pointer = os.environ.get("GRAMLAB_ANDROID_APK_PROVENANCE")
    if not all((manifest, client_apk, codec_apk, provenance_pointer)) or not os.access(
        "/dev/kvm", os.R_OK | os.W_OK
    ):
        pytest.skip(
            "Requires normal31 provenance, media-group codec probe, Android profile and KVM"
        )
    assert (
        manifest is not None
        and client_apk is not None
        and codec_apk is not None
        and provenance_pointer is not None
    )
    toolchain = json.loads(Path("clients/android/toolchain.json").read_text())
    verified = verify_android_build_provenance(
        Path(client_apk), Path(provenance_pointer), toolchain
    )
    profile = RuntimeProfile.load(Path(manifest))
    shutil.copy2(client_apk, tmp_path / "client.apk")
    shutil.copy2(codec_apk, tmp_path / "media-groups-probe.apk")
    authored, _expected = codec_cases()
    (tmp_path / "media-groups-codec-cases.json").write_text(
        json.dumps(authored, ensure_ascii=False)
    )
    shutil.copytree(
        "src/gramlab", tmp_path / "gramlab", ignore=shutil.ignore_patterns("__pycache__")
    )
    for source, target in zip(
        (
            Path("tests/assets/rich-media/photo-square-16x16.png"),
            Path("tests/assets/rich-media/photo-quadrants-64x48.jpg"),
        ),
        PHOTO_FILES,
        strict=True,
    ):
        shutil.copy2(source, tmp_path / target)
    (tmp_path / DOCUMENT_FILES[0]).write_bytes(b"GramLab first grouped document\n")
    (tmp_path / DOCUMENT_FILES[1]).write_bytes(
        b"%PDF-1.4\nGramLab second grouped document\n%%EOF\n"
    )
    (tmp_path / "emulator-profile.json").write_text(json.dumps(asdict(profile)))
    for name in (
        "emulator_process.py",
        "android_guest.py",
        "android_document_ui.py",
        "document_round_trip.py",
        "component_bot.py",
        "android_media_groups_codec.py",
        "android_media_groups.py",
    ):
        shutil.copy2(Path("tests/probes") / name, tmp_path / name)
    image = (
        f"system-images;android-{toolchain['sdk']['platform']};"
        f"{toolchain['runtime']['imageType']};{toolchain['runtime']['abi']}"
    )
    result = Sandbox(profile).supervise(
        [
            profile.python,
            "/work/android_media_groups.py",
            profile.executables["emulator"],
            profile.executables["adb"],
            profile.executables["avdmanager"],
            image,
        ],
        data=tmp_path,
        kvm=True,
        timeout=720,
    )
    (tmp_path / "album-native-stdout.log").write_text(result.stdout)
    (tmp_path / "album-native-result.json").write_text(result.stdout)
    (tmp_path / "album-native-stderr.log").write_text(result.stderr)
    (tmp_path / "verified-provenance.json").write_text(
        json.dumps(verified, indent=2, sort_keys=True)
    )
    assert result.returncode == 0, result.stderr
    full = json.loads(result.stdout)
    assert_isolation(full)
    assert_focused_observation(tmp_path, full["extra_probe"])
    assert digest(tmp_path / "client.apk") == verified["apk_sha256"]
    report = write_focused_report(
        tmp_path,
        full,
        full["extra_probe"],
        profile_digest=digest(Path(manifest)),
        apk_digest=verified["apk_sha256"],
        toolchain=toolchain,
        provenance=verified,
    )
    assert report == tmp_path / "report.html"
    report_text = report.read_text()
    assert report_text.count("data:image/png;base64,") == 5
    assert "manual visual inspection" in report_text
