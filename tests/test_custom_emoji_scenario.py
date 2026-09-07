"""Register original media through the actual authenticated scenario control."""

import base64
import http.client
import io
import json
import random
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import pytest
from PIL import Image

from gramlab._control import WorldControl
from gramlab.scenario import Scenario, ScenarioError
from gramlab.world import World


@contextmanager
def _serve(handler: type[BaseHTTPRequestHandler]) -> Iterator[str]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)


def _large_webp() -> bytes:
    # Independent source pixels ensure the complete registration exceeds the old 64 KiB limit.
    source = random.Random(811).randbytes(100 * 100 * 4)
    image = Image.frombytes("RGBA", (100, 100), source)
    buffer = io.BytesIO()
    image.save(buffer, format="WEBP", lossless=True, exact=True)
    return buffer.getvalue()


def _post(
    endpoint: str,
    path: str,
    body: bytes,
    capability: str,
    *,
    extra_headers: dict[str, str] | None = None,
) -> tuple[int, dict[str, Any]]:
    url = urlsplit(endpoint)
    connection = http.client.HTTPConnection("127.0.0.1", url.port, timeout=5)
    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + capability,
        }
        headers.update(extra_headers or {})
        try:
            connection.request("POST", path, body, headers)
        except BrokenPipeError:
            # A bounded server can reject from Content-Length before consuming a large body.
            pass
        response = connection.getresponse()
        return response.status, json.loads(response.read())
    finally:
        connection.close()


def _post_duplicate_length(
    endpoint: str, path: str, body: bytes, capability: str
) -> tuple[int, dict[str, Any]]:
    url = urlsplit(endpoint)
    connection = http.client.HTTPConnection("127.0.0.1", url.port, timeout=5)
    try:
        connection.putrequest("POST", path)
        connection.putheader("Content-Type", "application/json")
        connection.putheader("Authorization", "Bearer " + capability)
        connection.putheader("Content-Length", str(len(body)))
        connection.putheader("Content-Length", str(len(body)))
        connection.endheaders(body)
        response = connection.getresponse()
        return response.status, json.loads(response.read())
    finally:
        connection.close()


def test_scenario_registers_large_media_and_retries_after_reopen(tmp_path: Path) -> None:
    directory = tmp_path / "world"
    with World.create(directory, seed=7, now=100):
        pass
    data = _large_webp()
    assert len(data) * 2 * 4 // 3 > 65536
    expected = {
        "custom_emoji_id": "9223372036854775807",
        "fallback": "🙂",
        "free": True,
        "needs_repainting": False,
        "main_asset_id": 1,
        "thumbnail_asset_id": 1,
        "duration_ms": 0,
    }
    for _ in range(2):
        with WorldControl(directory) as control:
            scenario = Scenario(
                control.base_url, capability=control.capability, world_id=control.world_id
            )
            assert (
                scenario.register_custom_emoji(
                    request_id="large-original",
                    custom_emoji_id="9223372036854775807",
                    main=data,
                    thumbnail=data,
                    fallback="🙂",
                )
                == expected
            )
            assert scenario.snapshot() == {
                "schema": 1,
                "seed": 7,
                "now": 100,
                "users": [],
                "chats": [],
            }
            assert scenario.events() == []
            with pytest.raises(ScenarioError) as failure:
                scenario.register_custom_emoji(
                    request_id="large-original", main=data, thumbnail=data, fallback="Different"
                )
            assert (failure.value.code, failure.value.outcome_uncertain) == (
                "invalid_request",
                False,
            )


def test_lost_registration_response_recovers_without_advancing_allocation(tmp_path: Path) -> None:
    directory = tmp_path / "world"
    with World.create(directory, seed=7, now=100):
        pass
    main = Path("tests/assets/custom-emoji/emoji-static.webp").read_bytes()
    thumbnail = Path("tests/assets/custom-emoji/emoji-thumbnail.webp").read_bytes()
    forwarded: list[tuple[int, dict[str, object]]] = []
    with WorldControl(directory) as control:
        target = urlsplit(control.base_url)

        class DropAfterCommit(BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                payload = self.rfile.read(int(self.headers["Content-Length"]))
                upstream = http.client.HTTPConnection("127.0.0.1", target.port, timeout=5)
                try:
                    upstream.request(
                        "POST",
                        self.path,
                        payload,
                        {
                            "Content-Type": "application/json",
                            "Authorization": self.headers["Authorization"],
                        },
                    )
                    response = upstream.getresponse()
                    forwarded.append((response.status, json.loads(response.read())))
                finally:
                    upstream.close()

            def log_message(self, format: str, *args: object) -> None:
                pass

        with _serve(DropAfterCommit) as endpoint:
            scenario = Scenario(endpoint, capability=control.capability, world_id=control.world_id)
            with pytest.raises(ScenarioError) as failure:
                scenario.register_custom_emoji(
                    request_id="lost", main=main, thumbnail=thumbnail, fallback="🙂"
                )
            assert (failure.value.code, failure.value.outcome_uncertain) == (
                "transport_error",
                True,
            )
        expected = {
            "custom_emoji_id": "1",
            "fallback": "🙂",
            "free": True,
            "needs_repainting": False,
            "main_asset_id": 1,
            "thumbnail_asset_id": 2,
            "duration_ms": 0,
        }
        assert forwarded == [(200, {"schema": 1, "world_id": control.world_id, "result": expected})]
    with WorldControl(directory) as reopened:
        scenario = Scenario(
            reopened.base_url, capability=reopened.capability, world_id=reopened.world_id
        )
        assert (
            scenario.register_custom_emoji(
                request_id="lost", main=main, thumbnail=thumbnail, fallback="🙂"
            )
            == expected
        )
        with pytest.raises(ScenarioError) as conflict:
            scenario.register_custom_emoji(
                request_id="lost", main=main, thumbnail=thumbnail, fallback="different"
            )
        assert (conflict.value.code, conflict.value.outcome_uncertain) == (
            "invalid_request",
            False,
        )
        assert scenario.register_custom_emoji(
            request_id="next", main=main, thumbnail=thumbnail, fallback="بعدی"
        ) == expected | {"custom_emoji_id": "2", "fallback": "بعدی"}


@pytest.mark.parametrize("operation", ["snapshot", "create_user", "register_custom_emoji"])
def test_dedicated_registration_route_rejects_wrong_operation_or_invalid_bytes(
    tmp_path: Path, operation: str
) -> None:
    directory = tmp_path / "world"
    with World.create(directory, seed=7, now=100):
        pass
    with WorldControl(directory) as control:
        url = urlsplit(control.base_url)
        connection = http.client.HTTPConnection("127.0.0.1", url.port, timeout=3)
        try:
            connection.request(
                "POST",
                "/v1/custom-emoji",
                json.dumps(
                    {
                        "schema": 1,
                        "world_id": control.world_id,
                        "operation": operation,
                        "parameters": {
                            "request_id": "bad",
                            "main": "%%%",
                            "thumbnail": "",
                            "fallback": "🙂",
                        },
                    }
                ),
                {
                    "Content-Type": "application/json",
                    "Authorization": "Bearer " + control.capability,
                },
            )
            response = connection.getresponse()
            body = json.loads(response.read())
            assert response.status == (400 if operation == "register_custom_emoji" else 404)
            assert body["error"]["code"] == (
                "invalid_request" if operation == "register_custom_emoji" else "unsupported"
            )
        finally:
            connection.close()
    with World.open(directory) as world:
        assert world.events() == []
        assert world.snapshot()["users"] == []


def test_registration_route_rejects_identity_and_decoded_size_before_mutation(
    tmp_path: Path,
) -> None:
    directory = tmp_path / "world"
    with World.create(directory, seed=7, now=100):
        pass
    with World.create(tmp_path / "other", seed=8, now=101) as other:
        other_id = other.world_id
    with WorldControl(directory) as control:
        base = {
            "schema": 1,
            "world_id": control.world_id,
            "operation": "register_custom_emoji",
            "parameters": {
                "request_id": "bounded",
                "main": base64.b64encode(b"x").decode(),
                "thumbnail": base64.b64encode(b"x").decode(),
                "fallback": "🙂",
            },
        }
        cases = [
            (control.capability + "x", base, 401, "unauthorized"),
            (control.capability, base | {"world_id": other_id}, 409, "wrong_world"),
        ]
        for capability, envelope, status, code in cases:
            actual_status, actual = _post(
                control.base_url,
                "/v1/custom-emoji",
                json.dumps(envelope).encode(),
                capability,
            )
            assert actual_status == status
            assert actual["error"]["code"] == code
        for field, size in (("main", 512 * 1024 + 1), ("thumbnail", 128 * 1024 + 1)):
            oversized = json.loads(json.dumps(base))
            oversized["parameters"][field] = base64.b64encode(b"x" * size).decode()
            status, response = _post(
                control.base_url,
                "/v1/custom-emoji",
                json.dumps(oversized).encode(),
                control.capability,
            )
            assert status == 400 and response["error"]["code"] == "invalid_request"
    with World.open(directory) as world:
        with pytest.raises(ValueError, match="unavailable"):
            world.custom_emoji_descriptor(1)
        assert world.events() == []


def test_control_routes_keep_distinct_encoded_limits_and_strict_framing(tmp_path: Path) -> None:
    directory = tmp_path / "world"
    with World.create(directory, seed=7, now=100):
        pass
    with WorldControl(directory) as control:
        main = Path("tests/assets/custom-emoji/emoji-static.webp").read_bytes()
        thumbnail = Path("tests/assets/custom-emoji/emoji-thumbnail.webp").read_bytes()
        duplicate = (
            '{"schema":1,"schema":1,"world_id":'
            + json.dumps(control.world_id)
            + ',"operation":"register_custom_emoji","parameters":{}}'
        ).encode()
        registration = {
            "schema": 1,
            "world_id": control.world_id,
            "operation": "register_custom_emoji",
            "parameters": {
                "request_id": "route-bound",
                "main": base64.b64encode(main).decode(),
                "thumbnail": base64.b64encode(thumbnail).decode(),
                "fallback": "🙂",
            },
        }
        ordinary = {
            "schema": 1,
            "world_id": control.world_id,
            "operation": "snapshot",
            "parameters": {},
        }
        registration_body = json.dumps(registration).encode()
        ordinary_body = json.dumps(ordinary).encode()
        for path, body, headers in (
            ("/v1/custom-emoji", duplicate, None),
            (
                "/v1/custom-emoji",
                registration_body + b" " * (1024 * 1024 + 1 - len(registration_body)),
                None,
            ),
            ("/v1/world", ordinary_body + b" " * (65537 - len(ordinary_body)), None),
            ("/v1/custom-emoji", b"{}", {"Transfer-Encoding": "chunked"}),
        ):
            status, response = _post(
                control.base_url,
                path,
                body,
                control.capability,
                extra_headers=headers,
            )
            assert status == 400
            assert response["error"]["code"] == "invalid_request"
        status, response = _post_duplicate_length(
            control.base_url, "/v1/world", ordinary_body, control.capability
        )
        assert status == 400 and response["error"]["code"] == "invalid_request"
        status, response = _post(
            control.base_url,
            "/v1/custom-emoji",
            json.dumps(ordinary).encode(),
            control.capability,
        )
        assert status == 404 and response["error"]["code"] == "unsupported"
        status, response = _post(
            control.base_url,
            "/v1/world",
            registration_body,
            control.capability,
        )
        assert status == 404 and response["error"]["code"] == "unsupported"
    with World.open(directory) as world:
        assert world.events() == []
