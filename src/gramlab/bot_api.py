"""Contained local Bot API prototype backed by the authoritative synthetic world.

Only the explicitly implemented method/parameter subset is accepted. This is not the
public server CLI; the trusted supervisor must launch it inside the runtime boundary.
"""

from __future__ import annotations

import json
import re
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import TracebackType
from typing import Any, Self
from urllib.parse import parse_qs, urlsplit

from gramlab.world import World, update_selection


def _public_rich(world: World, bot_id: int, value: Any) -> Any:
    if isinstance(value, list):
        return [_public_rich(world, bot_id, item) for item in value]
    if isinstance(value, dict):
        if value.get("type") == "photo" and "asset_id" in value:
            result: dict[str, Any] = {
                "type": "photo",
                "photo": [world.photo_size(bot_id, int(value["asset_id"]))],
            }
            if "caption" in value:
                result["caption"] = _public_rich(world, bot_id, value["caption"])
            return result
        return {key: _public_rich(world, bot_id, item) for key, item in value.items()}
    return value


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
    }
    if "rich_message" in message:
        result["rich_message"] = _public_rich(world, int(chat["bot_id"]), message["rich_message"])
    elif "photo" in message:
        result["photo"] = [world.photo_size(int(chat["bot_id"]), message["photo"]["asset_id"])]
        for field in ("caption", "caption_entities"):
            if field in message:
                result[field] = message[field]
    else:
        result["text"] = message["text"]
    for field in ("reply_markup", "edit_date", "entities"):
        if field in message:
            result[field] = message[field]
    return result


def _integer(value: Any, name: str) -> int:
    if isinstance(value, str) and len(value) <= 20 and re.fullmatch(r"-?[0-9]+", value):
        value = int(value)
    if type(value) is not int or not -(2**63) <= value < 2**63:
        raise ValueError(f"{name} must be a signed 64-bit integer")
    return value


def _boolean(value: Any, name: str) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"true", "yes", "1"}
    if type(value) is not bool:
        raise ValueError(f"{name} must be a Boolean or text")
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


def _form_parameters(value: str) -> dict[str, Any]:
    fields = parse_qs(value, keep_blank_values=True, max_num_fields=64, errors="strict")
    if any(len(values) != 1 for values in fields.values()):
        raise ValueError("Repeated request parameters are unsupported")
    return {key: values[0] for key, values in fields.items()}


def _json_value(value: str | bytes) -> Any:
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="strict")
    try:
        return json.loads(value, object_pairs_hook=_json_object)
    except RecursionError:
        raise ValueError("Request JSON exceeds the nesting limit") from None


class _PollInterrupted(Exception):
    def __init__(self, status: int, description: str) -> None:
        super().__init__(description)
        self.status = status


class _Polling:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._waiting: dict[int, threading.Event] = {}
        self._stopping = False

    def stop(self) -> None:
        with self._lock:
            self._stopping = True
            for pending in self._waiting.values():
                pending.set()

    def get_updates(
        self,
        world: World,
        bot_id: int,
        offset: int,
        limit: int,
        timeout: int,
        allowed_updates: list[str] | None,
    ) -> list[dict[str, Any]]:
        cancelled = threading.Event()
        deadline = time.monotonic() + timeout
        with self._lock:
            if previous := self._waiting.get(bot_id):
                previous.set()
            self._waiting[bot_id] = cancelled
        try:
            while True:
                with self._lock:
                    if self._stopping:
                        raise _PollInterrupted(503, "GRAMLAB_SHUTDOWN: Bot API server is stopping")
                    if cancelled.is_set():
                        raise _PollInterrupted(
                            409,
                            "Conflict: terminated by other getUpdates request; "
                            "make sure that only one bot instance is running",
                        )
                    # Serialize ownership with the short acknowledgment transaction. A replaced
                    # request must never acknowledge state after its successor starts polling.
                    updates = world.poll_updates(
                        bot_id, offset=offset, limit=limit, allowed_updates=allowed_updates
                    )
                    # Selection and negative-tail recovery belong to the initial read. Repeating
                    # either during a wait can overwrite a later setting or discard new arrivals.
                    allowed_updates = None
                    offset = max(0, offset)
                    remaining = deadline - time.monotonic()
                    if updates or remaining <= 0:
                        return [_update(world, update) for update in updates]
                # Writers may live in another process; reread committed world state without
                # holding a database transaction or the ownership lock during the wait.
                cancelled.wait(min(0.05, remaining))
        finally:
            with self._lock:
                if self._waiting.get(bot_id) is cancelled:
                    del self._waiting[bot_id]


def _dispatch(
    world: World,
    bot_id: int,
    method: str,
    parameters: dict[str, Any],
    polling: _Polling,
    uploads: dict[str, bytes] | None = None,
) -> Any:
    supported = {
        "getme": set(),
        "getupdates": {"offset", "limit", "timeout", "allowed_updates"},
        "deletewebhook": {"drop_pending_updates"},
        "sendmessage": {"chat_id", "text", "reply_markup", "entities"},
        "sendrichmessage": {"chat_id", "rich_message", "reply_markup"},
        "sendphoto": {"chat_id", "photo", "caption", "caption_entities", "reply_markup"},
        "getfile": {"file_id"},
        "editmessagetext": {
            "chat_id",
            "message_id",
            "text",
            "reply_markup",
            "entities",
            "rich_message",
        },
        "answercallbackquery": {"callback_query_id", "text", "show_alert", "cache_time"},
    }
    if method not in supported:
        raise LookupError("GRAMLAB_UNSUPPORTED: Bot API method")
    if parameters.keys() - supported[method]:
        raise ValueError("GRAMLAB_UNSUPPORTED: Bot API parameters")
    for name in ("reply_markup", "entities", "caption_entities", "rich_message"):
        if isinstance(parameters.get(name), str):
            parameters[name] = _json_value(parameters[name])
    if method == "getme":
        return world.get_user(bot_id)
    if method == "getfile":
        if set(parameters) != {"file_id"} or not isinstance(parameters["file_id"], str):
            raise ValueError("file_id is required")
        info, _ = world.bot_file(bot_id, parameters["file_id"])
        info.pop("mime_type")
        return info
    if method == "deletewebhook":
        if "drop_pending_updates" in parameters and _boolean(
            parameters["drop_pending_updates"], "drop_pending_updates"
        ):
            world.discard_pending_updates(bot_id)
        return True
    if method == "getupdates":
        offset = _integer(parameters.get("offset", 0), "offset")
        limit = _integer(parameters.get("limit", 100), "limit")
        timeout = min(50, max(0, _integer(parameters.get("timeout", 0), "timeout")))
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        selection = parameters.get("allowed_updates")
        if isinstance(selection, str):
            try:
                selection = _json_value(selection)
            except ValueError:
                selection = None
        return polling.get_updates(
            world, bot_id, offset, limit, timeout, update_selection(selection)
        )
    if method == "answercallbackquery":
        if "callback_query_id" not in parameters:
            raise ValueError("callback_query_id is required")
        show_alert = parameters.get("show_alert", False)
        if isinstance(show_alert, str):
            show_alert = show_alert.strip().lower() in {"true", "yes", "1"}
        world.answer_callback(
            bot_id=bot_id,
            callback_id=parameters["callback_query_id"],
            text=parameters.get("text", ""),
            show_alert=show_alert,
            cache_time=_integer(parameters.get("cache_time", 0), "cache_time"),
        )
        return True
    if "chat_id" not in parameters:
        raise ValueError("chat_id is required")
    if method == "sendphoto":
        if "chat_id" not in parameters or "photo" not in parameters:
            raise ValueError("chat_id and photo are required")
        chat = world.private_chat_for_bot(bot_id, _integer(parameters["chat_id"], "chat_id"))
        return _message(
            world,
            world.send_photo(
                chat_id=chat["id"],
                sender_id=bot_id,
                photo={"type": "photo", "media": parameters["photo"]},
                uploads=uploads,
                caption=parameters.get("caption"),
                caption_entities=parameters.get("caption_entities"),
                reply_markup=parameters.get("reply_markup"),
            ),
        )
    if "rich_message" in parameters:
        if parameters["rich_message"] is None:
            raise ValueError("rich_message must be an object")
        if "text" in parameters or "entities" in parameters:
            raise ValueError("GRAMLAB_UNSUPPORTED: combined text and rich content")
    elif method == "sendrichmessage" or "text" not in parameters:
        raise ValueError("rich_message or text is required")
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
                text=parameters.get("text"),
                rich_message=parameters.get("rich_message"),
                reply_markup=parameters.get("reply_markup"),
                uploads=uploads,
                entities=parameters.get("entities"),
            ),
        )
    if method == "sendrichmessage":
        return _message(
            world,
            world.send_rich_message(
                chat_id=chat["id"],
                sender_id=bot_id,
                rich_message=parameters["rich_message"],
                reply_markup=parameters.get("reply_markup"),
                uploads=uploads,
            ),
        )
    return _message(
        world,
        world.send_message(
            chat_id=chat["id"],
            sender_id=bot_id,
            text=parameters["text"],
            reply_markup=parameters.get("reply_markup"),
            entities=parameters.get("entities"),
        ),
    )


def _multipart(raw: bytes, content_type: str) -> tuple[dict[str, Any], dict[str, bytes]]:
    match = re.fullmatch(
        r'multipart/form-data;\s*boundary=(?:"([^"\r\n]+)"|([^;\s]+))', content_type
    )
    if match is None:
        raise ValueError("Malformed multipart Content-Type")
    boundary = (match.group(1) or match.group(2)).encode("ascii", errors="strict")
    if not 1 <= len(boundary) <= 70:
        raise ValueError("Malformed multipart boundary")
    delimiter = b"--" + boundary
    if not raw.startswith(delimiter + b"\r\n") or not raw.endswith(b"\r\n" + delimiter + b"--\r\n"):
        raise ValueError("Malformed multipart body")
    middle = raw[len(delimiter) + 2 : -(len(delimiter) + 6)]
    chunks = middle.split(b"\r\n" + delimiter + b"\r\n")
    if len(chunks) > 64:
        raise ValueError("Multipart request exceeds 64 parts")
    fields: dict[str, Any] = {}
    uploads: dict[str, bytes] = {}
    text_size = upload_size = 0
    for chunk in chunks:
        if b"\r\n\r\n" not in chunk:
            raise ValueError("Malformed multipart part")
        header_bytes, payload = chunk.split(b"\r\n\r\n", 1)
        if b"\r\n " in header_bytes or b"\r\n\t" in header_bytes:
            raise ValueError("Malformed multipart headers")
        headers: dict[str, str] = {}
        for line in header_bytes.split(b"\r\n"):
            header_name, separator, value = line.partition(b":")
            key = header_name.decode("ascii", errors="strict").lower()
            if not separator or key in headers:
                raise ValueError("Malformed multipart headers")
            headers[key] = value.decode("utf-8", errors="strict").strip()
        disposition = headers.get("content-disposition", "")
        if headers.get("content-type", "").lower().startswith("multipart/"):
            raise ValueError("Nested multipart content is unsupported")
        named = re.fullmatch(
            r'form-data;\s*name="([^"\r\n]+)"(?:;\s*filename="([^"\r\n]*)")?', disposition
        )
        if named is None or set(headers) - {"content-disposition", "content-type"}:
            raise ValueError("Malformed multipart part headers")
        field_name, filename = named.groups()
        if field_name in fields or field_name in uploads:
            raise ValueError("Repeated request parameters are unsupported")
        if filename is not None:
            upload_size += len(payload)
            if upload_size > 20_000_000:
                raise ValueError("Uploaded file data exceeds the request limit")
            uploads[field_name] = payload
        else:
            text_size += len(payload)
            if text_size > 65_536:
                raise ValueError("Multipart text fields exceed the request limit")
            fields[field_name] = payload.decode("utf-8", errors="strict")
    return fields, uploads


class BotAPIServer:
    def __init__(self, directory: Path) -> None:
        if [name for _, name in socket.if_nameindex()] != ["lo"]:
            raise RuntimeError("Bot API requires the isolated loopback-only runtime")
        directory = directory.absolute()
        polling = _Polling()
        reading: set[socket.socket] = set()
        reading_lock = threading.Lock()
        closing = threading.Event()

        class Handler(BaseHTTPRequestHandler):
            def setup(self) -> None:
                super().setup()
                self.connection.settimeout(5)
                with reading_lock:
                    if closing.is_set():
                        self.connection.shutdown(socket.SHUT_RDWR)
                    else:
                        reading.add(self.connection)

            def handle(self) -> None:
                try:
                    super().handle()
                except (ConnectionError, TimeoutError):
                    pass  # Disconnect or shutdown during HTTP header/body input.

            def finish(self) -> None:
                try:
                    super().finish()
                finally:
                    with reading_lock:
                        reading.discard(self.connection)

            def log_message(self, format: str, *args: Any) -> None:
                # Request paths contain capabilities. They must never enter access/error logs.
                pass

            def _reply(self, status: int, body: dict[str, Any]) -> None:
                payload = json.dumps(body, ensure_ascii=True).encode("utf-8")
                try:
                    self.send_response(status)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)
                except (ConnectionError, TimeoutError):
                    # A disconnected consumer can retry its offset. Writing a response never
                    # confirms returned updates, and disconnects must not produce access traces.
                    pass

            def do_GET(self) -> None:
                self._handle()

            def do_POST(self) -> None:
                self._handle()

            def _handle(self) -> None:
                try:
                    url = urlsplit(self.path)
                    parts = url.path.split("/")
                    if len(parts) == 5 and parts[1] == "file" and parts[2].startswith("bot"):
                        if self.command != "GET" or url.query or parts[3] != "photos":
                            raise LookupError("Not Found")
                        with World.open(directory) as world:
                            bot_id = world.authenticate_bot(parts[2][3:])
                            if bot_id is None:
                                self._reply(
                                    401,
                                    {"ok": False, "error_code": 401, "description": "Unauthorized"},
                                )
                                return
                            file_id, dot, _extension = parts[4].rpartition(".")
                            if not dot:
                                raise LookupError("Not Found")
                            info, data = world.bot_file(bot_id, file_id)
                            if info["file_path"] != f"photos/{parts[4]}":
                                raise LookupError("Not Found")
                            self.send_response(200)
                            self.send_header("Content-Type", info["mime_type"])
                            self.send_header("Content-Length", str(len(data)))
                            self.send_header("Cache-Control", "no-store")
                            self.end_headers()
                            self.wfile.write(data)
                        return
                    if len(parts) != 3 or not parts[1].startswith("bot"):
                        raise LookupError("Not Found")
                    with World.open(directory) as world:
                        bot_id = world.authenticate_bot(parts[1][3:])
                        if bot_id is None:
                            self._reply(
                                401, {"ok": False, "error_code": 401, "description": "Unauthorized"}
                            )
                            return
                        parameters = _form_parameters(url.query)
                        uploads: dict[str, bytes] = {}
                        if self.command == "POST":
                            lengths = self.headers.get_all("Content-Length", [])
                            if len(lengths) != 1 or "Transfer-Encoding" in self.headers:
                                raise ValueError("Request requires one bounded Content-Length")
                            length = int(lengths[0])
                            content_type_header = self.headers.get("Content-Type", "")
                            multipart = content_type_header.lower().startswith(
                                "multipart/form-data"
                            )
                            maximum = 20_200_000 if multipart else 65_536
                            if not 0 <= length <= maximum:
                                raise ValueError("Request body exceeds the prototype limit")
                            raw = self.rfile.read(length)
                            if len(raw) != length:
                                raise ValueError("Incomplete request body")
                            content_type = self.headers.get_content_type()
                            if not raw and "Content-Type" not in self.headers:
                                body = {}
                            elif content_type == "application/json":
                                body = _json_value(raw)
                                if not isinstance(body, dict):
                                    raise ValueError("Request body must be a JSON object")
                            elif content_type == "application/x-www-form-urlencoded":
                                body = _form_parameters(raw.decode("utf-8", errors="strict"))
                            elif content_type == "multipart/form-data":
                                body, uploads = _multipart(raw, content_type_header)
                            else:
                                raise ValueError("GRAMLAB_UNSUPPORTED: request content type")
                            if parameters.keys() & body.keys():
                                raise ValueError("Repeated request parameters are unsupported")
                            if parameters.keys() & uploads.keys() or body.keys() & uploads.keys():
                                raise ValueError("Repeated request parameters are unsupported")
                            parameters.update(body)
                        if parts[2].lower() == "sendphoto" and "photo" in uploads:
                            parameters["photo"] = "attach://photo"
                        with reading_lock:
                            reading.discard(self.connection)
                            if closing.is_set():
                                raise _PollInterrupted(
                                    503, "GRAMLAB_SHUTDOWN: Bot API server is stopping"
                                )
                        result = _dispatch(
                            world, bot_id, parts[2].lower(), parameters, polling, uploads
                        )
                        self._reply(200, {"ok": True, "result": result})
                except _PollInterrupted as error:
                    self._reply(
                        error.status,
                        {"ok": False, "error_code": error.status, "description": str(error)},
                    )
                except (ValueError, UnicodeError) as error:
                    self._reply(400, {"ok": False, "error_code": 400, "description": str(error)})
                except LookupError as error:
                    self._reply(404, {"ok": False, "error_code": 404, "description": str(error)})

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._server.daemon_threads = False
        self._polling = polling
        self._reading = reading
        self._reading_lock = reading_lock
        self._closing = closing
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
        self._polling.stop()
        with self._reading_lock:
            self._closing.set()
            for connection in self._reading:
                try:
                    connection.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass  # The consumer already closed the connection.
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=10)
        if self._thread.is_alive():
            raise RuntimeError("Bot API server did not stop")
