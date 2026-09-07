"""Original list checkbox state and actual bot send/edit/restart in a dedicated guest."""

import json
import re
import subprocess
import xml.etree.ElementTree as ET
from collections.abc import Callable
from pathlib import Path
from typing import Any

from android_guest import main
from android_rich_messages import probe

from gramlab.world import World


def list_probe(guest: Callable[..., subprocess.CompletedProcess[str]]) -> dict[str, object]:
    checkbox: dict[str, Any] = {}

    def adb(*args: str, **kwargs: Any) -> str:
        result = guest(*args, **kwargs)
        if result.returncode:
            raise RuntimeError(f"Dedicated list input command failed: {args[0]}")
        return result.stdout

    def boxes(ui: str) -> list[dict[str, str]]:
        tree = ET.fromstring(ui)  # noqa: S314 — dedicated guest UIAutomator XML
        return [
            dict(n.attrib) for n in tree.iter("node") if n.get("class") == "android.widget.CheckBox"
        ]

    def initial(ui: str) -> None:
        before = boxes(ui)
        checkbox["before"] = before
        Path("checkbox-before.json").write_text(json.dumps(before))
        if len(before) != 2 or [n["checked"] for n in before] != ["false", "true"]:
            raise RuntimeError(
                "Expected exactly two visible bot checkbox states; empty item adds none"
            )
        if any(n["clickable"] != "false" or n["checkable"] != "true" for n in before):
            raise RuntimeError(
                "Incoming bot list checkbox unexpectedly allows accessibility mutation"
            )
        with World.open(Path("world")) as world:
            state = world.client_snapshot(1, version=2), world.events()

        target = before[0]
        bounds = re.fullmatch(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", target["bounds"])
        if bounds is None:
            raise RuntimeError("Checkbox has no bounded original row")
        left, top, right, bottom = map(int, bounds.groups())
        # Original RichBlock exposes the text row's bounds. Its LTR checkbox is drawn
        # 26dp before that row, with a 20dp square. This fixture pins 160dpi / LTR.
        x, y = left - 16, top + 10
        if not (0 <= x < right <= 320 and 0 <= top < y < bottom <= 640):
            raise RuntimeError("Original checkbox target is outside the pinned viewport")
        checkbox["target"] = {"node": target, "x": x, "y": y}
        adb("shell", "input", "tap", str(x), str(y), timeout=20)

        def capture(name: str) -> str:
            adb("shell", "uiautomator", "dump", "/data/local/tmp/list-checkbox.xml", timeout=15)
            captured = adb("shell", "cat", "/data/local/tmp/list-checkbox.xml")
            Path(name + ".xml").write_text(captured)
            adb("shell", "screencap", "-p", "/data/local/tmp/list-checkbox.png")
            adb("pull", "/data/local/tmp/list-checkbox.png", "/work/" + name + ".png")
            return captured

        after_ui = capture("checkbox-action")
        checkbox["action_ui"] = after_ui
        checkbox["menu_dismissed"] = False
        if not boxes(after_ui):
            tree = ET.fromstring(after_ui)  # noqa: S314 — dedicated guest UIAutomator XML
            labels = {node.get("text") for node in tree.iter("node")}
            if not {"Reply", "Copy", "Forward", "Delete"} <= labels:
                raise RuntimeError("Unexpected original UI after bot checkbox input")
            adb("shell", "input", "keyevent", "4")
            checkbox["menu_dismissed"] = True
        after_ui = capture("after-checkbox")
        checkbox["after"] = boxes(after_ui)
        with World.open(Path("world")) as world:
            checkbox["world_unchanged"] = state == (
                world.client_snapshot(1, version=2),
                world.events(),
            )
        Path("checkbox-observed.json").write_text(json.dumps(checkbox))

    observed = probe(
        guest,
        scene_checks={
            "initial": ["Unchecked task", "Checked task", "Nested فارسی"],
            "edited": ["انجام شد", "باز مانده", "Nested edited"],
        },
        on_initial=initial,
    )
    observed["checkbox"] = checkbox
    return observed


if __name__ == "__main__":
    main(list_probe)
