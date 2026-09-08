"""Observe original custom-emoji rendering, animation, cache reuse and live edit."""

import json
import re
import shlex
import subprocess
import time
import xml.etree.ElementTree as ET
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

from android_guest import main
from custom_emoji_round_trip import run
from guest_screenshot_burst import capture_burst
from native_asset_proxy import NativeAssetProxy

PACKAGE = "org.gramlab.android"
CONFIG = "files/gramlab/config.json"
TRACE = "files/gramlab/trace.jsonl"
BOUNDS = re.compile(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]")


def probe(guest: Callable[..., subprocess.CompletedProcess[str]]) -> dict[str, object]:
    capability = ""
    proxy: NativeAssetProxy | None = None
    captures: dict[str, str] = {}
    launches: dict[str, str] = {}
    taps: dict[str, Any] = {}
    cache: dict[str, Any] = {}
    carrier_bounds: dict[str, dict[str, list[int]]] = {}
    burst_timestamps_ns: list[int] = []
    burst_end_timestamps_ns: list[int] = []
    animation_profile: dict[str, Any] = {}
    navigation_frame = 0
    phase = "initial"

    def retain(name: str, value: str) -> str:
        if capability and capability in value:
            raise RuntimeError("Custom emoji diagnostics contained a capability")
        Path(name).write_text(value)
        return value

    def adb(*arguments: str, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        result = guest(*arguments, **kwargs)
        if result.returncode:
            retain("guest-command-error.txt", result.stdout + result.stderr)
            raise RuntimeError(f"Dedicated custom emoji guest command failed: {arguments[0]}")
        return result

    def trace(name: str) -> list[dict[str, Any]]:
        raw = adb("shell", "run-as", PACKAGE, "cat", TRACE).stdout
        retain(name + "-trace.jsonl", raw)
        return [json.loads(line) for line in raw.splitlines()]

    def screenshot(name: str) -> None:
        adb("shell", "screencap", "-p", "/data/local/tmp/custom-emoji.png")
        adb("pull", "/data/local/tmp/custom-emoji.png", f"/work/{name}.png")

    def screen(name: str, *, readiness_phase: str | None = None) -> str:
        expected_phase = readiness_phase or name
        deadline = time.monotonic() + 35
        ui = ""
        while time.monotonic() < deadline:
            adb("shell", "uiautomator", "dump", "/data/local/tmp/custom-emoji.xml", timeout=15)
            ui = adb("shell", "cat", "/data/local/tmp/custom-emoji.xml").stdout
            rows = trace(name)
            readiness_labels = ("سلام", "Ordinary", "Rich") + (
                ("Animate / متحرک",) if expected_phase == "initial" else ()
            )
            if all(label in ui for label in readiness_labels) and (
                expected_phase == "initial"
                or any(row.get("event") == "events_applied" for row in rows)
            ):
                break
            time.sleep(0.2)
        else:
            screenshot(name + "-failure")
            retain(name + "-failure.xml", ui)
            retain(name + "-failure-logcat.txt", adb("logcat", "-d", "-t", "2000").stdout)
            raise RuntimeError(f"Original custom emoji scene did not render during {name}")
        captures[name] = retain(name + ".xml", ui)
        carrier_labels = {"incoming": "سلام", "ordinary": "Ordinary", "rich": "Rich"}
        selected: dict[str, list[int]] = {}
        nodes = list(ET.fromstring(ui).iter("node"))  # noqa: S314
        for carrier, label in carrier_labels.items():
            candidates = []
            for node in nodes:
                if label not in node.get("text", ""):
                    continue
                match = BOUNDS.fullmatch(node.get("bounds", ""))
                if match:
                    values = [int(value) for value in match.groups()]
                    candidates.append(((values[2] - values[0]) * (values[3] - values[1]), values))
            if candidates:
                selected[carrier] = min(candidates)[1]
        if set(selected) != {"incoming", "ordinary", "rich"}:
            raise RuntimeError("Custom emoji carriers lack semantic message regions")
        rich = selected["rich"]
        # The source-authored rich paragraph precedes its button row. Keep a gap between
        # their visual regions so antialiased pixels cannot join the two glyph clusters.
        middle = rich[1] + (rich[3] - rich[1]) * 2 // 5
        selected["rich"] = [rich[0], rich[1], rich[2], middle]
        selected["button"] = [rich[0], middle, rich[2], rich[3]]
        if len({tuple(value) for value in selected.values()}) != 4:
            raise RuntimeError("Custom emoji carriers do not have four distinct regions")
        carrier_bounds[name] = selected
        screenshot(name)
        retain(name + "-logcat.txt", adb("logcat", "-d", "-t", "2000").stdout)
        return ui

    def write_config(configuration: dict[str, Any]) -> None:
        nonlocal capability
        capability = configuration["capability"]
        native = {key: value for key, value in configuration.items() if key != "stage"} | {
            "endpoint": proxy.base_url.replace("127.0.0.1", "10.0.2.2")  # type: ignore[union-attr]
        }
        if native.get("bridge_version") != 4 or native.get("user_id") != 1:
            raise RuntimeError("Custom emoji lifecycle requires v4 persona 1")
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
        launches[name] = retain(name + "-launch.log", result.stdout + result.stderr)

    def settings_tree(name: str) -> ET.Element:
        adb("shell", "uiautomator", "dump", "/data/local/tmp/custom-emoji-settings.xml", timeout=15)
        xml = adb("shell", "cat", "/data/local/tmp/custom-emoji-settings.xml").stdout
        retain(name + ".xml", xml)
        screenshot(name)
        retain(name + "-preferences.json", json.dumps(preferences(), indent=2))
        return ET.fromstring(xml)  # noqa: S314

    def find_setting(text: str, tree: ET.Element) -> tuple[ET.Element, ET.Element]:
        nonlocal navigation_frame
        for _ in range(6):
            found = [node for node in tree.iter("node") if node.get("text") == text]
            if len(found) == 1:
                return found[0], tree
            if len(found) > 1:
                raise RuntimeError("Original animation setting is ambiguous: " + text)
            adb("shell", "input", "swipe", "170", "540", "170", "280", "400")
            navigation_frame += 1
            tree = settings_tree(f"settings-{navigation_frame:02d}")
        raise RuntimeError("Original animation setting is unavailable: " + text)

    def tap_node(node: ET.Element) -> None:
        match = BOUNDS.fullmatch(node.get("bounds", ""))
        if match is None:
            raise RuntimeError("Original animation setting has no bounds")
        left, top, right, bottom = map(int, match.groups())
        adb("shell", "input", "tap", str((left + right) // 2), str((top + bottom) // 2))

    def preferences() -> dict[str, Any]:
        value = adb("shell", "run-as", PACKAGE, "cat", "shared_prefs/mainconfig.xml").stdout
        tree = ET.fromstring(value)  # noqa: S314
        keys = {"overrideDevicePerformanceClass", "lite_mode6", "lite_mode_battery_level"}
        return {
            node.attrib["name"]: {"type": node.tag, "value": node.get("value")}
            for node in tree
            if node.get("name") in keys
        }

    def animation_checkbox(tree: ET.Element, label: str) -> ET.Element:
        controls = [
            node
            for node in tree.iter("node")
            if node.get("content-desc") == label and node.get("class") == "android.widget.CheckBox"
        ]
        if len(controls) != 1:
            raise RuntimeError("Original animation checkbox is ambiguous: " + label)
        if controls[0].get("checked") not in {"false", "true"}:
            raise RuntimeError("Original animation checkbox has no checked state: " + label)
        return controls[0]

    def tap_checkbox_side(node: ET.Element) -> None:
        match = BOUNDS.fullmatch(node.get("bounds", ""))
        if match is None:
            raise RuntimeError("Original animation checkbox has no bounds")
        left, top, right, bottom = map(int, match.groups())
        if not (0 <= left < right <= 320 and 0 <= top < bottom <= 640):
            raise RuntimeError("Original animation checkbox is outside the guest display")
        adb(
            "shell",
            "input",
            "tap",
            str(left + (right - left) // 4),
            str((top + bottom) // 2),
        )

    def enable_animation_checkbox(label: str, tree: ET.Element) -> ET.Element:
        nonlocal navigation_frame
        for _attempt in range(3):
            control = animation_checkbox(tree, label)
            if control.get("checked") == "true":
                return tree
            tap_checkbox_side(control)
            for poll in range(3):
                if poll:
                    time.sleep(0.25)
                navigation_frame += 1
                tree = settings_tree(f"settings-{navigation_frame:02d}")
                if animation_checkbox(tree, label).get("checked") == "true":
                    return tree
        raise RuntimeError(
            "No enabled state was observed for original animation checkbox: " + label
        )

    def enable_animations() -> None:
        nonlocal navigation_frame
        animation_profile["before"] = preferences()
        try:
            animation_profile["battery"] = adb("shell", "dumpsys", "battery").stdout
            adb(
                "shell",
                "am",
                "start",
                "-W",
                "-n",
                f"{PACKAGE}/org.telegram.ui.LaunchActivity",
                "-a",
                "org.telegram.messenger.OPEN_ACCOUNT",
                timeout=40,
            )
            navigation_frame += 1
            tree = settings_tree(f"settings-{navigation_frame:02d}")
            if any(node.get("text") == "Turn on notifications" for node in tree.iter("node")):
                adb("shell", "input", "keyevent", "4")
                navigation_frame += 1
                tree = settings_tree(f"settings-{navigation_frame:02d}")
            power, tree = find_setting("Power Saving", tree)
            tap_node(power)
            navigation_frame += 1
            tree = settings_tree(f"settings-{navigation_frame:02d}")
            emoji, tree = find_setting("Animated Emoji", tree)
            tap_node(
                emoji
            )  # Text-side tap expands the original category without toggling all flags.
            navigation_frame += 1
            tree = settings_tree(f"settings-{navigation_frame:02d}")
            checked: dict[str, str] = {}
            for label in ("Autoplay in keyboard", "Autoplay in chat"):
                _, tree = find_setting(label, tree)
                tree = enable_animation_checkbox(label, tree)
                checked[label] = animation_checkbox(tree, label).get("checked", "")
            animation_profile["checked"] = checked
        finally:
            animation_profile["after"] = preferences()
            retain("animation-profile.json", json.dumps(animation_profile, indent=2))
        adb("shell", "am", "force-stop", PACKAGE)
        launch("animation-enabled")

    def cache_files(name: str) -> None:
        external = f"/storage/emulated/0/Android/data/{PACKAGE}"
        paths = [
            (path, True)
            for path in adb(
                "shell", "run-as", PACKAGE, "find", ".", "-type", "f"
            ).stdout.splitlines()
        ]
        paths += [
            (path, False)
            for path in adb("shell", "find", external, "-type", "f").stdout.splitlines()
        ]
        selected: dict[str, Any] = {}
        for filename in ("2_2.jpg", "-1_1109.webm"):
            matches = [(path, internal) for path, internal in paths if Path(path).name == filename]
            copies = []
            for path, internal in matches:
                quoted = shlex.quote(path)
                command = ("shell", "run-as", PACKAGE) if internal else ("shell",)
                digest = adb(*command, "toybox", "sha256sum", quoted).stdout.split()[0]
                size = int(adb(*command, "toybox", "wc", "-c", quoted).stdout.split()[0])
                copies.append({"path": path, "sha256": digest, "size": size})
            selected[filename] = copies
        partials = [path for path, _ in paths if ".gramlab-" in path and path.endswith(".part")]
        cache[name] = {"files": selected, "partials": partials}
        retain(name + "-cache.json", json.dumps(cache[name], indent=2))

    def settle(name: str) -> None:
        expected = {"2_2.jpg"} if name == "initial" else {"2_2.jpg", "-1_1109.webm"}
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            cache_files(name)
            record = cache[name]
            if not record["partials"] and all(record["files"][item] for item in expected):
                return
            time.sleep(0.2)
        raise RuntimeError(f"Original custom emoji cache did not settle during {name}")

    def capture(name: str, configuration: dict[str, Any]) -> str:
        nonlocal proxy, phase
        stage = configuration.get("stage", name)
        if stage != name or name not in ("initial", "edited", "restarted"):
            raise RuntimeError("Unexpected custom emoji lifecycle phase")
        phase = name
        if proxy is None:
            adb("install", "--no-streaming", "/work/client.apk", timeout=60)
            proxy = NativeAssetProxy(configuration["endpoint"], configuration["capability"])
            proxy.__enter__()
        else:
            proxy.retarget(configuration["endpoint"])
        proxy.phase(name)
        write_config(configuration)
        if name == "initial":
            launch(name)
        elif name == "restarted":
            adb("shell", "am", "force-stop", PACKAGE)
            launch(name)
        ui = screen(name)
        settle(name)
        ui = screen(name)
        if name == "edited":
            starts, ends = capture_burst(guest, Path("/work"))
            burst_timestamps_ns.extend(starts)
            burst_end_timestamps_ns.extend(ends)
        return ui

    def tap(name: str, label: str) -> None:
        nonlocal phase
        assert proxy is not None
        enable_animations()
        ui = screen("pre-tap", readiness_phase=name)
        captures.pop("pre-tap")
        carrier_bounds.pop("pre-tap")
        candidates = []
        for node in ET.fromstring(ui).iter("node"):  # noqa: S314
            if label not in node.get("text", "") + node.get("content-desc", ""):
                continue
            match = BOUNDS.fullmatch(node.get("bounds", ""))
            if match:
                left, top, right, bottom = map(int, match.groups())
                if 0 <= left < right <= 320 and 0 <= top < bottom <= 640:
                    candidates.append(((right - left) * (bottom - top), left, top, right, bottom))
        if not candidates:
            raise RuntimeError("Original custom emoji callback has no semantic bounds")
        _, left, top, right, bottom = min(candidates)
        taps[name] = {"label": label, "bounds": [left, top, right, bottom]}
        phase = "edited"
        proxy.phase("edited")
        adb("shell", "input", "tap", str((left + right) // 2), str((top + bottom) // 2))

    def observe() -> dict[str, Any]:
        assert proxy is not None
        rows = trace("final")
        return {
            "observed": {
                "captures": captures,
                "launches": launches,
                "taps": taps,
                "cache": cache,
                "carrier_bounds": carrier_bounds,
                "burst_timestamps_ns": burst_timestamps_ns,
                "burst_end_timestamps_ns": burst_end_timestamps_ns,
                "animation_profile": animation_profile,
                "native_requests": proxy.requests(),
                "document_requests": proxy.document_requests(),
                "trace": rows,
                "phase": phase,
                "accounts": adb("shell", "dumpsys", "account").stdout,
            }
        }

    try:
        return cast(dict[str, object], run(capture, tap, observe))
    finally:
        guest("shell", "am", "force-stop", PACKAGE)
        if proxy is not None:
            retain("native-asset-requests.json", json.dumps(proxy.requests(), indent=2))
            retain("native-document-requests.json", json.dumps(proxy.document_requests(), indent=2))
            proxy.__exit__(None, None, None)
        guest("shell", "rm", "-f", "/data/local/tmp/custom-emoji.xml")


if __name__ == "__main__":
    main(probe)
