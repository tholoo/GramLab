"""Feed atomic-media-group envelopes through the actual Android bridge codec."""

from __future__ import annotations

import json
import re
import subprocess
import threading
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

from android_guest import main

_CLIENT = "/data/local/tmp/gramlab-media-groups-client.apk"
_PROBE = "/data/local/tmp/gramlab-media-groups-probe.apk"
_CONFIG = "/data/local/tmp/gramlab-media-groups-config.json"
_REQUESTED = "/data/local/tmp/gramlab-media-groups-requested.json"
_LIMIT = 1024 * 1024


def probe(guest: Callable[..., subprocess.CompletedProcess[str]]) -> dict[str, object]:
    cases = json.loads(Path("media-groups-codec-cases.json").read_text())
    capability = "gramlab-client_" + "g" * 43
    current: dict[str, Any] = {}
    snapshots: list[dict[str, Any]] = []
    requests: list[dict[str, Any]] = []

    class FixtureBridge(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:
            pass

        def respond(self, status: int, value: dict[str, Any]) -> None:
            payload = json.dumps(value, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Connection", "close")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def authorized(self) -> bool:
            return self.headers.get("Authorization") == f"Bearer {capability}"

        def do_GET(self) -> None:
            requests.append({"method": "GET", "path": self.path})
            if not self.authorized():
                self.respond(401, {})
                return
            if self.path in {"/v5/snapshot", "/v6/snapshot"} and snapshots:
                self.respond(200, snapshots.pop(0))
                return
            replies = current.get("get", {})
            response = replies.get(self.path)
            if response is not None:
                self.respond(int(response.get("status", 200)), response["body"])
                return
            self.respond(404, {})

        def do_POST(self) -> None:
            size = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(size))
            requests.append({"method": "POST", "path": self.path, "body": body})
            if not self.authorized():
                self.respond(401, {})
                return
            expected = current.get("expected_request", {}).get(self.path)
            if expected is not None:
                accepted = set(body) == set(expected["keys"])
                accepted = accepted and all(
                    body.get(key) == value for key, value in expected.get("values", {}).items()
                )
                if expected.get("generated_request_id"):
                    accepted = accepted and isinstance(body.get("request_id"), str)
                    accepted = (
                        accepted
                        and re.fullmatch(r"[A-Za-z0-9_-]{1,128}", body["request_id"]) is not None
                    )
                if not accepted:
                    self.respond(400, {})
                    return
            response = current.get("post", {}).get(self.path)
            if response is None:
                self.respond(404, {})
                return
            self.respond(int(response.get("status", 200)), response["body"])

    def require_success(*arguments: str, **kwargs: Any) -> None:
        result = guest(*arguments, **kwargs)
        if result.returncode:
            raise RuntimeError(f"Dedicated media-group codec command failed: {arguments[0]}")

    def write_guest(path: str, value: object) -> None:
        require_success(
            "shell",
            "-T",
            "sh",
            "-c",
            f"'umask 077; cat > {path}'",
            input=json.dumps(value, ensure_ascii=False),
        )

    def observe(case: dict[str, Any], port: int) -> dict[str, Any]:
        nonlocal current, snapshots, requests
        current = case
        snapshots = list(case["snapshots"])
        requests = []
        config = {
            "endpoint": f"http://10.0.2.2:{port}",
            "capability": capability,
            "world_id": case.get("world_id", "media-groups-codec-world"),
            "user_id": case.get("user_id", 1),
            "bridge_version": case.get("bridge_version", 6),
        }
        write_guest(_CONFIG, config)
        arguments = [
            "shell",
            f"CLASSPATH={_PROBE}:{_CLIENT}",
            "/system/bin/app_process",
            "/system/bin",
            "org.telegram.gramlab.MediaGroupsCodecProbe",
            _CONFIG,
            case.get("mode", "snapshot"),
        ]
        if "requested" in case:
            write_guest(_REQUESTED, case["requested"])
            arguments.append(_REQUESTED)
        result = guest(*arguments, timeout=30)
        if capability in result.stdout or capability in result.stderr:
            raise RuntimeError("Media-group codec diagnostics contained a capability")
        if len(result.stdout.encode()) > _LIMIT or len(result.stderr.encode()) > _LIMIT:
            raise RuntimeError("Media-group codec process output exceeds the retained bound")
        Path(f"{case['name']}-codec-process.json").write_text(
            json.dumps(
                {
                    "returncode": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "requests": requests,
                    "unconsumed_snapshots": len(snapshots),
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n"
        )
        try:
            decoded = json.loads(result.stdout)
        except json.JSONDecodeError:
            decoded = {"invalid_json": True}
        return {"returncode": result.returncode, "result": decoded, "requests": list(requests)}

    require_success("push", "/work/client.apk", _CLIENT, timeout=30)
    require_success("push", "/work/media-groups-probe.apk", _PROBE, timeout=30)
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
        guest("shell", "rm", "-f", _CONFIG, _REQUESTED, _CLIENT, _PROBE)


if __name__ == "__main__":
    main(probe)
