"""Test-only observation of native asset GETs to one selected loopback bridge."""

from __future__ import annotations

import http.client
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
                asset = re.fullmatch(r"/v3/assets/([1-9][0-9]{0,18})", self.path)
                allowed = (
                    self.command == "GET"
                    and (
                        self.path == "/v3/snapshot"
                        or asset is not None
                        or re.fullmatch(r"/v3/changes\?after=[0-9]+&limit=[0-9]+", self.path)
                        is not None
                        or re.fullmatch(r"/v3/callbacks/[A-Za-z0-9_-]{1,128}", self.path)
                        is not None
                    )
                ) or (self.command == "POST" and self.path in ("/v3/callbacks", "/v2/messages"))
                if self.headers.get("Authorization") != "Bearer " + owner._capability:
                    self.send_error(401, "Unauthorized")
                    return
                if not allowed or self.headers.get("Transfer-Encoding") is not None:
                    self.send_error(400, "Unsupported fixture route")
                    return
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    if not 0 <= length <= 65536:
                        raise ValueError
                except ValueError:
                    self.send_error(400, "Invalid request size")
                    return
                self.connection.settimeout(5)
                payload = self.rfile.read(length) if length else None
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
                    while chunk := response.read(65536):
                        self.wfile.write(chunk)
                        if record is not None:
                            with owner._lock:
                                record["bytes"] += len(chunk)
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
