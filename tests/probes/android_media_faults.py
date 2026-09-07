"""Drive bounded local photo failures and explicit cold-restart recovery."""

import hashlib
import json
import shlex
import subprocess
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from android_guest import main
from media_transfer_server import Fault, MediaTransferServer

PACKAGE = "org.gramlab.android"
EXTERNAL = "/storage/emulated/0/Android/data/org.gramlab.android"
MEDIA_EVENTS = {
    "media_load_start",
    "media_load_coalesced",
    "media_cache_hit",
    "media_load_success",
    "media_load_failure",
    "media_load_cancel",
}


def probe(guest: Callable[..., subprocess.CompletedProcess[str]]) -> dict[str, object]:
    capability = "gramlab-client_" + "a" * 43
    photo = Path("photo-quadrants-64x48.jpg").read_bytes()
    digest = hashlib.sha256(photo).hexdigest()
    results: dict[str, Any] = {}

    def retain(name: str, result: subprocess.CompletedProcess[str]) -> None:
        combined = result.stdout + result.stderr
        if capability in combined:
            raise RuntimeError("Media fault command diagnostics contained a capability")
        Path(name).write_text(
            json.dumps(
                {
                    "returncode": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                },
                indent=2,
            )
        )

    def adb(name: str, *arguments: str, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        result = guest(*arguments, **kwargs)
        retain(name, result)
        if result.returncode:
            raise RuntimeError(f"Dedicated Android fault command failed: {arguments[0]}")
        return result

    def snapshot(world_id: str) -> dict[str, Any]:
        return {
            "schema": 3,
            "world_id": world_id,
            "user_id": 1,
            "cursor": 4,
            "now": 1700000000,
            "users": [
                {"id": 1, "is_bot": False, "first_name": "Sara", "language_code": "fa"},
                {
                    "id": 2,
                    "is_bot": True,
                    "first_name": "Echo",
                    "username": "gramlab_echo_bot",
                },
            ],
            "chats": [{"id": 1, "type": "private", "user_id": 1, "bot_id": 2}],
            "messages": [
                {
                    "id": 1,
                    "chat_id": 1,
                    "sender_id": 2,
                    "date": 1700000000,
                    "text": "",
                    "photo": {"asset_id": 1},
                    "caption": "Fault recovery / بازیابی تصویر",
                }
            ],
            "message_position": 1,
            "sends": [],
            "assets": [
                {
                    "asset_id": 1,
                    "mime_type": "image/jpeg",
                    "file_size": len(photo),
                    "sha256": digest,
                    "width": 64,
                    "height": 48,
                }
            ],
            "message_revisions": [{"chat_id": 1, "message_id": 1, "revision": 4}],
        }

    def configure(endpoint: str, world_id: str, case: str) -> None:
        body = json.dumps(
            {
                "endpoint": endpoint.replace("127.0.0.1", "10.0.2.2"),
                "capability": capability,
                "world_id": world_id,
                "user_id": 1,
                "bridge_version": 3,
            }
        )
        adb(
            f"{case}-config-command.json",
            "shell",
            "-T",
            "run-as",
            PACKAGE,
            "sh",
            "-c",
            "'mkdir -p files/gramlab && cat > files/gramlab/config.json'",
            input=body,
        )

    def launch(case: str, stage: str) -> None:
        adb(
            f"{case}-{stage}-launch-command.json",
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

    def trace(case: str, stage: str) -> list[dict[str, Any]]:
        result = adb(
            f"{case}-{stage}-trace-command.json",
            "shell",
            "run-as",
            PACKAGE,
            "cat",
            "files/gramlab/trace.jsonl",
        )
        Path(f"{case}-{stage}-trace.jsonl").write_text(result.stdout)
        return [json.loads(line) for line in result.stdout.splitlines()]

    def wait_terminal(case: str, event: str, stage: str) -> list[dict[str, Any]]:
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            rows = trace(case, stage)
            media = [row for row in rows if row.get("event") in MEDIA_EVENTS]
            if any(row["event"] == event and row["asset_id"] == 1 for row in media):
                return media
            time.sleep(0.25)
        raise RuntimeError(f"Media fault case {case} did not reach {event}")

    def capture(case: str, stage: str) -> dict[str, str]:
        remote = f"/data/local/tmp/{case}-{stage}"
        adb(
            f"{case}-{stage}-xml-dump-command.json",
            "shell",
            "uiautomator",
            "dump",
            remote + ".xml",
            timeout=15,
        )
        xml = adb(f"{case}-{stage}-xml-read-command.json", "shell", "cat", remote + ".xml").stdout
        Path(f"{case}-{stage}.xml").write_text(xml)
        adb(
            f"{case}-{stage}-screen-command.json",
            "shell",
            "screencap",
            "-p",
            remote + ".png",
        )
        adb(
            f"{case}-{stage}-pull-command.json",
            "pull",
            remote + ".png",
            f"/work/{case}-{stage}.png",
        )
        return {"xml": xml, "png": f"{case}-{stage}.png"}

    def inventory(case: str, stage: str) -> list[dict[str, Any]]:
        commands = (
            ("internal", ["shell", "run-as", PACKAGE, "find", ".", "-type", "f"]),
            ("external", ["shell", "find", EXTERNAL, "-type", "f"]),
        )
        files: list[dict[str, Any]] = []
        for area, command in commands:
            listing = adb(f"{case}-{stage}-{area}-find-command.json", *command).stdout
            for path in sorted(set(listing.splitlines())):
                if "1_1.jpg" not in Path(path).name:
                    continue
                quoted = shlex.quote(path)
                prefix = (
                    ["shell", "run-as", PACKAGE, "sh", "-c"]
                    if area == "internal"
                    else ["shell", "sh", "-c"]
                )
                stat = adb(
                    f"{case}-{stage}-{area}-{Path(path).name}-stat-command.json",
                    *prefix,
                    f"toybox wc -c < {quoted}; toybox sha256sum {quoted}",
                ).stdout.splitlines()
                files.append(
                    {
                        "area": area,
                        "path": path,
                        "size": int(stat[0]),
                        "sha256": stat[1].split()[0],
                    }
                )
        Path(f"{case}-{stage}-files.json").write_text(json.dumps(files, indent=2))
        return files

    adb("install-command.json", "install", "--no-streaming", "/work/client.apk", timeout=60)
    for fault in ("truncate", "corrupt", "redirect", "missing"):
        typed_fault: Fault = fault
        world_id = f"media-fault-{fault}"
        adb(f"{fault}-clear-command.json", "shell", "pm", "clear", PACKAGE)
        with MediaTransferServer(
            snapshot=snapshot(world_id),
            assets={1: ("image/jpeg", photo)},
            capability=capability,
            default_fault=typed_fault,
        ) as server:
            configure(server.base_url, world_id, fault)
            launch(fault, "failed")
            failed_trace = wait_terminal(fault, "media_load_failure", "failed")
            failed_capture = capture(fault, "failed")
            failed_files = inventory(fault, "failed")
            before = server.requests()
            if not before or any(
                row.get("operation") == "asset" and row.get("fault") == "complete" for row in before
            ):
                raise RuntimeError("Fault case was masked by an unplanned complete transfer")
            adb(f"{fault}-stop-command.json", "shell", "am", "force-stop", PACKAGE)
            server.default_fault("complete")
            launch(fault, "recovered")
            recovered_trace = wait_terminal(fault, "media_load_success", "recovered")
            recovered_capture = capture(fault, "recovered")
            recovered_files = inventory(fault, "recovered")
            requests = server.requests()
        results[fault] = {
            "failed_trace": failed_trace,
            "failed_capture": failed_capture,
            "failed_files": failed_files,
            "requests_before_retry": before,
            "recovered_trace": recovered_trace,
            "recovered_capture": recovered_capture,
            "recovered_files": recovered_files,
            "requests": requests,
        }
    return {
        "cases": results,
        "photo": {"size": len(photo), "sha256": digest},
        "accounts": adb("accounts-command.json", "shell", "dumpsys", "account").stdout,
    }


if __name__ == "__main__":
    main(probe)
