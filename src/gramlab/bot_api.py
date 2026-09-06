"""Contained local Bot API prototype backed by the authoritative synthetic world.

Only the explicitly implemented method/parameter subset is accepted. This is not the
public server CLI; the trusted supervisor must launch it inside the runtime boundary.
"""

from __future__ import annotations

import json
import re
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import TracebackType
from typing import Any, Self
from urllib.parse import parse_qs, urlsplit

from gramlab.world import World


def _message(world: World, message: dict[str, Any]) -> dict[str, Any]:
    chat = world.get_chat(message["chat_id"])
    user = world.get_user(chat["user_id"])
    api_chat = {"id": user["id"], "type": "private", "first_name": user["first_name"]}
    if "username" in user:
        api_chat["username"] = user["username"]
    result = {
        "message_id": message["id"],
        "from": world.get_user(message["sender_id"]),
        "chat": api_chat,
        "date": message["date"],
        "text": message["text"],
    }
    for field in ("reply_markup", "edit_date"):
        if field in message:
            result[field] = message[field]
    return result


def _integer(value: Any, name: str) -> int:
    if isinstance(value, str) and len(value) <= 20 and re.fullmatch(r"-?[0-9]+", value):
        value = int(value)
    if type(value) is not int or not -(2**63) <= value < 2**63:
        raise ValueError(f"{name} must be a signed 64-bit integer")
    return value


def _update(world: World, update: dict[str, Any]) -> dict[str, Any]:
    if "message" in update:
        return {"update_id": update["update_id"], "message": _message(world, update["message"])}
    if "callback_query" in update:
        callback = update["callback_query"]
        return {
            "update_id": update["update_id"],
            "callback_query": {
                "id": callback["id"],
                "from": world.get_user(callback["user_id"]),
                "message": _message(world, callback["message"]),
                "chat_instance": callback["chat_instance"],
                "data": callback["data"],
            },
        }
    raise ValueError("GRAMLAB_UNSUPPORTED: stored bot update type")


def _json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = dict(pairs)
    if len(result) != len(pairs):
        raise ValueError("Repeated JSON members are unsupported")
    return result


def _dispatch(world: World, bot_id: int, method: str, parameters: dict[str, Any]) -> Any:
    supported = {
        "getme": set(),
        "getupdates": {"offset", "limit"},
        "sendmessage": {"chat_id", "text", "reply_markup"},
        "editmessagetext": {"chat_id", "message_id", "text", "reply_markup"},
        "answercallbackquery": {"callback_query_id", "text", "show_alert", "cache_time"},
    }
    if method not in supported:
        raise LookupError("GRAMLAB_UNSUPPORTED: Bot API method")
    if parameters.keys() - supported[method]:
        raise ValueError("GRAMLAB_UNSUPPORTED: Bot API parameters")
    if method == "getme":
        return world.get_user(bot_id)
    if method == "getupdates":
        offset = _integer(parameters.get("offset", 0), "offset")
        limit = _integer(parameters.get("limit", 100), "limit")
        if offset < 0:
            raise ValueError("GRAMLAB_UNSUPPORTED: negative update offsets")
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        return [
            _update(world, update)
            for update in world.poll_updates(bot_id, offset=offset, limit=limit)
        ]
    if method == "answercallbackquery":
        if "callback_query_id" not in parameters:
            raise ValueError("callback_query_id is required")
        world.answer_callback(
            bot_id=bot_id,
            callback_id=parameters["callback_query_id"],
            text=parameters.get("text", ""),
            show_alert=parameters.get("show_alert", False),
            cache_time=_integer(parameters.get("cache_time", 0), "cache_time"),
        )
        return True
    if "chat_id" not in parameters or "text" not in parameters:
        raise ValueError("chat_id and text are required")
    chat = world.private_chat_for_bot(bot_id, _integer(parameters["chat_id"], "chat_id"))
    if method == "editmessagetext":
        if "message_id" not in parameters:
            raise ValueError("message_id is required")
        return _message(
            world,
            world.edit_message(
                chat_id=chat["id"],
                message_id=_integer(parameters["message_id"], "message_id"),
                bot_id=bot_id,
                text=parameters["text"],
                reply_markup=parameters.get("reply_markup"),
            ),
        )
    return _message(
        world,
        world.send_message(
            chat_id=chat["id"],
            sender_id=bot_id,
            text=parameters["text"],
            reply_markup=parameters.get("reply_markup"),
        ),
    )


class BotAPIServer:
    def __init__(self, directory: Path) -> None:
        if [name for _, name in socket.if_nameindex()] != ["lo"]:
            raise RuntimeError("Bot API requires the isolated loopback-only runtime")
        directory = directory.absolute()

        class Handler(BaseHTTPRequestHandler):
            def setup(self) -> None:
                super().setup()
                self.connection.settimeout(5)

            def log_message(self, format: str, *args: Any) -> None:
                # Request paths contain capabilities. They must never enter access/error logs.
                pass

            def _reply(self, status: int, body: dict[str, Any]) -> None:
                payload = json.dumps(body, ensure_ascii=True).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def do_GET(self) -> None:
                self._handle()

            def do_POST(self) -> None:
                self._handle()

            def _handle(self) -> None:
                try:
                    url = urlsplit(self.path)
                    parts = url.path.split("/")
                    if len(parts) != 3 or not parts[1].startswith("bot"):
                        raise LookupError("Not Found")
                    with World.open(directory) as world:
                        bot_id = world.authenticate_bot(parts[1][3:])
                        if bot_id is None:
                            self._reply(
                                401, {"ok": False, "error_code": 401, "description": "Unauthorized"}
                            )
                            return
                        fields = parse_qs(url.query, keep_blank_values=True, max_num_fields=64)
                        if any(len(values) != 1 for values in fields.values()):
                            raise ValueError("Repeated request parameters are unsupported")
                        parameters: dict[str, Any] = {
                            key: values[0] for key, values in fields.items()
                        }
                        if self.command == "POST":
                            if "Transfer-Encoding" in self.headers:
                                raise ValueError("Transfer-Encoding is unsupported")
                            length = int(self.headers.get("Content-Length", "0"))
                            if not 0 <= length <= 65536:
                                raise ValueError("Request body exceeds the prototype limit")
                            raw = self.rfile.read(length)
                            if len(raw) != length:
                                raise ValueError("Incomplete request body")
                            content_type = self.headers.get_content_type()
                            if content_type != "application/json":
                                raise ValueError("GRAMLAB_UNSUPPORTED: request content type")
                            body = json.loads(raw, object_pairs_hook=_json_object)
                            if not isinstance(body, dict):
                                raise ValueError("Request body must be a JSON object")
                            if parameters.keys() & body.keys():
                                raise ValueError("Repeated request parameters are unsupported")
                            parameters.update(body)
                        result = _dispatch(world, bot_id, parts[2].lower(), parameters)
                        self._reply(200, {"ok": True, "result": result})
                except (ValueError, UnicodeError) as error:
                    self._reply(400, {"ok": False, "error_code": 400, "description": str(error)})
                except LookupError as error:
                    self._reply(404, {"ok": False, "error_code": 404, "description": str(error)})

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
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
            raise RuntimeError("Bot API server did not stop")
