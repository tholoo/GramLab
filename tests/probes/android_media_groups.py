"""One-AVD codec, stock album UI, transfer retry and cold-cache acceptance."""

from __future__ import annotations

import hashlib
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
from typing import Any, Self
from urllib.parse import urlsplit

from android_document_ui import disable_automatic_document_download, document_button_point
from android_guest import main
from android_media_groups_codec import probe as codec_probe

from gramlab.client_bridge import ClientBridge
from gramlab.documents import DocumentUpload
from gramlab.world import World

PACKAGE = "org.gramlab.android"
CONFIG = "files/gramlab/config.json"
TRACE = "files/gramlab/trace.jsonl"
BOUNDS = re.compile(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]")
PHOTO_NAMES = ("photo-one.png", "photo-two.jpg")
DOCUMENTS = (
    ("1", "first-album.txt", "First / نخست", "first-document.bin"),
    ("2", "second-album.pdf", "Second / دوم", "second-document.bin"),
)


class AlbumProxy:
    """Strict v6 forwarder; the second document's first body is truncated."""

    def __init__(self, endpoint: str, capability: str) -> None:
        parsed = urlsplit(endpoint)
        if parsed.scheme != "http" or parsed.hostname != "127.0.0.1" or parsed.port is None:
            raise ValueError("Album proxy requires a selected loopback bridge")
        if [name for _, name in socket.if_nameindex()] != ["lo"]:
            raise RuntimeError("Album proxy requires the isolated loopback runtime")
        self._port = parsed.port
        self._capability = capability
        self._lock = threading.Lock()
        self._publication_gate = threading.Lock()
        self._application_observed = threading.Event()
        self._phase = "startup"
        self._requests: list[dict[str, Any]] = []
        self._second_attempts = 0
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args: Any) -> None:
                pass

            def do_GET(self) -> None:
                self.forward()

            def do_POST(self) -> None:
                self.forward()

            def forward(self) -> None:
                allowed = re.fullmatch(
                    r"/v6/(?:snapshot|changes\?after=[0-9]+&limit=[0-9]+|"
                    r"assets/[1-9][0-9]{0,18}|documents/[1-9][0-9]{0,18}|"
                    r"callbacks(?:/[A-Za-z0-9_-]{1,128})?|messages|custom-emoji-documents)",
                    self.path,
                )
                if allowed is None or self.headers.get_all("Authorization", []) != [
                    "Bearer " + owner._capability
                ]:
                    self.send_error(400, "Rejected fixture request")
                    return
                lengths = self.headers.get_all("Content-Length", [])
                if len(lengths) > 1 or self.headers.get("Transfer-Encoding") is not None:
                    self.send_error(400, "Rejected fixture framing")
                    return
                size = int(lengths[0]) if lengths else 0
                if not 0 <= size <= 65536:
                    self.send_error(400, "Rejected fixture size")
                    return
                body = self.rfile.read(size) if size else None
                record: dict[str, Any] = {
                    "sequence": 0,
                    "method": self.command,
                    "path": self.path,
                    "started_ns": time.monotonic_ns(),
                    "forwarded_ns": None,
                    "finished_ns": None,
                    "phase": None,
                    "status": None,
                    "bytes": 0,
                    "sha256": None,
                    "truncated": False,
                    "error": None,
                    "response": None,
                }
                with owner._lock:
                    record["sequence"] = len(owner._requests) + 1
                    owner._requests.append(record)
                connection = http.client.HTTPConnection("127.0.0.1", owner._port, timeout=10)
                owner._publication_gate.acquire()
                with owner._lock:
                    blocked_snapshot = owner._phase == "published" and self.path == "/v6/snapshot"
                if blocked_snapshot:
                    owner._publication_gate.release()
                    if not owner._application_observed.wait(timeout=30):
                        record["status"] = 503
                        record["error"] = "application_barrier_timeout"
                        record["finished_ns"] = time.monotonic_ns()
                        self.send_error(503, "Application observation timed out")
                        connection.close()
                        return
                    owner._publication_gate.acquire()
                try:
                    with owner._lock:
                        record["forwarded_ns"] = time.monotonic_ns()
                        record["phase"] = owner._phase
                    headers = {
                        "Authorization": "Bearer " + owner._capability,
                        "Connection": "close",
                    }
                    if body is not None:
                        headers["Content-Type"] = "application/json"
                    connection.request(self.command, self.path, body, headers)
                    response = connection.getresponse()
                    payload = response.read()
                    record["status"] = response.status
                    if response.status == 200 and (
                        self.path == "/v6/snapshot" or self.path.startswith("/v6/changes?")
                    ):
                        decoded = json.loads(payload)
                        if self.path == "/v6/snapshot":
                            record["response"] = {"message_position": decoded["message_position"]}
                        elif self.path.startswith("/v6/changes?"):
                            record["response"] = {
                                "cursor": decoded["cursor"],
                                "positions": [row["position"] for row in decoded["changes"]],
                            }
                    self.send_response(response.status)
                    for name in ("Content-Type", "Content-Length", "Cache-Control"):
                        value = response.getheader(name)
                        if value is not None:
                            self.send_header(name, value)
                    self.send_header("Connection", "close")
                    self.end_headers()
                    truncate = False
                    if self.path == "/v6/documents/2":
                        with owner._lock:
                            owner._second_attempts += 1
                            truncate = owner._second_attempts == 1
                    delivered = payload[: max(1, len(payload) // 2)] if truncate else payload
                    self.wfile.write(delivered)
                    self.wfile.flush()
                    record["bytes"] = len(delivered)
                    record["sha256"] = hashlib.sha256(delivered).hexdigest()
                    record["truncated"] = truncate
                    if truncate:
                        record["error"] = "truncated_body"
                        self.close_connection = True
                except (OSError, http.client.HTTPException):
                    record["error"] = record["error"] or "transport_error"
                    self.close_connection = True
                finally:
                    record["finished_ns"] = time.monotonic_ns()
                    connection.close()
                    owner._publication_gate.release()

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._server.daemon_threads = False
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self._server.server_port}"

    def requests(self) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(row) for row in self._requests]

    def begin_publication(self) -> dict[str, int | str]:
        self._publication_gate.acquire()
        with self._lock:
            self._phase = "publishing"
            return {
                "phase": self._phase,
                "at_ns": time.monotonic_ns(),
                "request_count": len(self._requests),
            }

    def finish_publication(self) -> dict[str, int | str]:
        with self._lock:
            self._phase = "published"
            marker: dict[str, int | str] = {
                "phase": self._phase,
                "at_ns": time.monotonic_ns(),
                "request_count": len(self._requests),
            }
        self._publication_gate.release()
        return marker

    def observe_application(self) -> dict[str, int | str]:
        with self._lock:
            self._phase = "applied"
            marker: dict[str, int | str] = {
                "phase": self._phase,
                "at_ns": time.monotonic_ns(),
                "request_count": len(self._requests),
            }
        self._application_observed.set()
        return marker

    def __enter__(self) -> Self:
        self._thread.start()
        return self

    def __exit__(
        self,
        kind: type[BaseException] | None,
        value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self._application_observed.set()
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=5)


def probe(guest: Callable[..., subprocess.CompletedProcess[str]]) -> dict[str, object]:
    codec = codec_probe(guest)
    captures: dict[str, dict[str, str]] = {}
    secret = ""

    def adb(*arguments: str, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        result = guest(*arguments, **kwargs)
        if secret and secret in result.stdout + result.stderr:
            raise RuntimeError("Album diagnostics contained a capability")
        if result.returncode:
            raise RuntimeError(f"Dedicated album command failed: {arguments[0]}")
        return result

    def write(path: str, value: dict[str, Any]) -> None:
        adb(
            "shell",
            "-T",
            "run-as",
            PACKAGE,
            "sh",
            "-c",
            shlex.quote(f"mkdir -p files/gramlab && cat > {path}"),
            input=json.dumps(value),
        )

    def trace() -> list[dict[str, Any]]:
        raw = adb("shell", "run-as", PACKAGE, "cat", TRACE).stdout
        Path("album-trace.jsonl").write_text(raw)
        return [json.loads(line) for line in raw.splitlines()]

    def capture(name: str) -> str:
        adb("shell", "uiautomator", "dump", "/data/local/tmp/album.xml", timeout=15)
        xml = adb("shell", "cat", "/data/local/tmp/album.xml").stdout
        if secret and secret in xml:
            raise RuntimeError("Album hierarchy contained a capability")
        Path(name + ".xml").write_text(xml)
        adb("shell", "screencap", "-p", "/data/local/tmp/album.png")
        adb("pull", "/data/local/tmp/album.png", f"/work/{name}.png")
        captures[name] = {"xml": name + ".xml", "png": name + ".png"}
        return xml

    def labels(xml: str) -> str:
        tree = ET.fromstring(xml)  # noqa: S314 — dedicated UIAutomator hierarchy.
        return "\n".join(
            value
            for node in tree.iter("node")
            for value in (node.get("text", ""), node.get("content-desc", ""))
            if value
        )

    def wait_screen(name: str, expected: tuple[str, ...], *, applied: bool = False) -> str:
        deadline = time.monotonic() + 45
        current = ""
        while time.monotonic() < deadline:
            current = capture(name)
            if all(value in labels(current) for value in expected) and (
                not applied
                or any(
                    row.get("event") == "events_applied" and row.get("token") == 2
                    for row in trace()
                )
            ):
                return current
            time.sleep(0.2)
        raise RuntimeError(f"Original album UI did not reach {name}")

    def bounds(xml: str, text: str) -> list[int]:
        tree = ET.fromstring(xml)  # noqa: S314 — dedicated UIAutomator hierarchy.
        candidates: list[list[int]] = []
        for node in tree.iter("node"):
            if text not in node.get("text", "") + node.get("content-desc", ""):
                continue
            match = BOUNDS.fullmatch(node.get("bounds", ""))
            if match is not None:
                candidate = [int(value) for value in match.groups()]
                if (
                    0 <= candidate[0] < candidate[2] <= 320
                    and 0 <= candidate[1] < candidate[3] <= 640
                ):
                    candidates.append(candidate)
        if not candidates:
            raise RuntimeError("Album document row lacks current semantic bounds")
        return max(candidates, key=lambda item: (item[2] - item[0]) * (item[3] - item[1]))

    def launch() -> None:
        adb(
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

    def document_events(identifier: str) -> list[dict[str, Any]]:
        return [
            row
            for row in trace()
            if row.get("document_id") == identifier
            and str(row.get("event", "")).startswith("media_")
        ]

    def wait_event(identifier: str, event: str) -> list[dict[str, Any]]:
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            rows = document_events(identifier)
            if any(row["event"] == event for row in rows):
                return rows
            time.sleep(0.1)
        raise RuntimeError(f"Grouped document {identifier} did not reach {event}")

    def wait_application(trace_start: int) -> tuple[list[dict[str, Any]], dict[str, int | str]]:
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            rows = trace()
            if any(
                row.get("event") == "events_applied"
                and row.get("method") == "messages"
                and row.get("token") == 2
                for row in rows[trace_start:]
            ):
                return rows, proxy.observe_application()
            time.sleep(0.1)
        raise RuntimeError("Live grouped documents did not use the atomic application path")

    def completed_differences(rows: list[dict[str, Any]]) -> list[int]:
        difference_rows = [row for row in rows if row.get("method") == "TL_updates_getDifference"]
        if len(difference_rows) % 2:
            raise RuntimeError("A native difference was pending at the publication boundary")
        tokens: list[int] = []
        for index in range(0, len(difference_rows), 2):
            request, response = difference_rows[index : index + 2]
            if (
                request.get("event") != "request"
                or response.get("event") != "response"
                or request.get("account") != response.get("account")
                or request.get("token") != response.get("token")
                or type(request.get("token")) is not int
            ):
                raise RuntimeError("Native difference lifecycle crossed publication")
            tokens.append(request["token"])
        return tokens

    def wait_photo_assets(asset_ids: set[int]) -> list[dict[str, Any]]:
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            rows = trace()
            loaded = {
                row.get("asset_id")
                for row in rows
                if row.get("event") in {"media_load_success", "media_cache_hit"}
                and row.get("digest_ok") is True
            }
            if asset_ids <= loaded:
                return rows
            time.sleep(0.1)
        raise RuntimeError("Grouped photos did not finish their original local loads")

    def tap_document(xml: str, file_name: str) -> dict[str, Any]:
        row = bounds(xml, file_name)
        point = document_button_point(row)
        started_ns = time.monotonic_ns()
        adb("shell", "input", "tap", str(point[0]), str(point[1]))
        return {
            "file_name": file_name,
            "bounds": row,
            "point": list(point),
            "started_ns": started_ns,
            "finished_ns": time.monotonic_ns(),
        }

    def stable_failure_window() -> dict[str, Any]:
        frozen_requests = sum(row["path"] == "/v6/documents/2" for row in proxy.requests())
        frozen_successes = sum(
            row.get("event") == "media_load_success" for row in document_events("2")
        )
        if frozen_requests != 1 or frozen_successes != 0:
            raise RuntimeError("D2 did not remain at its first failed request")
        samples: list[dict[str, int]] = []
        for _ in range(40):
            request_count = sum(row["path"] == "/v6/documents/2" for row in proxy.requests())
            success_count = sum(
                row.get("event") == "media_load_success" for row in document_events("2")
            )
            sample = {
                "observed_ns": time.monotonic_ns(),
                "request_count": request_count,
                "success_count": success_count,
            }
            samples.append(sample)
            if request_count != frozen_requests or success_count != frozen_successes:
                raise RuntimeError("D2 retried before original radial input")
            if (
                len(samples) >= 20
                and samples[-1]["observed_ns"] - samples[0]["observed_ns"] >= 2_000_000_000
            ):
                break
            time.sleep(0.1)
        else:
            raise RuntimeError("D2 stable observation window did not span two seconds")
        return {
            "request_count": frozen_requests,
            "success_count": frozen_successes,
            "samples": samples,
        }

    def inventory() -> dict[str, Any]:
        roots = (
            ("internal", ("shell", "run-as", PACKAGE), "."),
            (
                "external",
                ("shell",),
                f"/storage/emulated/0/Android/data/{PACKAGE}",
            ),
        )
        files: list[dict[str, Any]] = []
        partials: list[str] = []
        for scope, prefix, root in roots:
            for path in adb(*prefix, "find", root, "-type", "f").stdout.splitlines():
                name = Path(path).name
                if name.endswith(".part") or ".gramlab-" in name:
                    partials.append(path)
                if name not in {item[1] for item in DOCUMENTS} and not re.fullmatch(
                    r"-1_-[12]\.(?:txt|pdf)", name
                ):
                    continue
                quoted = shlex.quote(path)
                size = int(adb(*prefix, "toybox", "wc", "-c", quoted).stdout.split()[0])
                digest = adb(*prefix, "toybox", "sha256sum", quoted).stdout.split()[0]
                files.append({"scope": scope, "path": path, "size": size, "sha256": digest})
        return {"files": sorted(files, key=lambda row: row["path"]), "partials": sorted(partials)}

    photo_bodies = [Path(name).read_bytes() for name in PHOTO_NAMES]
    document_bodies = {
        identifier: Path(source).read_bytes() for identifier, _, _, source in DOCUMENTS
    }
    with World.create(Path("world"), seed=114, now=1_700_000_000) as world:
        user = world.create_user(first_name="Sara", language_code="fa")
        bot = world.create_user(first_name="Albums", username="albums_bot", is_bot=True)
        chat = world.open_private_chat(user_id=user["id"], bot_id=bot["id"])
        photos = world.send_media_group(
            chat_id=chat["id"],
            sender_id=bot["id"],
            media=[
                {"type": "photo", "media": "attach://one", "caption": "Album / آلبوم"},
                {"type": "photo", "media": "attach://two"},
            ],
            uploads={"one": photo_bodies[0], "two": photo_bodies[1]},
        )
        capability = world.issue_client_token(user["id"])
        secret = capability
        world_id = world.world_id
        initial = world.client_snapshot(user["id"], version=6)

    adb("install", "--no-streaming", "/work/client.apk", timeout=60)
    disable_automatic_document_download(adb)
    with ClientBridge(Path("world")) as bridge, AlbumProxy(bridge.base_url, capability) as proxy:
        configuration = {
            "endpoint": proxy.base_url.replace("127.0.0.1", "10.0.2.2"),
            "capability": capability,
            "world_id": world_id,
            "user_id": user["id"],
            "bridge_version": 6,
        }
        write(CONFIG, configuration)
        launch()
        photo_xml = wait_screen("album-photos", ("Album / آلبوم",))
        wait_photo_assets({item["photo"]["asset_id"] for item in photos})
        photo_xml = capture("album-photos")
        publication_started = proxy.begin_publication()
        try:
            precommit_trace = trace()
            precommit_differences = completed_differences(precommit_trace)
            publication_trace_start = len(precommit_trace)
            with World.open(Path("world")) as world:
                documents = world.send_media_group(
                    chat_id=chat["id"],
                    sender_id=bot["id"],
                    media=[
                        {
                            "type": "document",
                            "media": "attach://first",
                            "caption": DOCUMENTS[0][2],
                        },
                        {
                            "type": "document",
                            "media": "attach://second",
                            "caption": DOCUMENTS[1][2],
                        },
                    ],
                    uploads={
                        "first": DocumentUpload(document_bodies["1"], DOCUMENTS[0][1]),
                        "second": DocumentUpload(document_bodies["2"], DOCUMENTS[1][1]),
                    },
                )
                final_snapshot = world.client_snapshot(user["id"], version=6)
                live_changes = world.client_changes(user["id"], after=2, limit=100, version=6)
        finally:
            publication_completed = proxy.finish_publication()
        publication = {
            "started": publication_started,
            "completed": publication_completed,
            "trace_start": publication_trace_start,
            "precommit_difference_tokens": precommit_differences,
        }
        application_trace, publication["application"] = wait_application(publication_trace_start)
        document_xml = wait_screen(
            "album-documents",
            tuple(
                value for _, file_name, caption, _ in DOCUMENTS for value in (file_name, caption)
            ),
            applied=True,
        )
        document_bounds = [bounds(document_xml, item[1]) for item in DOCUMENTS]
        if document_bounds[0][1] >= document_bounds[1][1]:
            raise RuntimeError("Original document group row order changed")
        before_transfers = len(proxy.requests())
        first_tap = tap_document(document_xml, DOCUMENTS[0][1])
        first_trace = wait_event("1", "media_load_success")
        second_tap = tap_document(document_xml, DOCUMENTS[1][1])
        second_failed_trace = wait_event("2", "media_load_failure")
        failed_xml = wait_screen("album-second-failed", (DOCUMENTS[1][1], DOCUMENTS[1][2]))
        failed_inventory = inventory()
        retry_guard = stable_failure_window()
        retry_tap = tap_document(failed_xml, DOCUMENTS[1][1])
        final_trace = wait_event("2", "media_load_success")
        final_xml = wait_screen(
            "album-final",
            tuple(value for _, name, caption, _ in DOCUMENTS for value in (name, caption)),
        )
        final_inventory = inventory()
        before_restart = len(proxy.requests())
        adb("shell", "am", "force-stop", PACKAGE)
        launch()
        cold_xml = wait_screen(
            "album-cold",
            tuple(value for _, name, caption, _ in DOCUMENTS for value in (name, caption)),
        )
        cold_inventory = inventory()
        adb("shell", "am", "force-stop", PACKAGE)
        accounts = adb("shell", "dumpsys", "account").stdout
    requests = proxy.requests()
    cold_requests = requests[before_restart:]

    return {
        "codec": codec,
        "initial_snapshot": initial,
        "final_snapshot": final_snapshot,
        "live_changes": live_changes,
        "publication": publication,
        "photos": photos,
        "documents": documents,
        "geometry": {
            "photo_xml_labels": labels(photo_xml),
            "document_bounds": document_bounds,
            "final_xml_labels": labels(final_xml),
            "cold_xml_labels": labels(cold_xml),
        },
        "taps": [first_tap, second_tap, retry_tap],
        "retry_guard": retry_guard,
        "traces": {
            "first": first_trace,
            "second_failed": second_failed_trace,
            "final": final_trace,
            "application": application_trace,
            "all": trace(),
        },
        "requests": requests,
        "transfer_request_start": before_transfers,
        "cold_requests": cold_requests,
        "failed_inventory": failed_inventory,
        "final_inventory": final_inventory,
        "cold_inventory": cold_inventory,
        "captures": captures,
        "accounts": accounts,
    }


if __name__ == "__main__":
    main(probe)
