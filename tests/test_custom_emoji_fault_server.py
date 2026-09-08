"""Verify actual HTTP custom-emoji fault and hold stimuli."""

import http.client
import importlib
import json
import threading
from collections.abc import Generator
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Protocol, cast
from urllib.parse import urlsplit

import pytest
from probes.custom_emoji_fault_server import CustomEmojiFaultServer, DocumentFault

CAPABILITY = "gramlab-client_" + "f" * 43
AUTHORIZATION = {"Authorization": "Bearer " + CAPABILITY}
DOCUMENTS: dict[str, Any] = {
    "schema": 4,
    "world_id": "fault-world",
    "user_id": 1,
    "custom_emoji": [
        {
            "custom_emoji_id": "1",
            "main_asset_id": 1,
            "thumbnail_asset_id": 2,
        },
        {
            "custom_emoji_id": "1109",
            "main_asset_id": 3,
            "thumbnail_asset_id": 2,
        },
    ],
    "assets": [
        {"asset_id": 1, "sha256": "one"},
        {"asset_id": 2, "sha256": "shared"},
        {"asset_id": 3, "sha256": "animated"},
    ],
}


class CheckpointWriter(Protocol):
    def __call__(self, path: Path, value: object, secrets: list[str]) -> None: ...


def test_checkpoint_publication_is_bounded_redacted_and_never_overwrites(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.syspath_prepend(str(Path("tests/probes").resolve()))
    probe = importlib.import_module("android_custom_emoji_faults")
    write_checkpoint = cast(CheckpointWriter, probe._write_checkpoint)
    maximum = cast(int, probe.MAX_CHECKPOINT_BYTES)
    path = tmp_path / "completed.json"
    value = {"case": "mixed-404", "result": {"requests": [1, 2]}}
    write_checkpoint(path, value, [CAPABILITY])
    original = path.read_bytes()
    assert json.loads(original) == value
    assert not list(tmp_path.glob("*.partial"))

    with pytest.raises(FileExistsError):
        write_checkpoint(path, {"changed": True}, [CAPABILITY])
    assert path.read_bytes() == original
    with pytest.raises(RuntimeError, match="capability"):
        write_checkpoint(tmp_path / "secret.json", {"value": CAPABILITY}, [CAPABILITY])
    with pytest.raises(ValueError, match="bound"):
        write_checkpoint(tmp_path / "oversized.json", {"value": "x" * maximum}, [CAPABILITY])
    assert {item.name for item in tmp_path.iterdir()} == {"completed.json"}


def request(
    endpoint: str,
    method: str,
    path: str,
    body: bytes = b"",
    *,
    authorization: bool = True,
) -> tuple[int, list[tuple[str, str]], bytes]:
    connection = http.client.HTTPConnection("127.0.0.1", urlsplit(endpoint).port, timeout=5)
    headers = dict(AUTHORIZATION) if authorization else {}
    if body:
        headers["Content-Type"] = "application/json"
    try:
        connection.request(method, path, body if body else None, headers)
        response = connection.getresponse()
        return response.status, response.getheaders(), response.read()
    finally:
        connection.close()


@pytest.fixture
def upstream() -> Generator[tuple[ThreadingHTTPServer, list[tuple[str, bytes, str | None]]]]:
    received: list[tuple[str, bytes, str | None]] = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: object) -> None:
            pass

        def handle_request(self) -> None:
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length) if length else b""
            received.append((self.path, body, self.headers.get("Authorization")))
            if self.path == "/v4/custom-emoji-documents":
                requested = set(json.loads(body)["custom_emoji_ids"])
                documents = [
                    item
                    for item in DOCUMENTS["custom_emoji"]
                    if item["custom_emoji_id"] in requested
                ]
                required = {
                    item[key]
                    for item in documents
                    for key in ("main_asset_id", "thumbnail_asset_id")
                }
                assets = [item for item in DOCUMENTS["assets"] if item["asset_id"] in required]
                payload = json.dumps(
                    DOCUMENTS | {"custom_emoji": documents, "assets": assets}
                ).encode()
                mime = "application/json; charset=utf-8"
            elif self.path == "/v4/assets/2":
                payload = b"shared-thumbnail-bytes"
                mime = "image/webp"
            else:
                payload = b'{"schema":4,"world_id":"fault-world"}'
                mime = "application/json"
            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "private, max-age=7")
            self.end_headers()
            self.wfile.write(payload)

        do_GET = handle_request
        do_POST = handle_request

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        yield server, received
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)


def test_peer_forwards_selected_v4_bridge_and_preserves_response(
    upstream: tuple[ThreadingHTTPServer, list[tuple[str, bytes, str | None]]],
) -> None:
    server, received = upstream
    endpoint = f"http://127.0.0.1:{server.server_port}"
    with CustomEmojiFaultServer(endpoint, CAPABILITY) as peer:
        payload = b'{"custom_emoji_ids":["1","1109"]}'
        status, headers, body = request(
            peer.base_url, "POST", "/v4/custom-emoji-documents", payload
        )
        assert status == 200 and json.loads(body) == DOCUMENTS
        assert dict(headers)["Content-Type"] == "application/json; charset=utf-8"
        assert dict(headers)["Cache-Control"] == "private, max-age=7"
        assert request(peer.base_url, "GET", "/v4/snapshot")[0] == 200
        assert request(peer.base_url, "GET", "/v4/changes?after=0&limit=10")[0] == 200
        assert received == [
            ("/v4/custom-emoji-documents", payload, "Bearer " + CAPABILITY),
            ("/v4/snapshot", b"", "Bearer " + CAPABILITY),
            ("/v4/changes?after=0&limit=10", b"", "Bearer " + CAPABILITY),
        ]
        rows = peer.requests()
        assert rows[0] == {
            "sequence": 1,
            "phase": "initial",
            "operation": "documents",
            "path": "/v4/custom-emoji-documents",
            "document_ids": ["1", "1109"],
            "asset_id": None,
            "fault": "complete",
            "status": 200,
            "bytes": len(body),
        }
        assert CAPABILITY not in json.dumps(rows)


@pytest.mark.parametrize("fault,status", [("missing", 404), ("partial", 200)])
def test_document_faults_are_real_and_never_fetch_assets(
    upstream: tuple[ThreadingHTTPServer, list[tuple[str, bytes, str | None]]],
    fault: DocumentFault,
    status: int,
) -> None:
    server, received = upstream
    with CustomEmojiFaultServer(f"http://127.0.0.1:{server.server_port}", CAPABILITY) as peer:
        peer.phase(fault)
        peer.document_fault(
            fault,
            missing_ids={"1109"} if fault == "missing" else None,
        )
        payload = b'{"custom_emoji_ids":["1","1109"]}'
        observed_status, _, body = request(
            peer.base_url, "POST", "/v4/custom-emoji-documents", payload
        )
        assert observed_status == status
        if fault == "missing":
            assert json.loads(body) == {"schema": 4, "error": "document_unavailable"}
            known_payload = b'{"custom_emoji_ids":["1"]}'
            known_status, _, known_body = request(
                peer.base_url, "POST", "/v4/custom-emoji-documents", known_payload
            )
            assert known_status == 200
            assert json.loads(known_body)["custom_emoji"] == DOCUMENTS["custom_emoji"][:1]
            assert received == [
                ("/v4/custom-emoji-documents", known_payload, "Bearer " + CAPABILITY)
            ]
            assert [
                (row["document_ids"], row["fault"], row["status"]) for row in peer.requests()
            ] == [
                (["1", "1109"], "missing", 404),
                (["1"], "complete", 200),
            ]
        else:
            partial = json.loads(body)
            assert partial["custom_emoji"] == DOCUMENTS["custom_emoji"][:1]
            assert partial["assets"] == DOCUMENTS["assets"][:2]
            single_payload = b'{"custom_emoji_ids":["1"]}'
            single_status, _, single_body = request(
                peer.base_url, "POST", "/v4/custom-emoji-documents", single_payload
            )
            assert single_status == 200
            single = json.loads(single_body)
            assert single["custom_emoji"] == [] and single["assets"] == []
            assert received == [
                ("/v4/custom-emoji-documents", payload, "Bearer " + CAPABILITY),
                ("/v4/custom-emoji-documents", single_payload, "Bearer " + CAPABILITY),
            ]
        assert all(row["operation"] != "asset" for row in peer.requests())


def test_held_shared_asset_completes_after_one_consumer_is_removed(
    upstream: tuple[ThreadingHTTPServer, list[tuple[str, bytes, str | None]]],
) -> None:
    server, _ = upstream
    with CustomEmojiFaultServer(f"http://127.0.0.1:{server.server_port}", CAPABILITY) as peer:
        hold = peer.hold_asset(2)

        def download() -> bytes:
            return request(peer.base_url, "GET", "/v4/assets/2")[2]

        with ThreadPoolExecutor(max_workers=1) as pool:
            result = pool.submit(download)
            assert hold.started.wait(timeout=5)
            assert hold.partial_sent.wait(timeout=5)
            assert not result.done()
            hold.release.set()
            assert result.result(timeout=5) == b"shared-thumbnail-bytes"
        assert hold.finished.wait(timeout=5)
        rows = peer.requests()
        assert [(row["operation"], row["asset_id"], row["bytes"]) for row in rows] == [
            ("asset", 2, len(b"shared-thumbnail-bytes"))
        ]


def test_peer_rejects_wrong_auth_routes_and_targets(
    upstream: tuple[ThreadingHTTPServer, list[tuple[str, bytes, str | None]]],
) -> None:
    server, received = upstream
    with CustomEmojiFaultServer(f"http://127.0.0.1:{server.server_port}", CAPABILITY) as peer:
        assert request(peer.base_url, "GET", "/v4/snapshot", authorization=False)[0] == 401
        assert request(peer.base_url, "GET", "/file/secret")[0] == 404
        assert peer.requests() == []
        assert received == []
    for target in (
        "https://127.0.0.1:9",
        "http://localhost:9",
        "http://192.0.2.1:9",
        "http://127.0.0.1",
        "http://user@127.0.0.1:9",
        "http://127.0.0.1:9/path",
    ):
        with pytest.raises(ValueError, match="selected loopback"):
            CustomEmojiFaultServer(target, CAPABILITY)
