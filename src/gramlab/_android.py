"""Trusted AOSP observation using the original Android client and semantic bridge."""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
import xml.etree.ElementTree as ET
from contextlib import ExitStack
from pathlib import Path
from typing import Any

from gramlab._captures import _rich_text
from gramlab.client_bridge import ClientBridge
from gramlab.reports import _png, _Redactor
from gramlab.runtime import RuntimeProfile, Sandbox
from gramlab.world import World

IMAGE_PACKAGE = "system-images;android-36;default;x86_64"


def _inline_fragments(message: dict[str, Any]) -> list[str]:
    """Readable content only; rich styling and hidden descendants cannot identify a cell."""
    if "rich_message" not in message:
        if message["text"]:
            return [message["text"]]
        return [message["caption"]] if "photo" in message and message.get("caption") else []
    fragments: list[str] = []

    def visit(blocks: list[dict[str, Any]]) -> None:
        for block in blocks:
            for field in ("text", "summary", "caption"):
                if field in block:
                    if field == "caption" and block["type"] == "photo":
                        caption = block[field]
                        fragments.extend(
                            _rich_text(caption[name])
                            for name in ("text", "credit")
                            if name in caption
                        )
                    else:
                        fragments.append(_rich_text(block[field]))
            if "cells" in block:
                for row in block["cells"]:
                    for cell in row:
                        if "text" in cell:
                            fragments.append(_rich_text(cell["text"]))
            if "blocks" in block and (block["type"] != "details" or block.get("is_open", False)):
                visit(block["blocks"])
            if "items" in block:
                for item in block["items"]:
                    visit(item["blocks"])
            if "credit" in block:
                fragments.append(_rich_text(block["credit"]))

    visit(message["rich_message"]["blocks"])
    return [fragment for fragment in fragments if fragment]


def _inline_matches(message: dict[str, Any], native_text: str) -> bool:
    if "rich_message" not in message:
        if message["text"]:
            return native_text.startswith(message["text"] + "\n")
        if "photo" not in message or not message.get("caption"):
            return False
        match = re.fullmatch(r"Photo\n(.*)\nReceived at [^\n]+\n", native_text, re.DOTALL)
        return match is not None and match[1] == message["caption"]
    # The pinned English host appends receipt metadata after a separate paragraph.
    # Do not let timestamps or status words supply otherwise absent message content.
    # Localized/changed host metadata must fail until its observation contract is verified.
    match = re.fullmatch(r"(.*\n)\nReceived at [^\n]+\n", native_text, re.DOTALL)
    fragments = _inline_fragments(message)
    if match is None or not any(fragment.strip() for fragment in fragments):
        return False
    body = match[1]
    offset = 0
    for fragment in fragments:
        found = body.find(fragment, offset)
        if found < 0:
            return False
        offset = found + len(fragment)
    return True


class Android:
    def __init__(
        self,
        profile: RuntimeProfile,
        *,
        deadline: float,
        secrets: list[str],
        bridge_version: int = 3,
    ) -> None:
        if type(bridge_version) is not int or bridge_version not in (3, 4):
            raise ValueError("Android bridge version must be 3 or 4")
        self._bridge_version = bridge_version
        self.profile = profile
        self.deadline = deadline
        self.secrets = secrets
        self.observations: dict[str, Any] = {}
        self._stack = ExitStack()
        self._guest: subprocess.Popen[str] | None = None
        self._bridge: ClientBridge | None = None
        self._persona: int | None = None
        self._capability = ""
        self._active_chat: int | None = None

    def _remaining(self, limit: float) -> float:
        remaining = min(limit, self.deadline - time.monotonic())
        if remaining <= 0:
            raise TimeoutError("Android run deadline expired")
        return remaining

    def _adb(
        self, *arguments: str, timeout: float = 15, input: str | None = None, check: bool = True
    ) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(  # noqa: S603 — trusted executable and dedicated namespace/serial
            [self.profile.executables["adb"], "-s", "emulator-5554", *arguments],
            input=input,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=self._remaining(timeout),
        )
        if check and result.returncode:
            self.observations["command_failure"] = _Redactor(self.secrets).clean(
                {
                    "arguments": arguments,
                    "returncode": result.returncode,
                    "stdout": result.stdout[:32768],
                    "stderr": result.stderr[:32768],
                }
            )
            raise RuntimeError(f"Dedicated Android command failed: {arguments[0]}")
        return result

    def _filesystem(self) -> dict[str, bool]:
        processes = []
        for entry in Path("/proc").iterdir():
            if not entry.name.isdecimal():
                continue
            try:
                executable = (entry / "exe").readlink()
            except FileNotFoundError:
                continue
            if executable.name in ("qemu-system-x86_64", "qemu-system-x86_64-headless"):
                processes.append(entry)
        if len(processes) != 1:
            raise RuntimeError("Expected exactly one dedicated QEMU process")
        process = processes[0]
        root = process / "root"
        result = {
            "world_visible": (root / "work/world").exists(),
            "bot_visible": (root / "work/bots").exists(),
            "scenario_visible": (root / "work/scenario").exists(),
            "private_avd_visible": (root / "work/avd/config.ini").is_file(),
            "same_pid_namespace": (process / "ns/pid").readlink()
            == Path("/proc/self/ns/pid").readlink(),
            "same_network": (process / "ns/net").readlink() == Path("/proc/self/ns/net").readlink(),
        }
        if result != {
            "world_visible": False,
            "bot_visible": False,
            "scenario_visible": False,
            "private_avd_visible": True,
            "same_pid_namespace": False,
            "same_network": True,
        }:
            raise RuntimeError("Dedicated emulator filesystem isolation failed")
        return result

    def start(self) -> None:
        if self._guest is not None:
            return
        started = time.monotonic()
        for variable in ("HOME", "ANDROID_USER_HOME", "ANDROID_AVD_HOME", "XDG_CACHE_HOME"):
            Path(os.environ[variable]).mkdir(parents=True, exist_ok=True)
        data = Path("emulator")
        data.mkdir()
        Path("captures").mkdir(mode=0o700)
        (data / "emulator.py").write_bytes((Path(__file__).parent / "_emulator.py").read_bytes())
        self._guest = self._stack.enter_context(
            Sandbox(self.profile).component(
                [
                    self.profile.python,
                    "/work/emulator.py",
                    self.profile.executables["emulator"],
                    self.profile.executables["avdmanager"],
                    IMAGE_PACKAGE,
                ],
                data=data,
                kvm=True,
                startup_timeout=self._remaining(10),
            )
        )
        boot_deadline = min(self.deadline, started + 120)
        while time.monotonic() < boot_deadline:
            if self._guest.poll() is not None:
                raise RuntimeError("Dedicated emulator exited during startup")
            boot = self._adb("shell", "getprop", "sys.boot_completed", check=False, timeout=5)
            if boot.returncode == 0 and boot.stdout.strip() == "1":
                break
            time.sleep(0.25)
        else:
            raise TimeoutError("Dedicated guest did not finish boot")
        self.observations["boot_ms"] = (time.monotonic() - started) * 1000
        for name, property_name in (
            ("api", "ro.build.version.sdk"),
            ("abi", "ro.product.cpu.abi"),
            ("fingerprint", "ro.build.fingerprint"),
        ):
            self.observations[name] = self._adb("shell", "getprop", property_name).stdout.strip()
        self.observations["filesystem"] = self._filesystem()
        network = {}
        for family, flag, address in (("ipv4", "-4", "192.0.2.1"), ("ipv6", "-6", "2001:db8::1")):
            attempted = self._adb(
                "shell", "toybox", "nc", flag, "-z", "-w", "2", address, "443", check=False
            )
            network[family] = attempted.returncode
            if attempted.returncode == 0:
                raise RuntimeError("Dedicated guest external traffic was unexpectedly accepted")
        self.observations["network"] = network
        self._adb("shell", "wm", "size", "320x640")
        self._adb("shell", "wm", "density", "160")
        self.observations["display"] = "320x640, 160 dpi; default fonts and app animation settings"
        graphics = self._adb("shell", "dumpsys", "SurfaceFlinger").stdout
        self.observations["graphics"] = next(
            (line for line in graphics.splitlines() if line.startswith("GLES:")), "unavailable"
        )
        self._adb("install", "--no-streaming", "/work/client.apk", timeout=60)
        self._adb("push", "/work/client.apk", "/data/local/tmp/composer-client.apk", timeout=30)
        self._adb("shell", "chmod", "0444", "/data/local/tmp/composer-client.apk")
        package = self._adb("shell", "dumpsys", "package", "org.gramlab.android").stdout
        self.observations["package_version"] = next(
            (line.strip() for line in package.splitlines() if "versionName=" in line), "unavailable"
        )
        self._bridge = self._stack.enter_context(ClientBridge(Path("world")))

    def capture(self, chat: dict[str, Any], label: str, contains: list[str]) -> dict[str, Any]:
        try:
            return self._capture(chat, label, contains)
        except Exception as error:
            self._record_failure("capture", error)
            raise

    def _record_failure(self, operation: str, error: Exception) -> None:
        self.observations[operation + "_failure"] = _Redactor(self.secrets).text(str(error))
        if self._guest is not None and self._guest.poll() is None:
            try:
                log = self._adb("logcat", "-d", "-t", "300", "-v", "brief", timeout=5, check=False)
                self.observations["failure_logcat"] = _Redactor(self.secrets).text(
                    log.stdout[-65536:]
                )
            except (OSError, subprocess.TimeoutExpired):
                self.observations["failure_logcat"] = "Unavailable before the run deadline"

    def _open_chat(self, chat: dict[str, Any]) -> str:
        if self._guest is None or self._guest.poll() is not None:
            raise RuntimeError("Dedicated emulator is not running")
        if self._bridge is None:
            raise RuntimeError("Dedicated client bridge did not start")
        self._adb("shell", "am", "force-stop", "org.gramlab.android")
        if self._persona != chat["user_id"]:
            cleared = self._adb("shell", "pm", "clear", "org.gramlab.android")
            if cleared.stdout.strip() != "Success":
                raise RuntimeError("Dedicated client persona could not be cleared")
            with World.open(Path("world")) as world:
                self._capability = world.issue_client_token(chat["user_id"])
            self.secrets.append(self._capability)
            self._persona = chat["user_id"]
        with World.open(Path("world")) as world:
            configuration = {
                "endpoint": self._bridge.base_url.replace("127.0.0.1", "10.0.2.2"),
                "capability": self._capability,
                "world_id": world.world_id,
                "user_id": self._persona,
                "bridge_version": self._bridge_version,
            }
        self._adb(
            "shell",
            "-T",
            "run-as",
            "org.gramlab.android",
            "sh",
            "-c",
            "'mkdir -p files/gramlab && cat > files/gramlab/config.json'",
            input=json.dumps(configuration),
        )
        launched = self._adb(
            "shell",
            "am",
            "start",
            "-W",
            "-n",
            "org.gramlab.android/org.telegram.ui.LaunchActivity",
            "-a",
            "com.tmessages.openchat",
            "--el",
            "userId",
            str(chat["bot_id"]),
            timeout=40,
        )
        if "Status: ok" not in launched.stdout:
            raise RuntimeError("Dedicated client activity failed to launch")
        self._active_chat = chat["id"]
        return launched.stdout

    def _wait_ui(self, contains: list[str]) -> str:
        ui_deadline = min(self.deadline, time.monotonic() + 45)
        ui = ""
        while time.monotonic() < ui_deadline:
            self._adb("shell", "uiautomator", "dump", "/data/local/tmp/gramlab-capture.xml")
            ui = self._adb("shell", "cat", "/data/local/tmp/gramlab-capture.xml").stdout
            # UIAutomator produces this XML inside the dedicated guest; no external entities.
            nodes = list(ET.fromstring(ui).iter("node"))  # noqa: S314
            if all(any(text in node.get("text", "") for node in nodes) for text in contains) and (
                contains
                or any(
                    node.get("package") == "org.gramlab.android"
                    and node.get("class") == "android.widget.EditText"
                    and node.get("enabled") == "true"
                    for node in nodes
                )
            ):
                break
            time.sleep(0.2)
        else:
            self.observations["unmatched_ui"] = _Redactor(self.secrets).text(ui)
            raise TimeoutError("Expected text did not render in the dedicated client")
        return ui

    def _capture(self, chat: dict[str, Any], label: str, contains: list[str]) -> dict[str, Any]:
        started = time.monotonic()
        launched = self._open_chat(chat)
        with World.open(Path("world")) as world:
            title = world.get_user(chat["bot_id"])["first_name"]
        ui = self._wait_ui(contains or [title])
        nodes = list(ET.fromstring(ui).iter("node"))  # noqa: S314 — dedicated UIAutomator XML
        redactor = _Redactor(self.secrets)
        if any(redactor.text(value) != value for node in nodes for value in node.attrib.values()):
            raise RuntimeError("Capture UI contains credential-shaped text")
        accounts = self._adb("shell", "dumpsys", "account").stdout
        if "Accounts: 0" not in accounts:
            raise RuntimeError("Dedicated guest must have no Android accounts")
        screenshot = subprocess.run(  # noqa: S603 — dedicated serial; original PNG, no conversion
            [self.profile.executables["adb"], "-s", "emulator-5554", "exec-out", "screencap", "-p"],
            capture_output=True,
            timeout=self._remaining(15),
            check=True,
        ).stdout
        _png(screenshot, redactor)
        with (Path("captures") / f"{label}.png").open("xb") as output:
            output.write(screenshot)
        (Path("captures") / f"{label}.xml").write_text(ui)
        return {
            "user_id": self._persona,
            "ui": ui,
            "launch": launched,
            "accounts": accounts,
            "elapsed_ms": (time.monotonic() - started) * 1000,
        }

    def tap_inline_button(
        self, chat: dict[str, Any], message: dict[str, Any], row: int, column: int
    ) -> dict[str, Any]:
        try:
            return self._tap_inline_button(chat, message, row, column)
        except Exception as error:
            self._record_failure("input", error)
            raise

    def type_message(
        self, chat: dict[str, Any], text: str, expected: dict[str, Any]
    ) -> dict[str, Any]:
        try:
            return self._send_composer_action(chat, text, expected)
        except Exception as error:
            self._record_failure("composer", error)
            raise

    def start_bot_chat(self, chat: dict[str, Any]) -> dict[str, Any]:
        try:
            return self._send_composer_action(chat, None, {"text": "/start"})
        except Exception as error:
            self._record_failure("start_bot_chat", error)
            raise

    def _send_composer_action(
        self, chat: dict[str, Any], text: str | None, expected: dict[str, Any]
    ) -> dict[str, Any]:
        started = time.monotonic()
        # Starting uses the original captured first-use screen. Reopening an empty dialog
        # can change the client's local first-use state before its Start button is pressed.
        launched = (
            None if text is None and self._active_chat == chat["id"] else self._open_chat(chat)
        )
        with World.open(Path("world")) as world:
            title = world.get_user(chat["bot_id"])["first_name"]
        ui = self._wait_ui([title, "Start Bot"] if text is None else [title])
        with World.open(Path("world")) as world:
            if world.get_chat(chat["id"]) != chat:
                raise RuntimeError("Composer chat changed before input")
            if text is None and world.history(chat["id"]):
                raise RuntimeError("Start Bot conversation changed before input")
            position = world.client_snapshot(chat["user_id"], version=self._bridge_version)[
                "message_position"
            ]
        entered = self._click_start(ui) if text is None else self._enter_text(text)
        return self._accepted_composer_send(
            chat, position, expected, started, launched, ui, entered
        )

    def _enter_text(self, text: str) -> dict[str, Any]:
        entered = json.loads(
            self._adb(
                "shell",
                "-T",
                "CLASSPATH=/data/local/tmp/composer-client.apk",
                "/system/bin/app_process",
                "/system/bin",
                "org.telegram.gramlab.GramLabInput",
                input=json.dumps(
                    {
                        "operation": "compose_and_send",
                        "package": "org.gramlab.android",
                        "expected_text": "",
                        "text": text,
                        "send_description": "Send",
                    }
                ),
                timeout=20,
            ).stdout
        )
        if entered != {
            "ok": True,
            "input": "accessibility",
            "text_verified": True,
            "send_actions": 1,
            "uid": 2000,
        }:
            raise RuntimeError("Unexpected native composer input result")
        return dict(entered)

    def _click_start(self, ui: str) -> dict[str, Any]:
        nodes = ET.fromstring(ui).iter("node")  # noqa: S314 — dedicated UIAutomator XML
        targets = [
            node
            for node in nodes
            if node.get("text") == "Start Bot"
            and node.get("package") == "org.gramlab.android"
            and node.get("enabled") == node.get("clickable") == "true"
        ]
        if len(targets) != 1:
            raise RuntimeError("Start Bot must have one enabled accessible target")
        bounds = re.fullmatch(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", targets[0].get("bounds", ""))
        if bounds is None:
            raise RuntimeError("Start Bot has no usable bounds")
        left, top, right, bottom = map(int, bounds.groups())
        if not (0 <= left < right <= 320 and 80 <= top < bottom <= 583):
            raise RuntimeError("Start Bot is not fully inside the chat viewport")
        x, y = (left + right) // 2, (top + bottom) // 2
        self._adb("shell", "input", "tap", str(x), str(y))
        return {"input": "touch", "send_actions": 1, "target": targets[0].attrib, "x": x, "y": y}

    def _accepted_composer_send(
        self,
        chat: dict[str, Any],
        position: int,
        expected: dict[str, Any],
        started: float,
        launched: str | None,
        ui: str,
        entered: dict[str, Any],
    ) -> dict[str, Any]:
        deadline = min(self.deadline, time.monotonic() + 15)
        while time.monotonic() < deadline:
            with World.open(Path("world")) as world:
                snapshot = world.client_snapshot(chat["user_id"], version=self._bridge_version)
            sends = [
                send
                for send in snapshot["sends"]
                if send["position"] > position and send["message"]["chat_id"] == chat["id"]
            ]
            if sends:
                messages = [send["message"] for send in sends]
                if (
                    len(messages) != 1
                    or messages[0]["sender_id"] != chat["user_id"]
                    or {
                        key: value
                        for key, value in messages[0].items()
                        if key not in {"id", "chat_id", "sender_id", "date"}
                    }
                    != expected
                ):
                    self.observations["unexpected_composer_sends"] = _Redactor(self.secrets).clean(
                        sends
                    )
                    raise RuntimeError("Native composer produced unexpected semantic messages")
                return {
                    "sends": sends,
                    "android": {
                        "input": entered,
                        "ui": ui,
                        "launch": launched,
                        "elapsed_ms": (time.monotonic() - started) * 1000,
                    },
                }
            time.sleep(0.05)
        raise RuntimeError("Native composer produced no accepted send before timeout")

    def _tap_inline_button(
        self, chat: dict[str, Any], message: dict[str, Any], row: int, column: int
    ) -> dict[str, Any]:
        started = time.monotonic()
        self._open_chat(chat)
        fragments = _inline_fragments(message)
        if not any(fragment.strip() for fragment in fragments):
            raise RuntimeError("Inline message has no observable text identity")
        ui = self._wait_ui(fragments)
        tree = ET.fromstring(ui)  # noqa: S314 — dedicated UIAutomator XML
        keyboard = message["reply_markup"]["inline_keyboard"]
        labels = [button["text"] for line in keyboard for button in line]
        candidates = []
        for node in tree.iter("node"):
            if node.get("package") != "org.gramlab.android" or not _inline_matches(
                message, node.get("text", "")
            ):
                continue
            buttons = [child for child in node if child.get("class") == "android.widget.Button"]
            if [button.get("text") for button in buttons] == labels:
                candidates.append((node.get("text", ""), buttons))
        if len(candidates) != 1:
            raise RuntimeError(
                "Inline message and complete keyboard must have one accessible match"
            )
        index = sum(len(line) for line in keyboard[:row]) + column
        native_text, buttons = candidates[0]
        target = buttons[index]
        bounds = re.fullmatch(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", target.get("bounds", ""))
        if bounds is None or target.get("clickable") != "true" or target.get("enabled") != "true":
            raise RuntimeError("Inline button is not an enabled accessible target")
        left, top, right, bottom = map(int, bounds.groups())
        if not (0 <= left < right <= 320 and 80 <= top < bottom <= 583):
            raise RuntimeError("Inline button is not fully inside the chat viewport")
        # Refuse known stale targets; edits after this check can still race native input.
        with World.open(Path("world")) as world:
            if world.get_message(chat["id"], message["id"]) != message:
                raise RuntimeError("Inline message changed before input")
            same_text = [
                item
                for item in world.history(chat["id"])
                if (
                    _inline_matches(item, native_text)
                    if "rich_message" in message or "rich_message" in item
                    else item["text"] == message["text"]
                )
            ]
            if len(same_text) != 1:
                raise RuntimeError("Inline message text is ambiguous in this chat")
            events = world.events()
            cursor = events[-1]["sequence"] if events else 0
        x, y = (left + right) // 2, (top + bottom) // 2
        self._adb("shell", "input", "tap", str(x), str(y))
        deadline = min(self.deadline, time.monotonic() + 15)
        while time.monotonic() < deadline:
            with World.open(Path("world")) as world:
                events = world.events(after=cursor)
                callbacks = [
                    event["data"]
                    for event in events
                    if event["type"] == "callback.created"
                    and event["data"]["user_id"] == chat["user_id"]
                    and event["data"]["chat_id"] == chat["id"]
                ]
                if callbacks:
                    expected = keyboard[row][column]["callback_data"]
                    if (
                        len(callbacks) != 1
                        or callbacks[0]["message"] != message
                        or callbacks[0]["data"] != expected
                    ):
                        raise RuntimeError("Native input produced an unexpected callback")
                    return {
                        "callback": world.get_callback(
                            user_id=chat["user_id"], callback_id=callbacks[0]["id"]
                        ),
                        "android": {
                            "ui": ui,
                            "target": target.attrib,
                            "x": x,
                            "y": y,
                            "elapsed_ms": (time.monotonic() - started) * 1000,
                        },
                    }
            time.sleep(0.05)
        raise RuntimeError("Native inline input produced no matching callback before timeout")

    def close(self) -> None:
        self._stack.close()
