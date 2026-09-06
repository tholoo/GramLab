"""Trusted run supervisor. Never import or execute consumer code in this process."""

from __future__ import annotations

import json
import os
import selectors
import subprocess
import time
from contextlib import ExitStack
from pathlib import Path
from typing import Any

from gramlab._android import Android
from gramlab._captures import Captures
from gramlab._control import WorldControl
from gramlab.bot_api import BotAPIServer
from gramlab.reports import _Redactor
from gramlab.runtime import RuntimeProfile, Sandbox
from gramlab.world import World

_LOG_LIMIT = 1024 * 1024
_TOTAL_LOG_LIMIT = 2 * 1024 * 1024


def execute() -> None:
    config = json.loads(Path("run-input.json").read_text())
    profile = RuntimeProfile(**json.loads(Path("profile.json").read_text()))
    sandbox = Sandbox(profile)
    deadline = time.monotonic() + config["timeout"]
    tokens = {}
    bots = {}
    with World.create(Path("world"), seed=config["seed"], now=config["now"]) as world:
        for alias in config["bots"]:
            bot = world.create_user(first_name=alias, is_bot=True)
            bots[alias] = bot["id"]
            tokens[alias] = world.issue_bot_token(bot["id"])
    processes: dict[str, subprocess.Popen[str]] = {}
    records: dict[str, Any] = {}
    buffers: dict[tuple[str, str], bytearray] = {}
    complete: set[tuple[str, str]] = set()
    total_bytes = 0
    failure: str | None = None
    secrets = list(tokens.values())
    android = None
    if config["mode"] == "headless-android":
        android = Android(
            RuntimeProfile(**json.loads(Path("android-profile.json").read_text())),
            deadline=deadline,
            secrets=secrets,
        )
    captures = Captures(Path("world"), render=android.capture if android is not None else None)
    try:
        # Namespace processes belong to this persistent owner, never a short-lived HTTP thread.
        if android is not None:
            android.start()
        with (
            WorldControl(Path("world"), bots=bots, capture_chat=captures.capture_chat) as control,
            BotAPIServer(Path("world")) as api,
        ):
            secrets.append(control.capability)
            with ExitStack() as stack, selectors.DefaultSelector() as ready:
                programs = [
                    (
                        f"bot:{alias}",
                        Path("bots") / alias,
                        program,
                        {"GRAMLAB_BOT_API": api.base_url, "GRAMLAB_BOT_TOKEN": tokens[alias]},
                    )
                    for alias, program in config["bots"].items()
                ]
                programs.append(
                    (
                        "scenario",
                        Path("scenario"),
                        config["scenario"],
                        {
                            "GRAMLAB_CONTROL_ENDPOINT": control.base_url,
                            "GRAMLAB_CONTROL_CAPABILITY": control.capability,
                            "GRAMLAB_WORLD_ID": control.world_id,
                        },
                    )
                )
                for name, directory, program, environment in programs:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise TimeoutError
                    process = stack.enter_context(
                        sandbox.component(
                            [profile.python, "-u", "/work/" + program["entry"]],
                            data=directory,
                            environment={"PYTHONPATH": "/work", **environment},
                            startup_timeout=min(10, remaining),
                        )
                    )
                    processes[name] = process
                    for stream in ("stdout", "stderr"):
                        pipe = getattr(process, stream)
                        ready.register(pipe, selectors.EVENT_READ, (name, stream))
                        buffers[name, stream] = bytearray()
                while True:
                    for key, _ in ready.select(timeout=0.02):
                        chunk = os.read(key.fd, 65536)
                        if not chunk:
                            complete.add(key.data)
                            ready.unregister(key.fileobj)
                            continue
                        buffer = buffers[key.data]
                        remaining_bytes = min(
                            _LOG_LIMIT - len(buffer), _TOTAL_LOG_LIMIT - total_bytes
                        )
                        buffer.extend(chunk[:remaining_bytes])
                        total_bytes += min(len(chunk), remaining_bytes)
                        if len(chunk) > remaining_bytes:
                            failure = "output_limit"
                    codes = {name: process.poll() for name, process in processes.items()}
                    if any(code not in (None, 0) for code in codes.values()):
                        failure = failure or "process_failed"
                    if time.monotonic() >= deadline:
                        failure = failure or "timeout"
                    scenario_streams = any(
                        key.data[0] == "scenario" for key in ready.get_map().values()
                    )
                    if failure or (codes["scenario"] is not None and not scenario_streams):
                        for name, code in codes.items():
                            records[name] = {"exit_code": code, "stopped_by_runner": code is None}
                        break
    except (TimeoutError, subprocess.TimeoutExpired):
        failure = "timeout"
    except (OSError, RuntimeError):
        failure = "component_startup_failed"
    finally:
        if android is not None:
            try:
                android.close()
            except (OSError, RuntimeError):
                failure = failure or "android_cleanup_failed"
    if captures.failed:
        failure = failure or "capture_failed"
    for name, process in processes.items():
        records.setdefault(name, {"exit_code": process.returncode, "stopped_by_runner": True})
        for stream in ("stdout", "stderr"):
            records[name][stream] = buffers[name, stream].decode("utf-8", errors="replace")
            records[name][stream + "_complete"] = (name, stream) in complete
    observation = _Redactor(secrets).clean(
        {
            "failure": failure,
            "processes": records,
            "captures": captures.records,
            "android": android.observations if android is not None else {},
        }
    )
    Path("observation.json").write_text(json.dumps(observation, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    execute()
