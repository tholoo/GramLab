"""Prove an old shared transfer completes after one rich receiver is edited."""

from __future__ import annotations

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
DIRECTORY = "files/gramlab/"
EXTERNAL = f"/storage/emulated/0/Android/data/{PACKAGE}"
CAPABILITY = "gramlab-client_" + "l" * 43
PHOTOS = {
    1: ("photo-square-16x16.png", "image/png", 16, 16),
    2: ("photo-landscape-48x12.png", "image/png", 48, 12),
    3: ("photo-quadrants-64x48.jpg", "image/jpeg", 64, 48),
}


def descriptor(asset_id: int) -> dict[str, Any]:
    name, mime, width, height = PHOTOS[asset_id]
    body = Path(name).read_bytes()
    return {
        "asset_id": asset_id,
        "mime_type": mime,
        "file_size": len(body),
        "sha256": hashlib.sha256(body).hexdigest(),
        "width": width,
        "height": height,
    }


def message(message_id: int, **content: Any) -> dict[str, Any]:
    return {
        "id": message_id,
        "chat_id": 1,
        "sender_id": 2,
        "date": 1700000000,
        "text": "",
        **content,
    }


def snapshot(world_id: str) -> dict[str, Any]:
    rich = {
        "blocks": [
            {"type": "photo", "asset_id": 1},
            {"type": "photo", "asset_id": 2},
        ]
    }
    return {
        "schema": 3,
        "world_id": world_id,
        "user_id": 1,
        "cursor": 5,
        "now": 1700000000,
        "users": [
            {"id": 1, "is_bot": False, "first_name": "Sara", "language_code": "fa"},
            {"id": 2, "is_bot": True, "first_name": "Echo", "username": "gramlab_echo_bot"},
        ],
        "chats": [{"id": 1, "type": "private", "user_id": 1, "bot_id": 2}],
        "messages": [
            message(1, rich_message=rich),
            message(2, photo={"asset_id": 2}, caption="Shared landscape / تصویر"),
        ],
        "message_position": 2,
        "sends": [],
        "assets": [descriptor(1), descriptor(2)],
        "message_revisions": [
            {"chat_id": 1, "message_id": 1, "revision": 4},
            {"chat_id": 1, "message_id": 2, "revision": 5},
        ],
    }


def edited(initial: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    result = copy.deepcopy(initial)
    result["messages"][0]["rich_message"]["blocks"][1] = {
        "type": "photo",
        "asset_id": 3,
    }
    result["messages"][0]["edit_date"] = 1700000000
    result["assets"].append(descriptor(3))
    result["message_position"] = 3
    result["cursor"] = 6
    result["message_revisions"][0]["revision"] = 6
    changes = {
        "schema": 3,
        "world_id": initial["world_id"],
        "user_id": 1,
        "head": 3,
        "now": 1700000000,
        "users": copy.deepcopy(initial["users"]),
        "assets": [descriptor(3)],
        "changes": [
            {
                "position": 3,
                "type": "message.edited",
                "revision": 6,
                "data": copy.deepcopy(result["messages"][0]),
            }
        ],
    }
    return result, changes


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
        self, *args: str, required: bool = True, **kwargs: Any
    ) -> subprocess.CompletedProcess[str]:
        if self.window_end is not None:
            remaining = self.window_end - time.monotonic()
            if remaining <= 0:
                raise RuntimeError("Missed controlled transfer scheduling deadline")
            kwargs["timeout"] = min(kwargs.get("timeout", 10), remaining)
        result = self.guest(*args, **kwargs)
        if CAPABILITY in result.stdout + result.stderr:
            raise RuntimeError("Rich photo diagnostics contain a capability")
        with Path("commands.jsonl").open("a") as stream:
            stream.write(
                json.dumps(
                    {
                        "case": self.case,
                        "returncode": result.returncode,
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                    }
                )
                + "\n"
            )
        if result.returncode and required:
            raise RuntimeError(f"Dedicated rich photo command failed: {args[0]}")
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

    def configure(
        self, server: MediaTransferServer, value: dict[str, Any], activation: dict[str, Any]
    ) -> None:
        self.adb("shell", "pm", "clear", PACKAGE)
        self.write(
            "config.json",
            {
                "endpoint": server.base_url.replace("127.0.0.1", "10.0.2.2"),
                "capability": CAPABILITY,
                "world_id": value["world_id"],
                "user_id": 1,
                "bridge_version": 3,
            },
        )
        self.activation = copy.deepcopy(activation)
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
        self.uptime_offset = uptime - before

    def raw_sample(self) -> dict[str, Any] | None:
        result = self.adb(
            "shell",
            "run-as",
            PACKAGE,
            "cat",
            DIRECTORY + "photo-observation-result.json",
            required=False,
        )
        return dict(json.loads(result.stdout)) if result.returncode == 0 else None

    def sample(
        self, predicate: Callable[[list[dict[str, Any]]], bool], *, timeout: float = 4
    ) -> dict[str, Any]:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            value = self.raw_sample()
            if value is not None:
                with Path(f"{self.case}-observations.jsonl").open("a") as stream:
                    stream.write(json.dumps(value) + "\n")
                age = (time.monotonic() + self.uptime_offset) * 1000 - value["uptime_ms"]
                if (
                    any(
                        value.get(k) != self.activation[k]
                        for k in ("schema", "nonce", "world_id", "user_id", "peer_id")
                    )
                    or value.get("pid") != self.pid
                ):
                    raise RuntimeError("Original rich photo observation identity mismatch")
                if (
                    value["generation"] > self.generation
                    and 0 <= age <= 1000
                    and value["available"]
                ):
                    rows = value["messages"]
                    targets = self.activation["targets"]
                    if [(r["message_id"], r["kind"]) for r in rows] != [
                        (t["message_id"], t["kind"]) for t in targets
                    ]:
                        raise RuntimeError("Original rich photo target identity mismatch")
                    for row, target in zip(rows, targets, strict=True):
                        if row["asset_id"] not in target["asset_ids"]:
                            raise RuntimeError("Original rich photo asset identity mismatch")
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
                    if predicate(rows):
                        self.generation = value["generation"]
                        return value
            time.sleep(0.035)
        raise RuntimeError("No fresh original rich photo observation meeting required state")

    def trace(self) -> list[dict[str, Any]]:
        rows = self.raw_trace()
        return [row for row in rows if str(row.get("event", "")).startswith("media_")]

    def raw_trace(self) -> list[dict[str, Any]]:
        result = self.adb(
            "shell", "run-as", PACKAGE, "cat", DIRECTORY + "trace.jsonl", required=False
        )
        Path(f"{self.case}-trace.jsonl").write_text(result.stdout)
        return (
            [json.loads(line) for line in result.stdout.splitlines()]
            if not result.returncode
            else []
        )

    def screenshot(self, stage: str) -> str:
        name = f"{self.case}-{stage}.png"
        self.adb("shell", "screencap", "-p", "/data/local/tmp/rich-photo.png")
        self.adb("pull", "/data/local/tmp/rich-photo.png", f"/work/{name}")
        return name

    def inventory(self) -> list[dict[str, Any]]:
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
        return files


def activation(world_id: str, targets: list[dict[str, Any]], nonce: str) -> dict[str, Any]:
    return {
        "schema": 2,
        "nonce": nonce,
        "world_id": world_id,
        "user_id": 1,
        "peer_id": 2,
        "targets": copy.deepcopy(targets),
    }


def require_window(transfer: Transfer) -> float:
    if not transfer.partial_sent.wait(timeout=5) or transfer.partial_sent_at is None:
        raise RuntimeError("Controlled B transfer never sent first bytes")
    elapsed = time.monotonic() - transfer.partial_sent_at
    if elapsed >= 4.8:
        raise RuntimeError("Missed five-second client read window")
    return elapsed


def guard_cases(base: dict[str, Any]) -> list[tuple[str, Any, str | None]]:
    target = {"message_id": 1, "kind": "rich", "asset_ids": [2, 3]}
    valid = activation(base["world_id"], [target], "guard")
    malformed: list[tuple[str, Any, str | None]] = [
        ("not-object", [], None),
        ("wrong-schema", valid | {"schema": 1}, None),
        ("extra-field", valid | {"extra": 1}, None),
        ("targets-scalar", valid | {"targets": target}, None),
        ("targets-empty", valid | {"targets": []}, None),
        ("target-extra", valid | {"targets": [target | {"extra": 1}]}, None),
        ("message-bool", valid | {"targets": [target | {"message_id": True}]}, None),
        ("kind-invalid", valid | {"targets": [target | {"kind": "article"}]}, None),
        ("ids-scalar", valid | {"targets": [target | {"asset_ids": 2}]}, None),
        ("ids-empty", valid | {"targets": [target | {"asset_ids": []}]}, None),
        ("id-zero", valid | {"targets": [target | {"asset_ids": [0]}]}, None),
        ("id-bool", valid | {"targets": [target | {"asset_ids": [True]}]}, None),
        ("id-duplicate", valid | {"targets": [target | {"asset_ids": [2, 2]}]}, None),
        ("message-duplicate", valid | {"targets": [target, target | {"kind": "ordinary"}]}, None),
        (
            "wrong-asset",
            activation(
                base["world_id"],
                [{"message_id": 1, "kind": "rich", "asset_ids": [3]}],
                "wrong-asset",
            ),
            "unsupported_photo",
        ),
        (
            "ambiguous",
            activation(
                base["world_id"],
                [{"message_id": 1, "kind": "rich", "asset_ids": [1, 2]}],
                "ambiguous",
            ),
            "ambiguous_photo",
        ),
        (
            "missing-message",
            activation(
                base["world_id"],
                [{"message_id": 99, "kind": "rich", "asset_ids": [2]}],
                "missing-message",
            ),
            "message_not_unique_or_visible",
        ),
        (
            "wrong-kind",
            activation(
                base["world_id"],
                [{"message_id": 1, "kind": "ordinary", "asset_ids": [2]}],
                "wrong-kind",
            ),
            "asset_mismatch",
        ),
    ]
    return malformed


def run_guards(observe: Observation, assets: dict[int, tuple[str, bytes]]) -> dict[str, Any]:
    results: dict[str, Any] = {}
    for name, configured, reason in guard_cases(snapshot("rich-photo-guard")):
        observe.case = "guard-" + name
        value = snapshot("rich-photo-guard")
        with MediaTransferServer(
            snapshot=value, assets=assets, capability=CAPABILITY, default_fault="missing"
        ) as server:
            sample = None
            trace: list[dict[str, Any]] = []
            try:
                observe.configure(server, value, activation(value["world_id"], [], name))
                if isinstance(configured, dict):
                    configured = copy.deepcopy(configured)
                    configured["nonce"] = name
                observe.adb(
                    "shell",
                    "-T",
                    "run-as",
                    PACKAGE,
                    "sh",
                    "-c",
                    shlex.quote(f"cat > {DIRECTORY}photo-observation.json"),
                    input=json.dumps(configured),
                )
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
                    required=False,
                )
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline:
                    sample = observe.raw_sample()
                    trace = observe.raw_trace()
                    if reason is None and any(
                        row.get("event") == "startup_rejected" for row in trace
                    ):
                        break
                    if reason is not None and sample is not None and sample.get("reason") == reason:
                        break
                    time.sleep(0.05)
                if reason is None and sample is not None:
                    raise RuntimeError(f"Malformed schema-2 activation accepted: {name}")
                if reason is None and not any(
                    row.get("event") == "startup_rejected" for row in trace
                ):
                    raise RuntimeError(f"Malformed schema-2 activation was not rejected: {name}")
                if reason is not None and (sample is None or sample.get("reason") != reason):
                    raise RuntimeError(f"Schema-2 lookup guard unavailable: {name}")
                if reason is not None:
                    expected = configured
                    assert isinstance(expected, dict)
                    assert sample is not None
                    if any(
                        sample.get(key) != expected[key]
                        for key in ("schema", "nonce", "world_id", "user_id", "peer_id")
                    ):
                        raise RuntimeError(f"Schema-2 lookup guard identity mismatch: {name}")
                results[name] = {
                    "sample": sample,
                    "trace": trace,
                    "requests": server.requests(),
                }
            except Exception as failure:
                results[name] = {
                    "sample": sample,
                    "trace": trace,
                    "requests": server.requests(),
                    "failure": {
                        "type": type(failure).__name__,
                        "message": str(failure).replace(CAPABILITY, "<redacted>"),
                    },
                }
            finally:
                observe.adb("shell", "am", "force-stop", PACKAGE, required=False)
    return results


def probe(guest: Callable[..., subprocess.CompletedProcess[str]]) -> dict[str, object]:
    observe = Observation(guest)
    observe.adb("install", "--no-streaming", "/work/client.apk", timeout=60)
    assets = {
        asset: (mime, Path(name).read_bytes()) for asset, (name, mime, _, _) in PHOTOS.items()
    }
    initial = snapshot("rich-photo-late")
    targets = [
        {"message_id": 1, "kind": "rich", "asset_ids": [2, 3]},
        {"message_id": 2, "kind": "ordinary", "asset_ids": [2]},
    ]
    result: dict[str, Any] = {"captures": [], "targets": targets}
    observe.case = "late-completion"
    with MediaTransferServer(
        snapshot=initial, assets=assets, capability=CAPABILITY, default_fault="missing"
    ) as server:
        server.plan(1, "complete")
        transfer = server.plan(2, "gated")
        try:
            observe.configure(
                server, initial, activation(initial["world_id"], targets, "late-completion")
            )
            observe.launch()
            require_window(transfer)
            assert transfer.partial_sent_at is not None
            result["partial_sent_at"] = transfer.partial_sent_at
            observe.window_end = transfer.partial_sent_at + 4.8
            loading = observe.sample(
                lambda rows: (
                    [r["asset_id"] for r in rows] == [2, 2]
                    and not any(r["has_image"] for r in rows)
                )
            )
            result["loading"] = loading
            result["captures"].append(observe.screenshot("loading"))
            revised, changes = edited(initial)
            server.plan(3, "complete")
            server.publish(revised, changes)
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline:
                rows = observe.trace()
                if any(r["event"] == "media_load_success" and r["asset_id"] == 3 for r in rows):
                    break
                time.sleep(0.035)
            else:
                raise RuntimeError("Edited C transfer did not complete")
            bound_c = observe.sample(
                lambda rows: (
                    [r["asset_id"] for r in rows] == [3, 2]
                    and rows[0]["has_image"]
                    and not rows[1]["has_image"]
                ),
                timeout=2,
            )
            result["edited_snapshot"] = revised
            result["changes"] = changes
            result["bound_c"] = bound_c
            result["captures"].append(observe.screenshot("edited-c"))
            result["release_elapsed"] = require_window(transfer)
            result["released_at"] = time.monotonic()
            observe.window_end = None
            transfer.release.set()
            post = []
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                current = observe.sample(
                    lambda rows: True, timeout=max(0.05, deadline - time.monotonic())
                )
                post.append(current)
                rows = current["messages"]
                if rows[0]["asset_id"] != 3 or not rows[0]["has_image"]:
                    raise RuntimeError("Old B rebound the edited rich receiver")
                trace = observe.trace()
                if (
                    rows[1]["asset_id"] == 2
                    and rows[1]["has_image"]
                    and any(
                        r["event"] == "media_load_success" and r["asset_id"] == 2 for r in trace
                    )
                ):
                    result["completed"] = current
                    result["trace"] = trace
                    break
            else:
                raise RuntimeError("Old shared B did not complete in its ordinary receiver")
            result["post_release"] = post
            result["captures"].append(observe.screenshot("b-completed"))
            stable = observe.sample(
                lambda rows: (
                    rows[0]["asset_id"] == 3
                    and rows[0]["has_image"]
                    and rows[1]["asset_id"] == 2
                    and rows[1]["has_image"]
                )
            )
            result["stable"] = stable
            result["captures"].append(observe.screenshot("stable"))
            result["files"] = observe.inventory()
            result["requests"] = server.requests()
            observe.adb("shell", "am", "force-stop", PACKAGE)
        except Exception as failure:
            result["failure"] = {
                "type": type(failure).__name__,
                "message": str(failure).replace(CAPABILITY, "<redacted>"),
            }
        finally:
            observe.window_end = None
            transfer.release.set()
            result["requests"] = server.requests()
            result["partial_trace"] = observe.raw_trace()
            try:
                result["partial_files"] = observe.inventory()
            except Exception as failure:
                result["evidence_failure"] = {
                    "type": type(failure).__name__,
                    "message": str(failure).replace(CAPABILITY, "<redacted>"),
                }
            observe.adb("shell", "am", "force-stop", PACKAGE, required=False)
    guards = run_guards(observe, assets)
    return {
        "case": result,
        "guards": guards,
        "assets": [descriptor(i) for i in PHOTOS],
        "accounts": observe.adb("shell", "dumpsys", "account").stdout,
    }


if __name__ == "__main__":
    main(probe)
