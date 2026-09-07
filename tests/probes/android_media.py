"""Observe local photos in the original Android renderer and its private cache."""

import hashlib
import json
import re
import shlex
import shutil
import subprocess
import time
import xml.etree.ElementTree as ET
from collections.abc import Callable
from pathlib import Path
from typing import Any

from android_guest import main
from media_round_trip import run
from native_asset_proxy import NativeAssetProxy

from gramlab.client_bridge import ClientBridge
from gramlab.world import World

PACKAGE = "org.gramlab.android"
CONFIG = "files/gramlab/config.json"
TRACE = "files/gramlab/trace.jsonl"
MEDIA_EVENTS = {
    "media_load_start",
    "media_load_coalesced",
    "media_cache_hit",
    "media_load_success",
    "media_load_failure",
    "media_load_cancel",
}
BOUNDS = re.compile(r"^\[(\d+),(\d+)\]\[(\d+),(\d+)\]$")


def bounds(node: ET.Element) -> tuple[int, int, int, int]:
    match = BOUNDS.fullmatch(node.get("bounds", ""))
    if match is None:
        raise ValueError("UI node has invalid bounds")
    left, top, right, bottom = (int(value) for value in match.groups())
    return left, top, right, bottom


def ordinary_frame(xml: str) -> dict[str, int] | None:
    """Locate the ordinary caption and derive unobscured chat bounds from UI structure."""
    root = ET.fromstring(xml)  # noqa: S314 — dedicated guest UIAutomator output
    parents = {child: parent for parent in root.iter() for child in parent}
    target = next(
        (
            node
            for node in root.iter("node")
            if "PNG ordinary / تصویر معمولی" in node.get("text", "")
        ),
        None,
    )
    if target is None:
        return None
    header_controls = [
        node
        for node in root.iter("node")
        if node.get("content-desc") in ("Go back", "More options")
    ]
    editor = next(
        (
            node
            for node in root.iter("node")
            if node.get("class") == "android.widget.EditText" and node.get("text") == "Message"
        ),
        None,
    )
    if not header_controls or editor is None:
        raise ValueError("Chat chrome is unavailable in UI structure")
    message_list = next(
        (
            node
            for node in root.iter("node")
            if node.get("class") == "androidx.recyclerview.widget.RecyclerView"
            and node.get("scrollable") == "true"
        ),
        None,
    )
    if message_list is None:
        raise ValueError("Chat message list is unavailable in UI structure")
    viewport_left, _, viewport_right, message_list_bottom = bounds(message_list)
    header_bottom = max(bounds(node)[3] for node in header_controls)
    composer = editor
    ancestor = editor
    while ancestor in parents:
        candidate = parents[ancestor]
        if not candidate.get("bounds"):
            ancestor = candidate
            continue
        left, top, right, bottom = bounds(candidate)
        if (
            right - left >= (viewport_right - viewport_left) * 0.9
            and top > header_bottom
            and bottom < message_list_bottom
        ):
            composer = candidate
        ancestor = candidate
    target_left, target_top, target_right, target_bottom = bounds(target)
    return {
        "target_left": target_left,
        "target_top": target_top,
        "target_right": target_right,
        "target_bottom": target_bottom,
        "viewport_left": viewport_left,
        "viewport_top": header_bottom,
        "viewport_right": viewport_right,
        "viewport_bottom": bounds(composer)[1],
    }


def probe(guest: Callable[..., subprocess.CompletedProcess[str]]) -> dict[str, object]:
    control = Path("unchanged-photo-control.json").exists()
    assets = {1} if control else {1, 2}
    capability = ""
    proxy: NativeAssetProxy | None = None
    phases: dict[str, dict[str, Any]] = {}
    active_phase = "initial"
    partials: dict[str, list[str]] = {}
    bindings: dict[str, dict[str, Any]] = {}
    control_frames: dict[str, dict[str, int]] = {}
    identity: dict[str, Any] | None = None
    expected_counts = (
        {"initial": {1: 1}, "restart": {1: 0}}
        if control
        else {"initial": {1: 1, 2: 2}, "edited": {1: 1, 2: 0}, "restart": {1: 0, 2: 1}}
    )
    installed = False
    launches: dict[str, str] = {}
    timings: dict[str, float] = {}
    captures: dict[str, str] = {}
    cache: dict[str, dict[str, Any]] = {}
    framing: list[dict[str, int]] = []

    def adb(*arguments: str, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        result = guest(*arguments, **kwargs)
        if result.returncode:
            retain(
                "command-failure.json",
                json.dumps(
                    {
                        "arguments": arguments,
                        "returncode": result.returncode,
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                    },
                    indent=2,
                ),
            )
            raise RuntimeError(f"Dedicated Android media command failed: {arguments[0]}")
        return result

    def retain(name: str, value: str) -> str:
        if capability and capability in value:
            raise RuntimeError("Android media evidence contained a client capability")
        Path(name).write_text(value)
        return value

    def trace(name: str) -> list[dict[str, Any]]:
        raw = adb("shell", "run-as", PACKAGE, "cat", TRACE).stdout
        retain(f"{name}-trace.jsonl", raw)
        return [json.loads(line) for line in raw.splitlines()]

    def write_config(configuration: dict[str, Any]) -> None:
        nonlocal capability
        capability = configuration["capability"]
        native = {key: value for key, value in configuration.items() if key != "stage"} | {
            "endpoint": configuration["endpoint"].replace("127.0.0.1", "10.0.2.2")
        }
        if native.get("bridge_version") != 3:
            raise RuntimeError("Media scenario requires explicit bridge version 3")
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
        started = time.monotonic()
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
        launches[name] = retain(f"{name}-launch.log", result.stdout + result.stderr)
        timings[f"{name}_launch_seconds"] = time.monotonic() - started

    def capture(name: str) -> str:
        adb("shell", "uiautomator", "dump", "/data/local/tmp/media.xml", timeout=15)
        ui = adb("shell", "cat", "/data/local/tmp/media.xml").stdout
        retain(f"{name}.xml", ui)
        adb("shell", "screencap", "-p", "/data/local/tmp/media.png")
        adb("pull", "/data/local/tmp/media.png", f"/work/{name}.png")
        captures[name] = ui
        return ui

    def frame_ordinary() -> str:
        for attempt in range(7):
            name = f"initial-framing-{attempt}"
            ui = capture(name)
            captures.pop(name)
            frame = ordinary_frame(ui)
            if frame is not None:
                if (
                    frame["target_left"] >= frame["viewport_left"]
                    and frame["target_right"] <= frame["viewport_right"]
                    and frame["target_top"] >= frame["viewport_top"]
                    and frame["target_bottom"] <= frame["viewport_bottom"]
                ):
                    shutil.copy2(f"{name}.xml", f"{name}-before-media.xml")
                    shutil.copy2(f"{name}.png", f"{name}-before-media.png")
                    wait_for_media("initial-framing", assets)
                    ui = capture(name)
                    captures.pop(name)
                    frame = ordinary_frame(ui)
                    if frame is None:
                        raise RuntimeError("Ordinary photo disappeared after media loading")
                framing.append(frame | {"attempt": attempt})
                if (
                    frame["target_left"] >= frame["viewport_left"]
                    and frame["target_right"] <= frame["viewport_right"]
                    and frame["target_top"] >= frame["viewport_top"]
                    and frame["target_bottom"] <= frame["viewport_bottom"]
                ):
                    # Preserve four public captures; intermediate framing artifacts remain separate.
                    shutil.copy2(f"{name}.xml", "initial-top.xml")
                    shutil.copy2(f"{name}.png", "initial-top.png")
                    captures["initial-top"] = ui
                    Path(f"{name}-structure.json").write_text(
                        json.dumps({"attempt": attempt, "frame": frame}, indent=2) + "\n"
                    )
                    return ui
                downward = frame["target_top"] < frame["viewport_top"]
            else:
                downward = True
            Path(f"{name}-structure.json").write_text(
                json.dumps({"attempt": attempt, "frame": frame}, indent=2) + "\n"
            )
            adb(
                "shell",
                "input",
                "swipe",
                "160",
                "220" if downward else "470",
                "160",
                "380" if downward else "310",
                "350",
            )
            time.sleep(0.35)
        raise RuntimeError("Ordinary photo could not be framed in seven bounded gestures")

    def media_rows(name: str) -> list[dict[str, Any]]:
        rows = [row for row in trace(name) if row.get("event") in MEDIA_EVENTS]
        for row in rows:
            if set(row) != {"event", "asset_id", "cache_file", "file_size", "digest_ok"}:
                raise RuntimeError("Media diagnostic row has an unexpected shape")
            if row["asset_id"] not in (1, 2) or row["cache_file"] not in (
                "1_1.jpg",
                "2_1.jpg",
            ):
                raise RuntimeError("Media diagnostic identifies an unexpected asset")
        return rows

    def cache_files(name: str) -> dict[str, Any]:
        listing = adb(
            "shell",
            "run-as",
            PACKAGE,
            "find",
            ".",
            "-type",
            "f",
            "-name",
            "*_1.jpg",
        ).stdout.splitlines()
        external = f"/storage/emulated/0/Android/data/{PACKAGE}"
        listing += adb(
            "shell", "find", external, "-type", "f", "-name", "'*_1.jpg'"
        ).stdout.splitlines()
        selected: dict[str, Any] = {}
        for filename in (f"{asset}_1.jpg" for asset in sorted(assets)):
            matches = [path for path in listing if Path(path).name == filename]
            copies = []
            for path in sorted(matches):
                quoted = shlex.quote(path)
                command = (
                    ("shell",) if path.startswith(external + "/") else ("shell", "run-as", PACKAGE)
                )
                digest = adb(*command, "toybox", "sha256sum", quoted).stdout.split()[0]
                size = int(adb(*command, "toybox", "wc", "-c", quoted).stdout.split()[0])
                copies.append({"path": path, "sha256": digest, "size": size})
            selected[filename] = {"copies": copies}
        unfinished = adb(
            "shell", "run-as", PACKAGE, "find", ".", "-type", "f", "-name", "'*.gramlab-*.part'"
        ).stdout.splitlines()
        unfinished += adb(
            "shell", "find", external, "-type", "f", "-name", "'*.gramlab-*.part'"
        ).stdout.splitlines()
        partials[name] = sorted(unfinished)
        Path(f"{name}-partials.json").write_text(json.dumps(partials[name]) + "\n")
        Path(f"{name}-cache.json").write_text(json.dumps(selected, indent=2) + "\n")
        cache[name] = selected
        return selected

    def wait_for_media(name: str, required_assets: set[int]) -> None:
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            rows = media_rows(name)[phases[active_phase]["media_start"] :]
            successful = {
                int(row["asset_id"])
                for row in rows
                if row["event"] in ("media_load_success", "media_cache_hit")
                and row["digest_ok"] is True
            }
            if required_assets <= successful:
                return
            time.sleep(0.25)
        raise RuntimeError(f"Original Android did not finish media loading during {name}")

    def begin_phase(name: str) -> None:
        nonlocal active_phase
        rows = trace(name + "-boundary") if installed and phases else []
        if phases:
            phases[active_phase]["trace_end"] = len(rows)
        active_phase = name
        phases[name] = {
            "trace_start": len(rows),
            "media_start": sum(row.get("event") in MEDIA_EVENTS for row in rows),
        }
        assert proxy is not None
        proxy.phase(name)

    def expected_paths(stage: str, asset: int) -> set[str]:
        root = f"/storage/emulated/0/Android/data/{PACKAGE}/"
        image = root + f"files/Telegram/Telegram Images/{asset}_1.jpg"
        cached = root + f"cache/{asset}_1.jpg"
        if control or (stage == "initial" and asset == 1):
            return {image}
        if stage == "edited" and asset == 2:
            return {cached}
        return {image, cached}

    def settle(stage: str) -> None:
        assert proxy is not None
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            rows = trace(stage)[phases[stage]["trace_start"] :]
            requests = [row for row in proxy.requests() if row["phase"] == stage]
            valid = True
            for asset, expected in expected_counts[stage].items():
                starts = [
                    r
                    for r in rows
                    if r.get("event") == "media_load_start" and r["asset_id"] == asset
                ]
                successes = [
                    r
                    for r in rows
                    if r.get("event") == "media_load_success"
                    and r["asset_id"] == asset
                    and r["digest_ok"] is True
                ]
                reads = [r for r in requests if r["asset_id"] == asset]
                if len(starts) > expected or len(reads) > expected:
                    raise RuntimeError(f"Unexpected new asset {asset} transfer in {stage}")
                source = Path(
                    "photo-square-16x16.png" if asset == 1 else "photo-quadrants-64x48.jpg"
                ).read_bytes()
                valid &= len(starts) == len(successes) == len(reads) == expected
                valid &= all(
                    r["status"] == 200
                    and r["bytes"] == len(source)
                    and r["error"] is None
                    and r["finished_ns"] is not None
                    for r in reads
                )
            if any(r.get("event") in ("media_load_failure", "media_load_cancel") for r in rows):
                raise RuntimeError(f"Original media failed or cancelled during {stage}")
            valid &= any(
                r.get("event") == ("events_applied" if stage == "edited" else "initialized")
                for r in rows
            )
            if not valid:
                time.sleep(0.25)
                continue
            # Inspect destinations after this phase's transfers finish, so hashing cannot
            # race the expected in-progress publication/deletion work.
            files = cache_files(stage)
            valid = not partials[stage]
            for asset in expected_counts[stage]:
                source = Path(
                    "photo-square-16x16.png" if asset == 1 else "photo-quadrants-64x48.jpg"
                ).read_bytes()
                copies = files[f"{asset}_1.jpg"]["copies"]
                valid &= {copy["path"] for copy in copies} == expected_paths(stage, asset)
                valid &= all(
                    copy["size"] == len(source)
                    and copy["sha256"] == hashlib.sha256(source).hexdigest()
                    for copy in copies
                )
            if valid:
                phases[stage]["trace_end"] = phases[stage]["trace_start"] + len(rows)
                return
            time.sleep(0.25)
        raise RuntimeError(
            f"Original media did not reach exact phase/cache/request state in {stage}"
        )

    def control_binding(configuration: dict[str, Any]) -> None:
        stage = configuration["stage"]
        deadline = time.monotonic() + 20
        pid = int(adb("shell", "pidof", PACKAGE).stdout.strip())
        while time.monotonic() < deadline:
            result = guest(
                "shell", "run-as", PACKAGE, "cat", "files/gramlab/photo-observation-result.json"
            )
            if result.returncode == 0:
                value = json.loads(result.stdout)
                uptime = float(adb("shell", "cat", "/proc/uptime").stdout.split()[0]) * 1000
                identity = {
                    "schema": 1,
                    "nonce": "unchanged-" + stage,
                    "world_id": configuration["world_id"],
                    "user_id": 1,
                    "peer_id": 2,
                    "pid": pid,
                }
                if any(value.get(key) != expected for key, expected in identity.items()):
                    raise RuntimeError("Unchanged-photo observer identity mismatch")
                if (
                    value["available"]
                    and value["generation"] > 0
                    and 0 <= uptime - value["uptime_ms"] <= 1000
                ):
                    messages = value["messages"]
                    if (
                        len(messages) == 1
                        and messages[0]["message_id"] == 1
                        and messages[0]["has_image"]
                        and str(messages[0]["image_key"]).startswith("1_1@")
                    ):
                        bindings[stage] = value | {"observed_uptime_ms": uptime}
                        retain(stage + "-binding.json", json.dumps(bindings[stage]))
                        return
            time.sleep(0.1)
        raise RuntimeError("Unchanged original photo did not decode into its current receiver")

    def show(configuration: dict[str, Any]) -> str:
        nonlocal installed, proxy, identity
        current_identity = {
            key: configuration[key]
            for key in ("capability", "world_id", "user_id", "bridge_version")
        }
        if identity is None:
            identity = current_identity
        elif current_identity != identity:
            raise RuntimeError("Native photo scenario changed its World/persona binding")
        stage = configuration["stage"]
        if stage not in expected_counts:
            raise RuntimeError("Unknown media observation stage")
        if not installed:
            started = time.monotonic()
            adb("install", "--no-streaming", "/work/client.apk", timeout=60)
            timings["install_seconds"] = time.monotonic() - started
            installed = True
        if stage == "restart":
            adb("shell", "am", "force-stop", PACKAGE)
        if proxy is None:
            proxy = NativeAssetProxy(configuration["endpoint"], configuration["capability"])
            proxy.__enter__()
            begin_phase(stage)
        else:
            proxy.retarget(configuration["endpoint"])
            if stage == "restart":
                begin_phase(stage)
        write_config(configuration | {"endpoint": proxy.base_url})
        if control:
            adb(
                "shell",
                "run-as",
                PACKAGE,
                "rm",
                "-f",
                "files/gramlab/photo-observation-result.json",
            )
            activation = {
                "schema": 1,
                "nonce": "unchanged-" + stage,
                "world_id": configuration["world_id"],
                "user_id": 1,
                "peer_id": 2,
                "message_ids": [1],
            }
            adb(
                "shell",
                "-T",
                "run-as",
                PACKAGE,
                "sh",
                "-c",
                "'cat > files/gramlab/photo-observation.json'",
                input=json.dumps(activation),
            )
        if stage in ("initial", "restart"):
            launch(stage)
        if control:
            if stage == "initial":
                wait_for_media(stage, {1})
                frame_ordinary()
            control_binding(configuration)
            settle(stage)
            capture(stage)
            frame = ordinary_frame(captures[stage])
            if frame is None or not (
                frame["viewport_left"]
                <= frame["target_left"]
                < frame["target_right"]
                <= frame["viewport_right"]
                and frame["viewport_top"]
                <= frame["target_top"]
                < frame["target_bottom"]
                <= frame["viewport_bottom"]
            ):
                raise RuntimeError("Unchanged ordinary photo/caption is not fully framed")
            control_frames[stage] = frame
            control_binding(configuration)
            settle(stage)
            if stage == "initial":
                captures.pop("initial-top")
            return captures[stage]
        if stage == "initial":
            wait_for_media(stage, {2})
            bottom = capture("initial-bottom")
            top = frame_ordinary()
            settle(stage)
            # The bot may edit before show(edited); its native work belongs to this next phase.
            begin_phase("edited")
            return bottom + "\n" + top
        if stage == "edited":
            deadline = time.monotonic() + 45
            while not any(
                r.get("event") == "events_applied"
                for r in trace(stage)[phases[stage]["trace_start"] :]
            ):
                if time.monotonic() >= deadline:
                    raise RuntimeError("Native edit did not apply")
                time.sleep(0.25)
            adb("shell", "input", "swipe", "160", "520", "160", "180", "500")
            time.sleep(0.5)
        settle(stage)
        capture(stage)
        settle(stage)
        return captures[stage]

    def observe() -> dict[str, Any]:
        final_trace = trace("final")
        phases[active_phase]["trace_end"] = len(final_trace)
        assert proxy is not None
        requests = proxy.requests()
        retain("native-asset-requests.json", json.dumps(requests, indent=2))
        return {
            "phases": phases,
            "native_requests": requests,
            "partials": {stage: partials[stage] for stage in expected_counts},
            "bindings": bindings,
            "control_frames": control_frames,
            "captures": captures,
            "launches": launches,
            "timings": timings,
            "media_trace": [row for row in final_trace if row.get("event") in MEDIA_EVENTS],
            "cache": {stage: cache[stage] for stage in expected_counts},
            "framing": framing,
            "accounts": adb("shell", "dumpsys", "account").stdout,
        }

    try:
        return run_unchanged(show, observe) if control else run(show, observe)
    except BaseException:
        raw_trace = guest("shell", "run-as", PACKAGE, "cat", TRACE)
        if raw_trace.returncode == 0:
            retain("failure-trace.jsonl", raw_trace.stdout)
        guest("shell", "uiautomator", "dump", "/data/local/tmp/media-failure.xml", timeout=15)
        failure_xml = guest("shell", "cat", "/data/local/tmp/media-failure.xml")
        if failure_xml.returncode == 0:
            retain("failure.xml", failure_xml.stdout)
        guest("shell", "screencap", "-p", "/data/local/tmp/media-failure.png")
        guest("pull", "/data/local/tmp/media-failure.png", "/work/failure.png")
        cache_listing = guest("shell", "run-as", PACKAGE, "find", ".", "-type", "f")
        if cache_listing.returncode == 0:
            retain("failure-cache-files.txt", cache_listing.stdout)
        failure_log = guest("logcat", "-d", "-t", "2000", "-v", "brief")
        if failure_log.returncode == 0:
            retain("failure-logcat.txt", failure_log.stdout)
        raise
    finally:
        guest("shell", "am", "force-stop", PACKAGE)
        if proxy is not None:
            retain("native-asset-requests.json", json.dumps(proxy.requests(), indent=2))
            proxy.__exit__(None, None, None)


def run_unchanged(
    show: Callable[[dict[str, Any]], str], observe: Callable[[], dict[str, Any]]
) -> dict[str, Any]:
    directory = Path("unchanged-world")
    with World.create(directory, seed=23, now=1700000000) as world:
        world.create_user(first_name="Sara", language_code="fa")
        world.create_user(first_name="Echo", username="gramlab_echo_bot", is_bot=True)
        world.open_private_chat(user_id=1, bot_id=2)
        world.send_photo(
            chat_id=1,
            sender_id=2,
            photo={"type": "photo", "media": "attach://photo"},
            uploads={"photo": Path("photo-square-16x16.png").read_bytes()},
            caption="PNG ordinary / تصویر معمولی",
        )
        capability = world.issue_client_token(1)
        world_id = world.world_id
        snapshot = world.client_snapshot(1, version=3)
    for stage in ("initial", "restart"):
        with ClientBridge(directory) as bridge:
            show(
                {
                    "stage": stage,
                    "endpoint": bridge.base_url,
                    "capability": capability,
                    "world_id": world_id,
                    "user_id": 1,
                    "bridge_version": 3,
                }
            )
            if stage == "restart":
                result = observe()
    with World.open(directory) as world:
        restarted = world.client_snapshot(1, version=3)
    value = {"snapshot": snapshot, "restarted_snapshot": restarted, "client": result}
    if capability in json.dumps(value):
        raise RuntimeError("Unchanged-photo evidence contains a capability")
    return value


if __name__ == "__main__":
    main(probe)
