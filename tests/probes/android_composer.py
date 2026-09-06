"""Actual composer actions, durable world sends, stock client storage and cold recovery."""

import base64
import http.client
import json
import re
import sqlite3
import subprocess
import threading
import time
import xml.etree.ElementTree as ET
from collections.abc import Callable
from contextlib import ExitStack, closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from android_guest import main
from android_live_gap import live_gap
from component_bot import FixtureBot
from jdwp import Debugger

from gramlab.bot_api import BotAPIServer
from gramlab.client_bridge import ClientBridge
from gramlab.world import World

TEXT = "سلام نیم‌فاصله e\u0301 👩🏽‍💻\nhello"
PACKAGE = "org.gramlab.android"


def probe(adb: Callable[..., subprocess.CompletedProcess[str]]) -> dict[str, Any]:
    secrets: list[str] = []

    def command(*arguments: str, **kwargs: Any) -> str:
        result = adb(*arguments, **kwargs)
        if result.returncode:
            retain(
                "guest-command-failure.json",
                json.dumps(
                    {"command": arguments[0], "stdout": result.stdout, "stderr": result.stderr}
                ),
            )
            retain(
                "guest-failure-logcat.txt",
                adb("logcat", "-b", "all", "-d", "-t", "3000", timeout=15).stdout,
            )
            retain(
                "guest-failure-memory.txt", adb("shell", "dumpsys", "meminfo", timeout=15).stdout
            )
            raise RuntimeError(f"Guest command failed: {arguments[0]}")
        return result.stdout

    def retain(name: str, value: str) -> str:
        if any(secret in value for secret in secrets):
            raise RuntimeError("Composer evidence contained a capability")
        Path(name).write_text(value)
        return value

    def trace() -> list[dict[str, Any]]:
        raw = command("shell", "run-as", PACKAGE, "cat", "files/gramlab/trace.jsonl")
        retain("composer-trace.jsonl", raw)
        return [json.loads(line) for line in raw.splitlines()]

    def screen(name: str) -> str:
        command("shell", "uiautomator", "dump", "/data/local/tmp/composer.xml", timeout=15)
        ui = retain(name + ".xml", command("shell", "cat", "/data/local/tmp/composer.xml"))
        command("shell", "screencap", "-p", "/data/local/tmp/composer.png")
        command("pull", "/data/local/tmp/composer.png", "/work/" + name + ".png")
        trace()
        return ui

    def launch() -> str:
        return command(
            "shell",
            "am",
            "start",
            "-W",
            "-n",
            PACKAGE + "/org.telegram.ui.LaunchActivity",
            "-a",
            "com.tmessages.openchat",
            "--el",
            "userId",
            "2",
            timeout=40,
        )

    def tap(ui: str, attribute: str, value: str) -> None:
        # Dedicated guest UIAutomator output; no scenario-provided XML.
        nodes = [
            node
            for node in ET.fromstring(ui).iter("node")  # noqa: S314
            if node.get(attribute) == value and node.get("enabled") == "true"
        ]
        if len(nodes) != 1:
            raise RuntimeError("Composer target is not unique")
        bounds = re.fullmatch(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", nodes[0].get("bounds", ""))
        if bounds is None:
            raise RuntimeError("Composer target has no bounds")
        left, top, right, bottom = map(int, bounds.groups())
        # The Send view includes transparent space over the editor. Its visible circular
        # control occupies the right-hand square, as verified in the retained screenshot.
        x = right - min(right - left, bottom - top) // 2 if value == "Send" else (left + right) // 2
        command("shell", "input", "tap", str(x), str((top + bottom) // 2))

    def await_sends(count: int) -> None:
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            with World.open(Path("world")) as world:
                sends = world.client_snapshot(1, version=2)["sends"]
            if (
                len(sends) == count
                and sum(row["event"] == "send_completed" for row in trace()) >= count
            ):
                return
            time.sleep(0.1)
        screen("send-timeout")
        raise RuntimeError("Actual composer did not complete the authoritative send")

    def database(name: str) -> dict[str, Any]:
        for suffix in ("", "-wal", "-shm"):
            result = adb(
                "shell", "run-as", PACKAGE, "base64", "-w", "0", "files/cache4.db" + suffix
            )
            if result.returncode == 0:
                Path(name + ".db" + suffix).write_bytes(base64.b64decode(result.stdout))
            elif not suffix:
                raise RuntimeError("Client database evidence unavailable")
        with closing(sqlite3.connect(f"file:{name}.db?mode=ro", uri=True)) as connection:
            return {
                "messages": connection.execute(
                    "SELECT uid,mid,send_state FROM messages_v2 ORDER BY uid,mid"
                ).fetchall(),
                "message_dates": connection.execute(
                    "SELECT mid,date FROM messages_v2 ORDER BY mid"
                ).fetchall(),
                "state": connection.execute(
                    "SELECT seq,pts,date,qts FROM params WHERE id=1"
                ).fetchone(),
                "outgoing_read_state": connection.execute(
                    "SELECT mid,read_state FROM messages_v2 WHERE out=1 ORDER BY mid"
                ).fetchall(),
                "pending_correlations": [
                    [str(random_id), mid, uid]
                    for random_id, mid, uid in connection.execute(
                        "SELECT r.random_id,r.mid,r.uid FROM randoms_v2 r JOIN messages_v2 m "
                        "ON m.mid=r.mid AND m.uid=r.uid WHERE r.mid<0 ORDER BY r.mid"
                    )
                ],
            }

    def codec(index: int) -> dict[str, Any]:
        directory = Path(f"codec-world-{index}")
        with World.create(directory, seed=19, now=1700000000) as world:
            world.create_user(first_name="Codec persona")
            world.create_user(first_name="Codec bot", is_bot=True)
            world.open_private_chat(user_id=1, bot_id=2)
            capability = world.issue_client_token(1)
            world_id = world.world_id
            secrets.append(capability)
        with ClientBridge(directory) as server:
            configuration = {
                "endpoint": server.base_url.replace("127.0.0.1", "10.0.2.2"),
                "capability": capability,
                "world_id": world_id,
                "user_id": 1,
            }
            try:
                command(
                    "shell",
                    "-T",
                    "sh",
                    "-c",
                    "'umask 077; cat > /data/local/tmp/composer-codec.json'",
                    input=json.dumps(configuration),
                )
                result = command(
                    "shell",
                    "CLASSPATH=/data/local/tmp/composer-client.apk",
                    "/system/bin/app_process",
                    "/system/bin",
                    "org.telegram.gramlab.ComposerProbe",
                    "/data/local/tmp/composer-codec.json",
                    timeout=30,
                )
                return dict(json.loads(retain(f"composer-codec-{index}.json", result)))
            finally:
                command("shell", "rm", "-f", "/data/local/tmp/composer-codec.json")

    def interrupted_send(
        configuration: dict[str, Any], bot_endpoint: str, token: str, fixture: FixtureBot
    ) -> dict[str, Any]:
        boundary = json.loads(Path("interruption.json").read_text())["boundary"]
        if boundary not in ("before_ack", "before_storage"):
            raise ValueError("Unknown composer interruption boundary")
        breakpoint: dict[str, Any] | None = None
        acknowledged_ui: str | None = None
        committed = threading.Event()
        release = threading.Event()
        accepted: list[dict[str, Any]] = []
        forwarded: list[dict[str, Any]] = []
        target = urlsplit(configuration["endpoint"].replace("10.0.2.2", "127.0.0.1"))

        class HoldResponse(BaseHTTPRequestHandler):
            def log_message(self, *arguments: object) -> None:
                pass

            def forward(self) -> None:
                connection = http.client.HTTPConnection(target.hostname, target.port, timeout=5)
                try:
                    payload = self.rfile.read(int(self.headers.get("Content-Length", "0")))
                    connection.request(
                        self.command,
                        self.path,
                        payload or None,
                        {
                            "Authorization": self.headers["Authorization"],
                            "Content-Type": "application/json",
                        },
                    )
                    response = connection.getresponse()
                    body = response.read()
                    forwarded.append({"method": self.command, "status": response.status})
                    if (
                        self.command == "POST"
                        and self.path == "/v2/messages"
                        and response.status == 200
                    ):
                        accepted.append(json.loads(body)["send"])
                        committed.set()
                        if boundary == "before_ack" and not release.wait(15):
                            return
                    self.send_response(response.status)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Connection", "close")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                except (ConnectionError, TimeoutError) as error:
                    # The client is intentionally killed before receiving this response.
                    forwarded.append({"method": self.command, "failure": type(error).__name__})
                finally:
                    connection.close()

            do_GET = forward
            do_POST = forward

        def configure(value: dict[str, Any]) -> None:
            command(
                "shell",
                "-T",
                "run-as",
                PACKAGE,
                "sh",
                "-c",
                "'cat > files/gramlab/config.json'",
                input=json.dumps(value),
            )

        with ThreadingHTTPServer(("127.0.0.1", 0), HoldResponse) as proxy, ExitStack() as cleanup:
            worker = threading.Thread(target=proxy.serve_forever, daemon=True)
            worker.start()
            try:
                configure(configuration | {"endpoint": f"http://10.0.2.2:{proxy.server_port}"})
                retain("loss-launch.log", launch())
                screen("before-lost-response")
                debugger = None
                if boundary == "before_storage":
                    pid = command("shell", "pidof", PACKAGE).strip()
                    if re.fullmatch(r"[1-9][0-9]*", pid) is None:
                        raise RuntimeError("Expected one dedicated client process")
                    port = int(command("forward", "tcp:0", "jdwp:" + pid).strip())
                    cleanup.callback(command, "forward", "--remove", f"tcp:{port}")
                    debugger = Debugger(port)
                    cleanup.callback(debugger.close)
                    # Killing precedes debugger detach, so cleanup cannot release a held write.
                    cleanup.callback(command, "shell", "am", "force-stop", PACKAGE)
                    debugger.breakpoint(
                        "Lorg/telegram/messenger/MessagesStorage;",
                        "updateMessageStateAndId",
                        "(JJLjava/lang/Integer;IIZII)[J",
                    )
                input_result = command(
                    "shell",
                    "-T",
                    "CLASSPATH=/data/local/tmp/composer-client.apk",
                    "/system/bin/app_process",
                    "/system/bin",
                    "org.telegram.gramlab.GramLabInput",
                    input=json.dumps(
                        {
                            "operation": "compose_and_send",
                            "package": PACKAGE,
                            "expected_text": "",
                            "text": "lost response بازیابی",
                            "send_description": "Send",
                        }
                    ),
                    timeout=20,
                )
                if not committed.wait(5) or len(accepted) != 1:
                    # Retain the actual missed boundary before cleanup; do not repeat Send.
                    with World.open(Path("world")) as world:
                        observed = world.client_snapshot(1, version=2)
                    retain(
                        "missed-commit.json",
                        json.dumps(
                            {
                                "input": json.loads(input_result),
                                "committed": committed.is_set(),
                                "accepted": list(accepted),
                                "forwarded": list(forwarded),
                                "position": observed["message_position"],
                                "sends": observed["sends"],
                            }
                        ),
                    )
                    screen("missed-commit")
                    raise RuntimeError(
                        "Native send did not reach the controlled post-commit boundary"
                    )
                if debugger is not None:
                    breakpoint = debugger.wait_breakpoint(
                        arguments=["random_id", "dialogId", "newId", "useQueue"], timeout=15
                    )
                    retain("storage-breakpoint.json", json.dumps(breakpoint))
                    acknowledged_ui = screen("after-ack-before-storage")
                # Preserve the app database: no package clear, reinstall or synthetic local row.
                command("shell", "am", "force-stop", PACKAGE)
                uncertain = database("uncertain-client")
                retain("uncertain-client.json", json.dumps(uncertain))
            finally:
                release.set()
                proxy.shutdown()
                worker.join(timeout=5)
                if worker.is_alive():
                    raise RuntimeError("Controlled client proxy did not stop")
        configure(configuration)
        recovered_launch = retain("lost-response-restart.log", launch())
        recovered_ui = screen("after-lost-response-restart")
        command("shell", "am", "force-stop", PACKAGE)
        reconciled = database("reconciled-client")
        with World.open(Path("world")) as world:
            updates = world.poll_updates(2)
            sends = world.client_snapshot(1, version=2)["sends"]
        bot = fixture.run({"GRAMLAB_BOT_API": bot_endpoint, "GRAMLAB_BOT_TOKEN": token})
        if bot.returncode:
            raise RuntimeError("Bot did not reply to the recovered composer send")
        retain("loss-reply-launch.log", launch())
        reply_ui = screen("after-lost-response-reply")
        command("shell", "am", "force-stop", PACKAGE)
        replied = database("replied-client")
        with World.open(Path("world")) as world:
            history = world.history(1)
        return {
            "boundary": boundary,
            "breakpoint": breakpoint,
            "acknowledged_ui": acknowledged_ui,
            "accepted": accepted[0],
            "input": json.loads(input_result),
            "uncertain": uncertain,
            "reconciled": reconciled,
            "replied": replied,
            "pending_before_bot": updates,
            "sends": sends,
            "history": history,
            "recovered_ui": recovered_ui,
            "reply_ui": reply_ui,
            "launch": recovered_launch,
        }

    if json.loads(Path("interruption.json").read_text())["boundary"] == "codec":
        command("push", "/work/client.apk", "/data/local/tmp/composer-client.apk", timeout=30)
        command("shell", "chmod", "0444", "/data/local/tmp/composer-client.apk")
        # Repeated fresh worlds expose the observed native connection-reuse and
        # forwarding failures without launching the unrelated chat application.
        return {"codecs": [codec(index) for index in range(8)]}

    with World.create(Path("world"), seed=17, now=1700000000) as world:
        world.create_user(first_name="Sara", language_code="fa")
        world.create_user(first_name="Composer", username="gramlab_composer_bot", is_bot=True)
        world.open_private_chat(user_id=1, bot_id=2)
        world.send_message(chat_id=1, sender_id=2, text="Write a message")
        capability = world.issue_client_token(1)
        token = world.issue_bot_token(2)
        identity = world.client_snapshot(1)["world_id"]
        secrets.extend((capability, token))
    command("install", "--no-streaming", "/work/client.apk", timeout=60)
    with ClientBridge(Path("world")) as bridge, BotAPIServer(Path("world")) as bot_api:
        configuration = {
            "endpoint": bridge.base_url.replace("127.0.0.1", "10.0.2.2"),
            "capability": capability,
            "world_id": identity,
            "user_id": 1,
        }
        boundary = json.loads(Path("interruption.json").read_text())["boundary"]
        if boundary in ("live_gap", "live_gap_timed", "live_gap_paged"):
            return live_gap(
                configuration=configuration,
                bot_endpoint=bot_api.base_url,
                token=token,
                command=command,
                retain=retain,
                launch=launch,
                screen=screen,
                trace=trace,
                await_sends=await_sends,
                database=database,
                clock_step=0 if boundary == "live_gap" else 60,
                backlog=1000 if boundary == "live_gap_paged" else 0,
            )
        command(
            "shell",
            "-T",
            "run-as",
            PACKAGE,
            "sh",
            "-c",
            "'mkdir -p files/gramlab && cat > files/gramlab/config.json'",
            input=json.dumps(configuration),
        )
        launches = [retain("composer-launch.log", launch())]
        ui = screen("before-compose")
        tap(ui, "class", "android.widget.EditText")
        # A fixed ASCII baseline also proves the old APK fails at the real send boundary.
        command("shell", "input", "text", "composer-baseline")
        ui = screen("ascii-entered")
        tap(ui, "content-desc", "Send")
        await_sends(1)
        screen("after-ascii-send")
        command("push", "/work/client.apk", "/data/local/tmp/composer-client.apk", timeout=30)
        command("shell", "chmod", "0444", "/data/local/tmp/composer-client.apk")
        inputs = []
        rejections = []
        for index in range(2):
            expected = ""
            if index == 1:
                # Literal text equal to the custom hint must remain an existing draft,
                # including when its insertion cursor is at zero.
                command("shell", "input", "text", "Message")
                command("shell", "input", "keyevent", "122")
                rejected = adb(
                    "shell",
                    "-T",
                    "CLASSPATH=/data/local/tmp/composer-client.apk",
                    "/system/bin/app_process",
                    "/system/bin",
                    "org.telegram.gramlab.GramLabInput",
                    input=json.dumps(
                        {
                            "operation": "compose_and_send",
                            "package": PACKAGE,
                            "expected_text": "",
                            "text": TEXT,
                            "send_description": "Send",
                        }
                    ),
                    timeout=20,
                )
                if rejected.returncode == 0:
                    raise RuntimeError("Stale draft was overwritten")
                rejections.append(json.loads(retain("stale-composer.json", rejected.stdout)))
                with World.open(Path("world")) as world:
                    if len(world.client_snapshot(1, version=2)["sends"]) != 2:
                        raise RuntimeError("Rejected composer action changed the world")
                screen("stale-composer")
                expected = "Message"
            result = command(
                "shell",
                "-T",
                "CLASSPATH=/data/local/tmp/composer-client.apk",
                "/system/bin/app_process",
                "/system/bin",
                "org.telegram.gramlab.GramLabInput",
                input=json.dumps(
                    {
                        "operation": "compose_and_send",
                        "package": PACKAGE,
                        "expected_text": expected,
                        "text": TEXT,
                        "send_description": "Send",
                    }
                ),
                timeout=20,
            )
            inputs.append(json.loads(result))
            await_sends(len(inputs) + 1)
        fixture = FixtureBot("echo_bot.py")
        bot = fixture.run({"GRAMLAB_BOT_API": bot_api.base_url, "GRAMLAB_BOT_TOKEN": token})
        if bot.returncode:
            raise RuntimeError("Real composer echo bot failed")
        command("shell", "input", "keyevent", "111")
        deadline = time.monotonic() + 20
        while True:
            ui = screen("after-compose")
            if "Echo:" in ui and sum(row["event"] == "events_applied" for row in trace()) >= 6:
                break
            if time.monotonic() > deadline:
                raise RuntimeError("Composer bot replies did not render")
        command("shell", "am", "force-stop", PACKAGE)
        stored = database("sent-client")
        launches.append(retain("composer-restart.log", launch()))
        restarted = screen("after-composer-restart")
        command("shell", "am", "force-stop", PACKAGE)
        recovered = database("restarted-client")
        with World.open(Path("world")) as world:
            snapshot = world.client_snapshot(1, version=2)
            history = world.history(1)
            updates = world.poll_updates(2)
        return {
            "history": history,
            "sends": snapshot["sends"],
            "position": snapshot["message_position"],
            "inputs": inputs,
            "rejections": rejections,
            "stored": stored,
            "recovered": recovered,
            "pending": updates,
            "launches": launches,
            "restarted": restarted,
            "loss": interrupted_send(configuration, bot_api.base_url, token, fixture),
        }


if __name__ == "__main__":
    main(probe)
