"""Test-only v4 bridge peer for custom-emoji faults and held asset responses."""

from __future__ import annotations

import http.client
import json
import math
import re
import socket
import threading
import time
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import TracebackType
from typing import Any, Literal, Self
from urllib.parse import urlsplit

DocumentFault = Literal["complete", "missing", "partial"]


@dataclass
class HeldAsset:
    """One explicitly delayed asset response controlled without timing sleeps."""

    asset_id: int
    progress_interval: float | None = None
    final_bytes: int = 1
    started: threading.Event = field(default_factory=threading.Event)
    partial_sent: threading.Event = field(default_factory=threading.Event)
    release: threading.Event = field(default_factory=threading.Event)
    finished: threading.Event = field(default_factory=threading.Event)
    progress_bytes_sent: int = 0
    error: str | None = None


class CustomEmojiFaultServer:
    """Forward one selected local bridge while altering only selected responses."""

    def __init__(self, endpoint: str, capability: str) -> None:
        if [name for _, name in socket.if_nameindex()] != ["lo"]:
            raise RuntimeError("Custom emoji fault server requires isolated loopback")
        self._endpoint = self._port(endpoint)
        self._capability = capability
        self._document_fault: DocumentFault = "complete"
        self._missing_ids: set[str] = set()
        self._phase = "initial"
        self._held_assets: dict[int, list[HeldAsset]] = {}
        self._holds: list[HeldAsset] = []
        self._requests: list[dict[str, Any]] = []
        self._lock = threading.Lock()
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def setup(self) -> None:
                super().setup()
                self.connection.settimeout(5)

            def log_message(self, format: str, *args: Any) -> None:
                pass

            def do_GET(self) -> None:
                self.serve_request()

            def do_POST(self) -> None:
                self.serve_request()

            def reply(
                self,
                status: int,
                headers: list[tuple[str, str]],
                body: bytes,
                *,
                length: int | None = None,
            ) -> None:
                self.send_response(status)
                preserved = {"content-type", "cache-control", "location"}
                for name, value in headers:
                    if name.lower() in preserved:
                        self.send_header(name, value)
                self.send_header("Content-Length", str(len(body) if length is None else length))
                self.send_header("Connection", "close")
                self.end_headers()
                if body:
                    self.wfile.write(body)
                    self.wfile.flush()

            def error(self, status: int, code: str) -> None:
                body = json.dumps({"schema": 4, "error": code}, separators=(",", ":")).encode()
                self.reply(status, [("Content-Type", "application/json")], body)

            def serve_request(self) -> None:
                authorization = self.headers.get_all("Authorization", [])
                if authorization != ["Bearer " + owner._capability]:
                    self.error(401, "unauthorized")
                    return
                if self.headers.get("Transfer-Encoding") is not None:
                    self.error(400, "unsupported_request")
                    return
                document = self.command == "POST" and self.path == "/v4/custom-emoji-documents"
                asset_match = (
                    re.fullmatch(r"/v4/assets/([1-9][0-9]{0,18})", self.path)
                    if self.command == "GET"
                    else None
                )
                allowed_get = self.command == "GET" and (
                    asset_match is not None
                    or re.fullmatch(
                        r"/v4/(?:snapshot|changes\?after=[0-9]+(?:&limit=[0-9]+)?|"
                        r"callbacks/[A-Za-z0-9_-]{1,128})",
                        self.path,
                    )
                    is not None
                )
                allowed_post = self.command == "POST" and self.path in {
                    "/v4/messages",
                    "/v4/callbacks",
                    "/v4/custom-emoji-documents",
                }
                if not allowed_get and not allowed_post:
                    self.error(404, "unsupported_operation")
                    return
                lengths = self.headers.get_all("Content-Length", [])
                try:
                    if len(lengths) > 1:
                        raise ValueError
                    length = int(lengths[0]) if lengths else 0
                    maximum = 16384 if document else 65536
                    if not 0 <= length <= maximum or (document and length == 0):
                        raise ValueError
                except ValueError:
                    self.error(400, "invalid_request_size")
                    return
                payload = self.rfile.read(length) if length else b""
                document_ids: list[str] | None = None
                if document:
                    try:
                        decoded = json.loads(payload)
                        values = decoded["custom_emoji_ids"]
                        if set(decoded) != {"custom_emoji_ids"} or not isinstance(values, list):
                            raise ValueError
                        if not 1 <= len(values) <= 200 or any(
                            not isinstance(value, str)
                            or re.fullmatch(r"[1-9][0-9]{0,18}", value) is None
                            or int(value) > 9223372036854775807
                            for value in values
                        ):
                            raise ValueError
                        document_ids = list(values)
                    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
                        self.error(400, "invalid_document_request")
                        return
                with owner._lock:
                    phase = owner._phase
                    fault = owner._document_fault if document else "complete"
                    if (
                        fault == "missing"
                        and document_ids is not None
                        and owner._missing_ids.isdisjoint(document_ids)
                    ):
                        fault = "complete"
                    hold: HeldAsset | None = None
                    asset_id = int(asset_match[1]) if asset_match is not None else None
                    if asset_id is not None:
                        planned = owner._held_assets.get(asset_id, [])
                        hold = planned.pop(0) if planned else None
                    record: dict[str, Any] = {
                        "sequence": len(owner._requests) + 1,
                        "phase": phase,
                        "operation": "documents" if document else "asset" if asset_id else "bridge",
                        "path": self.path,
                        "document_ids": document_ids,
                        "asset_id": asset_id,
                        "fault": fault,
                        "status": None,
                        "bytes": 0,
                    }
                    owner._requests.append(record)
                if document and fault == "missing":
                    body = json.dumps(
                        {"schema": 4, "error": "document_unavailable"}, separators=(",", ":")
                    ).encode()
                    record["status"] = 404
                    record["bytes"] = len(body)
                    self.reply(404, [("Content-Type", "application/json")], body)
                    return
                status, headers, body = owner._forward(
                    self.command, self.path, payload, self.headers
                )
                if document and fault == "partial" and status == 200:
                    body = owner._partial(body)
                    headers = [
                        (name, value) for name, value in headers if name.lower() != "content-length"
                    ]
                record["status"] = status
                record["bytes"] = len(body)
                if hold is None or status != 200:
                    self.reply(status, headers, body)
                    return
                split = max(1, len(body) // 2)
                if hold.progress_interval is not None and (
                    not body
                    or len(body) - split - hold.final_bytes < math.ceil(30 / hold.progress_interval)
                ):
                    hold.error = "unsupported_progressive_body"
                    record["fault"] = hold.error
                    failure = json.dumps(
                        {"schema": 4, "error": hold.error}, separators=(",", ":")
                    ).encode()
                    record["status"] = 500
                    record["bytes"] = len(failure)
                    self.reply(500, [("Content-Type", "application/json")], failure)
                    hold.finished.set()
                    return
                if not body:
                    self.reply(status, headers, body)
                    return
                hold.started.set()
                self.reply(status, headers, body[:split], length=len(body))
                hold.partial_sent.set()
                try:
                    cursor = split
                    deadline = time.monotonic() + 30
                    if hold.progress_interval is not None:
                        progressive_end = len(body) - hold.final_bytes
                        while cursor < progressive_end and not hold.release.is_set():
                            remaining = deadline - time.monotonic()
                            if remaining <= 0 or hold.release.wait(
                                timeout=min(hold.progress_interval, remaining)
                            ):
                                break
                            self.wfile.write(body[cursor : cursor + 1])
                            self.wfile.flush()
                            cursor += 1
                            hold.progress_bytes_sent += 1
                    if not hold.release.is_set():
                        remaining = deadline - time.monotonic()
                        if remaining > 0:
                            hold.release.wait(timeout=remaining)
                    if hold.release.is_set():
                        self.wfile.write(body[cursor:])
                        self.wfile.flush()
                except (ConnectionError, OSError):
                    pass
                finally:
                    hold.finished.set()

        class Server(ThreadingHTTPServer):
            daemon_threads = False

        self._server = Server(("127.0.0.1", 0), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever)

    @staticmethod
    def _port(endpoint: str) -> int:
        parsed = urlsplit(endpoint)
        if (
            parsed.scheme != "http"
            or parsed.hostname != "127.0.0.1"
            or parsed.port is None
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path not in ("", "/")
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("Fault target must be the selected loopback bridge")
        return parsed.port

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self._server.server_port}"

    def phase(self, value: str) -> None:
        with self._lock:
            self._phase = value

    def document_fault(self, value: DocumentFault, *, missing_ids: set[str] | None = None) -> None:
        selected = set() if missing_ids is None else set(missing_ids)
        if value == "missing" and not selected:
            raise ValueError("Missing document fault requires selected unavailable IDs")
        if any(re.fullmatch(r"[1-9][0-9]{0,18}", item) is None for item in selected):
            raise ValueError("Missing document IDs must be positive decimal strings")
        with self._lock:
            self._document_fault = value
            self._missing_ids = selected

    def hold_asset(
        self,
        asset_id: int,
        *,
        progress_interval: float | None = None,
        final_bytes: int = 1,
    ) -> HeldAsset:
        if asset_id <= 0:
            raise ValueError("Held asset ID must be positive")
        if progress_interval is not None and not 0.05 <= progress_interval <= 4.0:
            raise ValueError("Progress interval must be between 0.05 and 4 seconds")
        if not 1 <= final_bytes <= 65536 or (progress_interval is None and final_bytes != 1):
            raise ValueError("Progress final-byte reservation is invalid")
        hold = HeldAsset(asset_id, progress_interval, final_bytes)
        with self._lock:
            self._held_assets.setdefault(asset_id, []).append(hold)
            self._holds.append(hold)
        return hold

    def requests(self) -> list[dict[str, Any]]:
        with self._lock:
            return [
                {**record, "document_ids": list(record["document_ids"] or [])}
                for record in self._requests
            ]

    def _forward(
        self,
        method: str,
        path: str,
        payload: bytes,
        incoming_headers: Any,
    ) -> tuple[int, list[tuple[str, str]], bytes]:
        connection = http.client.HTTPConnection("127.0.0.1", self._endpoint, timeout=5)
        headers = {"Authorization": "Bearer " + self._capability, "Connection": "close"}
        for name in ("Content-Type", "Accept", "Range"):
            value = incoming_headers.get(name)
            if value is not None:
                headers[name] = value
        try:
            connection.request(method, path, payload if payload else None, headers)
            response = connection.getresponse()
            return response.status, response.getheaders(), response.read()
        finally:
            connection.close()

    @staticmethod
    def _partial(raw: bytes) -> bytes:
        value = json.loads(raw)
        documents = value.get("custom_emoji")
        assets = value.get("assets")
        if not isinstance(documents, list) or not isinstance(assets, list):
            raise ValueError("Selected bridge returned an invalid document envelope")
        retained = documents[:-1]
        required = {
            item[key] for item in retained for key in ("main_asset_id", "thumbnail_asset_id")
        }
        value["custom_emoji"] = retained
        value["assets"] = [item for item in assets if item.get("asset_id") in required]
        return json.dumps(value, separators=(",", ":")).encode()

    def __enter__(self) -> Self:
        self._thread.start()
        return self

    def __exit__(
        self,
        kind: type[BaseException] | None,
        value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        with self._lock:
            for hold in self._holds:
                hold.release.set()
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=5)
        if self._thread.is_alive():
            raise RuntimeError("Custom emoji fault server failed to stop")
