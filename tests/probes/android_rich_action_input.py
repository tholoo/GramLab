"""Explicit test-only guest input using the GPL experiment's observed post-draw rectangles.

This consumer never derives native layout or dispatches a callback. Each selected rectangle
receives exactly one ordinary guest tap; missing or stale observations fail without fallback.
"""

import json
import math
import subprocess
import time
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

from android_guest import main
from android_rich_messages import probe
from rich_action_input_round_trip import before_action, run, wait_answer

from gramlab.world import World

AGE_LIMIT_MS = 5000
PACKAGE = "org.gramlab.android"
DIRECTORY = "files/gramlab/"


def action_probe(guest: Callable[..., subprocess.CompletedProcess[str]]) -> dict[str, object]:
    experiment: dict[str, Any] = {"taps": [], "age_limit_ms": AGE_LIMIT_MS}
    activation: dict[str, Any] = {}
    expected = json.loads(Path("action-expected.json").read_text())["world_initial"]
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
        nonlocal original_state
        original_state = world_state()
        snapshot = original_state[0]
        if (
            snapshot["world_id"] != configuration["world_id"]
            or snapshot["user_id"] != 1
            or len(snapshot["messages"]) != 2
            or snapshot["messages"][1] != expected
        ):
            raise RuntimeError("Experimental activation does not match the real initial world")
        activate(configuration, expected["id"] + 1000000)

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

    def capture(name: str) -> None:
        # Same original screencap/UIAutomator path as the shared rich-message probe.
        adb("shell", "uiautomator", "dump", "/data/local/tmp/rich-action.xml", timeout=15)
        ui = adb("shell", "cat", "/data/local/tmp/rich-action.xml")
        Path(name + ".xml").write_text(ui)
        if "Inline action" not in ui:
            raise RuntimeError("Initial original scene disappeared before input")
        adb("shell", "screencap", "-p", "/data/local/tmp/rich-action.png")
        adb("pull", "/data/local/tmp/rich-action.png", "/work/" + name + ".png")

    def target_for(sample: dict[str, Any], index: int) -> dict[str, Any]:
        targets = sample.get("targets")
        if not isinstance(targets, list) or len(targets) != 2:
            raise RuntimeError("Expected exactly the original row and inline rectangles")
        for position, (kind, label, data) in enumerate(
            (("row", "Row action", "row:1"), ("inline", "Inline action", "inline:1"))
        ):
            target = targets[position]
            if {
                key: target.get(key) for key in ("kind", "block", "index", "text", "callback_data")
            } != {
                "kind": kind,
                "block": position,
                "index": 0,
                "text": label,
                "callback_data": data,
            }:
                raise RuntimeError(
                    "Original action bytes or placement differ from the real fixture"
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

    def initial(_: str) -> None:
        wrong = sample_after(0, unavailable=True)
        wrong_now, wrong_pid = fresh(wrong, 0)
        experiment["wrong_checked_uptime_ms"] = wrong_now
        experiment["wrong_checked_pid"] = wrong_pid
        experiment["wrong_identity"] = wrong
        experiment["wrong_identity_unchanged"] = original_state == world_state()
        if not experiment["wrong_identity_unchanged"]:
            raise RuntimeError("Wrong identity observation changed authoritative state")
        adb("shell", "am", "force-stop", PACKAGE)
        activate(activation, expected["id"])
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
        Path("correct-launch.log").write_text(launch)
        experiment["correct_launch"] = launch
        if "Status: ok" not in launch or "LaunchState: COLD" not in launch:
            raise RuntimeError("Correct activation did not cold launch successfully")
        sample_after(0)  # Wait for actual stable drawing before asking UIAutomator to capture.
        minimum = 0
        process = None
        for index, phase in enumerate(("before-row", "before-inline")):
            capture(phase)
            # Read and check freshness only after the potentially slow PNG/XML capture.
            sample = sample_after(minimum)
            target = target_for(sample, index)
            if sample["pid"] == wrong["pid"] or (process is not None and sample["pid"] != process):
                raise RuntimeError("Unexpected experimental process lifecycle before tap")
            state = before_action(index)
            if state["world_id"] != activation["world_id"] or state["message"] != expected:
                raise RuntimeError("World content changed since native observation")
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
                "world_before": state,
            }
            experiment["taps"].append(tap)
            Path(phase + "-geometry.json").write_text(json.dumps(tap))
            adb("shell", "input", "tap", str(x), str(y), timeout=20)
            tap["answer"] = wait_answer(index)
            minimum = sample["generation"]

    try:
        result = probe(
            guest,
            scene_checks={"initial": ["Inline action"], "edited": ["Rich actions complete"]},
            on_configured=configured,
            on_initial=initial,
            run_scenario=run,
        )
        result["input"] = experiment
        return result
    finally:
        Path("action-input-evidence.json").write_text(json.dumps(experiment))
        with World.open(Path("world")) as world:
            Path("action-input-final-events.json").write_text(json.dumps(world.events()))
        guest("shell", "run-as", PACKAGE, "rm", "-f", DIRECTORY + "rich-action-geometry.json")


if __name__ == "__main__":
    main(action_probe)
