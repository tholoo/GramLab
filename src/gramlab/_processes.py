"""Persistent supervisor-thread ownership of private consumer process generations."""

from __future__ import annotations

import os
import queue
import selectors
import subprocess
import threading
import time
from contextlib import ExitStack
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from gramlab.runtime import Sandbox

_LOG_LIMIT = 1024 * 1024
_TOTAL_LOG_LIMIT = 2 * 1024 * 1024
Program = tuple[Path, dict[str, Any], dict[str, str]]


@dataclass
class _Request:
    operation: str
    name: str
    generation: int | None
    done: threading.Event = field(default_factory=threading.Event)
    result: dict[str, Any] | None = None
    error: ValueError | RuntimeError | None = None


@dataclass
class _Instance:
    name: str
    generation: int
    process: subprocess.Popen[str]
    context: ExitStack
    intentional: bool = False

    def status(self) -> dict[str, Any]:
        code = self.process.poll()
        return {
            "name": self.name.removeprefix("bot:"),
            "generation": self.generation,
            "state": "running" if code is None else "stopped" if self.intentional else "exited",
            "exit_code": code,
        }


class Processes:
    def __init__(self, sandbox: Sandbox, *, deadline: float, bots: set[str]) -> None:
        self.sandbox = sandbox
        self.deadline = deadline
        self.bots = bots
        self.failure: str | None = None
        self.records: dict[str, Any] = {}
        self.lifecycle: list[dict[str, Any]] = []
        self._pending: queue.Queue[_Request] = queue.Queue(maxsize=64)
        self._queue_lock = threading.Lock()
        self._closed = False
        self._instances: dict[str, _Instance] = {}
        self._latest: dict[str, str] = {}
        self._programs: dict[str, Program] = {}
        self._buffers: dict[tuple[str, str], bytearray] = {}
        self._complete: set[tuple[str, str]] = set()
        self._total_bytes = 0
        self._stack = ExitStack()
        self._ready = selectors.DefaultSelector()

    def _request(self, operation: str, name: str, generation: int | None = None) -> dict[str, Any]:
        if not isinstance(name, str) or name not in self.bots:
            raise ValueError("Lifecycle target must be a configured bot alias")
        if operation != "bot_status" and (type(generation) is not int or generation < 1):
            raise ValueError("Lifecycle mutation requires a positive expected generation")
        request = _Request(operation, name, generation)
        with self._queue_lock:
            if self._closed:
                raise RuntimeError("Consumer lifecycle has closed")
            try:
                self._pending.put_nowait(request)
            except queue.Full:
                raise ValueError("Too many pending lifecycle requests") from None
        if not request.done.wait(max(0, self.deadline - time.monotonic())):
            raise RuntimeError("Lifecycle request exceeded the run deadline")
        if request.error is not None:
            raise request.error
        if request.result is None:
            raise RuntimeError("Lifecycle request produced no result")
        return request.result

    def bot_status(self, name: str) -> dict[str, Any]:
        return self._request("bot_status", name)

    def stop_bot(self, name: str, *, generation: int) -> dict[str, Any]:
        return self._request("stop_bot", name, generation)

    def start_bot(self, name: str, *, generation: int) -> dict[str, Any]:
        return self._request("start_bot", name, generation)

    def _launch(self, name: str, generation: int) -> _Instance:
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("Consumer run deadline expired")
        directory, program, environment = self._programs[name]
        context = ExitStack()
        self._stack.callback(context.close)
        process = context.enter_context(
            self.sandbox.component(
                [self.sandbox.profile.python, "-u", "/work/" + program["entry"]],
                data=directory,
                environment={"PYTHONPATH": "/work", **environment},
                startup_timeout=min(10, remaining),
            )
        )
        key = name if generation == 1 else f"{name}#{generation}"
        instance = _Instance(name, generation, process, context)
        self._instances[key] = instance
        self._latest[name] = key
        for stream in ("stdout", "stderr"):
            pipe = getattr(process, stream)
            self._ready.register(pipe, selectors.EVENT_READ, (key, stream))
            self._buffers[key, stream] = bytearray()
        return instance

    def _drain(self) -> None:
        for key, _ in self._ready.select(timeout=0.02):
            chunk = os.read(key.fd, 65536)
            if not chunk:
                self._complete.add(key.data)
                self._ready.unregister(key.fileobj)
                continue
            buffer = self._buffers[key.data]
            remaining = min(_LOG_LIMIT - len(buffer), _TOTAL_LOG_LIMIT - self._total_bytes)
            buffer.extend(chunk[:remaining])
            self._total_bytes += min(len(chunk), remaining)
            if len(chunk) > remaining:
                self.failure = "output_limit"

    def _retire(self, key: str) -> None:
        instance = self._instances[key]
        deadline = min(self.deadline, time.monotonic() + 10)
        while any(item.data[0] == key for item in self._ready.get_map().values()):
            if time.monotonic() >= deadline:
                raise TimeoutError("Bot streams did not close before cleanup")
            self._drain()
        instance.context.close()

    def _dispatch(self) -> None:
        try:
            request = self._pending.get_nowait()
        except queue.Empty:
            return
        try:
            name = "bot:" + request.name
            key = self._latest[name]
            instance = self._instances[key]
            status = instance.status()
            if request.operation != "bot_status":
                if request.generation != instance.generation:
                    raise ValueError("Bot generation changed; inspect its current status")
                if request.operation == "stop_bot":
                    if status["state"] != "running":
                        raise ValueError("Bot generation is already stopped or exited")
                    instance.intentional = True
                    try:
                        instance.process.kill()
                    except ProcessLookupError:
                        pass  # Retain the observed exit if it raced the requested stop.
                    self._retire(key)
                else:
                    if status["state"] == "running":
                        raise ValueError("Bot must be stopped before starting its replacement")
                    if instance.generation >= 8:
                        raise ValueError("At most eight generations per bot are supported")
                    self._retire(key)
                    instance = self._launch(name, instance.generation + 1)
                status = instance.status()
                self.lifecycle.append({"operation": request.operation, "result": status})
            request.result = status
        except ValueError as error:
            request.error = error
        except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
            self.failure = self.failure or (
                "timeout" if time.monotonic() >= self.deadline else "lifecycle_failed"
            )
            self.lifecycle.append(
                {
                    "operation": request.operation,
                    "name": request.name,
                    "generation": request.generation,
                    "failure": type(error).__name__,
                }
            )
            request.error = RuntimeError("Bot lifecycle operation failed")
        finally:
            request.done.set()

    def run(self, programs: dict[str, Program]) -> None:
        self._programs = programs
        try:
            for name in programs:
                self._launch(name, 1)
            while True:
                self._drain()
                if any(
                    instance.process.poll() not in (None, 0) and not instance.intentional
                    for instance in self._instances.values()
                ):
                    self.failure = self.failure or "process_failed"
                if time.monotonic() >= self.deadline:
                    self.failure = self.failure or "timeout"
                scenario = self._instances["scenario"].process
                scenario_streams = any(
                    key.data[0] == "scenario" for key in self._ready.get_map().values()
                )
                if self.failure or (scenario.poll() is not None and not scenario_streams):
                    break
                self._dispatch()
        finally:
            self.close()

    def close(self) -> None:
        with self._queue_lock:
            if self._closed:
                return
            self._closed = True
            while not self._pending.empty():
                request = self._pending.get_nowait()
                request.error = RuntimeError("Consumer lifecycle has closed")
                request.done.set()
        for key, instance in self._instances.items():
            self.records[key] = {
                "exit_code": instance.process.poll(),
                "stopped_by_runner": instance.process.returncode is None,
                "stopped_by_scenario": instance.intentional,
                "generation": instance.generation,
            }
            for stream in ("stdout", "stderr"):
                self.records[key][stream] = self._buffers[key, stream].decode(
                    "utf-8", errors="replace"
                )
                self.records[key][stream + "_complete"] = (key, stream) in self._complete
        try:
            self._stack.close()
        finally:
            self._ready.close()
