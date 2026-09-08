"""Experimental Python world control for scenario code inside the private runtime."""

from __future__ import annotations

import base64
import http.client
import json
import math
import os
import re
import socket
from typing import Any, Self, cast
from urllib.parse import urlsplit
from uuid import UUID

_READS = {"snapshot", "history", "events", "get_callback", "bots", "bot_status"}
_REJECTIONS = {400: "invalid_request", 401: "unauthorized", 404: "unsupported", 409: "wrong_world"}


def _object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value = dict(pairs)
    if len(value) != len(pairs):
        raise ValueError("Repeated response members")
    return value


class ScenarioError(RuntimeError):
    """A control failure with an explicit indication of possible committed effects."""

    def __init__(
        self,
        message: str,
        *,
        operation: str,
        code: str,
        outcome_uncertain: bool = False,
        status: int | None = None,
    ) -> None:
        super().__init__(message)
        self.operation = operation
        self.code = code
        self.outcome_uncertain = outcome_uncertain
        self.status = status


class Scenario:
    def __init__(
        self, endpoint: str, *, capability: str, world_id: str, timeout: float = 5
    ) -> None:
        try:
            if not isinstance(endpoint, str):
                raise ValueError
            url = urlsplit(endpoint)
            port = url.port
        except ValueError:
            raise ValueError("Scenario requires an explicit local control origin") from None
        if (
            url.scheme != "http"
            or url.hostname != "127.0.0.1"
            or port is None
            or not 1 <= port <= 65535
            or url.username is not None
            or url.password is not None
            or url.path not in ("", "/")
            or url.query
            or url.fragment
            or any(character.isspace() for character in endpoint)
        ):
            raise ValueError("Scenario requires an explicit local control origin")
        if [name for _, name in socket.if_nameindex()] != ["lo"]:
            raise RuntimeError("Scenario requires the isolated loopback-only runtime")
        if (
            not isinstance(capability, str)
            or re.fullmatch(r"gramlab-control_[A-Za-z0-9_-]{43}", capability) is None
        ):
            raise ValueError("Scenario requires a run control capability")
        try:
            if not isinstance(world_id, str) or str(UUID(world_id)) != world_id:
                raise ValueError
        except ValueError:
            raise ValueError("Scenario requires a canonical world identity") from None
        if type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("Scenario timeout must be finite and positive")
        self._port = port
        self._capability = capability
        self._world_id = world_id
        self._timeout = timeout

    @classmethod
    def from_environment(cls, *, timeout: float = 5) -> Self:
        try:
            endpoint = os.environ["GRAMLAB_CONTROL_ENDPOINT"]
            capability = os.environ["GRAMLAB_CONTROL_CAPABILITY"]
            world_id = os.environ["GRAMLAB_WORLD_ID"]
        except KeyError:
            raise ValueError("Missing scenario control configuration") from None
        return cls(endpoint, capability=capability, world_id=world_id, timeout=timeout)

    def _request(
        self, operation: str, parameters: dict[str, Any], *, timeout: float | None = None
    ) -> Any:
        registration = operation == "register_custom_emoji"
        try:
            payload = json.dumps(
                {
                    "schema": 1,
                    "world_id": self._world_id,
                    "operation": operation,
                    "parameters": parameters,
                },
                ensure_ascii=False,
                allow_nan=False,
            ).encode("utf-8")
            if len(payload) > (1024 * 1024 if registration else 65536):
                raise ValueError
        except (TypeError, ValueError, RecursionError):
            raise ScenarioError(
                "Invalid or oversized scenario command; nothing was sent",
                operation=operation,
                code="invalid_request",
            ) from None
        connection = http.client.HTTPConnection(
            "127.0.0.1", self._port, timeout=self._timeout if timeout is None else timeout
        )
        attempted = False
        status = None
        try:
            connection.connect()
            attempted = True
            connection.request(
                "POST",
                "/v1/custom-emoji" if registration else "/v1/world",
                payload,
                {
                    "Content-Type": "application/json",
                    "Authorization": "Bearer " + self._capability,
                },
            )
            response = connection.getresponse()
            status = response.status
            if status >= 500:
                raise ScenarioError(
                    "World control failed while handling the operation",
                    operation=operation,
                    code="server_error",
                    status=status,
                    outcome_uncertain=operation not in _READS,
                )
            if status != 200 and status not in _REJECTIONS:
                raise ValueError("Unexpected HTTP status")
            lengths = response.headers.get_all("Content-Length", [])
            if len(lengths) != 1 or "Transfer-Encoding" in response.headers:
                raise ValueError("Invalid response framing")
            length = int(lengths[0])
            if not 0 < length <= 16 * 1024 * 1024:
                raise ValueError("Invalid response size")
            if response.headers.get_content_type() != "application/json":
                raise ValueError("Invalid response content type")
            raw = response.read(length)
            if len(raw) != length:
                raise ValueError("Incomplete response")
            body = json.loads(raw.decode("utf-8"), object_pairs_hook=_object)
            json.dumps(body, ensure_ascii=False, allow_nan=False).encode("utf-8")
            if not isinstance(body, dict):
                raise ValueError("Invalid response envelope")
            if status in _REJECTIONS:
                error = body.get("error")
                if (
                    body.keys() != {"error"}
                    or not isinstance(error, dict)
                    or error.keys() != {"code", "message"}
                    or error["code"] != _REJECTIONS[status]
                    or not isinstance(error["message"], str)
                ):
                    raise ValueError("Invalid rejection response")
                raise ScenarioError(
                    "World control rejected the operation",
                    operation=operation,
                    code=_REJECTIONS[status],
                    status=status,
                )
            if (
                body.keys() != {"schema", "world_id", "result"}
                or type(body["schema"]) is not int
                or body["schema"] != 1
                or body["world_id"] != self._world_id
            ):
                raise ValueError("Invalid response identity")
            result = body["result"]
            expected = (
                int
                if operation == "advance_time"
                else list
                if operation in {"history", "events"}
                else dict
            )
            if type(result) is not expected or (
                isinstance(result, list) and any(not isinstance(item, dict) for item in result)
            ):
                raise ValueError("Invalid response result shape")
            return result
        except (ValueError, UnicodeError, RecursionError):
            raise ScenarioError(
                "World control returned an invalid response; no automatic retry was made",
                operation=operation,
                code="invalid_response",
                status=status,
                outcome_uncertain=attempted and operation not in _READS,
            ) from None
        except (OSError, http.client.HTTPException):
            raise ScenarioError(
                "World control connection failed; no automatic retry was made",
                operation=operation,
                code="transport_error",
                outcome_uncertain=attempted and operation not in _READS,
                status=status,
            ) from None
        finally:
            connection.close()

    def create_user(
        self,
        *,
        first_name: str,
        is_bot: bool = False,
        username: str | None = None,
        language_code: str | None = None,
    ) -> dict[str, Any]:
        return cast(
            dict[str, Any],
            self._request(
                "create_user",
                {
                    "first_name": first_name,
                    "is_bot": is_bot,
                    "username": username,
                    "language_code": language_code,
                },
            ),
        )

    def open_private_chat(self, *, user_id: int, bot_id: int) -> dict[str, Any]:
        return cast(
            dict[str, Any],
            self._request("open_private_chat", {"user_id": user_id, "bot_id": bot_id}),
        )

    def register_custom_emoji(
        self,
        *,
        request_id: str,
        main: bytes,
        thumbnail: bytes,
        fallback: str,
        custom_emoji_id: int | str | None = None,
        free: bool = True,
        needs_repainting: bool = False,
        timeout: float = 30,
    ) -> dict[str, Any]:
        """Register immutable local bytes; repeat the request ID after an uncertain response."""
        if (
            not isinstance(main, bytes)
            or not isinstance(thumbnail, bytes)
            or not 0 < len(main) <= 512 * 1024
            or not 0 < len(thumbnail) <= 128 * 1024
            or type(timeout) not in (int, float)
            or not math.isfinite(timeout)
            or timeout <= 0
        ):
            raise ScenarioError(
                "Invalid custom emoji media or timeout; nothing was sent",
                operation="register_custom_emoji",
                code="invalid_request",
            )
        return cast(
            dict[str, Any],
            self._request(
                "register_custom_emoji",
                {
                    "request_id": request_id,
                    "main": base64.b64encode(main).decode("ascii"),
                    "thumbnail": base64.b64encode(thumbnail).decode("ascii"),
                    "fallback": fallback,
                    "custom_emoji_id": custom_emoji_id,
                    "free": free,
                    "needs_repainting": needs_repainting,
                },
                timeout=timeout,
            ),
        )

    def send_message(
        self,
        *,
        chat_id: int,
        sender_id: int,
        text: str,
        reply_markup: dict[str, Any] | None = None,
        entities: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        return cast(
            dict[str, Any],
            self._request(
                "send_message",
                {
                    "chat_id": chat_id,
                    "sender_id": sender_id,
                    "text": text,
                    "reply_markup": reply_markup,
                    "entities": entities,
                },
            ),
        )

    def advance_time(self, seconds: int) -> int:
        return cast(int, self._request("advance_time", {"seconds": seconds}))

    def history(self, chat_id: int) -> list[dict[str, Any]]:
        return cast(list[dict[str, Any]], self._request("history", {"chat_id": chat_id}))

    def snapshot(self) -> dict[str, Any]:
        return cast(dict[str, Any], self._request("snapshot", {}))

    def bots(self) -> dict[str, int]:
        """Return the manifest's bot aliases and their world identities."""
        return cast(dict[str, int], self._request("bots", {}))

    def bot_status(self, name: str) -> dict[str, Any]:
        """Observe one configured bot's current process generation."""
        return cast(dict[str, Any], self._request("bot_status", {"name": name}))

    def stop_bot(self, name: str, *, generation: int) -> dict[str, Any]:
        """Hard-stop the expected generation, including its detached descendants."""
        return cast(
            dict[str, Any],
            self._request(
                "stop_bot",
                {"name": name, "generation": generation},
                timeout=30,
            ),
        )

    def start_bot(self, name: str, *, generation: int) -> dict[str, Any]:
        """Start a successor to a stopped generation, preserving private bot files."""
        return cast(
            dict[str, Any],
            self._request(
                "start_bot",
                {"name": name, "generation": generation},
                timeout=30,
            ),
        )

    def capture_chat(
        self, *, chat_id: int, label: str, contains: list[str], timeout: float = 180
    ) -> dict[str, Any]:
        """Retain chat evidence, with original screenshots when Android mode is selected."""
        if type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("Capture timeout must be finite and positive")
        return cast(
            dict[str, Any],
            self._request(
                "capture_chat",
                {"chat_id": chat_id, "label": label, "contains": contains},
                timeout=timeout,
            ),
        )

    def tap_inline_button(
        self, *, chat_id: int, message_id: int, row: int, column: int, timeout: float = 180
    ) -> dict[str, Any]:
        """Select a current keyboard cell, using actual native input in Android mode.

        Each call is a new action. A lost response or backend failure is uncertain;
        callers must inspect world events before deciding whether another action is appropriate.
        """
        if type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("Inline input timeout must be finite and positive")
        return cast(
            dict[str, Any],
            self._request(
                "tap_inline_button",
                {"chat_id": chat_id, "message_id": message_id, "row": row, "column": column},
                timeout=timeout,
            ),
        )

    def rich_buttons(
        self, *, chat_id: int, message_id: int, timeout: float = 180
    ) -> dict[str, Any]:
        """Issue canonical targets bound to this run, message revision and client lifetime.

        A fresh observation allocates new IDs. A lost response may consume observation capacity
        or change the selected native client lifetime; the SDK never retries automatically.
        """
        if type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("Rich observation timeout must be finite and positive")
        return cast(
            dict[str, Any],
            self._request(
                "rich_buttons", {"chat_id": chat_id, "message_id": message_id}, timeout=timeout
            ),
        )

    def tap_rich_button(self, *, target_id: str, timeout: float = 180) -> dict[str, Any]:
        """Consume an issued rich target; repeat the same ID to observe its existing receipt.

        Repeated calls never send another tap. A new intentional action requires a fresh target.
        """
        if type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("Rich input timeout must be finite and positive")
        return cast(
            dict[str, Any],
            self._request("tap_rich_button", {"target_id": target_id}, timeout=timeout),
        )

    def type_message(self, *, chat_id: int, text: str, timeout: float = 180) -> dict[str, Any]:
        """Compose and send text, retaining raw input and accepted send receipts.

        Android uses the original editable node and Send control. Each call is a new action;
        a lost response is uncertain and is never retried automatically. The experimental
        profile rejects unsatisfied splitting/formatting contracts before input in both modes.
        """
        if type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("Composer input timeout must be finite and positive")
        return cast(
            dict[str, Any],
            self._request("type_message", {"chat_id": chat_id, "text": text}, timeout=timeout),
        )

    def start_bot_chat(self, *, chat_id: int, timeout: float = 180) -> dict[str, Any]:
        """Press Start Bot in a new conversation, producing the ordinary /start message."""
        if type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("Start Bot timeout must be finite and positive")
        return cast(
            dict[str, Any],
            self._request("start_bot_chat", {"chat_id": chat_id}, timeout=timeout),
        )

    def events(self, *, after: int = 0) -> list[dict[str, Any]]:
        return cast(list[dict[str, Any]], self._request("events", {"after": after}))

    def create_callback(
        self,
        *,
        user_id: int,
        chat_id: int,
        message_id: int,
        data: str,
        request_id: str,
    ) -> dict[str, Any]:
        return cast(
            dict[str, Any],
            self._request(
                "create_callback",
                {
                    "user_id": user_id,
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "data": data,
                    "request_id": request_id,
                },
            ),
        )

    def get_callback(self, *, user_id: int, callback_id: str) -> dict[str, Any]:
        return cast(
            dict[str, Any],
            self._request(
                "get_callback",
                {
                    "user_id": user_id,
                    "callback_id": callback_id,
                },
            ),
        )
