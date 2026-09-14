"""Authenticated host control for one persistent, offline playground owner."""

from __future__ import annotations

import json
import os
import re
import secrets
import socket
import stat
from collections.abc import Callable
from pathlib import Path
from typing import Any, Self
from uuid import UUID

_REQUEST_LIMIT = 65536
_RESPONSE_LIMIT = 16 * 1024 * 1024


def _object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value = dict(pairs)
    if len(value) != len(pairs):
        raise ValueError("Repeated playground control members")
    return value


def _control(output: Path) -> dict[str, str | int]:
    path = output.absolute() / "playground-control.json"
    metadata = path.lstat()
    if not stat.S_ISREG(metadata.st_mode) or stat.S_IMODE(metadata.st_mode) != 0o600:
        raise ValueError("Playground control file must be a private regular file")
    if not 0 < metadata.st_size <= _REQUEST_LIMIT:
        raise ValueError("Playground control file has an invalid size")
    body = json.loads(path.read_text(), object_pairs_hook=_object)
    if not isinstance(body, dict) or body.keys() != {"schema", "run_id", "socket", "capability"}:
        raise ValueError("Invalid playground control file")
    if body["schema"] != 1 or type(body["schema"]) is not int:
        raise ValueError("Unsupported playground control schema")
    if not isinstance(body["run_id"], str) or str(UUID(body["run_id"])) != body["run_id"]:
        raise ValueError("Invalid playground run identity")
    if body["socket"] != "playground.sock":
        raise ValueError("Invalid playground control socket")
    if (
        not isinstance(body["capability"], str)
        or re.fullmatch(r"gramlab-playground_[A-Za-z0-9_-]{43}", body["capability"]) is None
    ):
        raise ValueError("Invalid playground control capability")
    return body


def request(
    output: Path, operation: str, parameters: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Send one bounded command to the owner named by a private control file."""
    try:
        control = _control(output)
    except FileNotFoundError:
        result_path = output.absolute() / "result.json"
        if operation != "stop" or not result_path.is_file():
            raise
        result = json.loads(result_path.read_text(), object_pairs_hook=_object)
        lifecycle = result.get("playground", {}).get("lifecycle", [])
        if (
            result.get("outcome") != "passed"
            or not lifecycle
            or lifecycle[-1].get("operation") != "stop"
        ):
            raise
        return {"state": "stopped", "run_id": result["run_id"]}
    payload = json.dumps(
        {
            "schema": 1,
            "run_id": control["run_id"],
            "capability": control["capability"],
            "operation": operation,
            "parameters": parameters or {},
        },
        ensure_ascii=True,
        allow_nan=False,
    ).encode()
    if len(payload) > _REQUEST_LIMIT:
        raise ValueError("Playground command is too large")
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    client.settimeout(15)
    try:
        directory = os.open(output.absolute(), os.O_RDONLY | os.O_DIRECTORY)
        try:
            client.connect(f"/proc/self/fd/{directory}/{control['socket']}")
        finally:
            os.close(directory)
        client.sendall(payload)
        client.shutdown(socket.SHUT_WR)
        chunks: list[bytes] = []
        size = 0
        while True:
            chunk = client.recv(min(65536, _RESPONSE_LIMIT + 1 - size))
            if not chunk:
                break
            chunks.append(chunk)
            size += len(chunk)
            if size > _RESPONSE_LIMIT:
                raise ValueError("Playground response is too large")
    finally:
        client.close()
    body = json.loads(b"".join(chunks), object_pairs_hook=_object)
    if not isinstance(body, dict) or body.keys() not in ({"result"}, {"error"}):
        raise ValueError("Invalid playground response")
    if "error" in body:
        if not isinstance(body["error"], str):
            raise ValueError("Invalid playground rejection")
        raise RuntimeError(body["error"])
    if not isinstance(body["result"], dict):
        raise ValueError("Invalid playground result")
    return body["result"]


class PlaygroundControl:
    """Unix-socket owner whose capability cannot be confused with another run."""

    def __init__(
        self,
        output: Path,
        *,
        run_id: str,
        dispatch: Callable[[str, dict[str, Any]], dict[str, Any]],
    ) -> None:
        self.output = output.absolute()
        self.run_id = run_id
        self.capability = "gramlab-playground_" + secrets.token_urlsafe(32)
        self.dispatch = dispatch
        self.path = self.output / "playground.sock"
        self.control_path = self.output / "playground-control.json"
        if self.path.exists() or self.control_path.exists():
            raise RuntimeError("Playground already has an owner")
        self._server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        directory = os.open(self.output, os.O_RDONLY | os.O_DIRECTORY)
        try:
            self._server.bind(f"/proc/self/fd/{directory}/{self.path.name}")
        finally:
            os.close(directory)
        os.chmod(self.path, 0o600)
        self._server.listen(4)
        self._server.settimeout(0.05)
        descriptor = os.open(
            self.control_path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
        )
        with os.fdopen(descriptor, "w") as stream:
            json.dump(
                {
                    "schema": 1,
                    "run_id": self.run_id,
                    "socket": self.path.name,
                    "capability": self.capability,
                },
                stream,
            )

    def __enter__(self) -> Self:
        return self

    def poll(self) -> bool:
        """Handle at most one command and return whether stop was accepted."""
        try:
            connection, _ = self._server.accept()
        except TimeoutError:
            return False
        with connection:
            connection.settimeout(2)
            raw = bytearray()
            while True:
                chunk = connection.recv(min(65536, _REQUEST_LIMIT + 1 - len(raw)))
                if not chunk:
                    break
                raw.extend(chunk)
                if len(raw) > _REQUEST_LIMIT:
                    break
            stopped = False
            response: dict[str, Any]
            try:
                body = json.loads(bytes(raw), object_pairs_hook=_object)
                if not isinstance(body, dict) or body.keys() != {
                    "schema",
                    "run_id",
                    "capability",
                    "operation",
                    "parameters",
                }:
                    raise ValueError("Invalid playground command")
                if (
                    body["schema"] != 1
                    or type(body["schema"]) is not int
                    or body["run_id"] != self.run_id
                    or not isinstance(body["capability"], str)
                    or not secrets.compare_digest(body["capability"], self.capability)
                    or not isinstance(body["operation"], str)
                    or not isinstance(body["parameters"], dict)
                ):
                    raise ValueError("Playground identity or capability did not match")
                result = self.dispatch(body["operation"], body["parameters"])
                response = {"result": result}
                stopped = body["operation"] == "stop"
            except (KeyError, TypeError, ValueError, RuntimeError) as error:
                response = {"error": str(error)}
            connection.sendall(json.dumps(response, ensure_ascii=True).encode())
            return stopped

    def close(self) -> None:
        self._server.close()
        self.control_path.unlink(missing_ok=True)
        self.path.unlink(missing_ok=True)

    def __exit__(self, *_: object) -> None:
        self.close()
