"""Real guarded HTTP observations for the bounded native-only request proxy."""

import http.client
import json
import socket
import threading
import time
from contextlib import ExitStack
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import pytest
from probes.native_asset_proxy import NativeAssetProxy

CAPABILITY = "gramlab-client_" + "c" * 43


def _post_document_request(
    endpoint: str,
    payload: bytes,
    *,
    capability: str = CAPABILITY,
) -> tuple[int, list[tuple[str, str]], bytes]:
    connection = http.client.HTTPConnection("127.0.0.1", urlsplit(endpoint).port, timeout=5)
    try:
        connection.request(
            "POST",
            "/v4/custom-emoji-documents",
            payload,
            {
                "Authorization": "Bearer " + capability,
                "Content-Length": str(len(payload)),
                "Content-Type": "application/json",
            },
        )
        response = connection.getresponse()
        return response.status, response.getheaders(), response.read()
    finally:
        connection.close()


@pytest.mark.parametrize("mode", ["complete", "redirect", "missing"])
def test_proxy_preserves_response_and_counts_only_native_assets(mode: str) -> None:
    received: list[tuple[str, str | None]] = []

    class Upstream(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:
            pass

        def do_GET(self) -> None:
            received.append((self.path, self.headers.get("Authorization")))
            payload = b"original-photo-bytes" if mode == "complete" else b""
            self.send_response(200 if mode == "complete" else 302 if mode == "redirect" else 404)
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Content-Type", "image/png")
            if mode == "redirect":
                self.send_header("Location", "http://192.0.2.1/forbidden")
            self.end_headers()
            self.wfile.write(payload)

    with ThreadingHTTPServer(("127.0.0.1", 0), Upstream) as upstream:
        worker = threading.Thread(target=upstream.serve_forever, daemon=True)
        worker.start()
        try:
            with NativeAssetProxy(f"http://127.0.0.1:{upstream.server_port}", CAPABILITY) as proxy:
                connection = http.client.HTTPConnection(
                    "127.0.0.1", urlsplit(proxy.base_url).port, timeout=5
                )
                try:
                    for path, auth, status in (
                        ("/v3/assets/1", "wrong", 401),
                        ("/file/botsecret/x", CAPABILITY, 400),
                    ):
                        connection.request("GET", path, headers={"Authorization": "Bearer " + auth})
                        response = connection.getresponse()
                        assert response.status == status
                        response.read()
                    assert received == [] and proxy.requests() == []
                    connection.request(
                        "GET", "/v3/snapshot", headers={"Authorization": "Bearer " + CAPABILITY}
                    )
                    response = connection.getresponse()
                    response.read()
                    assert proxy.requests() == []
                    proxy.phase("restart")
                    connection.request(
                        "GET", "/v3/assets/1", headers={"Authorization": "Bearer " + CAPABILITY}
                    )
                    response = connection.getresponse()
                    assert response.status == (
                        200 if mode == "complete" else 302 if mode == "redirect" else 404
                    )
                    assert response.read() == (
                        b"original-photo-bytes" if mode == "complete" else b""
                    )
                    if mode == "redirect":
                        assert response.getheader("Location") == "http://192.0.2.1/forbidden"
                    deadline = time.monotonic() + 5
                    while (
                        proxy.requests()[0]["finished_ns"] is None and time.monotonic() < deadline
                    ):
                        time.sleep(0.01)
                    record = proxy.requests()[0]
                    assert record == {
                        "sequence": 1,
                        "phase": "restart",
                        "asset_id": 1,
                        "status": response.status,
                        "bytes": 20 if mode == "complete" else 0,
                        "started_ns": record["started_ns"],
                        "finished_ns": record["finished_ns"],
                        "error": None,
                    }
                    assert record["finished_ns"] >= record["started_ns"] > 0
                    assert CAPABILITY not in json.dumps(proxy.requests())
                    assert received == [
                        ("/v3/snapshot", "Bearer " + CAPABILITY),
                        ("/v3/assets/1", "Bearer " + CAPABILITY),
                    ]
                finally:
                    connection.close()
        finally:
            upstream.shutdown()
            worker.join(timeout=5)


@pytest.mark.parametrize(
    "target",
    [
        "https://127.0.0.1:9",
        "http://192.0.2.1:9",
        "http://localhost:9",
        "http://127.0.0.1",
        "http://user@127.0.0.1:9",
        "http://127.0.0.1:9/other",
        "http://127.0.0.1:9/?secret=x",
        "http://127.0.0.1:9/#fragment",
    ],
)
def test_proxy_rejects_nonselected_targets(target: str) -> None:
    with pytest.raises(ValueError, match="selected loopback"):
        NativeAssetProxy(target, CAPABILITY)


def test_proxy_retargets_reopened_bridge_and_excludes_direct_scenario_reads(tmp_path: Path) -> None:
    from test_android_media import assert_unchanged_snapshot

    from gramlab.client_bridge import ClientBridge
    from gramlab.world import World

    image = Path("tests/assets/rich-media/photo-square-16x16.png").read_bytes()
    directory = tmp_path / "world"
    with World.create(directory, seed=23, now=1700000000) as world:
        world.create_user(first_name="Sara", language_code="fa")
        world.create_user(first_name="Echo", username="gramlab_echo_bot", is_bot=True)
        world.open_private_chat(user_id=1, bot_id=2)
        world.send_photo(
            chat_id=1,
            sender_id=2,
            photo={"type": "photo", "media": "attach://photo"},
            uploads={"photo": image},
            caption="PNG ordinary / تصویر معمولی",
        )
        capability = world.issue_client_token(1)

    def get(endpoint: str, path: str) -> tuple[int, bytes]:
        connection = http.client.HTTPConnection("127.0.0.1", urlsplit(endpoint).port, timeout=5)
        try:
            connection.request("GET", path, headers={"Authorization": "Bearer " + capability})
            response = connection.getresponse()
            return response.status, response.read()
        finally:
            connection.close()

    with ExitStack() as stack:
        with ClientBridge(directory) as first:
            proxy = stack.enter_context(NativeAssetProxy(first.base_url, capability))
            assert get(first.base_url, "/v3/assets/1") == (200, image)
            assert proxy.requests() == []
            assert get(proxy.base_url, "/v3/assets/1") == (200, image)
            snapshot = get(proxy.base_url, "/v3/snapshot")
            assert snapshot[0] == 200
            assert_unchanged_snapshot(json.loads(snapshot[1]))
        with ClientBridge(directory) as reopened:
            proxy.retarget(reopened.base_url)
            proxy.phase("restart")
            assert get(proxy.base_url, "/v3/snapshot") == snapshot
            assert get(reopened.base_url, "/v3/assets/1") == (200, image)
            assert get(proxy.base_url, "/v3/assets/1") == (200, image)
            assert get(proxy.base_url, "/v3/assets/2")[0] == 404
            deadline = time.monotonic() + 5
            while (
                any(row["finished_ns"] is None for row in proxy.requests())
                and time.monotonic() < deadline
            ):
                time.sleep(0.01)
            records = proxy.requests()
            assert [
                (row["phase"], row["asset_id"], row["status"], row["bytes"]) for row in records
            ] == [
                ("initial", 1, 200, len(image)),
                ("restart", 1, 200, len(image)),
                ("restart", 2, 404, records[2]["bytes"]),
            ]
            assert records[2]["bytes"] > 0
            assert all(
                row["finished_ns"] >= row["started_ns"] > 0 and row["error"] is None
                for row in records
            )
            assert capability not in json.dumps(records)


def test_v4_document_requests_preserve_response_and_use_a_separate_journal() -> None:
    received: list[tuple[str, bytes, str | None]] = []
    response_body = b'{"documents":[{"custom_emoji_id":"7","file_id":"doc-7"}]}'

    class Upstream(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:
            pass

        def do_GET(self) -> None:
            received.append((self.path, b"", self.headers.get("Authorization")))
            body = b"asset"
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self) -> None:
            length = int(self.headers["Content-Length"])
            received.append((self.path, self.rfile.read(length), self.headers.get("Authorization")))
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(response_body)))
            self.send_header("Cache-Control", "private, max-age=5")
            self.end_headers()
            self.wfile.write(response_body)

    with ThreadingHTTPServer(("127.0.0.1", 0), Upstream) as upstream:
        worker = threading.Thread(target=upstream.serve_forever, daemon=True)
        worker.start()
        try:
            with NativeAssetProxy(f"http://127.0.0.1:{upstream.server_port}", CAPABILITY) as proxy:
                payload = b'{"custom_emoji_ids":["7","7","9223372036854775807"]}'
                status, headers, body = _post_document_request(proxy.base_url, payload)
                assert status == 200
                assert body == response_body
                assert dict(headers)["Content-Type"] == "application/json; charset=utf-8"
                assert dict(headers)["Content-Length"] == str(len(response_body))
                assert dict(headers)["Cache-Control"] == "private, max-age=5"

                connection = http.client.HTTPConnection(
                    "127.0.0.1", urlsplit(proxy.base_url).port, timeout=5
                )
                try:
                    for path in (
                        "/v4/snapshot",
                        "/v4/changes?after=0&limit=50",
                        "/v4/callbacks/callback_1",
                    ):
                        connection.request(
                            "GET", path, headers={"Authorization": "Bearer " + CAPABILITY}
                        )
                        assert connection.getresponse().read() == b"asset"
                    for path in ("/v4/callbacks", "/v4/messages"):
                        connection.request(
                            "POST",
                            path,
                            b"{}",
                            {
                                "Authorization": "Bearer " + CAPABILITY,
                                "Content-Type": "application/json",
                            },
                        )
                        assert connection.getresponse().read() == response_body
                    connection.request(
                        "GET", "/v4/assets/9", headers={"Authorization": "Bearer " + CAPABILITY}
                    )
                    assert connection.getresponse().read() == b"asset"
                finally:
                    connection.close()

                deadline = time.monotonic() + 5
                while (
                    proxy.document_requests()[0]["finished_ns"] is None
                    and time.monotonic() < deadline
                ):
                    time.sleep(0.01)
                documents = proxy.document_requests()
                record = documents[0]
                assert record == {
                    "sequence": 1,
                    "phase": "initial",
                    "custom_emoji_ids": ["7", "7", "9223372036854775807"],
                    "status": 200,
                    "bytes": len(response_body),
                    "started_ns": record["started_ns"],
                    "finished_ns": record["finished_ns"],
                    "error": None,
                }
                assert record["finished_ns"] >= record["started_ns"] > 0
                documents[0]["custom_emoji_ids"].append("secret")
                documents[0]["status"] = 500
                assert proxy.document_requests()[0]["custom_emoji_ids"] == [
                    "7",
                    "7",
                    "9223372036854775807",
                ]
                assert proxy.document_requests()[0]["status"] == 200
                assert [
                    (row["asset_id"], row["status"], row["bytes"]) for row in proxy.requests()
                ] == [(9, 200, 5)]
                serialized = json.dumps(proxy.document_requests())
                assert CAPABILITY not in serialized
                assert response_body.decode() not in serialized
                assert received == [
                    (
                        "/v4/custom-emoji-documents",
                        payload,
                        "Bearer " + CAPABILITY,
                    ),
                    ("/v4/snapshot", b"", "Bearer " + CAPABILITY),
                    ("/v4/changes?after=0&limit=50", b"", "Bearer " + CAPABILITY),
                    ("/v4/callbacks/callback_1", b"", "Bearer " + CAPABILITY),
                    ("/v4/callbacks", b"{}", "Bearer " + CAPABILITY),
                    ("/v4/messages", b"{}", "Bearer " + CAPABILITY),
                    ("/v4/assets/9", b"", "Bearer " + CAPABILITY),
                ]
        finally:
            upstream.shutdown()
            worker.join(timeout=5)


@pytest.mark.parametrize(
    "payload",
    [
        b"{}",
        b'{"custom_emoji_ids":[]}',
        b'{"custom_emoji_ids":["0"]}',
        b'{"custom_emoji_ids":["01"]}',
        b'{"custom_emoji_ids":[1]}',
        b'{"custom_emoji_ids":["9223372036854775808"]}',
        b'{"custom_emoji_ids":["1"],"extra":true}',
        b'{"custom_emoji_ids":["1"],"custom_emoji_ids":["2"]}',
        b'{"custom_emoji_ids":',
        b'{"custom_emoji_ids":["1"' + b',"1"' * 200 + b"]}",
    ],
)
def test_v4_document_requests_reject_invalid_json_before_forwarding(payload: bytes) -> None:
    class Upstream(BaseHTTPRequestHandler):
        forwarded = 0

        def do_POST(self) -> None:
            type(self).forwarded += 1
            self.send_error(500)

    with ThreadingHTTPServer(("127.0.0.1", 0), Upstream) as upstream:
        worker = threading.Thread(target=upstream.serve_forever, daemon=True)
        worker.start()
        try:
            with NativeAssetProxy(f"http://127.0.0.1:{upstream.server_port}", CAPABILITY) as proxy:
                assert _post_document_request(proxy.base_url, payload)[0] == 400
                assert Upstream.forwarded == 0
                assert proxy.document_requests() == []
        finally:
            upstream.shutdown()
            worker.join(timeout=5)


def test_v4_document_requests_reject_wrong_auth_and_nonlocal_routes() -> None:
    class Upstream(BaseHTTPRequestHandler):
        forwarded = 0

        def do_GET(self) -> None:
            type(self).forwarded += 1
            self.send_error(500)

        def do_POST(self) -> None:
            type(self).forwarded += 1
            self.send_error(500)

    with ThreadingHTTPServer(("127.0.0.1", 0), Upstream) as upstream:
        worker = threading.Thread(target=upstream.serve_forever, daemon=True)
        worker.start()
        try:
            with NativeAssetProxy(f"http://127.0.0.1:{upstream.server_port}", CAPABILITY) as proxy:
                assert (
                    _post_document_request(
                        proxy.base_url, b'{"custom_emoji_ids":["1"]}', capability="wrong"
                    )[0]
                    == 401
                )
                connection = http.client.HTTPConnection(
                    "127.0.0.1", urlsplit(proxy.base_url).port, timeout=5
                )
                try:
                    for method, path in (
                        ("POST", "/v3/custom-emoji-documents"),
                        ("GET", "/v4/custom-emoji-documents"),
                        ("POST", "/v5/custom-emoji-documents"),
                        ("POST", "http://192.0.2.1/v4/custom-emoji-documents"),
                        ("GET", "/file/bot-secret/document"),
                    ):
                        connection.request(
                            method,
                            path,
                            headers={"Authorization": "Bearer " + CAPABILITY},
                        )
                        response = connection.getresponse()
                        assert response.status == 400
                        response.read()
                finally:
                    connection.close()
                port = urlsplit(proxy.base_url).port
                assert port is not None
                request = (
                    "POST /v4/custom-emoji-documents HTTP/1.1\r\n"
                    "Host: 127.0.0.1\r\n"
                    f"Authorization: Bearer {CAPABILITY}\r\n"
                    f"Authorization: Bearer {CAPABILITY}\r\n"
                    "Content-Length: 26\r\n"
                    "Content-Type: application/json\r\n"
                    "Connection: close\r\n\r\n"
                    '{"custom_emoji_ids":["1"]}'
                ).encode()
                with socket.create_connection(("127.0.0.1", port), timeout=5) as client:
                    client.sendall(request)
                    assert client.recv(4096).startswith(b"HTTP/1.0 401 ")
                assert Upstream.forwarded == 0
                assert proxy.requests() == []
                assert proxy.document_requests() == []
        finally:
            upstream.shutdown()
            worker.join(timeout=5)


@pytest.mark.parametrize(
    "headers",
    [
        "Content-Type: application/json\r\nContent-Length: 26\r\nContent-Length: 26\r\n",
        "Content-Type: application/json\r\nContent-Length: 26\r\nTransfer-Encoding: chunked\r\n",
        "Content-Type: application/json\r\nContent-Length: 16385\r\n",
        "Content-Length: 26\r\n",
        "Content-Type: text/plain\r\nContent-Length: 26\r\n",
    ],
)
def test_v4_document_requests_reject_unsafe_framing(headers: str) -> None:
    class Upstream(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            raise AssertionError("invalid request reached upstream")

    with ThreadingHTTPServer(("127.0.0.1", 0), Upstream) as upstream:
        worker = threading.Thread(target=upstream.serve_forever, daemon=True)
        worker.start()
        try:
            with NativeAssetProxy(f"http://127.0.0.1:{upstream.server_port}", CAPABILITY) as proxy:
                port = urlsplit(proxy.base_url).port
                assert port is not None
                request = (
                    "POST /v4/custom-emoji-documents HTTP/1.1\r\n"
                    "Host: 127.0.0.1\r\n"
                    f"Authorization: Bearer {CAPABILITY}\r\n"
                    f"{headers}"
                    "Connection: close\r\n\r\n"
                    '{"custom_emoji_ids":["1"]}'
                ).encode()
                with socket.create_connection(("127.0.0.1", port), timeout=5) as connection:
                    connection.sendall(request)
                    response = connection.recv(4096)
                assert response.startswith(b"HTTP/1.0 400 ")
                assert proxy.document_requests() == []
        finally:
            upstream.shutdown()
            worker.join(timeout=5)


def test_v4_document_journal_preserves_missing_and_interrupted_responses() -> None:
    class Upstream(BaseHTTPRequestHandler):
        request_count = 0

        def log_message(self, format: str, *args: Any) -> None:
            pass

        def do_POST(self) -> None:
            type(self).request_count += 1
            self.rfile.read(int(self.headers["Content-Length"]))
            if type(self).request_count == 1:
                body = b'{"error":"missing"}'
                self.send_response(404)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if type(self).request_count == 2:
                self.send_response(302)
                self.send_header("Content-Length", "0")
                self.send_header("Location", "http://192.0.2.1/forbidden")
                self.end_headers()
                return
            self.send_response(200)
            self.send_header("Content-Length", "20")
            self.end_headers()
            self.wfile.write(b"partial")
            self.wfile.flush()
            self.connection.shutdown(socket.SHUT_RDWR)
            self.connection.close()

    with ThreadingHTTPServer(("127.0.0.1", 0), Upstream) as upstream:
        worker = threading.Thread(target=upstream.serve_forever, daemon=True)
        worker.start()
        try:
            with NativeAssetProxy(f"http://127.0.0.1:{upstream.server_port}", CAPABILITY) as proxy:
                status, headers, body = _post_document_request(
                    proxy.base_url, b'{"custom_emoji_ids":["404"]}'
                )
                assert status == 404
                assert dict(headers)["Content-Length"] == "19"
                assert body == b'{"error":"missing"}'
                status, headers, body = _post_document_request(
                    proxy.base_url, b'{"custom_emoji_ids":["6"]}'
                )
                assert status == 302
                assert dict(headers)["Location"] == "http://192.0.2.1/forbidden"
                assert body == b""
                connection = http.client.HTTPConnection(
                    "127.0.0.1", urlsplit(proxy.base_url).port, timeout=5
                )
                try:
                    payload = b'{"custom_emoji_ids":["5"]}'
                    connection.request(
                        "POST",
                        "/v4/custom-emoji-documents",
                        payload,
                        {
                            "Authorization": "Bearer " + CAPABILITY,
                            "Content-Length": str(len(payload)),
                            "Content-Type": "application/json",
                        },
                    )
                    response = connection.getresponse()
                    assert response.status == 200
                    with pytest.raises(http.client.IncompleteRead):
                        response.read()
                finally:
                    connection.close()
                deadline = time.monotonic() + 5
                while (
                    any(row["finished_ns"] is None for row in proxy.document_requests())
                    and time.monotonic() < deadline
                ):
                    time.sleep(0.01)
                records = proxy.document_requests()
                assert [(row["status"], row["bytes"], row["error"]) for row in records] == [
                    (404, 19, None),
                    (302, 0, None),
                    (200, 7, "transport_error"),
                ]
        finally:
            upstream.shutdown()
            worker.join(timeout=5)


def test_v4_document_inflight_request_keeps_start_phase_and_target() -> None:
    first_started = threading.Event()
    release_first = threading.Event()
    received: list[tuple[str, str]] = []

    def peer(name: str, *, blocked: bool) -> type[BaseHTTPRequestHandler]:
        class Upstream(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args: Any) -> None:
                pass

            def do_POST(self) -> None:
                payload = self.rfile.read(int(self.headers["Content-Length"]))
                received.append((name, payload.decode()))
                if blocked:
                    first_started.set()
                    assert release_first.wait(5)
                body = name.encode()
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        return Upstream

    with ExitStack() as stack:
        first = stack.enter_context(
            ThreadingHTTPServer(("127.0.0.1", 0), peer("first", blocked=True))
        )
        second = stack.enter_context(
            ThreadingHTTPServer(("127.0.0.1", 0), peer("second", blocked=False))
        )
        workers = [
            threading.Thread(target=server.serve_forever, daemon=True) for server in (first, second)
        ]
        for worker in workers:
            worker.start()
        with NativeAssetProxy(f"http://127.0.0.1:{first.server_port}", CAPABILITY) as proxy:
            first_result: list[tuple[int, list[tuple[str, str]], bytes]] = []
            requester = threading.Thread(
                target=lambda: first_result.append(
                    _post_document_request(proxy.base_url, b'{"custom_emoji_ids":["1"]}')
                )
            )
            requester.start()
            assert first_started.wait(5)
            proxy.retarget(f"http://127.0.0.1:{second.server_port}")
            proxy.phase("restart")
            assert (
                _post_document_request(proxy.base_url, b'{"custom_emoji_ids":["2"]}')[2]
                == b"second"
            )
            release_first.set()
            requester.join(timeout=5)
            assert not requester.is_alive()
            assert first_result[0][2] == b"first"
            assert received == [
                ("first", '{"custom_emoji_ids":["1"]}'),
                ("second", '{"custom_emoji_ids":["2"]}'),
            ]
            assert [
                (row["sequence"], row["phase"], row["custom_emoji_ids"])
                for row in proxy.document_requests()
            ] == [(1, "initial", ["1"]), (2, "restart", ["2"])]
        for server, worker in zip((first, second), workers, strict=True):
            server.shutdown()
            worker.join(timeout=5)
