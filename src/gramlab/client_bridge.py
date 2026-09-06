"""Authenticated semantic state and callback actions for the Android adapter.

No upstream TL classes or schema-generated objects cross into this implementation.
The trusted supervisor must run this service inside the independent process boundary.
"""

from __future__ import annotations

import json
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import TracebackType
from typing import Any, Self
from urllib.parse import parse_qs, urlsplit

from gramlab.world import World


def _json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = dict(pairs)
    if len(result) != len(pairs):
        raise ValueError("Repeated JSON members are unsupported")
    return result


class ClientBridge:
    def __init__(self, directory: Path) -> None:
        if [name for _, name in socket.if_nameindex()] != ["lo"]:
            raise RuntimeError("Client bridge requires the isolated loopback-only runtime")
        directory = directory.absolute()

        class Handler(BaseHTTPRequestHandler):
            def setup(self) -> None:
                super().setup()
                self.connection.settimeout(5)

            def log_message(self, format: str, *args: Any) -> None:
                # No raw request/header logging; capabilities never belong in artifacts.
                pass

            def reply(self, status: int, body: dict[str, Any]) -> None:
                payload = json.dumps(body).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def error(self, status: int, code: str, message: str) -> None:
                self.reply(status, {"schema": 1, "error": {"code": code, "message": message}})

            def do_GET(self) -> None:
                self.handle_operation()

            def do_POST(self) -> None:
                self.handle_operation()

            def callback_parameters(self) -> dict[str, Any]:
                lengths = self.headers.get_all("Content-Length", [])
                if len(lengths) != 1 or "Transfer-Encoding" in self.headers:
                    raise ValueError("Callback requires one bounded Content-Length")
                length = int(lengths[0])
                if not 0 < length <= 16384:
                    raise ValueError("Callback body exceeds the prototype limit")
                if self.headers.get_content_type() != "application/json":
                    raise ValueError("Callback requires application/json")
                raw = self.rfile.read(length)
                if len(raw) != length:
                    raise ValueError("Incomplete callback body")
                body = json.loads(raw.decode("utf-8"), object_pairs_hook=_json_object)
                if not isinstance(body, dict) or body.keys() != {
                    "request_id",
                    "chat_id",
                    "message_id",
                    "data",
                }:
                    raise ValueError(
                        "Callback requires only request_id, chat_id, message_id and data"
                    )
                return body

            def handle_operation(self) -> None:
                authorization = self.headers.get_all("Authorization", [])
                if len(authorization) != 1:
                    self.error(401, "unauthorized", "Client capability required")
                    return
                scheme, _, token = authorization[0].partition(" ")
                with World.open(directory) as world:
                    persona = (
                        world.authenticate_client(token) if scheme.lower() == "bearer" else None
                    )
                    if persona is None:
                        self.error(401, "unauthorized", "Client capability required")
                        return
                    try:
                        url = urlsplit(self.path)
                        fields = parse_qs(url.query, keep_blank_values=True, max_num_fields=4)
                        if any(len(values) != 1 for values in fields.values()):
                            raise ValueError("Repeated client parameters are unsupported")
                        if self.command == "POST":
                            if url.path != "/v1/callbacks":
                                self.error(404, "unsupported", "Unknown client bridge operation")
                                return
                            if fields:
                                raise ValueError("Callback does not accept query parameters")
                            callback = world.create_callback(
                                user_id=persona, **self.callback_parameters()
                            )
                            result = {
                                "schema": 1,
                                "world_id": world.world_id,
                                "user_id": persona,
                                "callback": callback,
                            }
                        elif url.path.startswith("/v1/callbacks/"):
                            if fields:
                                raise ValueError("Callback does not accept query parameters")
                            callback = world.get_callback(
                                user_id=persona, callback_id=url.path.removeprefix("/v1/callbacks/")
                            )
                            result = {
                                "schema": 1,
                                "world_id": world.world_id,
                                "user_id": persona,
                                "callback": callback,
                            }
                        elif url.path == "/v1/snapshot":
                            if fields:
                                raise ValueError("Snapshot does not accept query parameters")
                            result = world.client_snapshot(persona)
                        elif url.path == "/v1/events":
                            if "after" not in fields or fields.keys() - {"after", "limit"}:
                                raise ValueError("Events require after and optionally limit")
                            try:
                                after = int(fields["after"][0])
                                limit = int(fields.get("limit", ["100"])[0])
                            except ValueError:
                                raise ValueError(
                                    "Client cursor and limit must be integers"
                                ) from None
                            result = world.client_events(persona, after=after, limit=limit)
                        else:
                            self.error(404, "unsupported", "Unknown client bridge operation")
                            return
                        self.reply(200, result)
                    except ValueError as error:
                        self.error(400, "invalid_request", str(error))

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._server.daemon_threads = False
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self._server.server_port}"

    def __enter__(self) -> Self:
        self._thread.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=10)
        if self._thread.is_alive():
            raise RuntimeError("Client bridge did not stop")
