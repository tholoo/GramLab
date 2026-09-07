"""Observe local photos in the original Android renderer and its private cache."""

import json
import shlex
import subprocess
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from android_guest import main
from media_round_trip import run

PACKAGE = "org.gramlab.android"
CONFIG = "files/gramlab/config.json"
TRACE = "files/gramlab/trace.jsonl"
MEDIA_EVENTS = {
    "media_load_start",
    "media_load_coalesced",
    "media_cache_hit",
    "media_load_success",
    "media_load_failure",
    "media_load_cancel",
}


def probe(guest: Callable[..., subprocess.CompletedProcess[str]]) -> dict[str, object]:
    capability = ""
    installed = False
    launches: dict[str, str] = {}
    timings: dict[str, float] = {}
    captures: dict[str, str] = {}
    cache: dict[str, dict[str, object]] = {}

    def adb(*arguments: str, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        result = guest(*arguments, **kwargs)
        if result.returncode:
            retain(
                "command-failure.json",
                json.dumps(
                    {
                        "arguments": arguments,
                        "returncode": result.returncode,
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                    },
                    indent=2,
                ),
            )
            raise RuntimeError(f"Dedicated Android media command failed: {arguments[0]}")
        return result

    def retain(name: str, value: str) -> str:
        if capability and capability in value:
            raise RuntimeError("Android media evidence contained a client capability")
        Path(name).write_text(value)
        return value

    def trace(name: str) -> list[dict[str, Any]]:
        raw = adb("shell", "run-as", PACKAGE, "cat", TRACE).stdout
        retain(f"{name}-trace.jsonl", raw)
        return [json.loads(line) for line in raw.splitlines()]

    def write_config(configuration: dict[str, Any]) -> None:
        nonlocal capability
        capability = configuration["capability"]
        native = {key: value for key, value in configuration.items() if key != "stage"} | {
            "endpoint": configuration["endpoint"].replace("127.0.0.1", "10.0.2.2")
        }
        if native.get("bridge_version") != 3:
            raise RuntimeError("Media scenario requires explicit bridge version 3")
        adb(
            "shell",
            "-T",
            "run-as",
            PACKAGE,
            "sh",
            "-c",
            f"'mkdir -p files/gramlab && cat > {CONFIG}'",
            input=json.dumps(native),
        )

    def launch(name: str) -> None:
        started = time.monotonic()
        result = adb(
            "shell",
            "am",
            "start",
            "-W",
            "-n",
            f"{PACKAGE}/org.telegram.ui.LaunchActivity",
            "-a",
            "com.tmessages.openchat",
            "--el",
            "userId",
            "2",
            timeout=45,
        )
        launches[name] = retain(f"{name}-launch.log", result.stdout + result.stderr)
        timings[f"{name}_launch_seconds"] = time.monotonic() - started

    def capture(name: str) -> str:
        adb("shell", "uiautomator", "dump", "/data/local/tmp/media.xml", timeout=15)
        ui = adb("shell", "cat", "/data/local/tmp/media.xml").stdout
        retain(f"{name}.xml", ui)
        adb("shell", "screencap", "-p", "/data/local/tmp/media.png")
        adb("pull", "/data/local/tmp/media.png", f"/work/{name}.png")
        captures[name] = ui
        return ui

    def media_rows(name: str) -> list[dict[str, Any]]:
        rows = [row for row in trace(name) if row.get("event") in MEDIA_EVENTS]
        for row in rows:
            if set(row) != {"event", "asset_id", "cache_file", "file_size", "digest_ok"}:
                raise RuntimeError("Media diagnostic row has an unexpected shape")
            if row["asset_id"] not in (1, 2) or row["cache_file"] not in (
                "1_1.jpg",
                "2_1.jpg",
            ):
                raise RuntimeError("Media diagnostic identifies an unexpected asset")
        return rows

    def cache_files(name: str) -> dict[str, object]:
        listing = adb(
            "shell",
            "run-as",
            PACKAGE,
            "find",
            ".",
            "-type",
            "f",
            "-name",
            "*_1.jpg",
        ).stdout.splitlines()
        external = f"/storage/emulated/0/Android/data/{PACKAGE}"
        listing += adb(
            "shell", "find", external, "-type", "f", "-name", "'*_1.jpg'"
        ).stdout.splitlines()
        selected: dict[str, object] = {}
        for filename in ("1_1.jpg", "2_1.jpg"):
            matches = [path for path in listing if Path(path).name == filename]
            if not matches:
                raise RuntimeError(f"No discovered app-owned cache file for {filename}")
            copies = []
            for path in sorted(matches):
                quoted = shlex.quote(path)
                command = (
                    ("shell",) if path.startswith(external + "/") else ("shell", "run-as", PACKAGE)
                )
                digest = adb(*command, "toybox", "sha256sum", quoted).stdout.split()[0]
                size = int(adb(*command, "toybox", "wc", "-c", quoted).stdout.split()[0])
                copies.append({"path": path, "sha256": digest, "size": size})
            selected[filename] = {"copies": copies}
        Path(f"{name}-cache.json").write_text(json.dumps(selected, indent=2) + "\n")
        cache[name] = selected
        return selected

    def wait_for_media(name: str, required_assets: set[int], *, edited: bool = False) -> None:
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            rows = media_rows(name)
            successful = {
                int(row["asset_id"])
                for row in rows
                if row["event"] in ("media_load_success", "media_cache_hit")
                and row["digest_ok"] is True
            }
            applied = not edited or any(row.get("event") == "events_applied" for row in trace(name))
            if required_assets <= successful and applied:
                return
            time.sleep(0.25)
        raise RuntimeError(f"Original Android did not finish media loading during {name}")

    def show(configuration: dict[str, Any]) -> str:
        nonlocal installed
        stage = configuration["stage"]
        if stage not in ("initial", "edited", "restart"):
            raise RuntimeError("Unknown media observation stage")
        if not installed:
            started = time.monotonic()
            adb("install", "--no-streaming", "/work/client.apk", timeout=60)
            timings["install_seconds"] = time.monotonic() - started
            installed = True
        if stage == "restart":
            adb("shell", "am", "force-stop", PACKAGE)
        write_config(configuration)
        if stage in ("initial", "restart"):
            launch(stage)
        if stage == "initial":
            wait_for_media(stage, {2})
            bottom = capture("initial-bottom")
            adb("shell", "input", "swipe", "160", "180", "160", "520", "500")
            time.sleep(0.5)
            wait_for_media(stage, {1, 2})
            top = capture("initial-top")
            cache_files(stage)
            return bottom + "\n" + top
        wait_for_media(stage, {1, 2}, edited=stage == "edited")
        if stage == "edited":
            adb("shell", "input", "swipe", "160", "520", "160", "180", "500")
            time.sleep(0.5)
        capture(stage)
        cache_files(stage)
        return captures[stage]

    def observe() -> dict[str, Any]:
        final_trace = trace("final")
        return {
            "captures": captures,
            "launches": launches,
            "timings": timings,
            "media_trace": [row for row in final_trace if row.get("event") in MEDIA_EVENTS],
            "cache": cache,
            "accounts": adb("shell", "dumpsys", "account").stdout,
        }

    try:
        return run(show, observe)
    except BaseException:
        raw_trace = guest("shell", "run-as", PACKAGE, "cat", TRACE)
        if raw_trace.returncode == 0:
            retain("failure-trace.jsonl", raw_trace.stdout)
        guest("shell", "uiautomator", "dump", "/data/local/tmp/media-failure.xml", timeout=15)
        failure_xml = guest("shell", "cat", "/data/local/tmp/media-failure.xml")
        if failure_xml.returncode == 0:
            retain("failure.xml", failure_xml.stdout)
        guest("shell", "screencap", "-p", "/data/local/tmp/media-failure.png")
        guest("pull", "/data/local/tmp/media-failure.png", "/work/failure.png")
        cache_listing = guest("shell", "run-as", PACKAGE, "find", ".", "-type", "f")
        if cache_listing.returncode == 0:
            retain("failure-cache-files.txt", cache_listing.stdout)
        failure_log = guest("logcat", "-d", "-t", "2000", "-v", "brief")
        if failure_log.returncode == 0:
            retain("failure-logcat.txt", failure_log.stdout)
        raise
    finally:
        guest("shell", "am", "force-stop", PACKAGE)


if __name__ == "__main__":
    main(probe)
