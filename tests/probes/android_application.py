"""Observe a synthetic conversation in the actual client activity, wholly in containment."""

import json
import os
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path

from android_guest import main

from gramlab.bot_api import BotAPIServer
from gramlab.client_bridge import ClientBridge
from gramlab.world import World


def probe(adb: Callable[..., subprocess.CompletedProcess[str]]) -> dict[str, object]:
    secrets: list[str] = []

    def retain(name: str, value: str) -> str:
        if any(secret in value for secret in secrets):
            raise RuntimeError("Application diagnostics contained a capability")
        Path(name).write_text(value)
        return value

    def stop() -> None:
        if adb("shell", "am", "force-stop", "org.gramlab.android").returncode:
            raise RuntimeError("Dedicated client could not be stopped")

    def launch(*, wait: bool = True) -> subprocess.CompletedProcess[str]:
        return adb(
            "shell",
            "am",
            "start",
            *(["-W"] if wait else []),
            "-n",
            "org.gramlab.android/org.telegram.ui.LaunchActivity",
            "-a",
            "com.tmessages.openchat",
            "--el",
            "userId",
            "2",
            timeout=40,
        )

    def configure(server: ClientBridge, capability: str, world_id: str) -> None:
        configured = adb(
            "shell",
            "-T",
            "run-as",
            "org.gramlab.android",
            "sh",
            "-c",
            "'mkdir -p files/gramlab && cat > files/gramlab/config.json'",
            input=json.dumps(
                {
                    "endpoint": server.base_url.replace("127.0.0.1", "10.0.2.2"),
                    "capability": capability,
                    "world_id": world_id,
                    "user_id": 1,
                }
            ),
        )
        if configured.returncode:
            raise RuntimeError("Private synthetic configuration could not be installed")

    def trace() -> str:
        return adb(
            "shell", "run-as", "org.gramlab.android", "cat", "files/gramlab/trace.jsonl"
        ).stdout

    def rejected(name: str) -> dict[str, str]:
        adb("logcat", "-c")
        launched = launch(wait=False)
        deadline = time.monotonic() + 10
        diagnostics = ""
        while time.monotonic() < deadline:
            diagnostics = adb("logcat", "-d", "-v", "brief").stdout
            failed = (
                "GRAMLAB_STARTUP_" in diagnostics or "GRAMLAB_TRACE_WRITE_FAILED" in diagnostics
            )
            # Android may retain the failed process while its own crash dialog is open.
            if failed and (
                "Showing crash dialog for package org.gramlab.android" in diagnostics
                or not adb("shell", "pidof", "org.gramlab.android").stdout.strip()
            ):
                break
            time.sleep(0.2)
        pid = adb("shell", "pidof", "org.gramlab.android").stdout.strip()
        result = {
            "pid": pid,
            "trace": retain(f"{name}-trace.jsonl", trace()),
            "logcat": retain(f"{name}-logcat.txt", diagnostics),
        }
        retain(f"{name}-launch.log", launched.stdout + launched.stderr)
        stop()
        return result

    def rendered(name: str) -> dict[str, str]:
        launched = launch()
        ui = ""
        deadline = time.monotonic() + 45
        if "Status: ok" in launched.stdout:
            while time.monotonic() < deadline:
                dumped = adb(
                    "shell", "uiautomator", "dump", "/data/local/tmp/gramlab-ui.xml", timeout=15
                )
                if dumped.returncode == 0:
                    ui = adb("shell", "cat", "/data/local/tmp/gramlab-ui.xml").stdout
                    if (
                        ui.count('text="Echo: سلام hello') == 1
                        and ui.count('text="سلام hello') == 1
                    ):
                        break
                time.sleep(1)
        adb("shell", "screencap", "-p", "/data/local/tmp/gramlab-ui.png")
        adb("pull", "/data/local/tmp/gramlab-ui.png", f"/work/{name}.png")
        result = {
            "launch": retain(f"{name}-launch.log", launched.stdout + launched.stderr),
            "ui": retain(f"{name}.xml", ui),
            "trace": retain(f"{name}-trace.jsonl", trace()),
            "accounts": retain(f"{name}-accounts.txt", adb("shell", "dumpsys", "account").stdout),
        }
        retain(f"{name}-windows.txt", adb("shell", "dumpsys", "window", "windows").stdout)
        retain(f"{name}-logcat.txt", adb("logcat", "-d", "-v", "brief", timeout=15).stdout)
        stop()
        return result

    directory = Path("world")
    with World.create(directory, seed=11, now=1700000000) as world:
        world.create_user(first_name="Sara", language_code="fa")
        world.create_user(first_name="Echo", username="gramlab_echo_bot", is_bot=True)
        world.open_private_chat(user_id=1, bot_id=2)
        world.send_message(chat_id=1, sender_id=1, text="سلام hello")
        bot_token = world.issue_bot_token(2)
        capability = world.issue_client_token(1)
        world_id = world.client_snapshot(1)["world_id"]
        secrets.extend((bot_token, capability))
    with BotAPIServer(directory) as bot_server:
        bot = subprocess.run(
            [sys.executable, "echo_bot.py"],
            env={
                **os.environ,
                "GRAMLAB_BOT_API": bot_server.base_url,
                "GRAMLAB_BOT_TOKEN": bot_token,
            },
            capture_output=True,
            text=True,
            timeout=10,
        )
        if bot.returncode:
            raise RuntimeError("Real local bot did not complete")
    installed = adb("install", "--no-streaming", "/work/client.apk", timeout=60)
    if installed.returncode:
        raise RuntimeError("Contained client installation failed: " + installed.stderr)
    missing = rejected("missing-configuration")
    # Only this freshly installed, dedicated test package is cleared, after retaining evidence.
    cleared = adb("shell", "pm", "clear", "org.gramlab.android")
    if cleared.stdout.strip() != "Success":
        raise RuntimeError("Dedicated package data could not be cleared")
    with ClientBridge(directory) as server:
        configure(server, capability, world_id)
        initial = rendered("ui")
        restarted = rendered("restarted")
        other_directory = Path("other-world")
        with World.create(other_directory, seed=11, now=1700000000) as other:
            other.create_user(first_name="Other persona")
            other_capability = other.issue_client_token(1)
            other_id = other.client_snapshot(1)["world_id"]
            secrets.append(other_capability)
        with ClientBridge(other_directory) as other_server:
            configure(other_server, other_capability, other_id)
            wrong_world = rejected("wrong-world")
        configure(server, capability, world_id)
        recovered = rendered("recovered")
    with World.open(directory) as world:
        history = world.history(1)
    return {
        "missing": missing,
        "initial": initial,
        "restarted": restarted,
        "wrong_world": wrong_world,
        "recovered": recovered,
        "history": history,
    }


if __name__ == "__main__":
    main(probe)
