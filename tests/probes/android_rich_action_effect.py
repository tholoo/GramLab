"""Explicit test-only guest input using the GPL experiment's observed post-draw rectangles.

This consumer never derives native layout or dispatches a callback. Each selected rectangle
receives exactly one ordinary guest tap; missing or stale observations fail without fallback.
"""

import json
import math
import subprocess
import time
import uuid
import xml.etree.ElementTree as ET
from collections.abc import Callable
from pathlib import Path
from typing import Any

from android_guest import main
from android_rich_messages import probe
from rich_action_effect_round_trip import run, state

from gramlab.world import World

AGE_LIMIT_MS = 5000
PACKAGE = "org.gramlab.android"
DIRECTORY = "files/gramlab/"


def effect_probe(guest: Callable[..., subprocess.CompletedProcess[str]]) -> dict[str, object]:
    experiment: dict[str, Any] = {"taps": [], "age_limit_ms": AGE_LIMIT_MS}
    activation: dict[str, Any] = {}
    binding: dict[str, Any] = {}
    expected = json.loads(Path("effect-expected.json").read_text())["world_initial"]
    original_state: tuple[dict[str, Any], list[dict[str, Any]]] | None = None

    def adb(*arguments: str, **kwargs: Any) -> str:
        result = guest(*arguments, **kwargs)
        if result.returncode:
            raise RuntimeError(f"Dedicated rich-action command failed: {arguments[0]}")
        return result.stdout

    def world_state() -> tuple[dict[str, Any], list[dict[str, Any]]]:
        with World.open(Path("world")) as world:
            return world.client_snapshot(1, version=2), world.events()

    def activate(configuration: dict[str, Any], message_id: int) -> None:
        nonlocal activation
        activation = {
            "schema": 1,
            "nonce": uuid.uuid4().hex,
            "world_id": configuration["world_id"],
            "user_id": configuration["user_id"],
            "peer_id": expected["sender_id"],
            "message_id": message_id,
        }
        adb(
            "shell",
            "-T",
            "run-as",
            PACKAGE,
            "sh",
            "-c",
            "'umask 077; cat > files/gramlab/rich-action-geometry.json'",
            input=json.dumps(activation),
        )
        experiment.setdefault("activations", []).append(dict(activation))

    def configured(configuration: dict[str, Any]) -> None:
        nonlocal original_state, binding
        binding = {key: configuration[key] for key in ("world_id", "user_id")}
        original_state = world_state()
        snapshot = original_state[0]
        if (
            snapshot["world_id"] != configuration["world_id"]
            or snapshot["user_id"] != 1
            or len(snapshot["messages"]) != 2
            or snapshot["messages"][1] != expected
        ):
            raise RuntimeError("Experimental activation does not match the real initial world")

    def clock_and_pid() -> tuple[int, int]:
        process = adb("shell", "pidof", PACKAGE).split()
        if len(process) != 1:
            raise RuntimeError("Expected one experimental application process")
        uptime = float(adb("shell", "cat", "/proc/uptime").split()[0])
        return round(uptime * 1000), int(process[0])

    def fresh(sample: dict[str, Any], minimum: int) -> tuple[int, int]:
        now, pid = clock_and_pid()
        if (
            sample.get("schema") != 1
            or sample.get("nonce") != activation["nonce"]
            or sample.get("peer_id") != activation["peer_id"]
            or sample.get("message_id") != activation["message_id"]
            or sample.get("pid") != pid
            or type(sample.get("generation")) is not int
            or sample["generation"] <= minimum
            or type(sample.get("uptime_ms")) is not int
            or not 0 <= now - sample["uptime_ms"] <= AGE_LIMIT_MS
        ):
            raise ValueError("Experimental geometry identity, generation or age mismatch")
        return now, pid

    def sample_after(minimum: int, *, unavailable: bool = False) -> dict[str, Any]:
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            result = guest(
                "shell", "run-as", PACKAGE, "cat", DIRECTORY + "rich-action-geometry-result.json"
            )
            if result.returncode == 0:
                sample = json.loads(result.stdout)
                with Path("geometry-observations.jsonl").open("a") as stream:
                    stream.write(json.dumps(sample) + "\n")
                try:
                    fresh(sample, minimum)
                except ValueError:
                    pass
                else:
                    if unavailable:
                        if sample.get("available") is True:
                            raise RuntimeError(
                                "Wrong message identity unexpectedly exposed targets"
                            )
                        if (
                            sample.get("available") is False
                            and sample.get("reason") == "message_not_unique_or_visible"
                        ):
                            return dict(sample)
                    elif sample.get("available") is True:
                        return dict(sample)
            # This waits only for real draws; it never invalidates layout or sends guest gestures.
            time.sleep(0.1)
        raise RuntimeError("No fresh explicit geometry observation; input is not attempted")

    def capture(name: str) -> str:
        # Same original screencap/UIAutomator path as the shared rich-message probe.
        adb("shell", "uiautomator", "dump", "/data/local/tmp/rich-action.xml", timeout=15)
        ui = adb("shell", "cat", "/data/local/tmp/rich-action.xml")
        Path(name + ".xml").write_text(ui)
        adb("shell", "screencap", "-p", "/data/local/tmp/rich-action.png")
        adb("pull", "/data/local/tmp/rich-action.png", "/work/" + name + ".png")
        if "Choose:" not in ui:
            raise RuntimeError("Initial original scene disappeared before input")
        return ui

    def target_for(sample: dict[str, Any], index: int) -> dict[str, Any]:
        targets = sample.get("targets")
        if not isinstance(targets, list) or len(targets) != 2:
            raise RuntimeError("Expected exactly the original row and inline rectangles")
        identities: list[tuple[str, str, dict[str, object]]] = [
            ("row", "Copy code", {"copy_text": "GramLab-copy-73Q9"}),
            ("inline", "Unavailable", {"disabled": True}),
        ]
        for position, (kind, label, action) in enumerate(identities):
            target = targets[position]
            expected_identity = {
                "kind": kind,
                "block": position,
                "index": 0,
                "text": label,
            } | action
            if {
                key: value
                for key, value in target.items()
                if key not in {"local_bounds", "origin", "screen_bounds"}
            } != expected_identity:
                raise RuntimeError(
                    "Original effect action or placement differs from the real fixture"
                )
            for field, length in (("screen_bounds", 4), ("local_bounds", 4), ("origin", 2)):
                values = target.get(field)
                if (
                    not isinstance(values, list)
                    or len(values) != length
                    or any(
                        type(value) not in (int, float) or not math.isfinite(value)
                        for value in values
                    )
                ):
                    raise RuntimeError("Missing finite observed native geometry")
            left, top, right, bottom = target["screen_bounds"]
            if not (0 <= left < right <= 320 and 0 <= top < bottom <= 640):
                raise RuntimeError("Original rectangle lies outside the pinned guest viewport")
        return dict(targets[index])

    def restart_with_activation(name: str, message_id: int) -> None:
        adb("shell", "am", "force-stop", PACKAGE)
        activate(binding, message_id)
        launch = adb(
            "shell",
            "am",
            "start",
            "-W",
            "-n",
            PACKAGE + "/org.telegram.ui.LaunchActivity",
            "-a",
            "com.tmessages.openchat",
            "--el",
            "userId",
            "2",
            timeout=40,
        )
        Path(name + "-launch.log").write_text(launch)
        experiment[name + "_launch"] = launch
        if "Status: ok" not in launch or "LaunchState: COLD" not in launch:
            raise RuntimeError("Experimental activation did not cold launch successfully")

    def initial(_: str) -> None:
        # A successful directory listing distinguishes absence from an unreadable app directory.
        files = set(adb("shell", "run-as", PACKAGE, "ls", "-1", DIRECTORY).splitlines())
        now, pid = clock_and_pid()
        absent = {
            "pid": pid,
            "checked_uptime_ms": now,
            "activation_present": "rich-action-geometry.json" in files,
            "geometry_present": "rich-action-geometry-result.json" in files,
            "world_unchanged": original_state == world_state(),
        }
        experiment["absent_activation"] = absent
        if (
            absent["activation_present"]
            or absent["geometry_present"]
            or not absent["world_unchanged"]
        ):
            raise RuntimeError("Absent activation exposed geometry or changed authoritative state")
        restart_with_activation("wrong", expected["id"] + 1000000)
        capture("before-wrong")
        wrong = sample_after(0, unavailable=True)
        wrong_now, wrong_pid = fresh(wrong, 0)
        experiment["wrong_checked_uptime_ms"] = wrong_now
        experiment["wrong_checked_pid"] = wrong_pid
        experiment["wrong_identity"] = wrong
        experiment["wrong_identity_unchanged"] = original_state == world_state()
        if not experiment["wrong_identity_unchanged"] or wrong_pid == pid:
            raise RuntimeError("Wrong identity changed authoritative state or reused its process")
        restart_with_activation("correct", expected["id"])
        sample_after(0)  # Wait for actual stable drawing before asking UIAutomator to capture.
        minimum = 0
        process = None
        for index, phase in enumerate(("before-copy", "before-disabled")):
            capture(phase)
            # Read and check freshness only after the potentially slow PNG/XML capture.
            sample = sample_after(minimum)
            target = target_for(sample, index)
            if sample["pid"] == wrong["pid"] or (process is not None and sample["pid"] != process):
                raise RuntimeError("Unexpected experimental process lifecycle before tap")
            before = state()
            if world_state() != original_state:
                raise RuntimeError("World changed before client-only rich effect")
            now, process = fresh(sample, minimum)
            left, top, right, bottom = target["screen_bounds"]
            x, y = round((left + right) / 2), round((top + bottom) / 2)
            if not left < x < right or not top < y < bottom:
                raise RuntimeError("Observed rectangle has no interior integer tap center")
            tap = {
                "sample": sample,
                "target": target,
                "guest_uptime_before_tap_ms": now,
                "x": x,
                "y": y,
                "world_before": before,
            }
            experiment["taps"].append(tap)
            Path(phase + "-geometry.json").write_text(json.dumps(tap))
            adb("shell", "input", "tap", str(x), str(y), timeout=20)
            # Capture feedback before slow XML traversal can dismiss a transient bulletin.
            adb("shell", "screencap", "-p", "/data/local/tmp/rich-effect-feedback.png")
            adb(
                "pull",
                "/data/local/tmp/rich-effect-feedback.png",
                "/work/" + phase + "-feedback.png",
            )
            paste_and_clear(phase)
            tap["world_after"] = state()
            if tap["world_after"] != before:
                raise RuntimeError("Client-only copy/disabled effect changed World state")
            minimum = sample["generation"]

        adb("shell", "am", "force-stop", PACKAGE)
        launch = adb(
            "shell",
            "am",
            "start",
            "-W",
            "-n",
            PACKAGE + "/org.telegram.ui.LaunchActivity",
            "-a",
            "com.tmessages.openchat",
            "--el",
            "userId",
            "2",
            timeout=40,
        )
        experiment["restart_launch"] = launch
        if "Status: ok" not in launch or "LaunchState: COLD" not in launch:
            raise RuntimeError("Rich-effect restart failed")
        ui = capture("restarted")
        if composer(ui).get("text") != "Message":
            raise RuntimeError("Cleared rich-effect draft survived restart")
        codec = adb(
            "shell",
            "CLASSPATH=/data/local/tmp/gramlab-rich.apk",
            "/system/bin/app_process",
            "/system/bin",
            "org.telegram.gramlab.BridgeProbe",
            "/data/local/tmp/gramlab-rich-config.json",
            timeout=30,
        )
        Path("restarted-codec.json").write_text(codec)
        experiment["restarted_codec"] = json.loads(codec)
        trace = adb("shell", "run-as", PACKAGE, "cat", DIRECTORY + "trace.jsonl")
        Path("effect-trace.jsonl").write_text(trace)
        if any(
            json.loads(line).get("method") == "TL_messages_getBotCallbackAnswer"
            for line in trace.splitlines()
        ):
            raise RuntimeError("Client-only rich effects attempted a native callback")

    def composer(ui: str) -> ET.Element:
        nodes = [
            node
            for node in ET.fromstring(ui).iter("node")  # noqa: S314
            if node.get("class") == "android.widget.EditText" and node.get("package") == PACKAGE
        ]
        if len(nodes) != 1:
            raise RuntimeError("Original composer is missing or ambiguous")
        return nodes[0]

    def paste_and_clear(phase: str) -> None:
        ui = capture(phase + "-after-tap")
        node = composer(ui)
        if node.get("text") != "Message":
            raise RuntimeError("Original composer was not empty before paste")
        # This fixture's original composer retains focus while rich buttons are tapped.
        # A redundant screen tap can hit Android's transient clipboard overlay instead.
        if node.get("focused") != "true":
            raise RuntimeError("Original composer lost focus before ordinary paste")
        adb("shell", "input", "keyevent", "279")
        pasted = composer(capture(phase + "-pasted"))
        if pasted.get("text") != "GramLab-copy-73Q9":
            raise RuntimeError("Original composer did not paste the exact copied payload")
        # Delete the verified ASCII draft through ordinary editing; never send a message.
        adb("shell", "input", "keyevent", "123")
        adb("shell", "input", "keyevent", *(["67"] * len("GramLab-copy-73Q9")))
        if composer(capture(phase + "-cleared")).get("text") != "Message":
            raise RuntimeError("Ordinary deletion did not clear the copied draft")
        adb("shell", "input", "keyevent", "111")
        experiment.setdefault("pastes", []).append(
            {"phase": phase, "text": pasted.get("text"), "cleared": True}
        )

    try:
        result = probe(
            guest,
            scene_checks={"initial": ["Choose:"], "edited": ["Choose:"]},
            on_configured=configured,
            on_initial=initial,
            run_scenario=run,
        )
        result["input"] = experiment
        return result
    finally:
        Path("effect-input-evidence.json").write_text(json.dumps(experiment))
        with World.open(Path("world")) as world:
            Path("effect-input-final-events.json").write_text(json.dumps(world.events()))
        guest("shell", "run-as", PACKAGE, "rm", "-f", DIRECTORY + "rich-action-geometry.json")


if __name__ == "__main__":
    main(effect_probe)
