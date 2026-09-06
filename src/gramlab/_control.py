"""Internal run-owner control for private scenario processes; not the Bot API."""

from __future__ import annotations

import json
import secrets
import socket
import threading
from collections.abc import Callable, Mapping
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import TracebackType
from typing import Any, Self

from gramlab.world import World


def _object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value = dict(pairs)
    if len(value) != len(pairs):
        raise ValueError("Repeated JSON members are unsupported")
    return value


def _parameters(value: dict[str, Any]) -> None:
    for name, item in value.items():
        if name in {"first_name", "text", "data", "request_id", "callback_id"}:
            valid = isinstance(item, str)
        elif name in {"username", "language_code"}:
            valid = item is None or isinstance(item, str)
        elif name == "is_bot":
            valid = type(item) is bool
        elif name in {
            "user_id",
            "bot_id",
            "chat_id",
            "sender_id",
            "message_id",
            "seconds",
            "after",
        }:
            valid = type(item) is int and 0 <= item < 2**63
        else:
            continue  # World method binding and entity/keyboard validation reject other shapes.
        if not valid:
            raise ValueError("Invalid world control parameter type or range")


class WorldControl:
    def __init__(
        self,
        directory: Path,
        *,
        bots: Mapping[str, int] | None = None,
        capture_chat: Callable[..., dict[str, Any]] | None = None,
        tap_inline_button: Callable[..., dict[str, Any]] | None = None,
        bot_status: Callable[..., dict[str, Any]] | None = None,
        stop_bot: Callable[..., dict[str, Any]] | None = None,
        start_bot: Callable[..., dict[str, Any]] | None = None,
    ) -> None:
        if [name for _, name in socket.if_nameindex()] != ["lo"]:
            raise RuntimeError("World control requires the isolated loopback-only runtime")
        directory = directory.absolute()
        with World.open(directory) as world:
            self.world_id = world.world_id
            named_bots = dict(bots or {})
            bot_ids = {user["id"] for user in world.snapshot()["users"] if user["is_bot"]}
            if any(type(value) is not int or value not in bot_ids for value in named_bots.values()):
                raise ValueError("Named bots must identify bots in this world")
        self.capability = "gramlab-control_" + secrets.token_urlsafe(32)
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def setup(self) -> None:
                super().setup()
                self.connection.settimeout(1)

            def log_message(self, format: str, *args: Any) -> None:
                pass

            def handle(self) -> None:
                try:
                    super().handle()
                except (ConnectionError, TimeoutError):
                    pass  # A partial or disconnected request must not produce access traces.

            def reply(self, status: int, value: dict[str, Any]) -> None:
                payload = json.dumps(value, ensure_ascii=True).encode()
                try:
                    self.send_response(status)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)
                except (ConnectionError, TimeoutError):
                    pass

            def error(self, status: int, code: str, message: str) -> None:
                self.reply(status, {"error": {"code": code, "message": message}})

            def do_POST(self) -> None:
                auth = self.headers.get_all("Authorization", [])
                expected = ("Bearer " + owner.capability).encode()
                if len(auth) != 1 or not secrets.compare_digest(auth[0].encode(), expected):
                    self.error(401, "unauthorized", "Run control capability required")
                    return
                if self.path != "/v1/world":
                    self.error(404, "unsupported", "Unknown world control endpoint")
                    return
                try:
                    lengths = self.headers.get_all("Content-Length", [])
                    if len(lengths) != 1 or "Transfer-Encoding" in self.headers:
                        raise ValueError("Control requires one bounded Content-Length")
                    if self.headers.get_content_type() != "application/json":
                        raise ValueError("Control requires application/json")
                    length = int(lengths[0])
                    if not 0 < length <= 65536:
                        raise ValueError("Control request exceeds the body limit")
                    raw = self.rfile.read(length)
                    if len(raw) != length:
                        raise ValueError("Incomplete world control body")
                    body = json.loads(raw.decode("utf-8"), object_pairs_hook=_object)
                    if not isinstance(body, dict) or body.keys() != {
                        "schema",
                        "world_id",
                        "operation",
                        "parameters",
                    }:
                        raise ValueError("Invalid world control envelope")
                    if type(body["schema"]) is not int or body["schema"] != 1:
                        raise ValueError("Unsupported world control schema")
                    if not isinstance(body["operation"], str) or not isinstance(
                        body["parameters"], dict
                    ):
                        raise ValueError("Invalid world control operation or parameters")
                    json.dumps(body, ensure_ascii=False, allow_nan=False).encode("utf-8")
                    _parameters(body["parameters"])
                    if body["world_id"] != owner.world_id:
                        self.error(409, "wrong_world", "Control request identifies another world")
                        return
                    with World.open(directory) as world:
                        if world.world_id != owner.world_id:
                            self.error(409, "wrong_world", "Control world has been replaced")
                            return
                        operations: dict[str, Callable[..., Any]] = {
                            "bots": lambda: dict(named_bots),
                            "create_user": world.create_user,
                            "open_private_chat": world.open_private_chat,
                            "send_message": world.send_message,
                            "advance_time": world.advance_time,
                            "history": world.history,
                            "snapshot": world.snapshot,
                            "events": world.events,
                            "create_callback": world.create_callback,
                            "get_callback": world.get_callback,
                        }
                        if capture_chat is not None:
                            operations["capture_chat"] = capture_chat
                        if tap_inline_button is not None:
                            operations["tap_inline_button"] = tap_inline_button
                        for name, lifecycle_operation in (
                            ("bot_status", bot_status),
                            ("stop_bot", stop_bot),
                            ("start_bot", start_bot),
                        ):
                            if lifecycle_operation is not None:
                                operations[name] = lifecycle_operation
                        operation = body["operation"]
                        if operation not in operations:
                            self.error(404, "unsupported", "Unknown world control operation")
                            return
                        result = operations[operation](**body["parameters"])
                    self.reply(200, {"schema": 1, "world_id": owner.world_id, "result": result})
                except (ValueError, UnicodeError) as error:
                    self.error(400, "invalid_request", str(error))
                except (TypeError, RecursionError):
                    self.error(
                        400, "invalid_request", "Invalid parameters or excessive JSON nesting"
                    )
                except RuntimeError:
                    self.error(500, "server_error", "World control operation failed")

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
        self._thread.join(timeout=5)
        if self._thread.is_alive():
            raise RuntimeError("World control server did not stop")
