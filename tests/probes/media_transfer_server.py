"""Controlled local HTTP faults for independent Android media acceptance.

This is a test server, not a simulator implementation. Server write completion is
not evidence of client acceptance; native results and original cache bytes must be
checked separately. Raw authorization and capability-bearing paths are never logged.
"""

from __future__ import annotations

import json
import socket
import threading
from collections.abc import Mapping
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import TracebackType
from typing import Any, Literal, Self

Fault = Literal["complete", "truncate", "corrupt", "redirect", "missing", "gated"]


@dataclass
class Transfer:
    """One planned attempt; explicit events control its scheduling without sleeps."""

    fault: Fault = "complete"
    started: threading.Event = field(default_factory=threading.Event)
    partial_sent: threading.Event = field(default_factory=threading.Event)
    release: threading.Event = field(default_factory=threading.Event)
    finished: threading.Event = field(default_factory=threading.Event)


class MediaTransferServer:
    def __init__(
        self,
        *,
        snapshot: Mapping[str, Any],
        assets: Mapping[int, tuple[str, bytes]],
        capability: str,
    ) -> None:
        if [name for _, name in socket.if_nameindex()] != ["lo"]:
            raise RuntimeError("Media fault server requires the isolated loopback runtime")
        self._snapshot = json.dumps(snapshot).encode()
        self._assets = dict(assets)
        self._plans: dict[int, list[Transfer]] = {}
        self._transfers: list[Transfer] = []
        self._requests: list[dict[str, Any]] = []
        self._lock = threading.Lock()
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def setup(self) -> None:
                super().setup()
                self.connection.settimeout(5)

            def log_message(self, format: str, *args: Any) -> None:
                pass

            def reply(
                self, status: int, mime: str, body: bytes, *, length: int | None = None
            ) -> None:
                self.send_response(status)
                self.send_header("Content-Type", mime)
                self.send_header("Content-Length", str(len(body) if length is None else length))
                self.send_header("Connection", "close")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)
                self.wfile.flush()

            def error(self, status: int, code: str, message: str) -> None:
                self.reply(
                    status,
                    "application/json",
                    json.dumps({"schema": 3, "error": {"code": code, "message": message}}).encode(),
                )

            def do_GET(self) -> None:
                try:
                    self.serve()
                except (ConnectionError, TimeoutError):
                    # An intentional client cancellation is observable through its
                    # own terminal result, not relabeled as successful delivery here.
                    pass

            def serve(self) -> None:
                if self.headers.get_all("Authorization", []) != [f"Bearer {capability}"]:
                    with owner._lock:
                        owner._requests.append({"operation": "unauthorized"})
                    self.error(401, "unauthorized", "Client capability required")
                    return
                if self.path == "/v3/snapshot":
                    with owner._lock:
                        payload = owner._snapshot
                        owner._requests.append({"operation": "snapshot"})
                    self.reply(200, "application/json", payload)
                    return
                suffix = self.path.removeprefix("/v3/assets/")
                if (
                    not self.path.startswith("/v3/assets/")
                    or not suffix.isascii()
                    or not suffix.isdecimal()
                ):
                    self.error(404, "unsupported", "Unknown fixture operation")
                    return
                asset_id = int(suffix)
                with owner._lock:
                    plans = owner._plans.get(asset_id, [])
                    transfer = plans.pop(0) if plans else Transfer()
                    if transfer not in owner._transfers:
                        owner._transfers.append(transfer)
                    owner._requests.append(
                        {"operation": "asset", "asset_id": asset_id, "fault": transfer.fault}
                    )
                    asset = owner._assets.get(asset_id)
                transfer.started.set()
                try:
                    if asset is None or transfer.fault == "missing":
                        self.error(404, "asset_unavailable", "Asset is unavailable")
                        return
                    if transfer.fault == "redirect":
                        self.send_response(302)
                        # A documentation-only address; a correct client never follows it.
                        self.send_header("Location", "http://192.0.2.1/forbidden-media")
                        self.send_header("Content-Length", "0")
                        self.send_header("Connection", "close")
                        self.end_headers()
                        return
                    mime, body = asset
                    if transfer.fault == "truncate":
                        self.reply(200, mime, body[: len(body) // 2], length=len(body))
                    elif transfer.fault == "corrupt":
                        changed = bytes([body[0] ^ 1]) + body[1:] if body else b"!"
                        self.reply(200, mime, changed)
                    elif transfer.fault == "gated":
                        split = len(body) // 2
                        self.reply(200, mime, body[:split], length=len(body))
                        transfer.partial_sent.set()
                        if not transfer.release.wait(timeout=20):
                            return
                        self.wfile.write(body[split:])
                        self.wfile.flush()
                    else:
                        self.reply(200, mime, body)
                finally:
                    transfer.finished.set()

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._server.daemon_threads = False
        self._thread = threading.Thread(target=self._server.serve_forever)

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self._server.server_port}"

    def plan(self, asset_id: int, fault: Fault) -> Transfer:
        transfer = Transfer(fault)
        with self._lock:
            self._plans.setdefault(asset_id, []).append(transfer)
            self._transfers.append(transfer)
        return transfer

    def snapshot(self, value: Mapping[str, Any]) -> None:
        payload = json.dumps(value).encode()
        with self._lock:
            self._snapshot = payload

    def requests(self) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(value) for value in self._requests]

    def __enter__(self) -> Self:
        self._thread.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        with self._lock:
            for transfer in self._transfers:
                transfer.release.set()
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=5)
        if self._thread.is_alive():
            raise RuntimeError("Media fault server failed to stop")
