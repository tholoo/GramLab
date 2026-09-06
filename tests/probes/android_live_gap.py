"""Hold real polling delivery; observe stock difference recovery without a restart."""

import http.client
import json
import threading
import time
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

from component_bot import FixtureBot

from gramlab.world import World

PACKAGE = "org.gramlab.android"


def live_gap(
    *,
    configuration: dict[str, Any],
    bot_endpoint: str,
    token: str,
    command: Callable[..., str],
    retain: Callable[[str, str], str],
    launch: Callable[[], str],
    screen: Callable[[str], str],
    trace: Callable[[], list[dict[str, Any]]],
    await_sends: Callable[[int], None],
    database: Callable[[str], dict[str, Any]],
) -> dict[str, Any]:
    held = threading.Event()
    release = threading.Event()
    differences: list[dict[str, Any]] = []
    exchanges: list[dict[str, Any]] = []
    target = urlsplit(configuration["endpoint"].replace("10.0.2.2", "127.0.0.1"))

    class HoldPolls(BaseHTTPRequestHandler):
        def log_message(self, *arguments: object) -> None:
            pass

        def forward(self) -> None:
            route = urlsplit(self.path)
            query = parse_qs(route.query)
            record: dict[str, Any] = {"method": self.command, "path": route.path}
            exchanges.append(record)
            if route.path == "/v2/changes":
                record.update(after=int(query["after"][0]), limit=int(query["limit"][0]))
                if record["limit"] == 100 and not release.is_set():
                    # Hold every ordinary poll, including retries after native read timeout.
                    # No changes, cursors, history or acknowledgments are invented or edited.
                    record["held"] = True
                    held.set()
                    if not release.wait(90):
                        record["failure"] = "gate_timeout"
                        return
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
                record["status"] = response.status
                if route.path == "/v2/changes" and record["limit"] == 1000:
                    result = json.loads(body)
                    differences.append(
                        {
                            "after": record["after"],
                            "limit": record["limit"],
                            "cursor": result["cursor"],
                            "head": result["head"],
                            "positions": [change["position"] for change in result["changes"]],
                            "status": response.status,
                        }
                    )
                self.send_response(response.status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Connection", "close")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except (ConnectionError, TimeoutError) as error:
                record["failure"] = type(error).__name__
            finally:
                connection.close()

        do_GET = forward
        do_POST = forward

    def compose(text: str, count: int) -> dict[str, Any]:
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
                    "expected_text": "",
                    "text": text,
                    "send_description": "Send",
                }
            ),
            timeout=20,
        )
        retain(f"gap-input-{count}.json", result)
        await_sends(count)
        return dict(json.loads(result))

    fixture = FixtureBot("echo_bot.py")
    bots: list[list[dict[str, Any]]] = []

    def reply() -> None:
        bot = fixture.run({"GRAMLAB_BOT_API": bot_endpoint, "GRAMLAB_BOT_TOKEN": token})
        if bot.returncode:
            raise RuntimeError("Real bot failed during live gap recovery")
        bots.append(json.loads(retain(f"gap-bot-{len(bots)}.json", bot.stdout)))

    with ThreadingHTTPServer(("127.0.0.1", 0), HoldPolls) as proxy:
        worker = threading.Thread(target=proxy.serve_forever, daemon=True)
        worker.start()
        try:
            command(
                "shell",
                "-T",
                "run-as",
                PACKAGE,
                "sh",
                "-c",
                "'mkdir -p files/gramlab && cat > files/gramlab/config.json'",
                input=json.dumps(
                    configuration | {"endpoint": f"http://10.0.2.2:{proxy.server_port}"}
                ),
            )
            command("push", "/work/client.apk", "/data/local/tmp/composer-client.apk", timeout=30)
            command("shell", "chmod", "0444", "/data/local/tmp/composer-client.apk")
            retain("gap-launch.log", launch())
            screen("gap-before")
            before_trace = trace()
            if any(
                row["method"] in ("TL_updates_getDifference", "TL_updates_getState")
                for row in before_trace
            ):
                raise RuntimeError("Live gap requires an unused first native difference")
            if not held.wait(5):
                raise RuntimeError("Ordinary native polling did not enter the controlled gate")
            pids = [command("shell", "pidof", PACKAGE).strip()]
            with World.open(Path("world")) as world:
                # An explicitly synthetic action by the same persona, as on another client.
                world.send_message(chat_id=1, sender_id=1, text="delayed message پیام")
            reply()
            withheld_ui = screen("gap-withheld")
            inputs = [compose("live gap بازیابی", 1)]
            deadline = time.monotonic() + 25
            while True:
                recovered_ui = screen("gap-recovered")
                recovered_trace = trace()
                if all(
                    text in recovered_ui
                    for text in (
                        "delayed message پیام",
                        "Echo: delayed message پیام",
                        "live gap بازیابی",
                    )
                ) and any(
                    row["event"] == "response" and row["method"] == "TL_updates_getDifference"
                    for row in recovered_trace
                ):
                    break
                if time.monotonic() > deadline:
                    raise RuntimeError("Native difference did not recover the withheld messages")
            # The replica must have caught up while every ordinary poll is still held.
            if release.is_set() or any(row["event"] == "events_applied" for row in recovered_trace):
                raise RuntimeError("Polling contaminated the native difference proof")
            pids.append(command("shell", "pidof", PACKAGE).strip())
            retain("gap-recovered-trace.json", json.dumps(recovered_trace))
            release.set()
            # Normal send completion follows stock storage/UI queues, after difference writes.
            inputs.append(compose("after recovery ادامه", 2))
            reply()
            deadline = time.monotonic() + 25
            while True:
                final_ui = screen("gap-replied")
                final_trace = trace()
                if (
                    "Echo: live gap بازیابی" in final_ui
                    and "Echo: after recovery ادامه" in final_ui
                    and sum(row["event"] == "events_applied" for row in final_trace) == 6
                ):
                    break
                if time.monotonic() > deadline:
                    raise RuntimeError("Replies after live gap recovery did not render")
            pids.append(command("shell", "pidof", PACKAGE).strip())
            command("shell", "am", "force-stop", PACKAGE)
            stored = database("gap-client")
            with World.open(Path("world")) as world:
                snapshot = world.client_snapshot(1, version=2)
                result = {
                    "history": world.history(1),
                    "sends": snapshot["sends"],
                    "position": snapshot["message_position"],
                    "pending": world.poll_updates(2),
                    "stored": stored,
                    "inputs": inputs,
                    "bots": bots,
                    "pids": pids,
                    "before_trace": before_trace,
                    "recovered_trace": recovered_trace,
                    "final_trace": final_trace,
                    "differences": differences,
                    "withheld_ui": withheld_ui,
                    "recovered_ui": recovered_ui,
                    "final_ui": final_ui,
                }
            retain("gap-observed.json", json.dumps(result))
            return result
        finally:
            release.set()
            proxy.shutdown()
            worker.join(timeout=5)
            retain("gap-http.json", json.dumps(exchanges))
            command("shell", "am", "force-stop", PACKAGE)
            if worker.is_alive():
                raise RuntimeError("Controlled polling proxy did not stop")
