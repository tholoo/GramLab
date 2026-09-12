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
from test_android_media_groups_codec import cases as codec_cases
from test_android_quoted_code import assert_isolation

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
    assert observed["final_snapshot"]["messages"] == [*photos, *documents]
    changes = observed["live_changes"]
    assert changes["cursor"] == changes["head"] == 4
    assert [row["position"] for row in changes["changes"]] == [3, 4]
    assert [row["data"] for row in changes["changes"]] == documents

    applied = [
        row
        for row in observed["traces"]["all"]
        if row.get("event") == "events_applied" and row.get("method") == "messages"
    ]
    assert len(applied) == 1 and applied[0]["token"] == 2
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
    assert any(row["event"] == "media_load_failure" for row in observed["traces"]["second_failed"])
    assert any(row["event"] == "media_load_success" for row in observed["traces"]["final"])
    assert observed["failed_inventory"]["partials"] == []

    expected = {
        hashlib.sha256((root / source).read_bytes()).hexdigest(): len((root / source).read_bytes())
        for source in DOCUMENT_FILES
    }
    for inventory in (observed["final_inventory"], observed["cold_inventory"]):
        assert inventory["partials"] == []
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


def test_focused_probe_runs_codec_before_installing_and_launching_ui() -> None:
    source = Path("tests/probes/android_media_groups.py").read_text()
    assert source.index("codec = codec_probe(guest)") < source.index(
        'adb("install", "--no-streaming", "/work/client.apk"'
    )
    assert source.count("main(probe)") == 1
    assert '"bridge_version": 6' in source
    assert 'row.get("event") == "events_applied" and row.get("token") == 2' in source


@pytest.mark.parametrize("fault", ["group", "cursor", "retry", "partial", "cold_get"])
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
    files = []
    for source in DOCUMENT_FILES:
        digest = hashlib.sha256((tmp_path / source).read_bytes()).hexdigest()
        for scope in ("internal", "external"):
            files.append(
                {
                    "scope": scope,
                    "path": f"{scope}/{source}",
                    "size": (tmp_path / source).stat().st_size,
                    "sha256": digest,
                }
            )
    value: dict[str, Any] = {
        "codec": {},
        "photos": photos,
        "documents": documents,
        "initial_snapshot": {"messages": photos},
        "final_snapshot": {"messages": [*photos, *documents]},
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
            "second_failed": [{"event": "media_load_failure"}],
            "final": [{"event": "media_load_success"}],
        },
        "geometry": {
            "photo_xml_labels": "Album / آلبوم",
            "document_bounds": [[0, 10, 100, 30], [0, 40, 100, 60]],
        },
        "requests": [
            {"path": "/v6/documents/1", "truncated": False, "error": None},
            {"path": "/v6/documents/2", "truncated": True, "error": "truncated_body"},
            {"path": "/v6/documents/2", "truncated": False, "error": None},
        ],
        "cold_requests": [],
        "taps": [
            {"file_name": DOCUMENT_NAMES[0]},
            {"file_name": DOCUMENT_NAMES[1]},
            {"file_name": DOCUMENT_NAMES[1]},
        ],
        "final_inventory": {"partials": [], "files": files},
        "cold_inventory": {"partials": [], "files": files},
        "failed_inventory": {"partials": [], "files": files[:2]},
        "captures": {name: {"png": f"{name}.png", "xml": f"{name}.xml"} for name in CAPTURES},
        "accounts": "Accounts: 0",
    }
    if fault == "group":
        value["documents"][1]["media_group_id"] = "3"
    elif fault == "cursor":
        value["live_changes"]["cursor"] = 3
    elif fault == "retry":
        value["requests"].pop()
    elif fault == "partial":
        value["final_inventory"]["partials"] = ["orphan.part"]
    else:
        value["cold_requests"] = [{"path": "/v6/documents/1"}]
    with pytest.raises((AssertionError, KeyError)):
        assert_focused_observation(tmp_path, value)


@pytest.mark.android
def test_actual_album_codec_ui_retry_and_cold_cache_share_one_guest(tmp_path: Path) -> None:
    manifest = os.environ.get("GRAMLAB_ANDROID_RUNTIME_PROFILE")
    client_apk = os.environ.get("GRAMLAB_ANDROID_PROBE_APK")
    codec_apk = os.environ.get("GRAMLAB_ANDROID_MEDIA_GROUPS_CODEC_PROBE_APK")
    if not all((manifest, client_apk, codec_apk)) or not os.access("/dev/kvm", os.R_OK | os.W_OK):
        pytest.skip("Requires normal31, media-group codec probe, Android profile and KVM")
    assert manifest is not None and client_apk is not None and codec_apk is not None
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
    toolchain = json.loads(Path("clients/android/toolchain.json").read_text())
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
    (tmp_path / "album-native-result.json").write_text(result.stdout)
    (tmp_path / "album-native-stderr.log").write_text(result.stderr)
    assert result.returncode == 0, result.stderr
    full = json.loads(result.stdout)
    assert_isolation(full)
    assert_focused_observation(tmp_path, full["extra_probe"])
