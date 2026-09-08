"""Observe original forced-document UI, download, callback reuse and cold restart."""

from __future__ import annotations

import http.client
import json
import re
import shlex
import socket
import subprocess
import threading
import time
import xml.etree.ElementTree as ET
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import TracebackType
from typing import Any, Self, cast
from urllib.parse import urlsplit

from android_guest import main
from document_round_trip import DOCUMENT_BYTES, SCENE, run

PACKAGE = "org.gramlab.android"
CONFIG = "files/gramlab/config.json"
TRACE = "files/gramlab/trace.jsonl"
BOUNDS = re.compile(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]")
MEDIA_EVENTS = {
    "media_load_start",
    "media_load_coalesced",
    "media_load_success",
    "media_load_failure",
    "media_load_cancel",
    "media_cache_hit",
}


class BridgeProxy:
    """Bounded v5 forwarder that records native document and asset requests."""

    def __init__(self, endpoint: str, capability: str) -> None:
        if [name for _, name in socket.if_nameindex()] != ["lo"]:
            raise RuntimeError("Document proxy requires the isolated loopback runtime")
        self._lock = threading.Lock()
        self._endpoint = self._port(endpoint)
        self._capability = capability
        self._phase = "initial"
        self._requests: list[dict[str, Any]] = []
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def setup(self) -> None:
                super().setup()
                self.connection.settimeout(5)

            def log_message(self, format: str, *args: Any) -> None:
                pass

            def do_GET(self) -> None:
                self.forward()

            def do_POST(self) -> None:
                self.forward()

            def forward(self) -> None:
                document = re.fullmatch(r"/v5/documents/([1-9][0-9]{0,18})", self.path)
                asset = re.fullmatch(r"/v5/assets/([1-9][0-9]{0,18})", self.path)
                versioned_get = re.fullmatch(
                    r"/v5/(?:snapshot|changes\?after=[0-9]+&limit=[0-9]+|"
                    r"callbacks/[A-Za-z0-9_-]{1,128})",
                    self.path,
                )
                allowed = (
                    self.command == "GET"
                    and (document is not None or asset is not None or versioned_get is not None)
                ) or (
                    self.command == "POST"
                    and self.path in ("/v5/callbacks", "/v5/messages", "/v5/custom-emoji-documents")
                )
                if self.headers.get_all("Authorization", []) != ["Bearer " + owner._capability]:
                    self.send_error(401, "Unauthorized")
                    return
                if not allowed or self.headers.get("Transfer-Encoding") is not None:
                    self.send_error(400, "Unsupported fixture route")
                    return
                try:
                    lengths = self.headers.get_all("Content-Length", [])
                    if len(lengths) > 1:
                        raise ValueError
                    length = int(lengths[0]) if lengths else 0
                    if not 0 <= length <= 65536:
                        raise ValueError
                except ValueError:
                    self.send_error(400, "Invalid request size")
                    return
                payload = self.rfile.read(length) if length else None
                kind = (
                    "document" if document is not None else "asset" if asset is not None else None
                )
                identifier = (
                    document[1] if document is not None else asset[1] if asset is not None else None
                )
                with owner._lock:
                    port = owner._endpoint
                    record: dict[str, Any] = {
                        "sequence": len(owner._requests) + 1,
                        "phase": owner._phase,
                        "method": self.command,
                        "path": self.path,
                        "kind": kind,
                        "identifier": identifier,
                        "status": None,
                        "bytes": 0,
                        "started_ns": time.monotonic_ns(),
                        "finished_ns": None,
                        "error": None,
                    }
                    owner._requests.append(record)
                connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
                try:
                    headers = {
                        "Authorization": "Bearer " + owner._capability,
                        "Connection": "close",
                    }
                    for name in ("Content-Type", "Accept", "Range"):
                        if self.headers.get(name) is not None:
                            headers[name] = self.headers[name]
                    connection.request(self.command, self.path, payload, headers)
                    response = connection.getresponse()
                    with owner._lock:
                        record["status"] = response.status
                    self.send_response(response.status)
                    for name in ("Content-Type", "Content-Length", "Cache-Control", "Location"):
                        value = response.getheader(name)
                        if value is not None:
                            self.send_header(name, value)
                    self.send_header("Connection", "close")
                    self.end_headers()
                    while chunk := response.read1(65536):
                        self.wfile.write(chunk)
                        self.wfile.flush()
                        with owner._lock:
                            record["bytes"] += len(chunk)
                    if response.length not in (None, 0):
                        with owner._lock:
                            record["error"] = "transport_error"
                        self.close_connection = True
                except (OSError, http.client.HTTPException):
                    with owner._lock:
                        record["error"] = "transport_error"
                    self.close_connection = True
                finally:
                    connection.close()
                    with owner._lock:
                        record["finished_ns"] = time.monotonic_ns()

        class Server(ThreadingHTTPServer):
            daemon_threads = False

        self._server = Server(("127.0.0.1", 0), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    @staticmethod
    def _port(endpoint: str) -> int:
        parsed = urlsplit(endpoint)
        if (
            parsed.scheme != "http"
            or parsed.hostname != "127.0.0.1"
            or parsed.port is None
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path not in ("", "/")
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("Proxy target must be the selected loopback bridge")
        return parsed.port

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self._server.server_port}"

    def retarget(self, endpoint: str) -> None:
        with self._lock:
            self._endpoint = self._port(endpoint)

    def phase(self, name: str) -> None:
        with self._lock:
            self._phase = name

    def requests(self) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(record) for record in self._requests]

    def __enter__(self) -> Self:
        self._thread.start()
        return self

    def __exit__(
        self,
        kind: type[BaseException] | None,
        value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=5)


def probe(guest: Callable[..., subprocess.CompletedProcess[str]]) -> dict[str, object]:
    capability = ""
    proxy: BridgeProxy | None = None
    captures: dict[str, str] = {}
    launches: dict[str, str] = {}
    taps: dict[str, Any] = {}
    cache: dict[str, Any] = {}
    phases: dict[str, dict[str, int]] = {}
    active_phase = ""

    def retain(name: str, value: str) -> str:
        if capability and capability in value:
            raise RuntimeError("Document diagnostics contained a capability")
        Path(name).write_text(value)
        return value

    def adb(*arguments: str, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        result = guest(*arguments, **kwargs)
        if result.returncode:
            retain("guest-command-error.txt", result.stdout + result.stderr)
            raise RuntimeError(f"Dedicated document guest command failed: {arguments[0]}")
        return result

    def trace(name: str) -> list[dict[str, Any]]:
        raw = adb("shell", "run-as", PACKAGE, "cat", TRACE).stdout
        retain(name + "-trace.jsonl", raw)
        return [json.loads(line) for line in raw.splitlines()]

    def screenshot(name: str) -> None:
        adb("shell", "screencap", "-p", "/data/local/tmp/document-ui.png")
        adb("pull", "/data/local/tmp/document-ui.png", f"/work/{name}.png")

    def screen(name: str, labels: tuple[str, ...], *, applied: bool = False) -> str:
        deadline = time.monotonic() + 40
        ui = ""
        while time.monotonic() < deadline:
            adb("shell", "uiautomator", "dump", "/data/local/tmp/document-ui.xml", timeout=15)
            ui = adb("shell", "cat", "/data/local/tmp/document-ui.xml").stdout
            rows = trace(name)
            if all(label in ui for label in labels) and (
                not applied or any(row.get("event") == "events_applied" for row in rows)
            ):
                break
            time.sleep(0.2)
        else:
            screenshot(name + "-failure")
            retain(name + "-failure.xml", ui)
            retain(name + "-failure-logcat.txt", adb("logcat", "-d", "-t", "2000").stdout)
            raise RuntimeError(f"Original document scene did not render during {name}")
        captures[name] = retain(name + ".xml", ui)
        screenshot(name)
        return ui

    def target(ui: str, label: str) -> list[int]:
        root = ET.fromstring(ui)  # noqa: S314
        parents = {child: parent for parent in root.iter() for child in parent}
        candidates: list[tuple[int, int, list[int]]] = []
        for semantic in root.iter("node"):
            if label not in semantic.get("text", "") + semantic.get("content-desc", ""):
                continue
            node: ET.Element | None = semantic
            while node is not None:
                match = BOUNDS.fullmatch(node.get("bounds", ""))
                if match:
                    values = [int(value) for value in match.groups()]
                    if 0 <= values[0] < values[2] <= 320 and 0 <= values[1] < values[3] <= 640:
                        candidates.append(
                            (
                                0 if node.get("clickable") == "true" else 1,
                                (values[2] - values[0]) * (values[3] - values[1]),
                                values,
                            )
                        )
                if node.get("clickable") == "true":
                    break
                node = parents.get(node)
        if not candidates:
            raise RuntimeError("Original document target lacks current semantic bounds: " + label)
        return min(candidates)[2]

    def begin_phase(name: str) -> None:
        nonlocal active_phase
        rows = trace(name + "-boundary") if active_phase else []
        if active_phase:
            phases[active_phase]["trace_end"] = len(rows)
            assert proxy is not None
            phases[active_phase]["request_end"] = len(proxy.requests())
        active_phase = name
        assert proxy is not None
        proxy.phase(name)
        phases[name] = {
            "trace_start": len(rows),
            "request_start": len(proxy.requests()),
        }

    def write_config(configuration: dict[str, Any]) -> None:
        nonlocal capability
        capability = configuration["capability"]
        if configuration.get("bridge_version") != 5 or configuration.get("user_id") != 1:
            raise RuntimeError("Document UI requires explicit v5 persona 1")
        assert proxy is not None
        native = {key: value for key, value in configuration.items() if key != "stage"} | {
            "endpoint": proxy.base_url.replace("127.0.0.1", "10.0.2.2")
        }
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
        launches[name] = retain(name + "-launch.log", result.stdout + result.stderr)

    def cache_files(name: str) -> dict[str, Any]:
        external = f"/storage/emulated/0/Android/data/{PACKAGE}"
        paths = [
            (path, True)
            for path in adb(
                "shell", "run-as", PACKAGE, "find", ".", "-type", "f"
            ).stdout.splitlines()
        ]
        paths += [
            (path, False)
            for path in adb("shell", "find", external, "-type", "f").stdout.splitlines()
        ]
        copies: list[dict[str, str | int]] = []
        for path, internal in paths:
            if Path(path).name not in (SCENE["file_name"], "-1_-1.pdf"):
                continue
            quoted = shlex.quote(path)
            command = ("shell", "run-as", PACKAGE) if internal else ("shell",)
            digest = adb(*command, "toybox", "sha256sum", quoted).stdout.split()[0]
            size = int(adb(*command, "toybox", "wc", "-c", quoted).stdout.split()[0])
            copies.append({"path": path, "sha256": digest, "size": size})
        partials = sorted(
            path for path, _ in paths if ".gramlab-" in path and path.endswith(".part")
        )
        value = {
            "copies": sorted(copies, key=lambda item: str(item["path"])),
            "partials": partials,
        }
        cache[name] = value
        retain(name + "-cache.json", json.dumps(value, ensure_ascii=False, indent=2))
        return value

    def wait_for_download(name: str, request_start: int) -> None:
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            requests = proxy.requests() if proxy is not None else []
            rows = trace(name)
            current = requests[request_start:]
            if (
                any(
                    row["kind"] == "document"
                    and row["identifier"] == "1"
                    and row["status"] == 200
                    and row["bytes"] == len(DOCUMENT_BYTES)
                    and row["error"] is None
                    for row in current
                )
                and any(
                    row.get("event") == "media_load_success"
                    and row.get("document_id") == "1"
                    and row.get("digest_ok") is True
                    for row in rows
                )
                and cache_files(name)["copies"]
            ):
                return
            time.sleep(0.2)
        raise RuntimeError("Original document download did not complete")

    def show(configuration: dict[str, Any]) -> str:
        nonlocal proxy
        name = str(configuration["stage"])
        if name not in ("initial", "reused", "restart"):
            raise RuntimeError("Unexpected document UI phase")
        if proxy is None:
            adb("install", "--no-streaming", "/work/client.apk", timeout=60)
            proxy = BridgeProxy(configuration["endpoint"], configuration["capability"])
            proxy.__enter__()
            write_config(configuration)
            launch("initial")
            begin_phase("initial")
            ui = screen(
                "initial",
                (SCENE["file_name"], SCENE["caption"], SCENE["button_text"]),
            )
            before = len(proxy.requests())
            if any(row["kind"] == "document" for row in proxy.requests()):
                raise RuntimeError("Document transfer started before the original download tap")
            bounds = target(ui, SCENE["file_name"])
            taps["download"] = {
                "label": SCENE["file_name"],
                "bounds": bounds,
                "requests_before": before,
            }
            adb(
                "shell",
                "input",
                "tap",
                str((bounds[0] + bounds[2]) // 2),
                str((bounds[1] + bounds[3]) // 2),
            )
            wait_for_download("downloaded", before)
            taps["download"]["requests_after"] = len(proxy.requests())
            screen(
                "downloaded",
                (SCENE["file_name"], SCENE["caption"], SCENE["button_text"]),
            )
            return ui

        proxy.retarget(configuration["endpoint"])
        if name == "reused":
            ui = screen("reused", (SCENE["file_name"], SCENE["reuse_caption"]), applied=True)
            cache_files("reused")
            return ui

        begin_phase("restart")
        write_config(configuration)
        adb("shell", "am", "force-stop", PACKAGE)
        launch("restart")
        ui = screen("restart-bottom", (SCENE["file_name"], SCENE["reuse_caption"]))
        for attempt in range(5):
            adb("shell", "uiautomator", "dump", "/data/local/tmp/document-ui.xml", timeout=15)
            older = adb("shell", "cat", "/data/local/tmp/document-ui.xml").stdout
            if SCENE["caption"] in older and SCENE["button_text"] in older:
                captures["restart-top"] = retain("restart-top.xml", older)
                screenshot("restart-top")
                break
            if attempt == 4:
                retain("restart-top-failure.xml", older)
                raise RuntimeError("Cold restart did not retain the original document and keyboard")
            adb("shell", "input", "swipe", "160", "220", "160", "520", "300")
            time.sleep(0.3)
        cache_files("restart")
        return ui

    def tap(name: str, label: str) -> None:
        if name != "initial" or label != SCENE["button_text"] or proxy is None:
            raise RuntimeError("Unexpected document callback target")
        begin_phase("reused")
        ui = captures["downloaded"]
        bounds = target(ui, label)
        taps["callback"] = {"label": label, "bounds": bounds}
        adb(
            "shell",
            "input",
            "tap",
            str((bounds[0] + bounds[2]) // 2),
            str((bounds[1] + bounds[3]) // 2),
        )

    def observe() -> dict[str, Any]:
        rows = trace("final")
        phases[active_phase]["trace_end"] = len(rows)
        assert proxy is not None
        phases[active_phase]["request_end"] = len(proxy.requests())
        return {
            "captures": captures,
            "launches": launches,
            "taps": taps,
            "cache": cache,
            "phases": phases,
            "requests": proxy.requests(),
            "trace": rows,
            "accounts": adb("shell", "dumpsys", "account").stdout,
        }

    try:
        return cast(dict[str, object], run(show, tap, observe))
    finally:
        guest("shell", "am", "force-stop", PACKAGE)
        if proxy is not None:
            retain("native-document-ui-requests.json", json.dumps(proxy.requests(), indent=2))
            proxy.__exit__(None, None, None)
        guest("shell", "rm", "-f", "/data/local/tmp/document-ui.xml")


if __name__ == "__main__":
    main(probe)
