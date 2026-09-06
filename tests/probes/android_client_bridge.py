"""Connect a real bot, world and Android-side TL projection inside one isolated runtime."""

import json
import subprocess
import threading
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from android_guest import main
from component_bot import FixtureBot

from gramlab.bot_api import BotAPIServer
from gramlab.client_bridge import ClientBridge
from gramlab.world import World


def probe(adb: Callable[..., subprocess.CompletedProcess[str]]) -> dict[str, object]:
    directory = Path("world")
    with World.create(directory, seed=11, now=1700000000) as world:
        world.create_user(first_name="Sara", language_code="fa")
        world.create_user(first_name="Echo", username="gramlab_echo_bot", is_bot=True)
        world.create_user(first_name="Bob")
        world.open_private_chat(user_id=1, bot_id=2)
        world.open_private_chat(user_id=3, bot_id=2)
        world.send_message(chat_id=1, sender_id=1, text="سلام hello")
        world.send_message(chat_id=2, sender_id=2, text="Private to Bob")
        bot_token = world.issue_bot_token(2)
        capability = world.issue_client_token(1)
        world_id = world.client_snapshot(1)["world_id"]
    with World.create(Path("other-world"), seed=11, now=1700000000) as other:
        other.create_user(first_name="Sara")
        other_capability = other.issue_client_token(1)
        other_id = other.client_snapshot(1)["world_id"]
    with BotAPIServer(directory) as bot_server:
        bot = FixtureBot("echo_bot.py").run(
            {"GRAMLAB_BOT_API": bot_server.base_url, "GRAMLAB_BOT_TOKEN": bot_token}
        )
        if bot.returncode:
            raise RuntimeError("Local bot did not complete")
    if Path("formatting.json").exists():
        formatting = json.loads(Path("formatting.json").read_text())
        with World.open(directory) as world:
            world.edit_message(chat_id=1, message_id=2, bot_id=2, **formatting)
    with ClientBridge(directory) as server:
        config = {
            "endpoint": server.base_url.replace("127.0.0.1", "10.0.2.2"),
            "capability": capability,
            "world_id": world_id,
            "user_id": 1,
        }
        for command in (
            ("shell", "mkdir", "-p", "/data/local/tmp/gramlab-bridge"),
            ("push", "/work/client.apk", "/data/local/tmp/gramlab-bridge/client.apk"),
            ("shell", "chmod", "0444", "/data/local/tmp/gramlab-bridge/client.apk"),
        ):
            result = adb(*command, timeout=30)
            if result.returncode:
                raise RuntimeError("Client bridge probe preparation failed")

        def observe(configuration: dict[str, object]) -> subprocess.CompletedProcess[str]:
            Path("client-config.json").write_text(json.dumps(configuration))
            try:
                for command in (
                    (
                        "push",
                        "/work/client-config.json",
                        "/data/local/tmp/gramlab-bridge/config.json",
                    ),
                    ("shell", "chmod", "0400", "/data/local/tmp/gramlab-bridge/config.json"),
                ):
                    if adb(*command, timeout=10).returncode:
                        raise RuntimeError("Client capability provisioning failed")
                return adb(
                    "shell",
                    "CLASSPATH=/data/local/tmp/gramlab-bridge/client.apk",
                    "/system/bin/app_process",
                    "/system/bin",
                    "org.telegram.gramlab.BridgeProbe",
                    "/data/local/tmp/gramlab-bridge/config.json",
                    timeout=30,
                )
            finally:
                Path("client-config.json").unlink()
                adb("shell", "rm", "/data/local/tmp/gramlab-bridge/config.json", timeout=10)

        result = observe(config)
        rejections = {}
        for name, overrides in (
            ("persona", {"user_id": 3}),
            ("world", {"world_id": other_id}),
            ("capability", {"capability": other_capability}),
            ("external", {"endpoint": "http://192.0.2.1:12345"}),
        ):
            rejected = observe({**config, **overrides})
            rejections[name] = {"returncode": rejected.returncode, "stdout": rejected.stdout}

        class Redirect(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args: object) -> None:
                pass

            def do_GET(self) -> None:
                self.send_response(302)
                self.send_header("Location", str(config["endpoint"]) + "/v1/snapshot")
                self.send_header("Content-Length", "0")
                self.end_headers()

        with HTTPServer(("127.0.0.1", 0), Redirect) as redirect:
            worker = threading.Thread(target=redirect.serve_forever, daemon=True)
            worker.start()
            try:
                rejected = observe(
                    {**config, "endpoint": f"http://10.0.2.2:{redirect.server_port}"}
                )
                rejections["redirect"] = {
                    "returncode": rejected.returncode,
                    "stdout": rejected.stdout,
                }
            finally:
                redirect.shutdown()
                worker.join(timeout=5)
        diagnostics = adb("logcat", "-d", "-v", "brief", timeout=15)
        report = result.stdout + result.stderr + json.dumps(rejections)
        for secret in (capability, bot_token, other_capability):
            if secret in report + diagnostics.stdout + diagnostics.stderr:
                raise RuntimeError("Probe output contained a capability")
        Path("bridge-probe.log").write_text(report)
        Path("bridge-logcat.txt").write_text(diagnostics.stdout + diagnostics.stderr)
    with World.open(directory) as world:
        pending = world.poll_updates(2)
    return {
        "returncode": result.returncode,
        "stdout": result.stdout,
        "pending": pending,
        "rejections": rejections,
    }


if __name__ == "__main__":
    main(probe)
