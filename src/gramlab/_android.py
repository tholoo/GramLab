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

from gramlab.client_bridge import ClientBridge
from gramlab.reports import _png, _Redactor
from gramlab.runtime import RuntimeProfile, Sandbox
from gramlab.world import World

IMAGE_PACKAGE = "system-images;android-36;default;x86_64"


class Android:
    def __init__(self, profile: RuntimeProfile, *, deadline: float, secrets: list[str]) -> None:
        self.profile = profile
        self.deadline = deadline
        self.secrets = secrets
        self.observations: dict[str, Any] = {}
        self._stack = ExitStack()
        self._guest: subprocess.Popen[str] | None = None
        self._bridge: ClientBridge | None = None
        self._persona: int | None = None
        self._capability = ""

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
        return launched.stdout

    def _wait_ui(self, contains: list[str]) -> str:
        ui_deadline = min(self.deadline, time.monotonic() + 45)
        ui = ""
        while time.monotonic() < ui_deadline:
            self._adb("shell", "uiautomator", "dump", "/data/local/tmp/gramlab-capture.xml")
            ui = self._adb("shell", "cat", "/data/local/tmp/gramlab-capture.xml").stdout
            # UIAutomator produces this XML inside the dedicated guest; no external entities.
            nodes = list(ET.fromstring(ui).iter("node"))  # noqa: S314
            if all(any(text in node.get("text", "") for node in nodes) for text in contains):
                break
            time.sleep(0.2)
        else:
            raise TimeoutError("Expected text did not render in the dedicated client")
        return ui

    def _capture(self, chat: dict[str, Any], label: str, contains: list[str]) -> dict[str, Any]:
        started = time.monotonic()
        launched = self._open_chat(chat)
        ui = self._wait_ui(contains)
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

    def _tap_inline_button(
        self, chat: dict[str, Any], message: dict[str, Any], row: int, column: int
    ) -> dict[str, Any]:
        started = time.monotonic()
        self._open_chat(chat)
        ui = self._wait_ui([message["text"]])
        tree = ET.fromstring(ui)  # noqa: S314 — dedicated UIAutomator XML
        keyboard = message["reply_markup"]["inline_keyboard"]
        labels = [button["text"] for line in keyboard for button in line]
        candidates = []
        for node in tree.iter("node"):
            if not node.get("text", "").startswith(message["text"] + "\n"):
                continue
            buttons = [child for child in node if child.get("class") == "android.widget.Button"]
            if [button.get("text") for button in buttons] == labels:
                candidates.append(buttons)
        if len(candidates) != 1:
            raise RuntimeError(
                "Inline message and complete keyboard must have one accessible match"
            )
        index = sum(len(line) for line in keyboard[:row]) + column
        target = candidates[0][index]
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
                item for item in world.history(chat["id"]) if item["text"] == message["text"]
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
