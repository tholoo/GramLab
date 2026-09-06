"""Bounded external breakpoint control using the published JDWP protocol.

This helper uses no class loading, method invocation, field writes, or class redefinition.
Attach only to a dedicated debug process. Kill the target before closing a held breakpoint.
"""

from __future__ import annotations

import socket
import struct
import time
from typing import Any


class _Reader:
    def __init__(self, data: bytes) -> None:
        self.data = data
        self.offset = 0

    def take(self, count: int) -> bytes:
        if count < 0 or self.offset + count > len(self.data):
            raise RuntimeError("Truncated JDWP data")
        value = self.data[self.offset : self.offset + count]
        self.offset += count
        return value

    def integer(self, width: int = 4, *, signed: bool = False) -> int:
        return int.from_bytes(self.take(width), "big", signed=signed)

    def string(self) -> str:
        return self.take(self.integer()).decode("utf-8")

    def finish(self) -> None:
        if self.offset != len(self.data):
            raise RuntimeError("Unexpected trailing JDWP data")


def _integer(value: int, width: int = 4) -> bytes:
    return value.to_bytes(width, "big")


def _string(value: str) -> bytes:
    raw = value.encode("utf-8")
    return _integer(len(raw)) + raw


class Debugger:
    """One loopback connection and one one-shot, event-thread-only breakpoint."""

    def __init__(self, port: int) -> None:
        self.socket = socket.create_connection(("127.0.0.1", port), timeout=5)
        self._sequence = 0
        self._events: list[bytes] = []
        self._target: dict[str, Any] | None = None
        self._thread: bytes | None = None
        try:
            self.socket.sendall(b"JDWP-Handshake")
            if self._read(14) != b"JDWP-Handshake":
                raise RuntimeError("JDWP handshake mismatch")
            sizes = self._command(1, 7)
            self._sizes = {
                name: sizes.integer()
                for name in ("field", "method", "object", "reference", "frame")
            }
            sizes.finish()
            if any(not 1 <= size <= 8 for size in self._sizes.values()):
                raise RuntimeError("Unsupported JDWP identifier size")
        except BaseException:
            self.socket.close()
            raise

    def close(self) -> None:
        """Disconnect; callers must first kill a target whose breakpoint must stay held."""
        self.socket.close()

    def _read(self, count: int) -> bytes:
        pieces = bytearray()
        while len(pieces) < count:
            value = self.socket.recv(count - len(pieces))
            if not value:
                raise ConnectionError("JDWP target disconnected")
            pieces.extend(value)
        return bytes(pieces)

    def _packet(self) -> tuple[int, bool, int, bytes]:
        length, sequence, flags, detail = struct.unpack(">IIBH", self._read(11))
        if not 11 <= length <= 1024 * 1024 or flags not in (0, 0x80):
            raise RuntimeError("Invalid or oversized JDWP packet")
        return sequence, flags == 0x80, detail, self._read(length - 11)

    def _command(self, group: int, command: int, payload: bytes = b"") -> _Reader:
        self._sequence += 1
        self.socket.sendall(
            struct.pack(">IIBBB", 11 + len(payload), self._sequence, 0, group, command) + payload
        )
        while True:
            sequence, reply, detail, data = self._packet()
            if reply:
                if sequence != self._sequence or detail:
                    raise RuntimeError(f"JDWP command {group}/{command} failed: {detail}")
                return _Reader(data)
            if detail != 64 * 256 + 100 or len(self._events) >= 16:
                raise RuntimeError("Unexpected JDWP event packet")
            self._events.append(data)

    def _id(self, reader: _Reader, kind: str) -> bytes:
        return reader.take(self._sizes[kind])

    def _location(self, reader: _Reader) -> bytes:
        return reader.take(1 + self._sizes["reference"] + self._sizes["method"] + 8)

    def breakpoint(self, signature: str, method: str, descriptor: str) -> None:
        if self._target is not None:
            raise ValueError("Only one breakpoint is supported per debugger")
        classes = self._command(1, 2, _string(signature))
        if classes.integer() != 1:
            raise ValueError("Breakpoint requires one loaded class")
        tag = classes.take(1)
        reference = self._id(classes, "reference")
        classes.integer()  # Class status.
        classes.finish()
        methods = self._command(2, 5, reference)
        matches = []
        for _ in range(methods.integer()):
            identity = self._id(methods, "method")
            name, declared = methods.string(), methods.string()
            methods.integer()  # Modifiers.
            if (name, declared) == (method, descriptor):
                matches.append(identity)
        methods.finish()
        if len(matches) != 1:
            raise ValueError("Breakpoint requires a unique method and descriptor")
        method_id = matches[0]
        lines = self._command(6, 1, reference + method_id)
        start, end = lines.integer(8), lines.integer(8)
        indices = [(lines.integer(8), lines.integer()) for _ in range(lines.integer())]
        lines.finish()
        if not indices or start != indices[0][0] or end < start:
            raise ValueError("Breakpoint requires debug information at method entry")
        location = tag + reference + method_id + _integer(start, 8)
        # Breakpoint, suspend event thread, location-only modifier, one occurrence.
        request = self._command(
            15, 1, b"\x02\x01" + _integer(2) + b"\x07" + location + b"\x01" + _integer(1)
        )
        request_id = request.integer()
        request.finish()
        self._target = {
            "request": request_id,
            "location": location,
            "reference": reference,
            "method_id": method_id,
            "signature": signature,
            "method": method,
            "descriptor": descriptor,
            "index": start,
        }

    def wait_breakpoint(self, *, arguments: list[str], timeout: float = 15) -> dict[str, Any]:
        if self._target is None or self._thread is not None:
            raise ValueError("No pending breakpoint")
        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("Target did not reach the breakpoint")
            self.socket.settimeout(remaining)
            if self._events:
                event = _Reader(self._events.pop(0))
            else:
                _, reply, detail, data = self._packet()
                if reply or detail != 64 * 256 + 100:
                    raise RuntimeError("Expected a JDWP composite event")
                event = _Reader(data)
            policy, count = event.integer(1), event.integer()
            if count != 1:
                raise RuntimeError("Unexpected composite breakpoint count")
            kind, request = event.integer(1), event.integer()
            thread = self._id(event, "object")
            if kind == 90 and policy == 0 and request == 0:  # Non-suspending VM-start event.
                event.finish()
                continue
            if kind != 2 or policy != 1 or request != self._target["request"]:
                raise RuntimeError("Unexpected JDWP suspension event")
            if self._location(event) != self._target["location"]:
                raise RuntimeError("Breakpoint location differs from requested method entry")
            event.finish()
            self._thread = thread
            self.socket.settimeout(5)
            name = self._command(11, 1, thread)
            thread_name = name.string()
            name.finish()
            return {
                "class": self._target["signature"],
                "method": self._target["method"],
                "descriptor": self._target["descriptor"],
                "code_index": self._target["index"],
                "suspend_policy": "event_thread",
                "thread_name": thread_name,
                "arguments": self._arguments(arguments),
            }

    def _arguments(self, names: list[str]) -> dict[str, int | bool]:
        if self._target is None or self._thread is None:
            raise ValueError("Arguments require a held breakpoint")
        frames = self._command(11, 6, self._thread + _integer(0) + _integer(1))
        if frames.integer() != 1:
            raise RuntimeError("Expected exactly one requested stack frame")
        frame = self._id(frames, "frame")
        if self._location(frames) != self._target["location"]:
            raise RuntimeError("Suspended frame differs from breakpoint")
        frames.finish()
        variables = self._command(6, 2, self._target["reference"] + self._target["method_id"])
        variables.integer()  # Argument word count.
        found: dict[str, tuple[int, str]] = {}
        for _ in range(variables.integer()):
            start = variables.integer(8)
            name, signature = variables.string(), variables.string()
            length, slot = variables.integer(), variables.integer()
            if name in names and start <= self._target["index"] < start + length:
                if signature not in ("I", "J", "Z") or name in found:
                    raise ValueError("Expected unique integer/boolean breakpoint arguments")
                found[name] = slot, signature
        variables.finish()
        if set(found) != set(names) or len(set(names)) != len(names):
            raise ValueError("Breakpoint argument debug information is unavailable")
        slots = b"".join(_integer(found[name][0]) + found[name][1].encode() for name in names)
        values = self._command(16, 1, self._thread + frame + _integer(len(names)) + slots)
        if values.integer() != len(names):
            raise RuntimeError("Unexpected breakpoint argument count")
        result: dict[str, int | bool] = {}
        for name in names:
            signature = chr(values.integer(1))
            if signature != found[name][1]:
                raise RuntimeError("Breakpoint argument type mismatch")
            value = values.integer({"I": 4, "J": 8, "Z": 1}[signature], signed=True)
            result[name] = bool(value) if signature == "Z" else value
        values.finish()
        return result

    def resume(self) -> None:
        if self._thread is None:
            raise ValueError("No held breakpoint")
        self._command(11, 3, self._thread).finish()
        self._thread = None
