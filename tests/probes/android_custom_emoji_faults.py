"""Drive bounded original custom-emoji lookup faults and explicit recovery."""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import time
import uuid
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
MAX_CHECKPOINT_BYTES = 4 * 1024 * 1024
MAX_FAILURE_OUTPUT_BYTES = 1024 * 1024


def _retain_text(path: Path, value: str, secrets: list[str]) -> str:
    if any(secret and secret in value for secret in secrets):
        raise RuntimeError("Custom emoji fault diagnostics contained a capability")
    path.write_text(value)
    return value


def _guest_before_deadline(
    guest: Callable[..., subprocess.CompletedProcess[str]],
    arguments: tuple[str, ...],
    options: dict[str, Any],
    deadline: float,
) -> subprocess.CompletedProcess[str]:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError("Custom emoji fault diagnostic deadline expired")
    return guest(*arguments, **(options | {"timeout": remaining}))


def _write_checkpoint(path: Path, value: object, secrets: list[str]) -> None:
    """Atomically retain one bounded record without replacing earlier evidence."""
    serialized = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
    if len(serialized) > MAX_CHECKPOINT_BYTES:
        raise ValueError("Custom emoji fault checkpoint exceeds its bound")
    if any(secret and secret.encode() in serialized for secret in secrets):
        raise RuntimeError("Custom emoji fault checkpoint contained a capability")
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.partial")
    try:
        with temporary.open("xb") as stream:
            stream.write(serialized)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        temporary.unlink(missing_ok=True)


def probe(guest: Callable[..., subprocess.CompletedProcess[str]]) -> dict[str, object]:
    manifest = json.loads(Path("cases.json").read_text())
    capabilities = [case["capability"] for case in manifest["document_cases"]] + [
        manifest["shared_case"]["capability"]
    ]
    active_phase = "install"
    shared_failure: dict[str, Any] = {}

    def retain(name: str, value: str) -> str:
        return _retain_text(Path(name), value, capabilities)

    def adb(name: str, *arguments: str, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        diagnostic_bound = kwargs.pop("diagnostic_bound", None)
        deadline = kwargs.pop("deadline", None)
        result = (
            guest(*arguments, **kwargs)
            if deadline is None
            else _guest_before_deadline(guest, arguments, kwargs, deadline)
        )
        if diagnostic_bound is not None and (
            len(result.stdout.encode()) > diagnostic_bound
            or len(result.stderr.encode()) > diagnostic_bound
        ):
            raise ValueError("Custom emoji fault diagnostic output exceeds its bound")
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
        body = json.dumps(
            {
                "endpoint": endpoint.replace("127.0.0.1", "10.0.2.2"),
                "capability": case["capability"],
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

    def trace(case: str, stage: str, *, deadline: float | None = None) -> list[dict[str, Any]]:
        options = (
            {}
            if deadline is None
            else {
                "deadline": deadline,
                "diagnostic_bound": MAX_FAILURE_OUTPUT_BYTES,
            }
        )
        raw = adb(
            case + "-" + stage + "-trace",
            "shell",
            "run-as",
            PACKAGE,
            "cat",
            TRACE,
            **options,
        ).stdout
        if deadline is not None and len(raw.encode()) > MAX_FAILURE_OUTPUT_BYTES:
            raise ValueError("Custom emoji fault trace exceeds its bound")
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

    def cache_files(
        case: str, stage: str, *, deadline: float | None = None
    ) -> dict[str, list[dict[str, Any]]]:
        external = f"/storage/emulated/0/Android/data/{PACKAGE}"
        selected: dict[str, list[dict[str, Any]]] = {"2_2.jpg": []}
        areas = (
            ("internal", ["shell", "run-as", PACKAGE, "find", ".", "-type", "f"]),
            ("external", ["shell", "find", external, "-type", "f"]),
        )
        for area, command in areas:
            options = (
                {}
                if deadline is None
                else {
                    "deadline": deadline,
                    "diagnostic_bound": MAX_FAILURE_OUTPUT_BYTES,
                }
            )
            paths = adb(case + "-" + stage + "-" + area + "-find", *command, **options).stdout
            for path in paths.splitlines():
                name = Path(path).name
                if name not in selected:
                    continue
                quoted = shlex.quote(path)
                prefix = ["shell", "run-as", PACKAGE] if area == "internal" else ["shell"]
                options = (
                    {}
                    if deadline is None
                    else {
                        "deadline": deadline,
                        "diagnostic_bound": MAX_FAILURE_OUTPUT_BYTES,
                    }
                )
                size = int(
                    adb(
                        case + "-" + stage + "-" + area + "-" + name + "-size",
                        *prefix,
                        "toybox",
                        "wc",
                        "-c",
                        quoted,
                        **options,
                    ).stdout.split()[0]
                )
                options = (
                    {}
                    if deadline is None
                    else {
                        "deadline": deadline,
                        "diagnostic_bound": MAX_FAILURE_OUTPUT_BYTES,
                    }
                )
                digest = adb(
                    case + "-" + stage + "-" + area + "-" + name + "-sha",
                    *prefix,
                    "toybox",
                    "sha256sum",
                    quoted,
                    **options,
                ).stdout.split()[0]
                selected[name].append({"area": area, "path": path, "size": size, "sha256": digest})
        serialized = json.dumps(selected, indent=2)
        if deadline is not None and len(serialized.encode()) > MAX_FAILURE_OUTPUT_BYTES:
            raise ValueError("Custom emoji fault cache evidence exceeds its bound")
        retain(case + "-" + stage + "-cache.json", serialized)
        return selected

    def failure_native_diagnostics(case: str) -> dict[str, object]:
        """Retain failure-only private state without extending the successful path."""
        deadline = time.monotonic() + 8
        observed: dict[str, object] = {}
        for name, path, operation in (
            (
                "trace",
                case + "-failure-trace.jsonl",
                lambda: trace(case, "failure", deadline=deadline),
            ),
            (
                "cache",
                case + "-failure-cache.json",
                lambda: cache_files(case, "failure", deadline=deadline),
            ),
        ):
            try:
                operation()
                observed[name + "_path"] = path
            except BaseException as error:
                observed[name] = {"unavailable_exception_class": type(error).__name__}
        try:
            logcat = adb(
                case + "-failure-logcat",
                "logcat",
                "-d",
                "-t",
                "2000",
                deadline=deadline,
                diagnostic_bound=MAX_FAILURE_OUTPUT_BYTES,
            ).stdout
            if len(logcat.encode()) > MAX_FAILURE_OUTPUT_BYTES:
                raise ValueError("Custom emoji fault logcat exceeds its bound")
            retain(case + "-failure-logcat.txt", logcat)
            observed["logcat_path"] = case + "-failure-logcat.txt"
        except BaseException as error:
            observed["logcat"] = {"unavailable_exception_class": type(error).__name__}
        return observed

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
        nonlocal active_phase
        name = str(case["name"])
        fault: DocumentFault = case["fault"]
        active_phase = f"document:{name}"
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
        nonlocal active_phase, shared_failure
        name = str(case["name"])
        partial_sent_ns: int | None = None
        release_ns: int | None = None
        finished_ns: int | None = None
        active_phase = "shared:setup"
        clear(name)
        with ClientBridge(Path(case["world"])) as bridge:
            with CustomEmojiFaultServer(bridge.base_url, case["capability"]) as peer:
                hold = peer.hold_asset(2, progress_interval=1.0)
                peer.phase("shared")
                with NativeAssetProxy(peer.base_url, case["capability"]) as proxy:
                    proxy.phase("shared")
                    configure(proxy.base_url, case)
                    try:
                        active_phase = "shared:launch"
                        launched = launch(name, "initial")
                        active_phase = "shared:wait_partial"
                        if not hold.partial_sent.wait(timeout=45):
                            capture(name, "hold-timeout")
                            raise RuntimeError(
                                "Shared custom emoji thumbnail did not reach held response"
                            )
                        partial_sent_ns = time.monotonic_ns()
                        active_phase = "shared:initial_capture"
                        initial_capture = wait_ui(name, "initial", case["labels"])
                        active_phase = "shared:edit"
                        with World.open(Path(case["world"])) as world:
                            world.edit_message(
                                chat_id=1,
                                message_id=1,
                                bot_id=2,
                                text="Static removed",
                            )
                        active_phase = "shared:removed_capture"
                        removed_capture = wait_ui(
                            name,
                            "removed",
                            ["Static removed", "Second carrier"],
                        )
                        active_phase = "shared:release"
                        release_ns = time.monotonic_ns()
                        hold.release.set()
                        active_phase = "shared:wait_finished"
                        if not hold.finished.wait(timeout=45):
                            raise RuntimeError("Held shared thumbnail did not finish")
                        finished_ns = time.monotonic_ns()
                        active_phase = "shared:wait_cache"
                        cache = wait_cache(name, "complete", {"2_2.jpg"})
                        active_phase = "shared:complete_capture"
                        complete_capture = wait_ui(
                            name,
                            "complete",
                            ["Static removed", "Second carrier"],
                        )
                        active_phase = "shared:final_trace"
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
                    except BaseException:
                        shared_failure = {
                            "peer_requests": peer.requests(),
                            "document_requests": proxy.document_requests(),
                            "asset_requests": proxy.requests(),
                            "hold": {
                                "started": hold.started.is_set(),
                                "partial_sent": hold.partial_sent.is_set(),
                                "released": hold.release.is_set(),
                                "finished": hold.finished.is_set(),
                                "partial_sent_observed_ns": partial_sent_ns,
                                "release_ns": release_ns,
                                "finished_observed_ns": finished_ns,
                            },
                            "native": failure_native_diagnostics(name),
                        }
                        raise
        force_stop(name, "cleanup")
        return result

    adb("install", "install", "--no-streaming", "/work/client.apk", timeout=60)
    document_results: dict[str, dict[str, Any]] = {}
    try:
        for index, case in enumerate(manifest["document_cases"]):
            name = str(case["name"])
            if re.fullmatch(r"[a-z0-9-]{1,64}", name) is None:
                raise ValueError("Invalid custom emoji fault case name")
            document_result = document_case(case)
            active_phase = f"document:{name}:checkpoint"
            _write_checkpoint(
                Path(f"custom-emoji-fault-document-{index:02d}-{name}.json"),
                {
                    "schema": 1,
                    "kind": "completed_document_case",
                    "case": name,
                    "result": document_result,
                },
                capabilities,
            )
            document_results[name] = document_result
        active_phase = "shared:setup"
        shared = shared_case(manifest["shared_case"])
        active_phase = "final:accounts"
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
        if any(secret in serialized for secret in capabilities):
            raise RuntimeError("Custom emoji fault result contained a capability")
        return result
    except BaseException as error:
        _write_checkpoint(
            Path("custom-emoji-fault-failure.json"),
            {
                "schema": 1,
                "kind": "failure",
                "phase": active_phase,
                "exception_class": type(error).__name__,
                "completed_document_cases": list(document_results),
                "shared": shared_failure or None,
            },
            capabilities,
        )
        raise
    finally:
        guest("shell", "am", "force-stop", PACKAGE)


if __name__ == "__main__":
    main(probe)
