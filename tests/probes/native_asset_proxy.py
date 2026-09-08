"""Test-only observation of native asset GETs to one selected loopback bridge."""

from __future__ import annotations

import http.client
import json
import re
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import TracebackType
from typing import Any, Self
from urllib.parse import urlsplit


class NativeAssetProxy:
    def __init__(self, endpoint: str, capability: str) -> None:
        if [name for _, name in socket.if_nameindex()] != ["lo"]:
            raise RuntimeError("Native asset proxy requires the isolated loopback runtime")
        self._lock = threading.Lock()
        self._endpoint = self._port(endpoint)
        self._capability = capability
        self._phase = "initial"
        self._requests: list[dict[str, Any]] = []
        self._document_requests: list[dict[str, Any]] = []
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def setup(self) -> None:
                super().setup()
                self.connection.settimeout(5)

            def log_message(self, format: str, *args: Any) -> None:
                pass

            def do_GET(self) -> None:
                self.forward()

            def do_POST(self) -> None:
                self.forward()

            def forward(self) -> None:
                asset = re.fullmatch(r"/v[34]/assets/([1-9][0-9]{0,18})", self.path)
                versioned_get = re.fullmatch(
                    r"/v[34]/(?:snapshot|changes\?after=[0-9]+&limit=[0-9]+|callbacks/[A-Za-z0-9_-]{1,128})",
                    self.path,
                )
                document_lookup = (
                    self.command == "POST" and self.path == "/v4/custom-emoji-documents"
                )
                allowed = (
                    self.command == "GET" and (asset is not None or versioned_get is not None)
                ) or (
                    self.command == "POST"
                    and self.path
                    in (
                        "/v2/messages",
                        "/v3/callbacks",
                        "/v4/callbacks",
                        "/v4/messages",
                        "/v4/custom-emoji-documents",
                    )
                )
                authorization = self.headers.get_all("Authorization", [])
                authenticated = (
                    authorization == ["Bearer " + owner._capability]
                    if self.path.startswith("/v4/")
                    else self.headers.get("Authorization") == "Bearer " + owner._capability
                )
                if not authenticated:
                    self.send_error(401, "Unauthorized")
                    return
                if not allowed or self.headers.get("Transfer-Encoding") is not None:
                    self.send_error(400, "Unsupported fixture route")
                    return
                try:
                    lengths = self.headers.get_all("Content-Length", [])
                    if document_lookup and len(lengths) != 1:
                        raise ValueError
                    length = int(lengths[0]) if lengths else 0
                    maximum = 16384 if document_lookup else 65536
                    if not 0 <= length <= maximum or (document_lookup and length == 0):
                        raise ValueError
                except ValueError:
                    self.send_error(400, "Invalid request size")
                    return
                self.connection.settimeout(5)
                payload = self.rfile.read(length) if length else None
                document_ids: list[str] | None = None
                if document_lookup:
                    if (
                        payload is None
                        or len(payload) != length
                        or self.headers.get_content_type() != "application/json"
                    ):
                        self.send_error(400, "Invalid document request")
                        return
                    try:
                        decoded = json.loads(
                            payload.decode("utf-8"), object_pairs_hook=_json_object
                        )
                    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError, ValueError):
                        self.send_error(400, "Invalid document request")
                        return
                    if not isinstance(decoded, dict) or set(decoded) != {"custom_emoji_ids"}:
                        self.send_error(400, "Invalid document request")
                        return
                    candidate_ids = decoded["custom_emoji_ids"]
                    if (
                        not isinstance(candidate_ids, list)
                        or not 1 <= len(candidate_ids) <= 200
                        or any(
                            not isinstance(item, str)
                            or re.fullmatch(r"[1-9][0-9]{0,18}", item) is None
                            or int(item) > 9223372036854775807
                            for item in candidate_ids
                        )
                    ):
                        self.send_error(400, "Invalid document request")
                        return
                    document_ids = candidate_ids
                with owner._lock:
                    port = owner._endpoint
                    record: dict[str, Any] | None = None
                    if asset is not None:
                        record = {
                            "sequence": len(owner._requests) + 1,
                            "phase": owner._phase,
                            "asset_id": int(asset[1]),
                            "status": None,
                            "bytes": 0,
                            "started_ns": time.monotonic_ns(),
                            "finished_ns": None,
                            "error": None,
                        }
                        owner._requests.append(record)
                    elif document_ids is not None:
                        record = {
                            "sequence": len(owner._document_requests) + 1,
                            "phase": owner._phase,
                            "custom_emoji_ids": list(document_ids),
                            "status": None,
                            "bytes": 0,
                            "started_ns": time.monotonic_ns(),
                            "finished_ns": None,
                            "error": None,
                        }
                        owner._document_requests.append(record)
                connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
                try:
                    headers = {
                        "Authorization": "Bearer " + owner._capability,
                        "Connection": "close",
                    }
                    for name in ("Content-Type", "Accept", "Range"):
                        if self.headers.get(name) is not None:
                            headers[name] = self.headers[name]
                    connection.request(self.command, self.path, payload, headers)
                    response = connection.getresponse()
                    if record is not None:
                        with owner._lock:
                            record["status"] = response.status
                    self.send_response(response.status)
                    for name in ("Content-Type", "Content-Length", "Cache-Control", "Location"):
                        value = response.getheader(name)
                        if value is not None:
                            self.send_header(name, value)
                    self.send_header("Connection", "close")
                    self.end_headers()
                    while chunk := response.read1(65536):
                        self.wfile.write(chunk)
                        self.wfile.flush()
                        if record is not None:
                            with owner._lock:
                                record["bytes"] += len(chunk)
                    if response.length not in (None, 0):
                        if record is not None:
                            with owner._lock:
                                record["error"] = "transport_error"
                        self.close_connection = True
                except http.client.IncompleteRead as exc:
                    if exc.partial:
                        try:
                            self.wfile.write(exc.partial)
                            self.wfile.flush()
                        except OSError:
                            pass
                        else:
                            if record is not None:
                                with owner._lock:
                                    record["bytes"] += len(exc.partial)
                    if record is not None:
                        with owner._lock:
                            record["error"] = "transport_error"
                    self.close_connection = True
                except (OSError, http.client.HTTPException):
                    if record is not None:
                        with owner._lock:
                            record["error"] = "transport_error"
                    self.close_connection = True
                finally:
                    connection.close()
                    if record is not None:
                        with owner._lock:
                            record["finished_ns"] = time.monotonic_ns()

        class Server(ThreadingHTTPServer):
            daemon_threads = False

        self._server = Server(("127.0.0.1", 0), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    @staticmethod
    def _port(endpoint: str) -> int:
        url = urlsplit(endpoint)
        if (
            url.scheme != "http"
            or url.hostname != "127.0.0.1"
            or url.port is None
            or url.username is not None
            or url.password is not None
            or url.path not in ("", "/")
            or url.query
            or url.fragment
        ):
            raise ValueError("Proxy target must be the selected loopback bridge")
        return url.port

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self._server.server_port}"

    def retarget(self, endpoint: str) -> None:
        port = self._port(endpoint)
        with self._lock:
            self._endpoint = port

    def phase(self, name: str) -> None:
        with self._lock:
            self._phase = name

    def requests(self) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(record) for record in self._requests]

    def document_requests(self) -> list[dict[str, Any]]:
        with self._lock:
            return [
                {**record, "custom_emoji_ids": list(record["custom_emoji_ids"])}
                for record in self._document_requests
            ]

    def __enter__(self) -> Self:
        self._thread.start()
        return self

    def __exit__(
        self,
        kind: type[BaseException] | None,
        value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=5)


def _json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("Repeated JSON field")
        value[key] = item
    return value
