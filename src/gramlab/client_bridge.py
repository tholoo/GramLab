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
                try:
                    self.send_response(status)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.send_header("Cache-Control", "no-store")
                    # This HTTP/1.0 handler closes after every response. Android's
                    # pooled HTTP client must not try another command on that socket.
                    self.send_header("Connection", "close")
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)
                except (ConnectionError, TimeoutError):
                    # Committed commands remain recoverable when their response is lost.
                    pass

            def error(self, status: int, code: str, message: str) -> None:
                self.reply(
                    status,
                    {
                        "schema": 4
                        if self.path.startswith("/v4/")
                        else (
                            3
                            if self.path.startswith("/v3/")
                            else (2 if self.path.startswith("/v2/") else 1)
                        ),
                        "error": {"code": code, "message": message},
                    },
                )

            def do_GET(self) -> None:
                self.handle_operation()

            def do_POST(self) -> None:
                self.handle_operation()

            def command_parameters(
                self,
                required: set[str],
                optional: set[str],
                maximum: int,
            ) -> dict[str, Any]:
                lengths = self.headers.get_all("Content-Length", [])
                if len(lengths) != 1 or "Transfer-Encoding" in self.headers:
                    raise ValueError("Client command requires one bounded Content-Length")
                length = int(lengths[0])
                if not 0 < length <= maximum:
                    raise ValueError("Client command body exceeds the prototype limit")
                if self.headers.get_content_type() != "application/json":
                    raise ValueError("Client command requires application/json")
                raw = self.rfile.read(length)
                if len(raw) != length:
                    raise ValueError("Incomplete client command body")
                try:
                    body = json.loads(raw.decode("utf-8"), object_pairs_hook=_json_object)
                except RecursionError:
                    raise ValueError("Client command exceeds the JSON nesting limit") from None
                if (
                    not isinstance(body, dict)
                    or required - body.keys()
                    or body.keys() - required - optional
                ):
                    raise ValueError("Client command has missing or unsupported fields")
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
                            if url.path not in (
                                "/v1/callbacks",
                                "/v2/messages",
                                "/v3/callbacks",
                                "/v4/callbacks",
                                "/v4/messages",
                                "/v4/custom-emoji-documents",
                            ):
                                self.error(404, "unsupported", "Unknown client bridge operation")
                                return
                            if fields:
                                raise ValueError("Client command does not accept query parameters")
                            if url.path == "/v4/custom-emoji-documents":
                                parameters = self.command_parameters(
                                    {"custom_emoji_ids"}, set(), 16384
                                )
                                try:
                                    custom_emoji, assets = world.granted_custom_emoji(
                                        persona, parameters["custom_emoji_ids"]
                                    )
                                except LookupError:
                                    self.error(
                                        404, "document_unavailable", "Document is unavailable"
                                    )
                                    return
                                result = {
                                    "schema": 4,
                                    "world_id": world.world_id,
                                    "user_id": persona,
                                    "custom_emoji": custom_emoji,
                                    "assets": assets,
                                }
                            elif url.path in ("/v2/messages", "/v4/messages"):
                                version = 4 if url.path.startswith("/v4/") else 2
                                sent = world.send_client_message(
                                    user_id=persona,
                                    **self.command_parameters(
                                        {"request_id", "chat_id", "text"}, {"entities"}, 65536
                                    ),
                                    version=version,
                                )
                                result = {
                                    "schema": version,
                                    "world_id": world.world_id,
                                    "user_id": persona,
                                    "send": sent,
                                }
                                if version == 4:
                                    message = sent["message"]
                                    result["users"] = world._identity_dependencies(
                                        persona, [message]
                                    )
                                    emoji_ids = world._message_custom_emoji(message)
                                    descriptors = [
                                        world.custom_emoji_descriptor(i) for i in sorted(emoji_ids)
                                    ]
                                    result["custom_emoji"] = descriptors
                                    asset_ids = set(world._message_assets(message))
                                    for descriptor in descriptors:
                                        asset_ids.update(
                                            (
                                                descriptor["main_asset_id"],
                                                descriptor["thumbnail_asset_id"],
                                            )
                                        )
                                    result["assets"] = [
                                        world.asset_descriptor(i) for i in sorted(asset_ids)
                                    ]
                                    result["message_revision"] = world._connection.execute(
                                        "SELECT revision FROM message_revisions WHERE chat_id=? AND message_id=?",  # noqa: E501
                                        (message["chat_id"], message["id"]),
                                    ).fetchone()[0]
                            else:
                                version = (
                                    4
                                    if url.path == "/v4/callbacks"
                                    else (3 if url.path == "/v3/callbacks" else 1)
                                )
                                callback = world.create_callback(
                                    user_id=persona,
                                    version=version,
                                    **self.command_parameters(
                                        {"request_id", "chat_id", "message_id", "data"},
                                        set(),
                                        16384,
                                    ),
                                )
                                result = {
                                    "schema": version,
                                    "world_id": world.world_id,
                                    "user_id": persona,
                                    "callback": callback,
                                }
                                if version >= 3:
                                    result.update(
                                        world.callback_dependencies(
                                            persona, callback, version=version
                                        )
                                    )
                        elif url.path.startswith(
                            ("/v1/callbacks/", "/v3/callbacks/", "/v4/callbacks/")
                        ):
                            if fields:
                                raise ValueError("Callback does not accept query parameters")
                            callback = world.get_callback(
                                user_id=persona, callback_id=url.path.rsplit("/", 1)[1]
                            )
                            version = (
                                4
                                if url.path.startswith("/v4/")
                                else (3 if url.path.startswith("/v3/") else 1)
                            )
                            if version < 3 and world._message_assets(callback["message"]):
                                raise ValueError(
                                    "GRAMLAB_UNSUPPORTED: media requires client bridge v3"
                                )
                            if version < 3 and world._message_users(callback["message"]):
                                raise ValueError(
                                    "GRAMLAB_UNSUPPORTED: rich mentions require client bridge v3"
                                )
                            if version < 4 and world._message_custom_emoji(callback["message"]):
                                raise ValueError(
                                    "GRAMLAB_UNSUPPORTED: custom emoji requires client bridge v4"
                                )
                            result = {
                                "schema": version,
                                "world_id": world.world_id,
                                "user_id": persona,
                                "callback": callback,
                            }
                            if version >= 3:
                                result.update(
                                    world.callback_dependencies(persona, callback, version=version)
                                )
                        elif url.path in (
                            "/v1/snapshot",
                            "/v2/snapshot",
                            "/v3/snapshot",
                            "/v4/snapshot",
                        ):
                            if fields:
                                raise ValueError("Snapshot does not accept query parameters")
                            result = world.client_snapshot(persona, version=int(url.path[2]))
                        elif url.path in (
                            "/v1/events",
                            "/v2/changes",
                            "/v3/changes",
                            "/v4/changes",
                        ):
                            if "after" not in fields or fields.keys() - {"after", "limit"}:
                                raise ValueError("Events require after and optionally limit")
                            try:
                                after = int(fields["after"][0])
                                limit = int(fields.get("limit", ["100"])[0])
                            except ValueError:
                                raise ValueError(
                                    "Client cursor and limit must be integers"
                                ) from None
                            if url.path.endswith("/changes"):
                                result = world.client_changes(
                                    persona,
                                    after=after,
                                    limit=limit,
                                    version=4
                                    if url.path.startswith("/v4/")
                                    else (3 if url.path.startswith("/v3/") else 2),
                                )
                            else:
                                result = world.client_events(persona, after=after, limit=limit)
                        elif url.path.startswith(("/v3/assets/", "/v4/assets/")):
                            if (
                                fields
                                or "Range" in self.headers
                                or "Transfer-Encoding" in self.headers
                            ):
                                raise ValueError("Asset download parameters are unsupported")
                            try:
                                asset_id = int(url.path.rsplit("/", 1)[1])
                            except ValueError:
                                self.error(404, "asset_unavailable", "Asset is unavailable")
                                return
                            try:
                                descriptor, data = world.granted_asset(persona, asset_id)
                            except ValueError:
                                self.error(404, "asset_unavailable", "Asset is unavailable")
                                return
                            if url.path.startswith("/v3/") and descriptor["mime_type"] in (
                                "image/webp",
                                "video/webm",
                            ):
                                raise ValueError(
                                    "GRAMLAB_UNSUPPORTED: custom emoji requires client bridge v4"
                                )
                            self.send_response(200)
                            self.send_header("Content-Type", descriptor["mime_type"])
                            self.send_header("Content-Length", str(len(data)))
                            self.send_header("Cache-Control", "no-store")
                            self.send_header("Connection", "close")
                            self.end_headers()
                            self.wfile.write(data)
                            return
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
