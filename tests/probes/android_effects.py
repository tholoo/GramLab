"""Observe original settings and the native glass shader path in one dedicated guest."""

import json
import re
import subprocess
import threading
import time
import xml.etree.ElementTree as ET
from collections.abc import Callable
from contextlib import ExitStack
from pathlib import Path
from typing import Any

from android_guest import main
from jdwp import Debugger

from gramlab.client_bridge import ClientBridge
from gramlab.world import World

PACKAGE = "org.gramlab.android"
ACTIVITY = PACKAGE + "/org.telegram.ui.LaunchActivity"
PREFERENCE_KEYS = {"overrideDevicePerformanceClass", "lite_mode6", "lite_mode_battery_level"}


def probe(guest: Callable[..., subprocess.CompletedProcess[str]]) -> dict[str, object]:
    capability = ""
    frame = 0
    timings: dict[str, float] = {}
    phases: dict[str, Any] = {}

    def adb(*arguments: str, **kwargs: Any) -> str:
        result = guest(*arguments, **kwargs)
        if result.returncode:
            raise RuntimeError("Effects observation ADB command failed: " + arguments[0])
        return result.stdout

    def retain(name: str, value: str) -> str:
        if capability and capability in value:
            raise RuntimeError("Effects evidence contains a capability")
        Path(name).write_text(value)
        return value

    def screen(name: str) -> str:
        adb("shell", "uiautomator", "dump", "/data/local/tmp/gramlab-effects.xml", timeout=20)
        ui = adb("shell", "cat", "/data/local/tmp/gramlab-effects.xml")
        retain(name + ".xml", ui)
        adb("shell", "screencap", "-p", "/data/local/tmp/gramlab-effects.png")
        adb("pull", "/data/local/tmp/gramlab-effects.png", "/work/" + name + ".png")
        return ui

    def observe() -> ET.Element:
        nonlocal frame
        frame += 1
        return ET.fromstring(screen(f"navigation-{frame:02d}"))  # noqa: S314 — dedicated guest XML

    def bounds(node: ET.Element) -> tuple[int, int, int, int]:
        match = re.fullmatch(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", node.get("bounds", ""))
        if match is None:
            raise RuntimeError("Native setting has no rectangular bounds")
        left, top, right, bottom = map(int, match.groups())
        return left, top, right, bottom

    def find_text(text: str, tree: ET.Element) -> tuple[ET.Element, ET.Element]:
        for attempt in range(5):
            found = []
            for node in tree.iter("node"):
                if node.get("text") != text:
                    continue
                left, top, right, bottom = bounds(node)
                if 0 <= left < right <= 320 and 80 <= top < bottom <= 600:
                    found.append(node)
            if len(found) == 1:
                return found[0], tree
            if len(found) > 1:
                raise RuntimeError("Native setting text is ambiguous")
            if attempt != 4:
                adb("shell", "input", "swipe", "170", "540", "170", "280", "400")
                tree = observe()
        raise RuntimeError("Native setting is unavailable: " + text)

    def tap_text(text: str, tree: ET.Element) -> None:
        node, _ = find_text(text, tree)
        left, top, right, bottom = bounds(node)
        adb("shell", "input", "tap", str((left + right) // 2), str((top + bottom) // 2))

    def settings() -> ET.Element:
        adb(
            "shell",
            "am",
            "start",
            "-W",
            "-n",
            ACTIVITY,
            "-a",
            "org.telegram.messenger.OPEN_ACCOUNT",
            timeout=40,
        )
        tree = observe()
        if any(node.get("text") == "Turn on notifications" for node in tree.iter("node")):
            # The original optional notification sheet can appear after cold settings launch.
            # Dismiss the observed sheet; never grant notification permission or open settings.
            adb("shell", "input", "keyevent", "4")
            tree = observe()
            if any(node.get("text") == "Turn on notifications" for node in tree.iter("node")):
                raise RuntimeError("Original notification sheet did not dismiss")
        power_saving, tree = find_text("Power Saving", tree)
        left, top, right, bottom = bounds(power_saving)
        adb("shell", "input", "tap", str((left + right) // 2), str((top + bottom) // 2))
        tree = observe()
        tap_text("Animations in Chats", tree)
        return observe()

    def set_flag(label: str, enabled: bool, tree: ET.Element) -> tuple[dict[str, str], ET.Element]:
        # Locate the currently visible row before deciding whether one input is necessary.
        target, tree = find_text(label, tree)
        nodes = [
            node
            for node in tree.iter("node")
            if node.get("content-desc") == label and node.get("class") == "android.widget.CheckBox"
        ]
        if len(nodes) != 1:
            raise RuntimeError("Native effects checkbox is ambiguous or unavailable")
        desired = str(enabled).lower()
        if nodes[0].get("checked") != desired:
            left, top, right, bottom = bounds(target)
            adb("shell", "input", "tap", str((left + right) // 2), str((top + bottom) // 2))
            tree = observe()
        checked = [
            node
            for node in tree.iter("node")
            if node.get("content-desc") == label and node.get("class") == "android.widget.CheckBox"
        ]
        if len(checked) != 1 or checked[0].get("checked") != desired:
            raise RuntimeError("Native effects setting did not reach requested state")
        return dict(checked[0].attrib), tree

    def preferences() -> dict[str, Any]:
        result = guest("shell", "run-as", PACKAGE, "cat", "shared_prefs/mainconfig.xml")
        if result.returncode:
            raise RuntimeError("Native preferences are unavailable")
        tree = ET.fromstring(result.stdout)  # noqa: S314 — dedicated package preferences
        return {
            node.attrib["name"]: {"type": node.tag, "value": node.get("value")}
            for node in tree
            if node.get("name") in PREFERENCE_KEYS
        }

    def capture_chat(name: str) -> dict[str, Any]:
        started = time.monotonic()
        adb("shell", "am", "force-stop", PACKAGE)
        launched = adb(
            "shell",
            "am",
            "start",
            "-W",
            "-n",
            ACTIVITY,
            "-a",
            "com.tmessages.openchat",
            "--el",
            "userId",
            "2",
            timeout=40,
        )
        retain(name + "-launch.log", launched)
        if "Status: ok" not in launched or "LaunchState: COLD" not in launched:
            raise RuntimeError("Effects chat did not cold-launch successfully")
        deadline = time.monotonic() + 30
        while True:
            ui = screen(name)
            tree = ET.fromstring(ui)  # noqa: S314 — dedicated guest XML
            visible = [node.get("text", "") for node in tree.iter("node")]
            if all(
                any(text in node for node in visible)
                for text in ("Native effects", "GramLab", "Same world and original renderer")
            ):
                break
            if time.monotonic() >= deadline:
                raise RuntimeError("Effects fixture is not visible")
        with World.open(Path("world")) as world:
            history = world.history(1)
        observed = {
            "ui": ui,
            "launch": launched,
            "preferences": preferences(),
            "history": history,
            "battery": adb("shell", "dumpsys", "battery"),
            "accounts": adb("shell", "dumpsys", "account"),
            "graphics": adb("shell", "dumpsys", "gfxinfo", PACKAGE),
        }
        timings[name] = (time.monotonic() - started) * 1000
        phases[name] = observed
        retain(name + "-observed.json", json.dumps(observed))
        return observed

    def shader_observation() -> dict[str, Any]:
        # The original draw path calls this method after constructing RuntimeShader/RenderEffect.
        # A one-shot debugger observation adds no class loading, field writes or injected methods.
        pid = adb("shell", "pidof", PACKAGE).strip()
        if re.fullmatch(r"[1-9][0-9]*", pid) is None:
            raise RuntimeError("Expected one dedicated effects process")
        tree = observe()
        targets = [
            n
            for n in tree.iter("node")
            if n.get("class") == "android.widget.EditText" and n.get("enabled") == "true"
        ]
        if len(targets) != 1 or targets[0].get("focused") != "true":
            raise RuntimeError("Expected one original composer to observe layout invalidation")
        with ExitStack() as cleanup:
            port = int(adb("forward", "tcp:0", "jdwp:" + pid).strip())
            cleanup.callback(adb, "forward", "--remove", f"tcp:{port}")
            debugger = Debugger(port)
            cleanup.callback(debugger.close)
            cleanup.callback(adb, "shell", "am", "force-stop", PACKAGE)
            debugger.breakpoint(
                "Lorg/telegram/ui/Components/blur3/LiquidGlassEffect;", "update", "(FFFFFFFFFFFI)V"
            )
            failures: list[BaseException] = []

            def resize_composer() -> None:
                try:
                    # The empty composer is already focused. Tapping it need not invalidate
                    # a cached RenderNode. An unsent wrapping draft changes actual geometry.
                    adb(
                        "shell",
                        "input",
                        "text",
                        "Original%sglass%sobservation%swith%sa%swrapping%sunsent%sdraft",
                        timeout=20,
                    )
                except BaseException as error:
                    failures.append(error)

            worker = threading.Thread(target=resize_composer)
            worker.start()
            resumed = False
            try:
                observed = debugger.wait_breakpoint(arguments=["foregroundColor"], timeout=15)
                retain("shader-breakpoint.json", json.dumps(observed))
                debugger.resume()
                resumed = True
            finally:
                # Kill before a failed held-breakpoint detach; unblock any pending shell input.
                if not resumed:
                    adb("shell", "am", "force-stop", PACKAGE)
                worker.join(timeout=25)
            if worker.is_alive() or failures:
                raise RuntimeError("Original composer draft input did not complete")
            observed["trigger_ui"] = screen("shader-trigger")
            with World.open(Path("world")) as world:
                observed["history_after_trigger"] = world.history(1)
            adb(
                "shell",
                "input",
                "keyevent",
                *(["67"] * len("Original glass observation with a wrapping unsent draft")),
                timeout=20,
            )
            cleared = ET.fromstring(screen("shader-cleared"))  # noqa: S314 — dedicated guest XML
            drafts = [
                n.get("text")
                for n in cleared.iter("node")
                if n.get("class") == "android.widget.EditText"
            ]
            if drafts != ["Message"]:
                raise RuntimeError("Shader observation draft was not cleared")
            retain("shader-observed.json", json.dumps(observed))
            return observed

    with World.create(Path("world"), seed=7, now=1700000000) as world:
        world.create_user(first_name="Sara", language_code="fa")
        world.create_user(first_name="Echo", username="gramlab_echo_bot", is_bot=True)
        world.open_private_chat(user_id=1, bot_id=2)
        world.send_message(chat_id=1, sender_id=1, text="Observe original effects")
        world.send_rich_message(
            chat_id=1,
            sender_id=2,
            rich_message={
                "skip_entity_detection": True,
                "blocks": [
                    {"type": "heading", "size": 2, "text": "Native effects"},
                    {
                        "type": "paragraph",
                        "text": ["سلام دنیا — ", {"type": "bold", "text": "GramLab"}],
                    },
                    {
                        "type": "blockquote",
                        "blocks": [
                            {"type": "paragraph", "text": "Same world and original renderer"}
                        ],
                    },
                ],
            },
        )
        capability = world.issue_client_token(1)
        world_id = world.world_id
    adb("install", "--no-streaming", "/work/client.apk", timeout=60)
    with ClientBridge(Path("world")) as bridge:
        adb(
            "shell",
            "-T",
            "run-as",
            PACKAGE,
            "sh",
            "-c",
            "'mkdir -p files/gramlab && cat > files/gramlab/config.json'",
            input=json.dumps(
                {
                    "endpoint": bridge.base_url.replace("127.0.0.1", "10.0.2.2"),
                    "capability": capability,
                    "world_id": world_id,
                    "user_id": 1,
                }
            ),
        )
        try:
            capture_chat("baseline")
            selected = {}
            shader = None
            for name, blur, glass in (
                ("blur", True, False),
                ("glass", True, True),
                ("restored", False, False),
            ):
                tree = settings()
                selected_blur, tree = set_flag("Blur", blur, tree)
                selected_glass, tree = set_flag("Liquid Glass", glass, tree)
                selected[name] = {
                    "blur": selected_blur,
                    "glass": selected_glass,
                }
                capture_chat(name)
                if name == "glass":
                    shader = shader_observation()
            if shader is None:
                raise RuntimeError("Native shader observation is missing")
            return {"phases": phases, "selected": selected, "shader": shader, "timings": timings}
        finally:
            retain("effects-logcat.txt", adb("logcat", "-d", "-v", "brief", timeout=15))
            adb("shell", "am", "force-stop", PACKAGE)


if __name__ == "__main__":
    main(probe)
