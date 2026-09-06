"""Observe a real bot's formatting-only edit and cold restart in the upstream chat."""

import json
import subprocess
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from android_guest import main
from formatted_round_trip import run


def probe(guest: Callable[..., subprocess.CompletedProcess[str]]) -> dict[str, object]:
    capability = ""
    launches: dict[str, str] = {}

    def adb(*arguments: str, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        result = guest(*arguments, **kwargs)
        if result.returncode:
            raise RuntimeError(f"Dedicated Android command failed: {arguments[0]}")
        return result

    def retain(name: str, value: str) -> str:
        if capability and capability in value:
            raise RuntimeError("Formatting diagnostics contained a capability")
        Path(name).write_text(value)
        return value

    def trace() -> str:
        return adb(
            "shell", "run-as", "org.gramlab.android", "cat", "files/gramlab/trace.jsonl"
        ).stdout

    def launch(name: str) -> None:
        result = adb(
            "shell",
            "am",
            "start",
            "-W",
            "-n",
            "org.gramlab.android/org.telegram.ui.LaunchActivity",
            "-a",
            "com.tmessages.openchat",
            "--el",
            "userId",
            "2",
            timeout=40,
        )
        launches[name] = retain(f"{name}-launch.log", result.stdout + result.stderr)

    def screen(name: str, *, edited: bool = False) -> str:
        deadline = time.monotonic() + 30
        ui = ""
        ready = False
        while time.monotonic() < deadline:
            applied = not edited or any(
                record["event"] == "events_applied"
                for record in (json.loads(line) for line in trace().splitlines())
            )
            adb("shell", "uiautomator", "dump", "/data/local/tmp/formatting.xml", timeout=15)
            ui = adb("shell", "cat", "/data/local/tmp/formatting.xml").stdout
            if applied and all(text in ui for text in ("Bold", "Underline", "Show formatting")):
                ready = True
                break
            time.sleep(0.2)
        adb("shell", "screencap", "-p", "/data/local/tmp/formatting.png")
        adb("pull", "/data/local/tmp/formatting.png", f"/work/{name}.png")
        retain(f"{name}.xml", ui)
        retain(f"{name}-trace.jsonl", trace())
        retain(f"{name}-logcat.txt", adb("logcat", "-d", "-t", "2000", "-v", "brief").stdout)
        if not ready:
            raise RuntimeError(f"Formatting scene did not render during {name}")
        return ui

    def show(configuration: dict[str, Any]) -> str:
        nonlocal capability
        capability = configuration["capability"]
        adb("install", "--no-streaming", "/work/client.apk", timeout=60)
        adb(
            "shell",
            "-T",
            "run-as",
            "org.gramlab.android",
            "sh",
            "-c",
            "'mkdir -p files/gramlab && cat > files/gramlab/config.json'",
            input=json.dumps(
                configuration
                | {"endpoint": configuration["endpoint"].replace("127.0.0.1", "10.0.2.2")}
            ),
        )
        launch("plain")
        return screen("plain")

    def observe() -> dict[str, Any]:
        formatted = screen("formatted", edited=True)
        adb("shell", "am", "force-stop", "org.gramlab.android")
        launch("restarted")
        restarted = screen("restarted")
        return {
            "formatted": formatted,
            "restarted": restarted,
            "launches": launches,
            "accounts": adb("shell", "dumpsys", "account").stdout,
        }

    try:
        return run(show, observe)
    finally:
        guest("shell", "am", "force-stop", "org.gramlab.android")


if __name__ == "__main__":
    main(probe)
