"""Observe canonical and malformed quoted-code entities through the original TL codec.

This isolated fixture server bypasses Python entity validation only in the
probe. It is neither a production bridge nor real-bot/rendering evidence.
"""

import json
import subprocess
import threading
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

from android_guest import main

from gramlab.world import World


def probe(guest: Callable[..., subprocess.CompletedProcess[str]]) -> dict[str, object]:
    with World.create(Path("codec-world"), seed=17, now=1700000000) as world:
        world.create_user(first_name="Sara", language_code="fa")
        world.create_user(first_name="Echo", username="gramlab_echo_bot", is_bot=True)
        world.open_private_chat(user_id=1, bot_id=2)
        world.send_message(chat_id=1, sender_id=2, text="Codec transport baseline")
        snapshot = world.client_snapshot(1, version=2)
        token, world_id = world.issue_client_token(1), world.world_id
    payload = b""

    class FixtureSnapshot(BaseHTTPRequestHandler):
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

    def adb(*arguments: str, **kwargs: Any) -> None:
        result = guest(*arguments, **kwargs)
        if result.returncode:
            raise RuntimeError(f"Dedicated quoted codec command failed: {arguments[0]}")

    def observe(name: str, content: dict[str, Any] | None) -> dict[str, Any]:
        nonlocal payload
        changed = json.loads(json.dumps(snapshot))
        if content is not None:
            changed["messages"][0].update(content)
        payload = json.dumps(changed).encode()
        result = guest(
            "shell",
            "CLASSPATH=/data/local/tmp/gramlab-quoted.apk",
            "/system/bin/app_process",
            "/system/bin",
            "org.telegram.gramlab.BridgeProbe",
            "/data/local/tmp/gramlab-quoted-config.json",
            timeout=30,
        )
        if token in result.stdout or token in result.stderr:
            raise RuntimeError("Quoted-code diagnostics contained a capability")
        Path(f"{name}-codec.json").write_text(result.stdout)
        return {"returncode": result.returncode, "result": json.loads(result.stdout)}

    adb("push", "/work/client.apk", "/data/local/tmp/gramlab-quoted.apk", timeout=30)
    try:
        with HTTPServer(("127.0.0.1", 0), FixtureSnapshot) as server:
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            try:
                adb(
                    "shell",
                    "-T",
                    "sh",
                    "-c",
                    "'umask 077; cat > /data/local/tmp/gramlab-quoted-config.json'",
                    input=json.dumps(
                        {
                            "endpoint": f"http://10.0.2.2:{server.server_port}",
                            "capability": token,
                            "world_id": world_id,
                            "user_id": 1,
                        }
                    ),
                )
                baseline = observe("baseline", None)
                cases = json.loads(Path("quoted-code-cases.json").read_text())
                return {
                    "baseline": baseline,
                    "cases": {
                        case["name"]: observe(case["name"], case["content"]) for case in cases
                    },
                }
            finally:
                server.shutdown()
                worker.join(timeout=5)
    finally:
        guest("shell", "rm", "-f", "/data/local/tmp/gramlab-quoted-config.json")


if __name__ == "__main__":
    main(probe)
