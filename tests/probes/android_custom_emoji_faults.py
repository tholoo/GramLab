"""Drive bounded original custom-emoji lookup faults and explicit recovery."""

from __future__ import annotations

import json
import re
import shlex
import subprocess
import time
import xml.etree.ElementTree as ET
from collections.abc import Callable
from pathlib import Path
from typing import Any

from android_guest import main
from custom_emoji_fault_server import CustomEmojiFaultServer, DocumentFault
from native_asset_proxy import NativeAssetProxy

from gramlab.client_bridge import ClientBridge
from gramlab.world import World

PACKAGE = "org.gramlab.android"
CONFIG = "files/gramlab/config.json"
TRACE = "files/gramlab/trace.jsonl"
IDLE_OBSERVATION_SECONDS = 3.0
# AnimatedEmojiDrawable removes a detached global drawable after 5,000 ms.
EVICTION_WAIT_SECONDS = 5.5
BOUNDS = re.compile(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]")


def probe(guest: Callable[..., subprocess.CompletedProcess[str]]) -> dict[str, object]:
    manifest = json.loads(Path("cases.json").read_text())
    capability = ""

    def retain(name: str, value: str) -> str:
        if capability and capability in value:
            raise RuntimeError("Custom emoji fault diagnostics contained a capability")
        Path(name).write_text(value)
        return value

    def adb(name: str, *arguments: str, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        result = guest(*arguments, **kwargs)
        retain(
            name + "-command.json",
            json.dumps(
                {
                    "returncode": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                },
                indent=2,
            ),
        )
        if result.returncode:
            raise RuntimeError(f"Dedicated custom emoji fault command failed: {arguments[0]}")
        return result

    def clear(case: str) -> None:
        adb(case + "-clear", "shell", "pm", "clear", PACKAGE)

    def configure(endpoint: str, case: dict[str, Any]) -> None:
        nonlocal capability
        capability = case["capability"]
        body = json.dumps(
            {
                "endpoint": endpoint.replace("127.0.0.1", "10.0.2.2"),
                "capability": capability,
                "world_id": case["world_id"],
                "user_id": 1,
                "bridge_version": 4,
            }
        )
        adb(
            case["name"] + "-configure",
            "shell",
            "-T",
            "run-as",
            PACKAGE,
            "sh",
            "-c",
            f"'mkdir -p files/gramlab && cat > {CONFIG}'",
            input=body,
        )

    def launch(case: str, stage: str) -> str:
        result = adb(
            case + "-" + stage + "-launch",
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
        return retain(case + "-" + stage + "-launch.log", result.stdout + result.stderr)

    def trace(case: str, stage: str) -> list[dict[str, Any]]:
        raw = adb(case + "-" + stage + "-trace", "shell", "run-as", PACKAGE, "cat", TRACE).stdout
        retain(case + "-" + stage + "-trace.jsonl", raw)
        return [json.loads(line) for line in raw.splitlines()]

    def capture(case: str, stage: str) -> dict[str, Any]:
        remote = f"/data/local/tmp/{case}-{stage}"
        adb(
            case + "-" + stage + "-dump",
            "shell",
            "uiautomator",
            "dump",
            remote + ".xml",
            timeout=15,
        )
        xml = adb(case + "-" + stage + "-xml", "shell", "cat", remote + ".xml").stdout
        retain(case + "-" + stage + ".xml", xml)
        labels = []
        bounds = []
        for node in ET.fromstring(xml).iter("node"):  # noqa: S314 -- dedicated guest XML
            text = node.get("text", "")
            if not text:
                continue
            labels.append(text)
            match = BOUNDS.fullmatch(node.get("bounds", ""))
            if match:
                bounds.append({"text": text, "bounds": [int(value) for value in match.groups()]})
        adb(case + "-" + stage + "-screen", "shell", "screencap", "-p", remote + ".png")
        adb(
            case + "-" + stage + "-pull",
            "pull",
            remote + ".png",
            f"/work/{case}-{stage}.png",
        )
        retain(
            case + "-" + stage + "-logcat.txt",
            adb(case + "-" + stage + "-logcat", "logcat", "-d", "-t", "2000").stdout,
        )
        return {
            "xml": xml,
            "labels": labels,
            "bounds": bounds,
            "png": f"{case}-{stage}.png",
        }

    def wait_ui(case: str, stage: str, labels: list[str]) -> dict[str, Any]:
        deadline = time.monotonic() + 35
        latest: dict[str, Any] | None = None
        while time.monotonic() < deadline:
            latest = capture(case, stage)
            joined = "\n".join(latest["labels"])
            if all(label in joined for label in labels):
                return latest
            time.sleep(0.2)
        raise RuntimeError(f"Original custom emoji labels did not stabilize during {case}/{stage}")

    def wait_trace_terminals(case: str, stage: str, count: int) -> list[dict[str, Any]]:
        deadline = time.monotonic() + 20
        rows: list[dict[str, Any]] = []
        while time.monotonic() < deadline:
            rows = trace(case, stage)
            terminals = [
                row
                for row in rows
                if row.get("method") == "TL_messages_getCustomEmojiDocuments"
                and (
                    row.get("event") == "response" or str(row.get("event", "")).startswith("error_")
                )
            ]
            if len(terminals) >= count:
                return rows
            time.sleep(0.2)
        raise RuntimeError(f"Original custom emoji trace did not settle during {case}/{stage}")

    def force_stop(case: str, stage: str) -> str:
        adb(case + "-" + stage + "-stop", "shell", "am", "force-stop", PACKAGE)
        deadline = time.monotonic() + 5
        last = ""
        while time.monotonic() < deadline:
            result = guest("shell", "pidof", PACKAGE)
            last = result.stdout.strip()
            if not last:
                retain(
                    case + "-" + stage + "-pid.json",
                    json.dumps({"returncode": result.returncode, "stdout": result.stdout}),
                )
                return last
            time.sleep(0.1)
        raise RuntimeError("Dedicated custom emoji application remained alive after force-stop")

    def cache_files(case: str, stage: str) -> dict[str, list[dict[str, Any]]]:
        external = f"/storage/emulated/0/Android/data/{PACKAGE}"
        selected: dict[str, list[dict[str, Any]]] = {"2_2.jpg": []}
        areas = (
            ("internal", ["shell", "run-as", PACKAGE, "find", ".", "-type", "f"]),
            ("external", ["shell", "find", external, "-type", "f"]),
        )
        for area, command in areas:
            paths = adb(case + "-" + stage + "-" + area + "-find", *command).stdout
            for path in paths.splitlines():
                name = Path(path).name
                if name not in selected:
                    continue
                quoted = shlex.quote(path)
                prefix = ["shell", "run-as", PACKAGE] if area == "internal" else ["shell"]
                size = int(
                    adb(
                        case + "-" + stage + "-" + area + "-" + name + "-size",
                        *prefix,
                        "toybox",
                        "wc",
                        "-c",
                        quoted,
                    ).stdout.split()[0]
                )
                digest = adb(
                    case + "-" + stage + "-" + area + "-" + name + "-sha",
                    *prefix,
                    "toybox",
                    "sha256sum",
                    quoted,
                ).stdout.split()[0]
                selected[name].append({"area": area, "path": path, "size": size, "sha256": digest})
        retain(case + "-" + stage + "-cache.json", json.dumps(selected, indent=2))
        return selected

    def wait_cache(case: str, stage: str, names: set[str]) -> dict[str, list[dict[str, Any]]]:
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            files = cache_files(case, stage)
            if all(files[name] for name in names):
                return files
            time.sleep(0.2)
        raise RuntimeError(f"Original custom emoji cache did not settle during {case}/{stage}")

    def wait_document_ids(
        proxy: NativeAssetProxy,
        start: int,
        expected: list[str],
        case: str,
        stage: str,
    ) -> list[dict[str, Any]]:
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            rows = proxy.document_requests()[start:]
            observed = {identifier for row in rows for identifier in row["custom_emoji_ids"]}
            if (
                set(expected) <= observed
                and rows
                and all(row["finished_ns"] is not None for row in rows)
            ):
                return rows
            time.sleep(0.2)
        trace(case, stage)
        capture(case, stage + "-document-timeout")
        raise RuntimeError(f"Original custom emoji IDs did not resolve during {case}/{stage}")

    def document_case(case: dict[str, Any]) -> dict[str, Any]:
        name = str(case["name"])
        fault: DocumentFault = case["fault"]
        clear(name)
        with ClientBridge(Path(case["world"])) as bridge:
            with CustomEmojiFaultServer(bridge.base_url, case["capability"]) as peer:
                peer.phase("failed")
                peer.document_fault(fault, missing_ids=set(case["missing_ids"]))
                with NativeAssetProxy(peer.base_url, case["capability"]) as proxy:
                    proxy.phase("failed")
                    configure(proxy.base_url, case)
                    failed_launch = launch(name, "failed")
                    failed_documents = wait_document_ids(
                        proxy, 0, case["expected_ids"], name, "failed"
                    )
                    failed_trace = wait_trace_terminals(name, "failed", len(failed_documents))
                    failed_capture = wait_ui(name, "failed", case["labels"])
                    count_before_idle = len(failed_documents)
                    idle_deadline = time.monotonic() + IDLE_OBSERVATION_SECONDS
                    while time.monotonic() < idle_deadline:
                        time.sleep(0.1)
                    idle_documents = proxy.document_requests()
                    idle_capture = wait_ui(name, "idle", case["labels"])
                    failed_assets = proxy.requests()

                    adb(
                        name + "-away",
                        "shell",
                        "am",
                        "start",
                        "-W",
                        "-a",
                        "android.settings.SETTINGS",
                        timeout=30,
                    )
                    time.sleep(EVICTION_WAIT_SECONDS)
                    before_reopen = len(proxy.document_requests())
                    reopen_launch = launch(name, "reopen")
                    refetch_deadline = time.monotonic() + 12
                    reopened_documents = proxy.document_requests()
                    while (
                        len(reopened_documents) <= before_reopen
                        and time.monotonic() < refetch_deadline
                    ):
                        time.sleep(0.2)
                        reopened_documents = proxy.document_requests()
                    same_process_refetch = len(reopened_documents) > before_reopen
                    reopen_capture = wait_ui(name, "reopen", case["labels"])

                    stopped_pid = force_stop(name, "failed")
                    proxy.phase("recovery")
                    proxy.retarget(bridge.base_url)
                    recovery_start = len(proxy.document_requests())
                    recovered_launch = launch(name, "recovered")
                    recovered_documents = wait_document_ids(
                        proxy,
                        recovery_start,
                        case["expected_ids"],
                        name,
                        "recovered",
                    )
                    expected_cache = {"2_2.jpg"}
                    recovered_cache = wait_cache(name, "recovered", expected_cache)
                    recovered_capture = wait_ui(name, "recovered", case["labels"])
                    recovered_trace = trace(name, "recovered")
                    result = {
                        "fault": fault,
                        "expected_ids": case["expected_ids"],
                        "batch_observed": any(
                            row["custom_emoji_ids"] == case["expected_ids"]
                            for row in failed_documents
                        ),
                        "failed_launch": failed_launch,
                        "failed_documents": failed_documents,
                        "failed_trace": failed_trace,
                        "failed_capture": failed_capture,
                        "failed_assets": failed_assets,
                        "idle_seconds": IDLE_OBSERVATION_SECONDS,
                        "idle_document_count": len(idle_documents),
                        "document_count_before_idle": count_before_idle,
                        "idle_capture": idle_capture,
                        "eviction_seconds": EVICTION_WAIT_SECONDS,
                        "same_process_refetch": same_process_refetch,
                        "reopened_documents": reopened_documents,
                        "reopen_launch": reopen_launch,
                        "reopen_capture": reopen_capture,
                        "stopped_pid": stopped_pid,
                        "recovered_launch": recovered_launch,
                        "recovered_documents": recovered_documents,
                        "recovered_assets": proxy.requests(),
                        "recovered_cache": recovered_cache,
                        "recovered_capture": recovered_capture,
                        "recovered_trace": recovered_trace,
                        "peer_requests": peer.requests(),
                    }
        force_stop(name, "cleanup")
        return result

    def shared_case(case: dict[str, Any]) -> dict[str, Any]:
        name = str(case["name"])
        clear(name)
        with ClientBridge(Path(case["world"])) as bridge:
            with CustomEmojiFaultServer(bridge.base_url, case["capability"]) as peer:
                hold = peer.hold_asset(2)
                peer.phase("shared")
                with NativeAssetProxy(peer.base_url, case["capability"]) as proxy:
                    proxy.phase("shared")
                    configure(proxy.base_url, case)
                    launched = launch(name, "initial")
                    if not hold.partial_sent.wait(timeout=45):
                        capture(name, "hold-timeout")
                        raise RuntimeError(
                            "Shared custom emoji thumbnail did not reach held response"
                        )
                    initial_capture = wait_ui(name, "initial", case["labels"])
                    with World.open(Path(case["world"])) as world:
                        world.edit_message(
                            chat_id=1,
                            message_id=1,
                            bot_id=2,
                            text="Static removed",
                        )
                    removed_capture = wait_ui(
                        name,
                        "removed",
                        ["Static removed", "Second carrier"],
                    )
                    hold.release.set()
                    if not hold.finished.wait(timeout=45):
                        raise RuntimeError("Held shared thumbnail did not finish")
                    cache = wait_cache(name, "complete", {"2_2.jpg"})
                    complete_capture = wait_ui(
                        name,
                        "complete",
                        ["Static removed", "Second carrier"],
                    )
                    result = {
                        "launch": launched,
                        "initial_capture": initial_capture,
                        "removed_capture": removed_capture,
                        "complete_capture": complete_capture,
                        "cache": cache,
                        "documents": proxy.document_requests(),
                        "assets": proxy.requests(),
                        "trace": trace(name, "complete"),
                        "peer_requests": peer.requests(),
                        "hold": {
                            "started": hold.started.is_set(),
                            "partial_sent": hold.partial_sent.is_set(),
                            "finished": hold.finished.is_set(),
                        },
                    }
        force_stop(name, "cleanup")
        return result

    adb("install", "install", "--no-streaming", "/work/client.apk", timeout=60)
    try:
        document_results = {
            case["name"]: document_case(case) for case in manifest["document_cases"]
        }
        shared = shared_case(manifest["shared_case"])
        accounts = adb("accounts", "shell", "dumpsys", "account").stdout
        result: dict[str, object] = {
            "document_cases": document_results,
            "shared": shared,
            "expected": manifest["expected"],
            "accounts": accounts,
            "limits": {
                "same_process_refetch": (
                    "External outcome only; callback owner identity is not observed."
                ),
                "late_completion": (
                    "File completion and surviving UI only; removed receiver delivery is not "
                    "observed."
                ),
                "batching": (
                    "A false batch_observed value retains failure evidence without claiming "
                    "original batching."
                ),
            },
        }
        serialized = json.dumps(result)
        capabilities = [case["capability"] for case in manifest["document_cases"]] + [
            manifest["shared_case"]["capability"]
        ]
        if any(secret in serialized for secret in capabilities):
            raise RuntimeError("Custom emoji fault result contained a capability")
        return result
    finally:
        guest("shell", "am", "force-stop", PACKAGE)


if __name__ == "__main__":
    main(probe)
