"""Real guarded HTTP observations for the bounded native-only request proxy."""

import http.client
import json
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
