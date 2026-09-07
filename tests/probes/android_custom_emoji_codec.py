"""Feed neutral custom emoji envelopes through the real Android bridge and TL codec."""

import json
import re
import subprocess
import threading
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

from android_guest import main


def probe(guest: Callable[..., subprocess.CompletedProcess[str]]) -> dict[str, object]:
    cases = json.loads(Path("custom-emoji-codec-cases.json").read_text())
    capability = "gramlab-client_" + "c" * 43
    current: dict[str, Any] = {}
    snapshots: list[dict[str, Any]] = []
    requests: list[str] = []

    class FixtureBridge(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:
            pass

        def respond(self, accepted: bool, value: dict[str, Any], status: int = 200) -> None:
            payload = json.dumps(value if accepted else {}).encode()
            self.send_response(status if accepted else 401)
            self.send_header("Content-Type", "application/json")
            self.send_header("Connection", "close")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def authorized(self) -> bool:
            return self.headers.get("Authorization") == f"Bearer {capability}"

        def do_GET(self) -> None:
            requests.append(self.path)
            version = current.get("bridge_version", 4)
            if self.path == f"/v{version}/snapshot" and snapshots:
                self.respond(self.authorized(), snapshots.pop(0))
            elif self.path == f"/v{version}/changes?after=0&limit=100" and "changes" in current:
                self.respond(self.authorized(), current["changes"])
            else:
                self.respond(False, {})

        def do_POST(self) -> None:
            requests.append(self.path)
            value = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
            version = current.get("bridge_version", 4)
            if self.path == "/v4/custom-emoji-documents":
                accepted = self.authorized() and value == {
                    "custom_emoji_ids": current["expected_ids"]
                }
                self.respond(accepted, current["documents"], current.get("document_status", 200))
                return
            path = f"/v{version}/callbacks" if version >= 3 else "/v1/callbacks"
            accepted = (
                self.authorized()
                and self.path == path
                and "callback" in current
                and set(value) == {"request_id", "chat_id", "message_id", "data"}
                and re.fullmatch(r"[A-Za-z0-9_-]{1,128}", value["request_id"]) is not None
                and value["chat_id"] == 1
                and value["message_id"] == 1
                and value["data"] == "mention-codec"
            )
            self.respond(accepted, current.get("callback", {}))

    def adb(*arguments: str, **kwargs: Any) -> None:
        result = guest(*arguments, **kwargs)
        if result.returncode:
            raise RuntimeError(f"Dedicated custom emoji codec command failed: {arguments[0]}")

    def observe(case: dict[str, Any], port: int) -> dict[str, Any]:
        nonlocal current, snapshots, requests
        current = case
        snapshots = list(case.get("snapshots", [case["snapshot"]]))
        requests = []
        config = {
            "endpoint": f"http://10.0.2.2:{port}",
            "capability": capability,
            "world_id": "custom-emoji-codec-world",
            "user_id": 1,
            "bridge_version": case.get("bridge_version", 4),
        }
        adb(
            "shell",
            "-T",
            "sh",
            "-c",
            "'umask 077; cat > /data/local/tmp/gramlab-custom-emoji-codec-config.json'",
            input=json.dumps(config),
        )
        adb(
            "shell",
            "-T",
            "sh",
            "-c",
            "'umask 077; cat > /data/local/tmp/gramlab-custom-emoji-codec-ids.json'",
            input=json.dumps(case.get("requested_ids", [])),
        )
        try:
            result = guest(
                "shell",
                "CLASSPATH=/data/local/tmp/gramlab-custom-emoji-codec.apk",
                "/system/bin/app_process",
                "/system/bin",
                "org.telegram.gramlab.BridgeProbe",
                "/data/local/tmp/gramlab-custom-emoji-codec-config.json",
                case.get("mode", "custom-emoji"),
                "/data/local/tmp/gramlab-custom-emoji-codec-ids.json",
                timeout=30,
            )
        except subprocess.TimeoutExpired as error:

            def redact(value: bytes | str | None) -> str:
                text = value.decode(errors="replace") if isinstance(value, bytes) else value or ""
                return text.replace(capability, "<REDACTED>")

            Path(f"{case['name']}-codec-timeout.json").write_text(
                json.dumps(
                    {
                        "stdout": redact(error.stdout),
                        "stderr": redact(error.stderr),
                        "requests": requests,
                        "unconsumed_snapshots": len(snapshots),
                    },
                    indent=2,
                )
            )
            raise RuntimeError(f"Custom emoji codec timed out: {case['name']}") from None
        if capability in result.stdout or capability in result.stderr:
            raise RuntimeError("Custom emoji codec diagnostics contained a capability")
        Path(f"{case['name']}-codec-process.json").write_text(
            json.dumps(
                {
                    "returncode": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "requests": requests,
                    "unconsumed_snapshots": len(snapshots),
                },
                indent=2,
            )
        )
        try:
            decoded = json.loads(result.stdout)
        except json.JSONDecodeError:
            return {"returncode": result.returncode, "invalid_json": True}
        return {"returncode": result.returncode, "result": decoded}

    adb("push", "/work/client.apk", "/data/local/tmp/gramlab-custom-emoji-codec.apk", timeout=30)
    try:
        with HTTPServer(("127.0.0.1", 0), FixtureBridge) as server:
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
        guest(
            "shell",
            "rm",
            "-f",
            "/data/local/tmp/gramlab-custom-emoji-codec-config.json",
            "/data/local/tmp/gramlab-custom-emoji-codec-ids.json",
            "/data/local/tmp/gramlab-custom-emoji-codec.apk",
        )


if __name__ == "__main__":
    main(probe)
