"""Trusted run supervisor. Never import or execute consumer code in this process."""

from __future__ import annotations

import json
import subprocess
import threading
import time
from pathlib import Path

from gramlab._android import Android
from gramlab._captures import Captures
from gramlab._control import WorldControl
from gramlab._interactions import Interactions
from gramlab._processes import Processes, Program
from gramlab._rich_interactions import RichInteractions
from gramlab.bot_api import BotAPIServer
from gramlab.reports import _Redactor
from gramlab.runtime import RuntimeProfile, Sandbox
from gramlab.world import World


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
    processes = Processes(sandbox, deadline=deadline, bots=set(bots))
    failure: str | None = None
    secrets = list(tokens.values())
    android = None
    if config["mode"] == "headless-android":
        android = Android(
            RuntimeProfile(**json.loads(Path("android-profile.json").read_text())),
            deadline=deadline,
            secrets=secrets,
            bridge_version=config["android"]["bridge_version"],
        )
    renderer_lock = threading.Lock()
    captures = Captures(
        Path("world"), lock=renderer_lock, render=android.capture if android is not None else None
    )
    interactions = Interactions(
        Path("world"),
        lock=renderer_lock,
        bridge_version=config["bridge_version"],
        tap=android.tap_inline_button if android is not None else None,
        compose=android.type_message if android is not None else None,
        start_chat=android.start_bot_chat if android is not None else None,
    )
    rich = None
    try:
        native_rich = None
        if android is not None:
            from gramlab._android_rich_buttons import AndroidRichInput

            native_rich = AndroidRichInput(android)
        rich = RichInteractions(
            Path("world"), lock=renderer_lock, interactions=interactions, native=native_rich
        )
        # Namespace processes belong to this persistent owner, never a short-lived HTTP thread.
        if android is not None:
            android.start()
        with (
            WorldControl(
                Path("world"),
                bots=bots,
                capture_chat=captures.capture_chat,
                tap_inline_button=interactions.tap_inline_button,
                rich_buttons=rich.rich_buttons,
                tap_rich_button=rich.tap_rich_button,
                type_message=interactions.type_message,
                start_bot_chat=interactions.start_bot_chat,
                bot_status=processes.bot_status,
                stop_bot=processes.stop_bot,
                start_bot=processes.start_bot,
            ) as control,
            BotAPIServer(Path("world")) as api,
        ):
            secrets.append(control.capability)
            programs: dict[str, Program] = {
                f"bot:{alias}": (
                    Path("bots") / alias,
                    program,
                    {"GRAMLAB_BOT_API": api.base_url, "GRAMLAB_BOT_TOKEN": tokens[alias]},
                )
                for alias, program in config["bots"].items()
            }
            programs["scenario"] = (
                Path("scenario"),
                config["scenario"],
                {
                    "GRAMLAB_CONTROL_ENDPOINT": control.base_url,
                    "GRAMLAB_CONTROL_CAPABILITY": control.capability,
                    "GRAMLAB_WORLD_ID": control.world_id,
                },
            )
            processes.run(programs)
            failure = processes.failure
    except (TimeoutError, subprocess.TimeoutExpired):
        failure = "timeout"
    except (OSError, RuntimeError):
        failure = "component_startup_failed"
    finally:
        processes.close()
        if rich is not None:
            try:
                rich.close()
            except OSError:
                failure = failure or "rich_button_journal_failed"
        if android is not None:
            try:
                android.close()
            except (OSError, RuntimeError):
                failure = failure or "android_cleanup_failed"
    if interactions.failed:
        failure = failure or "interaction_failed"
    if rich is not None and rich.failed:
        failure = failure or rich.failure or "rich_button_component_failed"
    if captures.failed:
        failure = failure or "capture_failed"
    observation = _Redactor(secrets).clean(
        {
            "failure": failure,
            "processes": processes.records,
            "lifecycle": processes.lifecycle,
            "captures": captures.records,
            "interactions": interactions.records,
            "android": android.observations if android is not None else {},
        }
    )
    Path("observation.json").write_text(json.dumps(observation, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    execute()
