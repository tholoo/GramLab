"""Observe and tap original photo controls during controlled real HTTP transfers."""

import copy
import hashlib
import json
import math
import shlex
import subprocess
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from android_guest import main
from media_transfer_server import MediaTransferServer, Transfer

PACKAGE = "org.gramlab.android"
EXTERNAL = f"/storage/emulated/0/Android/data/{PACKAGE}"
DIRECTORY = "files/gramlab/"
CAPABILITY = "gramlab-client_" + "a" * 43
# Constants from the pinned original MediaActionDrawable, not the adapter implementation.
DOWNLOAD, CANCEL, NONE = 2, 3, 4
PHOTOS = {
    1: ("photo-wide-48x8.png", "image/png", 48, 8),
    2: ("photo-quadrants-64x48.jpg", "image/jpeg", 64, 48),
}


def scene(world: str, count: int) -> dict[str, Any]:
    return {
        "schema": 3,
        "world_id": world,
        "user_id": 1,
        "cursor": 5,
        "now": 1700000000,
        "users": [
            {"id": 1, "is_bot": False, "first_name": "Sara", "language_code": "fa"},
            {"id": 2, "is_bot": True, "first_name": "Echo", "username": "gramlab_echo_bot"},
        ],
        "chats": [{"id": 1, "type": "private", "user_id": 1, "bot_id": 2}],
        "messages": [
            {
                "id": number,
                "chat_id": 1,
                "sender_id": 2,
                "date": 1700000000,
                "text": "",
                "photo": {"asset_id": 1},
                "caption": f"Photo {number} / تصویر",
            }
            for number in range(1, count + 1)
        ],
        "message_position": count,
        "sends": [],
        "assets": [descriptor(1)],
        "message_revisions": [
            {"chat_id": 1, "message_id": number, "revision": number + 3}
            for number in range(1, count + 1)
        ],
    }


def descriptor(asset: int) -> dict[str, Any]:
    name, mime, width, height = PHOTOS[asset]
    body = Path(name).read_bytes()
    return {
        "asset_id": asset,
        "mime_type": mime,
        "file_size": len(body),
        "sha256": hashlib.sha256(body).hexdigest(),
        "width": width,
        "height": height,
    }


class Observation:
    def __init__(self, guest: Callable[..., subprocess.CompletedProcess[str]]) -> None:
        self.guest = guest
        self.case = "install"
        self.activation: dict[str, Any] = {}
        self.generation = 0
        self.pid = 0
        self.uptime_offset = 0.0
        self.window_end: float | None = None

    def adb(
        self, *arguments: str, required: bool = True, **kwargs: Any
    ) -> subprocess.CompletedProcess[str]:
        if self.window_end is not None:
            remaining = self.window_end - time.monotonic()
            if remaining <= 0:
                raise RuntimeError("Missed controlled transfer scheduling deadline")
            kwargs["timeout"] = min(kwargs.get("timeout", 10), remaining)
        try:
            result = self.guest(*arguments, **kwargs)
        except subprocess.TimeoutExpired as failure:
            if self.window_end is not None:
                raise RuntimeError("Missed controlled transfer scheduling deadline") from failure
            raise
        if CAPABILITY in result.stdout + result.stderr:
            raise RuntimeError("Photo interaction diagnostics contain a capability")
        with Path("commands.jsonl").open("a") as stream:
            stream.write(
                json.dumps(
                    {
                        "case": self.case,
                        "at": time.monotonic(),
                        "returncode": result.returncode,
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                    }
                )
                + "\n"
            )
        if result.returncode and required:
            raise RuntimeError(f"Dedicated photo interaction command failed: {arguments[0]}")
        return result

    def write(self, name: str, value: dict[str, Any]) -> None:
        self.adb(
            "shell",
            "-T",
            "run-as",
            PACKAGE,
            "sh",
            "-c",
            shlex.quote(f"mkdir -p {DIRECTORY} && cat > {DIRECTORY}{name}"),
            input=json.dumps(value),
        )

    def configure(self, server: MediaTransferServer, snapshot: dict[str, Any]) -> None:
        self.adb("shell", "pm", "clear", PACKAGE)
        self.write(
            "config.json",
            {
                "endpoint": server.base_url.replace("127.0.0.1", "10.0.2.2"),
                "capability": CAPABILITY,
                "world_id": snapshot["world_id"],
                "user_id": 1,
                "bridge_version": 3,
            },
        )
        self.activation = {
            "schema": 1,
            "nonce": self.case,
            "world_id": snapshot["world_id"],
            "user_id": 1,
            "peer_id": 2,
            "message_ids": [row["id"] for row in snapshot["messages"]],
        }
        self.write("photo-observation.json", self.activation)
        self.generation = 0

    def launch(self) -> None:
        self.adb(
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
        self.pid = int(self.adb("shell", "pidof", PACKAGE).stdout.strip())
        before = time.monotonic()
        uptime = float(self.adb("shell", "cat", "/proc/uptime").stdout.split()[0])
        # Use the pre-command bound: estimated guest age can only be older, never fresher.
        self.uptime_offset = uptime - before

    def trace(self) -> list[dict[str, Any]]:
        result = self.adb("shell", "run-as", PACKAGE, "cat", DIRECTORY + "trace.jsonl")
        rows = [json.loads(line) for line in result.stdout.splitlines()]
        Path(f"{self.case}-trace.jsonl").write_text(result.stdout)
        return [row for row in rows if str(row.get("event", "")).startswith("media_")]

    def sample(
        self, predicate: Callable[[list[dict[str, Any]]], bool], *, timeout: float = 4
    ) -> dict[str, Any]:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            result = self.adb(
                "shell",
                "run-as",
                PACKAGE,
                "cat",
                DIRECTORY + "photo-observation-result.json",
                required=False,
            )
            if result.returncode == 0:
                value = json.loads(result.stdout)
                with Path(f"{self.case}-observations.jsonl").open("a") as stream:
                    stream.write(json.dumps(value) + "\n")
                age = (time.monotonic() + self.uptime_offset) * 1000 - value["uptime_ms"]
                if (
                    any(
                        value.get(key) != self.activation[key]
                        for key in ("schema", "nonce", "world_id", "user_id", "peer_id")
                    )
                    or value.get("pid") != self.pid
                ):
                    raise RuntimeError("Original photo observation identity mismatch; no input")
                if (
                    value["generation"] > self.generation
                    and 0 <= age <= 1000
                    and value["available"]
                ):
                    messages = value["messages"]
                    if [row["message_id"] for row in messages] != self.activation["message_ids"]:
                        raise RuntimeError("Original photo observation message identity mismatch")
                    for row in messages:
                        for key in (
                            "cell_bounds",
                            "visible_bounds",
                            "image_bounds",
                            "progress_bounds",
                        ):
                            rect = row[key]
                            if len(rect) != 4 or not all(
                                type(x) in (int, float) and math.isfinite(x) for x in rect
                            ):
                                raise RuntimeError("Invalid original photo rectangle")
                    if predicate(messages):
                        self.generation = value["generation"]
                        return dict(value)
            time.sleep(0.035)
        raise RuntimeError(
            "No fresh original photo observation meeting the required state; no input"
        )

    def screenshot(self, stage: str) -> str:
        name = f"{self.case}-{stage}.png"
        self.adb("shell", "screencap", "-p", "/data/local/tmp/photo-interaction.png")
        self.adb("pull", "/data/local/tmp/photo-interaction.png", f"/work/{name}")
        return name

    def tap(self, sample: dict[str, Any], message_id: int) -> dict[str, Any]:
        if (
            any(
                sample.get(key) != self.activation[key]
                for key in ("schema", "nonce", "world_id", "user_id", "peer_id")
            )
            or sample.get("pid") != self.pid
        ):
            raise RuntimeError("Original photo input identity mismatch; no input")
        current_pid = self.adb("shell", "pidof", PACKAGE).stdout.strip()
        if current_pid != str(self.pid):
            raise RuntimeError("Original photo process lifetime changed; no input")
        age = (time.monotonic() + self.uptime_offset) * 1000 - sample["uptime_ms"]
        if not 0 <= age <= 1000 or sample["generation"] != self.generation:
            raise RuntimeError("Stale original photo control; no input")
        row = next(row for row in sample["messages"] if row["message_id"] == message_id)
        left, top, right, bottom = row["progress_bounds"]
        visible = row["visible_bounds"]
        if not (
            visible[0] <= left < right <= visible[2] and visible[1] <= top < bottom <= visible[3]
        ):
            raise RuntimeError("Original photo control is not fully visible; no input")
        x, y = round((left + right) / 2), round((top + bottom) / 2)
        at = time.monotonic()
        self.adb("shell", "input", "tap", str(x), str(y))
        return {"at": at, "x": x, "y": y, "sample": sample, "message_id": message_id}

    def terminal(self, event: str, asset_id: int, *, timeout: float = 5) -> list[dict[str, Any]]:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            rows = self.trace()
            if any(row["event"] == event and row["asset_id"] == asset_id for row in rows):
                return rows
            time.sleep(0.035)
        raise RuntimeError(f"Original transfer did not reach {event} for asset {asset_id}")

    def inventory(self, stage: str) -> list[dict[str, Any]]:
        files = []
        for prefix, directory in ((["shell", "run-as", PACKAGE], "."), (["shell"], EXTERNAL)):
            listing = self.adb(*prefix, "find", directory, "-type", "f").stdout
            for path in sorted(set(listing.splitlines())):
                if not (
                    Path(path).name.endswith(".part")
                    or any(f"{asset}_1.jpg" in Path(path).name for asset in PHOTOS)
                ):
                    continue
                quoted = shlex.quote(path)
                size = int(self.adb(*prefix, "toybox", "wc", "-c", quoted).stdout.split()[0])
                digest = self.adb(*prefix, "toybox", "sha256sum", quoted).stdout.split()[0]
                files.append({"path": path, "size": size, "sha256": digest})
        Path(f"{self.case}-{stage}-files.json").write_text(json.dumps(files, indent=2))
        return files


def observation_guards(observe: Observation) -> dict[str, Any]:
    results: dict[str, Any] = {}
    for case in ("absent", "wrong-world", "missing-message"):
        observe.case = "guard-" + case
        snapshot = scene("media-observer-" + case, 1)
        with MediaTransferServer(
            snapshot=snapshot,
            assets={1: ("image/png", Path(PHOTOS[1][0]).read_bytes())},
            capability=CAPABILITY,
        ) as server:
            observe.configure(server, snapshot)
            if case == "absent":
                observe.adb("shell", "run-as", PACKAGE, "rm", DIRECTORY + "photo-observation.json")
            elif case == "wrong-world":
                observe.write(
                    "photo-observation.json", observe.activation | {"world_id": "unrelated-world"}
                )
            else:
                observe.activation["message_ids"] = [99]
                observe.write("photo-observation.json", observe.activation)
            # A rejected activation may kill startup, so do not require a live app PID here.
            observe.adb(
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
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                raw = observe.guest("shell", "run-as", PACKAGE, "cat", DIRECTORY + "trace.jsonl")
                rows = (
                    [json.loads(line) for line in raw.stdout.splitlines()]
                    if raw.returncode == 0
                    else []
                )
                sample = observe.guest(
                    "shell", "run-as", PACKAGE, "cat", DIRECTORY + "photo-observation-result.json"
                )
                value = json.loads(sample.stdout) if sample.returncode == 0 else None
                if case == "wrong-world":
                    ready = any(row["event"] == "startup_rejected" for row in rows)
                elif case == "missing-message":
                    ready = (
                        value is not None and value.get("reason") == "message_not_unique_or_visible"
                    )
                else:
                    ready = any(row["event"] == "media_load_success" for row in rows)
                if ready:
                    results[case] = {"trace": rows, "sample": value, "requests": server.requests()}
                    break
                time.sleep(0.05)
            else:
                raise RuntimeError(f"Observation guard {case} never reached its required outcome")
            Path(f"guard-{case}-result.json").write_text(json.dumps(results[case], indent=2))
            observe.adb("shell", "am", "force-stop", PACKAGE)
    return results


def require_window(transfer: Transfer) -> float:
    if not transfer.partial_sent.wait(timeout=5) or transfer.partial_sent_at is None:
        raise RuntimeError("Controlled transfer never sent its first bytes")
    elapsed = time.monotonic() - transfer.partial_sent_at
    if elapsed >= 4.8:
        raise RuntimeError(
            "Missed five-second client read window; not cancellation/late-edit evidence"
        )
    return elapsed


def probe(guest: Callable[..., subprocess.CompletedProcess[str]]) -> dict[str, object]:
    observe = Observation(guest)
    observe.adb("install", "--no-streaming", "/work/client.apk", timeout=60)
    results: dict[str, Any] = {}
    old_sample: dict[str, Any] | None = None
    stale_rejections = []
    for case in ("cancel-retry", "shared-consumer", "late-edit"):
        observe.case = case
        snapshot = scene("media-interaction-" + case, 1 if case == "cancel-retry" else 2)
        result: dict[str, Any] = {"captures": [], "taps": []}
        with MediaTransferServer(
            snapshot=snapshot,
            assets={
                asset: (mime, Path(name).read_bytes())
                for asset, (name, mime, _, _) in PHOTOS.items()
            },
            capability=CAPABILITY,
            default_fault="missing",
        ) as server:
            transfer = server.plan(1, "gated")
            try:
                observe.configure(server, snapshot)
                observe.launch()
                require_window(transfer)
                result["partial_sent_at"] = transfer.partial_sent_at
                assert transfer.partial_sent_at is not None
                observe.window_end = transfer.partial_sent_at + 4.8
                result["captures"].append(observe.screenshot("loading"))
                loading = observe.sample(
                    lambda rows: all(
                        row["progress_icon"] == CANCEL and not row["has_image"] for row in rows
                    )
                )
                result["loading"] = loading
                if old_sample is not None:
                    try:
                        observe.tap(old_sample, 1)
                    except RuntimeError as failure:
                        if str(failure) != "Original photo input identity mismatch; no input":
                            raise
                        stale_rejections.append(
                            {"from": old_sample["nonce"], "to": case, "reason": str(failure)}
                        )
                    else:
                        raise RuntimeError("Prior client observation unexpectedly permitted input")
                old_sample = loading
                require_window(transfer)
                if case == "late-edit":
                    edited = copy.deepcopy(snapshot)
                    edited["messages"][0]["photo"] = {"asset_id": 2}
                    edited["messages"][0]["caption"] = "Edited photo / تصویر جدید"
                    edited["messages"][0]["edit_date"] = 1700000000
                    edited["assets"].append(descriptor(2))
                    edited["message_position"] = 3
                    edited["cursor"] = 6
                    edited["message_revisions"][0]["revision"] = 6
                    server.plan(2, "complete")
                    server.publish(
                        edited,
                        {
                            "schema": 3,
                            "world_id": snapshot["world_id"],
                            "user_id": 1,
                            "head": 3,
                            "now": 1700000000,
                            "users": snapshot["users"],
                            "assets": [descriptor(2)],
                            "changes": [
                                {
                                    "position": 3,
                                    "type": "message.edited",
                                    "revision": 6,
                                    "data": edited["messages"][0],
                                }
                            ],
                        },
                    )
                    result["new_trace"] = observe.terminal("media_load_success", 2, timeout=3)
                    result["new_binding"] = observe.sample(
                        lambda rows: rows[0]["has_image"] and not rows[1]["has_image"], timeout=2
                    )
                    result["captures"].append(observe.screenshot("new-completed"))
                    result["release_elapsed"] = require_window(transfer)
                    result["released_at"] = time.monotonic()
                    observe.window_end = None
                    transfer.release.set()
                    result["post_release_bindings"] = []
                    deadline = time.monotonic() + 5
                    while time.monotonic() < deadline:
                        binding = observe.sample(
                            lambda rows: True, timeout=max(0.01, deadline - time.monotonic())
                        )
                        result["post_release_bindings"].append(binding)
                        first = binding["messages"][0]
                        if (
                            first["image_key"] != result["new_binding"]["messages"][0]["image_key"]
                            or not first["has_image"]
                        ):
                            raise RuntimeError(
                                "Old transfer changed the observed edited image binding"
                            )
                        rows = observe.trace()
                        if all(row["has_image"] for row in binding["messages"]) and any(
                            row["event"] == "media_load_success" and row["asset_id"] == 1
                            for row in rows
                        ):
                            result["final_binding"] = binding
                            result["final_trace"] = rows
                            break
                    else:
                        raise RuntimeError(
                            "Late old completion did not produce both original images"
                        )
                    result["captures"].append(observe.screenshot("old-completed"))
                else:
                    result["taps"].append(observe.tap(loading, 1))
                    result["cancel_elapsed"] = require_window(transfer)
                    result["after_tap"] = observe.sample(lambda rows: True)
                    observe.screenshot("after-tap")
                    if case == "cancel-retry":
                        result["cancel_trace"] = observe.terminal("media_load_cancel", 1)
                    canceled = observe.sample(
                        lambda rows: (
                            rows[0]["progress_icon"] == DOWNLOAD
                            and not rows[0]["has_image"]
                            and (
                                len(rows) == 1
                                or (rows[1]["progress_icon"] == CANCEL and not rows[1]["has_image"])
                            )
                        )
                    )
                    result["canceled"] = canceled
                    result["release_elapsed"] = require_window(transfer)
                    result["released_at"] = time.monotonic()
                    observe.window_end = None
                    transfer.release.set()
                    if case == "shared-consumer":
                        result["shared_trace"] = observe.terminal("media_load_success", 1)
                        result["shared_binding"] = observe.sample(
                            lambda rows: not rows[0]["has_image"] and rows[1]["has_image"]
                        )
                    result["captures"].append(observe.screenshot("canceled"))
                    result["files_before_retry"] = observe.inventory("before-retry")
                    result["requests_before_retry"] = server.requests()
                    if case == "cancel-retry":
                        server.plan(1, "complete")
                    retry = observe.sample(
                        lambda rows: (
                            rows[0]["progress_icon"] == DOWNLOAD and not rows[0]["has_image"]
                        )
                    )
                    result["taps"].append(observe.tap(retry, 1))
                    result["final_trace"] = observe.terminal("media_load_success", 1)
                    result["final_binding"] = observe.sample(
                        lambda rows: all(row["has_image"] for row in rows)
                    )
                    result["captures"].append(observe.screenshot("retried"))
                result["files"] = observe.inventory("final")
                result["requests"] = server.requests()
                result["final_trace"] = observe.trace()
                observe.adb("shell", "am", "force-stop", PACKAGE)
                results[case] = result
            except Exception as failure:
                observe.window_end = None
                result["failure"] = {
                    "type": type(failure).__name__,
                    "message": str(failure).replace(CAPABILITY, "<redacted>"),
                }
                # Preserve independent case evidence in one guest instead of paying another boot
                # for each later case. Host acceptance still fails if any case failed.
                raw = observe.guest("shell", "run-as", PACKAGE, "cat", DIRECTORY + "trace.jsonl")
                if raw.returncode == 0:
                    Path(f"{case}-failure-trace.jsonl").write_text(raw.stdout)
                stopped = observe.guest("shell", "am", "force-stop", PACKAGE)
                if stopped.returncode:
                    raise RuntimeError(
                        "Cannot stop failed case before independent app reset"
                    ) from failure
                results[case] = result
            finally:
                observe.window_end = None
                raw = observe.guest(
                    "shell", "run-as", PACKAGE, "cat", DIRECTORY + "photo-observation-result.json"
                )
                if raw.returncode == 0:
                    Path(f"{case}-last-observation.json").write_text(raw.stdout)
                result["requests"] = server.requests()
                Path(f"{case}-partial-result.json").write_text(json.dumps(result, indent=2))
                transfer.release.set()
    guards = observation_guards(observe)
    return {
        "observation_guards": guards,
        "stale_rejections": stale_rejections,
        "cases": results,
        "assets": [descriptor(1), descriptor(2)],
        "accounts": observe.adb("shell", "dumpsys", "account").stdout,
    }


if __name__ == "__main__":
    main(probe)
