"""Observe edits to older cached messages made while the actual client is stopped."""

import json
import subprocess
import time
import xml.etree.ElementTree as ET
from collections.abc import Callable
from pathlib import Path
from typing import Any

from android_guest import main
from recovery_round_trip import run


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
            raise RuntimeError("Recovery diagnostics contained a capability")
        Path(name).write_text(value)
        return value

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

    def screen(name: str, *, recovered: bool = False) -> str:
        expected = (
            ["Check recovery", "corrected", "Previously newest", "Sent while away"]
            if recovered
            else ["Check recovery", "original", "Original action", "Previously newest"]
        )
        deadline = time.monotonic() + 30
        ui = ""
        ready = False
        while time.monotonic() < deadline:
            adb("shell", "uiautomator", "dump", "/data/local/tmp/recovery.xml", timeout=15)
            ui = adb("shell", "cat", "/data/local/tmp/recovery.xml").stdout
            values = "\n".join(
                value
                for node in ET.fromstring(ui).iter("node")  # noqa: S314 — dedicated UIAutomator output
                for key, value in node.attrib.items()
                if key in {"text", "content-desc"}
            )
            if all(text in values for text in expected) and (
                not recovered or ("original" not in values and "Original action" not in values)
            ):
                ready = True
                break
            time.sleep(0.2)
        adb("shell", "screencap", "-p", "/data/local/tmp/recovery.png")
        adb("pull", "/data/local/tmp/recovery.png", f"/work/{name}.png")
        retain(f"{name}.xml", ui)
        retain(
            f"{name}-trace.jsonl",
            adb(
                "shell", "run-as", "org.gramlab.android", "cat", "files/gramlab/trace.jsonl"
            ).stdout,
        )
        retain(f"{name}-logcat.txt", adb("logcat", "-d", "-t", "2000", "-v", "brief").stdout)
        if not ready:
            raise RuntimeError(f"Authoritative recovery history did not render during {name}")
        return ui

    def suspend(configuration: dict[str, Any]) -> str:
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
        launch("before")
        before = screen("before")
        adb("shell", "am", "force-stop", "org.gramlab.android")
        return before

    def recover() -> dict[str, Any]:
        result: dict[str, Any] = {}
        for phase in ("recovered", "repeated"):
            launch(phase)
            result[phase] = screen(phase, recovered=True)
            adb("shell", "am", "force-stop", "org.gramlab.android")
        result["launches"] = launches
        result["accounts"] = adb("shell", "dumpsys", "account").stdout
        return result

    try:
        return run(suspend, recover)
    finally:
        guest("shell", "am", "force-stop", "org.gramlab.android")


if __name__ == "__main__":
    main(probe)
