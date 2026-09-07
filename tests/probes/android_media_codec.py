"""Exercise independently authored v3 media snapshots through the native TL codec."""

import json
import subprocess
import threading
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

from android_guest import main


def probe(guest: Callable[..., subprocess.CompletedProcess[str]]) -> dict[str, object]:
    cases = json.loads(Path("media-codec-cases.json").read_text())
    capability = "gramlab-client_" + "c" * 43
    world_id = "media-codec-world"
    payload = b""
    requested_version = 3

    class FixtureSnapshot(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:
            pass

        def do_GET(self) -> None:
            expected = f"/v{requested_version}/snapshot"
            accepted = (
                self.path == expected
                and self.headers.get("Authorization") == f"Bearer {capability}"
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
            raise RuntimeError(f"Dedicated media codec command failed: {arguments[0]}")

    def observe(case: dict[str, Any], port: int) -> dict[str, Any]:
        nonlocal payload, requested_version
        requested_version = case.get("bridge_version", 3)
        payload = json.dumps(case["snapshot"]).encode()
        adb(
            "shell",
            "-T",
            "sh",
            "-c",
            "'umask 077; cat > /data/local/tmp/gramlab-media-codec-config.json'",
            input=json.dumps(
                {
                    "endpoint": f"http://10.0.2.2:{port}",
                    "capability": capability,
                    "world_id": world_id,
                    "user_id": 1,
                    "bridge_version": requested_version,
                }
            ),
        )
        result = guest(
            "shell",
            "CLASSPATH=/data/local/tmp/gramlab-media-codec.apk",
            "/system/bin/app_process",
            "/system/bin",
            "org.telegram.gramlab.BridgeProbe",
            "/data/local/tmp/gramlab-media-codec-config.json",
            timeout=30,
        )
        if capability in result.stdout or capability in result.stderr:
            raise RuntimeError("Media codec diagnostics contained a capability")
        process = {
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
        Path(f"{case['name']}-codec-process.json").write_text(json.dumps(process, indent=2))
        try:
            decoded = json.loads(result.stdout)
        except json.JSONDecodeError:
            return {"returncode": result.returncode, "invalid_json": True}
        return {"returncode": result.returncode, "result": decoded}

    adb("push", "/work/client.apk", "/data/local/tmp/gramlab-media-codec.apk", timeout=30)
    try:
        with HTTPServer(("127.0.0.1", 0), FixtureSnapshot) as server:
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            try:
                return {
                    "cases": {case["name"]: observe(case, server.server_port) for case in cases}
                }
            finally:
                server.shutdown()
                worker.join(timeout=5)
    finally:
        guest("shell", "rm", "-f", "/data/local/tmp/gramlab-media-codec-config.json")


if __name__ == "__main__":
    main(probe)
