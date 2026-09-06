"""Observe a real bot's structured rich-message send/edit and cold restart in the upstream chat."""

import json
import subprocess
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from android_guest import main
from rich_round_trip import run


def probe(guest: Callable[..., subprocess.CompletedProcess[str]]) -> dict[str, object]:
    capability = ""
    launches: dict[str, str] = {}
    codecs: dict[str, Any] = {}
    timings: dict[str, float] = {}

    def codec(name: str) -> None:
        start = time.monotonic()
        result = adb(
            "shell",
            "CLASSPATH=/data/local/tmp/gramlab-rich.apk",
            "/system/bin/app_process",
            "/system/bin",
            "org.telegram.gramlab.BridgeProbe",
            "/data/local/tmp/gramlab-rich-config.json",
            timeout=30,
        )
        codecs[name] = json.loads(retain(f"{name}-codec.json", result.stdout))
        timings[f"{name}_codec_seconds"] = time.monotonic() - start

    def adb(*arguments: str, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        result = guest(*arguments, **kwargs)
        if result.returncode:
            raise RuntimeError(f"Dedicated Android command failed: {arguments[0]}")
        return result

    def retain(name: str, value: str) -> str:
        if capability and capability in value:
            raise RuntimeError("Rich-message diagnostics contained a capability")
        Path(name).write_text(value)
        return value

    def trace() -> str:
        return adb(
            "shell", "run-as", "org.gramlab.android", "cat", "files/gramlab/trace.jsonl"
        ).stdout

    def launch(name: str) -> None:
        start = time.monotonic()
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
        timings[f"{name}_launch_seconds"] = time.monotonic() - start

    def screen(name: str, *, edited: bool = False) -> str:
        start = time.monotonic()
        deadline = time.monotonic() + 30
        ui = ""
        ready = False
        while time.monotonic() < deadline:
            applied = not edited or any(
                record["event"] == "events_applied"
                for record in (json.loads(line) for line in trace().splitlines())
            )
            adb("shell", "uiautomator", "dump", "/data/local/tmp/rich-message.xml", timeout=15)
            ui = adb("shell", "cat", "/data/local/tmp/rich-message.xml").stdout
            if applied and all(
                text in ui
                for text in (
                    ("Rich blocks updated", "Edited rich message")
                    if edited or name == "restarted"
                    else ("Rich blocks", "Original Android rendering")
                )
            ):
                ready = True
                break
            time.sleep(0.2)
        adb("shell", "screencap", "-p", "/data/local/tmp/rich-message.png")
        adb("pull", "/data/local/tmp/rich-message.png", f"/work/{name}.png")
        retain(f"{name}.xml", ui)
        retain(f"{name}-trace.jsonl", trace())
        retain(f"{name}-logcat.txt", adb("logcat", "-d", "-t", "2000", "-v", "brief").stdout)
        if not ready:
            raise RuntimeError(f"Rich-message scene did not render during {name}")
        timings[f"{name}_capture_seconds"] = time.monotonic() - start
        return ui

    def show(configuration: dict[str, Any]) -> str:
        nonlocal capability
        capability = configuration["capability"]
        start = time.monotonic()
        adb("install", "--no-streaming", "/work/client.apk", timeout=60)
        timings["install_seconds"] = time.monotonic() - start
        local_config = json.dumps(
            configuration | {"endpoint": configuration["endpoint"].replace("127.0.0.1", "10.0.2.2")}
        )
        adb(
            "shell",
            "-T",
            "run-as",
            "org.gramlab.android",
            "sh",
            "-c",
            "'mkdir -p files/gramlab && cat > files/gramlab/config.json'",
            input=local_config,
        )
        adb("push", "/work/client.apk", "/data/local/tmp/gramlab-rich.apk", timeout=30)
        adb(
            "shell",
            "-T",
            "sh",
            "-c",
            "'umask 077; cat > /data/local/tmp/gramlab-rich-config.json'",
            input=local_config,
        )
        codec("initial")
        launch("initial")
        return screen("initial")

    def observe() -> dict[str, Any]:
        edited = screen("edited", edited=True)
        codec("edited")
        adb("shell", "am", "force-stop", "org.gramlab.android")
        launch("restarted")
        restarted = screen("restarted")
        return {
            "edited": edited,
            "restarted": restarted,
            "launches": launches,
            "codecs": codecs,
            "timings": timings,
            "accounts": adb("shell", "dumpsys", "account").stdout,
        }

    try:
        return run(show, observe)
    finally:
        guest("shell", "am", "force-stop", "org.gramlab.android")
        guest("shell", "rm", "-f", "/data/local/tmp/gramlab-rich-config.json")


if __name__ == "__main__":
    main(probe)
