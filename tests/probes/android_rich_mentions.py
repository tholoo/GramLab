"""Original rich mention rendering, accessible inline callbacks and cold restart."""

import json
import re
import subprocess
import time
import xml.etree.ElementTree as ET
from collections.abc import Callable
from pathlib import Path
from typing import Any

from android_guest import main
from rich_mentions_round_trip import run


def probe(guest: Callable[..., subprocess.CompletedProcess[str]]) -> dict[str, object]:
    capability = ""
    launches: dict[str, str] = {}
    codecs: dict[str, Any] = {}
    taps: dict[str, Any] = {}
    timings: dict[str, float] = {}
    labels = {
        "initial": ("Explicit mention A", "Arman", "Mention B / نفر بعد"),
        "edited": ("Explicit mention B", "Mina", "Remove mention / حذف نام"),
        "removed": ("Mentions removed", "No named user"),
        "restarted": ("Mentions removed", "No named user"),
    }

    def retain(name: str, value: str) -> str:
        if capability and capability in value:
            raise RuntimeError("Mention diagnostics contained a capability")
        Path(name).write_text(value)
        return value

    def adb(*arguments: str, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        result = guest(*arguments, **kwargs)
        if result.returncode:
            retain("guest-command-error.txt", result.stdout + result.stderr)
            raise RuntimeError(f"Dedicated mention guest command failed: {arguments[0]}")
        return result

    def trace() -> str:
        return adb(
            "shell", "run-as", "org.gramlab.android", "cat", "files/gramlab/trace.jsonl"
        ).stdout

    def launch(phase: str) -> None:
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
        launches[phase] = retain(f"{phase}-launch.log", result.stdout + result.stderr)

    def screen(phase: str) -> str:
        started = time.monotonic()
        deadline = started + 30
        ui = ""
        ready = False
        while time.monotonic() < deadline:
            adb("shell", "uiautomator", "dump", "/data/local/tmp/mentions-ui.xml", timeout=15)
            ui = adb("shell", "cat", "/data/local/tmp/mentions-ui.xml").stdout
            records = [json.loads(line) for line in trace().splitlines()]
            applied = sum(record["event"] == "events_applied" for record in records)
            if all(text in ui for text in labels[phase]) and (
                phase == "initial" or applied >= (1 if phase == "edited" else 2)
            ):
                ready = True
                break
            time.sleep(0.2)
        # These four filenames are the only primary captures, including refreshed pre-input views.
        adb("shell", "screencap", "-p", "/data/local/tmp/mentions-ui.png")
        adb("pull", "/data/local/tmp/mentions-ui.png", f"/work/{phase}.png")
        retain(f"{phase}.xml", ui)
        retain(f"{phase}-trace.jsonl", trace())
        retain(f"{phase}-logcat.txt", adb("logcat", "-d", "-t", "2000", "-v", "brief").stdout)
        if not ready:
            raise RuntimeError(f"Original mention scene did not render: {phase}")
        timings[phase + "_capture_seconds"] = time.monotonic() - started
        return ui

    def codec(phase: str) -> None:
        result = adb(
            "shell",
            "CLASSPATH=/data/local/tmp/gramlab-mentions.apk",
            "/system/bin/app_process",
            "/system/bin",
            "org.telegram.gramlab.BridgeProbe",
            "/data/local/tmp/gramlab-mentions-config.json",
            "mentions",
            timeout=30,
        )
        codecs[phase] = json.loads(retain(f"{phase}-codec.json", result.stdout))

    def capture(phase: str, configuration: dict[str, Any]) -> str:
        nonlocal capability
        capability = configuration["capability"]
        if phase == "initial":
            started = time.monotonic()
            adb("install", "--no-streaming", "/work/client.apk", timeout=60)
            config = json.dumps(
                configuration
                | {"endpoint": configuration["endpoint"].replace("127.0.0.1", "10.0.2.2")}
            )
            adb(
                "shell",
                "-T",
                "run-as",
                "org.gramlab.android",
                "sh",
                "-c",
                "'mkdir -p files/gramlab && cat > files/gramlab/config.json'",
                input=config,
            )
            adb(
                "shell",
                "-T",
                "sh",
                "-c",
                "'umask 077; cat > /data/local/tmp/gramlab-mentions-config.json'",
                input=config,
            )
            adb("push", "/work/client.apk", "/data/local/tmp/gramlab-mentions.apk", timeout=30)
            timings["install_seconds"] = time.monotonic() - started
            launch(phase)
        elif phase == "restarted":
            adb("shell", "am", "force-stop", "org.gramlab.android")
            launch(phase)
        ui = screen(phase)
        # Separate app_process only observes TL round trips after the live original screen;
        # it cannot prime the application's controller identity cache before that screen.
        codec(phase)
        return ui

    def tap(phase: str, label: str) -> None:
        ui = screen(phase)
        candidates = []
        for node in ET.fromstring(ui).iter("node"):  # noqa: S314 — dedicated UIAutomator output
            if label not in node.get("text", "") + node.get("content-desc", ""):
                continue
            bounds = re.fullmatch(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", node.get("bounds", ""))
            if bounds:
                left, top, right, bottom = map(int, bounds.groups())
                if 0 <= left < right <= 320 and 0 <= top < bottom <= 640:
                    candidates.append(
                        (
                            (right - left) * (bottom - top),
                            (left + right) // 2,
                            (top + bottom) // 2,
                            node.attrib,
                        )
                    )
        if not candidates:
            raise RuntimeError("Original ordinary inline mention button has no observed bounds")
        _, x, y, selected_node = min(candidates, key=lambda item: item[0])
        taps[phase] = {"x": x, "y": y, "node": selected_node}
        adb("shell", "input", "tap", str(x), str(y))
        retain(f"{phase}-tap-trace.jsonl", trace())

    def observe() -> dict[str, Any]:
        return {
            "launches": launches,
            "codecs": codecs,
            "taps": taps,
            "timings": timings,
            "accounts": adb("shell", "dumpsys", "account").stdout,
            "trace": retain("final-trace.jsonl", trace()),
        }

    try:
        result = run(capture, tap, observe)
        # Pre-input screen refreshes are the retained initial/edited structures.
        for phase in ("initial", "edited"):
            result["client"][phase] = Path(f"{phase}.xml").read_text()
        return result
    finally:
        guest("shell", "am", "force-stop", "org.gramlab.android")
        guest("shell", "rm", "-f", "/data/local/tmp/gramlab-mentions-config.json")


if __name__ == "__main__":
    main(probe)
