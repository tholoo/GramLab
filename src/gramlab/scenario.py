"""Experimental Python world control for scenario code inside the private runtime."""

from __future__ import annotations

import http.client
import json
import math
import os
import re
import socket
from typing import Any, Self, cast
from urllib.parse import urlsplit
from uuid import UUID

_READS = {"snapshot", "history", "events", "get_callback", "bots"}
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

    def _request(self, operation: str, parameters: dict[str, Any]) -> Any:
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
            if len(payload) > 65536:
                raise ValueError
        except (TypeError, ValueError, RecursionError):
            raise ScenarioError(
                "Invalid or oversized scenario command; nothing was sent",
                operation=operation,
                code="invalid_request",
            ) from None
        connection = http.client.HTTPConnection("127.0.0.1", self._port, timeout=self._timeout)
        attempted = False
        status = None
        try:
            connection.connect()
            attempted = True
            connection.request(
                "POST",
                "/v1/world",
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
