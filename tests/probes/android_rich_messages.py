"""Observe a real bot's structured rich-message send/edit and cold restart in the upstream chat."""

import json
import subprocess
import threading
import time
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

from android_guest import main
from rich_round_trip import run

from gramlab.client_bridge import ClientBridge
from gramlab.world import World


def probe(
    guest: Callable[..., subprocess.CompletedProcess[str]],
    *,
    scene_checks: dict[str, list[str]] | None = None,
    on_initial: Callable[[str], None] | None = None,
) -> dict[str, object]:
    capability = ""
    launches: dict[str, str] = {}
    codecs: dict[str, Any] = {}
    timings: dict[str, float] = {}
    required = scene_checks or {
        "initial": ["Rich blocks", "Original Android rendering", "GramLab", "Language", "۱۲۳"],
        "edited": ["Rich blocks updated", "Edited rich message", "GramLab", "زبان", "۴۵۶"],
    }

    def configure_codec(configuration: dict[str, Any]) -> None:
        nonlocal capability
        capability = configuration["capability"]
        adb(
            "shell",
            "-T",
            "sh",
            "-c",
            "'umask 077; cat > /data/local/tmp/gramlab-rich-config.json'",
            input=json.dumps(
                configuration
                | {"endpoint": configuration["endpoint"].replace("127.0.0.1", "10.0.2.2")}
            ),
        )

    def catalog() -> None:
        with World.create(Path("catalog-world"), seed=17, now=1700000000) as world:
            world.create_user(first_name="Sara", language_code="fa")
            world.create_user(first_name="Echo", username="gramlab_echo_bot", is_bot=True)
            world.open_private_chat(user_id=1, bot_id=2)
            world.send_rich_message(
                chat_id=1,
                sender_id=2,
                rich_message=json.loads(Path("rich-message-catalog.json").read_text())
                | {"skip_entity_detection": True},
            )
            token, world_id = world.issue_client_token(1), world.world_id
            snapshot = world.client_snapshot(1, version=2)
        with ClientBridge(Path("catalog-world")) as bridge:
            configure_codec(
                {
                    "endpoint": bridge.base_url,
                    "capability": token,
                    "world_id": world_id,
                    "user_id": 1,
                }
            )
            codec("catalog")
        # Explicit adversarial snapshots exercise the native guard independently of core
        # validation. Only this dedicated codec receives the injected invalid content.
        payload = b""

        class FaultSnapshot(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args: Any) -> None:
                pass

            def do_GET(self) -> None:
                accepted = (
                    self.path == "/v2/snapshot"
                    and self.headers.get("Authorization") == f"Bearer {token}"
                )
                body = payload if accepted else b"{}"
                self.send_response(200 if accepted else 401)
                self.send_header("Content-Type", "application/json")
                self.send_header("Connection", "close")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        rejections = {}
        with HTTPServer(("127.0.0.1", 0), FaultSnapshot) as server:
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            try:
                configure_codec(
                    {
                        "endpoint": f"http://127.0.0.1:{server.server_port}",
                        "capability": token,
                        "world_id": world_id,
                        "user_id": 1,
                    }
                )
                for case in json.loads(Path("rich-invalid-tables.json").read_text()):
                    changed = json.loads(json.dumps(snapshot))
                    changed["messages"][0]["rich_message"] = case["rich_message"]
                    payload = json.dumps(changed).encode()
                    result = invoke_codec()
                    retain(case["name"] + "-codec.json", result.stdout)
                    rejections[case["name"]] = {
                        "returncode": result.returncode,
                        "result": json.loads(result.stdout),
                    }
            finally:
                server.shutdown()
                worker.join(timeout=5)
        codecs["rejections"] = rejections

    def invoke_codec() -> subprocess.CompletedProcess[str]:
        return guest(
            "shell",
            "CLASSPATH=/data/local/tmp/gramlab-rich.apk",
            "/system/bin/app_process",
            "/system/bin",
            "org.telegram.gramlab.BridgeProbe",
            "/data/local/tmp/gramlab-rich-config.json",
            timeout=30,
        )

    def codec(name: str) -> None:
        start = time.monotonic()
        result = invoke_codec()
        if result.returncode:
            raise RuntimeError("Native rich-message codec failed")
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
                for text in required["edited" if edited or name == "restarted" else "initial"]
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
        configure_codec(configuration)
        codec("initial")
        launch("initial")
        initial = screen("initial")
        if on_initial is not None:
            on_initial(initial)
        return initial

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
        result = run(show, observe)
        adb("shell", "am", "force-stop", "org.gramlab.android")
        if scene_checks is None:
            catalog()
        return result
    finally:
        guest("shell", "am", "force-stop", "org.gramlab.android")
        guest("shell", "rm", "-f", "/data/local/tmp/gramlab-rich-config.json")


if __name__ == "__main__":
    main(probe)
