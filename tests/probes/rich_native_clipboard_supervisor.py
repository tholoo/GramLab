"""Post-dispatch original paste/clear acceptance; never changes rich target dispatch."""

from __future__ import annotations

import copy
import hashlib
import json
import re
import runpy
import sqlite3
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from gramlab._android_rich_buttons import AndroidRichInput
from gramlab.reports import _Redactor
from gramlab.world import World

PACKAGE = "org.gramlab.android"
ROW = "row copied / ردیف"
INLINE = "inline copied / درون"
CASES: list[tuple[str, list[str | int], str]] = [
    ("row_copy", ["blocks", 16, "buttons", 1], ROW),
    ("inline_copy", ["blocks", 17, "text", 1, "text", 2, "button"], INLINE),
    ("inline_disabled", ["blocks", 17, "text", 2, "button"], INLINE),
    ("row_disabled", ["blocks", 16, "buttons", 2], INLINE),
]
FOCUS = r"mCurrentFocus=Window\{([^\s{}]+) u(\d+) ([^{}\r\n]+)\}"
LIMIT = 1024 * 1024


def composer(xml: str, expected: str) -> dict[str, str]:
    if len(xml.encode()) > LIMIT:
        raise ValueError("Composer XML exceeds bound")
    nodes = [
        node
        for node in ET.fromstring(xml).iter("node")  # noqa: S314 — original guest XML
        if node.get("class") == "android.widget.EditText" and node.get("package") == PACKAGE
    ]
    if len(nodes) != 1:
        raise ValueError("Original composer missing or ambiguous")
    node = nodes[0]
    bounds = re.fullmatch(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", node.get("bounds", ""))
    if bounds is None:
        raise ValueError("Original composer has no bounds")
    left, top, right, bottom = map(int, bounds.groups())
    if not (
        node.get("text") == expected
        and node.get("focused") == "true"
        and node.get("enabled") == "true"
        and node.get("password", "false") == "false"
        and 0 <= left < right <= 320
        and 0 <= top < bottom <= 640
    ):
        raise ValueError("Original composer state does not match")
    return dict(node.attrib)


def redact_ui(xml: str, secrets: list[str]) -> str:
    """Retain XML structure with redacted values, not byte-identical raw XML."""
    if len(xml.encode()) > LIMIT:
        raise ValueError("Composer XML exceeds bound")
    root = ET.fromstring(xml)  # noqa: S314 — bounded original guest XML
    redactor = _Redactor(secrets)
    for node in root.iter():
        for name, value in list(node.attrib.items()):
            node.set(name, redactor.text(value))
        if node.text is not None:
            node.text = redactor.text(node.text)
        if node.tail is not None:
            node.tail = redactor.text(node.tail)
    serialized = ET.tostring(root, encoding="unicode")
    if len(serialized.encode()) > LIMIT:
        raise ValueError("Redacted composer XML exceeds bound")
    if any(secret in serialized for secret in redactor.secrets):
        raise ValueError("Composer XML structure contains a capability")
    return serialized


def semantic_state(directory: Path) -> dict[str, Any]:
    """One read-only snapshot; update generation counts exclude ordinary queue ACK races."""
    uri = (directory / "world.sqlite3").absolute().as_uri() + "?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    try:
        connection.execute("BEGIN")
        world = World(connection)
        snapshot = world.snapshot()
        return {
            "snapshot": snapshot,
            "histories": {str(chat["id"]): world.history(chat["id"]) for chat in snapshot["chats"]},
            "events": world.events(),
            "callbacks": connection.execute(
                "SELECT id,user_id,bot_id,request_id,request_body,body,answer "
                "FROM callbacks ORDER BY id"
            ).fetchall(),
            "client_sends": connection.execute(
                "SELECT user_id,chat_id,request_id,request_body,body,position FROM client_sends "
                "ORDER BY user_id,chat_id,request_id"
            ).fetchall(),
            "update_counters": connection.execute(
                "SELECT id,next_update FROM bots ORDER BY id"
            ).fetchall(),
        }
    finally:
        connection.close()


class ClipboardProbe:
    def __init__(self, host: AndroidRichInput, directory: Path, record: dict[str, Any]) -> None:
        self.host = host
        self.android = host.android
        self.directory = directory
        self.record = record
        self.calls = 0

    def adb(self, *arguments: str) -> str:
        if self.calls >= 32:
            raise ValueError("Clipboard probe command count exceeds bound")
        self.android._remaining(15)
        self.calls += 1
        self.record["phase"] = "command:" + "/".join(arguments[:3])
        result = self.android._adb(*arguments)
        if len(result.stdout.encode()) > LIMIT or len(result.stderr.encode()) > LIMIT:
            raise ValueError("Clipboard probe output exceeds bound")
        self.record.setdefault("commands", []).append(
            _Redactor(self.android.secrets).clean(
                {
                    "arguments": list(arguments),
                    "returncode": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                }
            )
        )
        return result.stdout

    def capture(self, phase: str, expected: str) -> None:
        self.record["phase"] = phase
        remote = f"/data/local/tmp/clipboard-{self.record['operation_id']}-{phase}.xml"
        self.adb("shell", "uiautomator", "dump", remote)
        xml = self.adb("shell", "cat", remote)
        xml = redact_ui(xml, self.android.secrets)
        self.record["ui_representation"] = "xml_with_redacted_attribute_and_text_values"
        with (self.directory / (phase + ".xml")).open("x") as stream:
            stream.write(xml)
        self.host._capture_original(self.directory / (phase + ".png"))
        composer(xml, expected)

    def dismiss_popup(self) -> None:
        windows = self.adb("shell", "dumpsys", "window", "displays")
        focused = re.findall(FOCUS, windows)
        if len(focused) != 1:
            raise ValueError("Ambiguous original foreground")
        if focused[0][2] == PACKAGE + "/org.telegram.ui.LaunchActivity":
            return
        if not focused[0][2].startswith("PopupWindow:"):
            raise ValueError("Unrelated foreground cannot be dismissed")
        pids = self.adb("shell", "pidof", PACKAGE).split()
        if len(pids) != 1 or not pids[0].isdecimal():
            raise ValueError("Original popup process is unavailable")
        # Reuse the strict PID/UID/parent/surface validator; never trust focused-app alone.
        self.host._owned_popup(focused[0], int(pids[0]))
        if self.adb("shell", "pidof", PACKAGE).split() != pids:
            raise ValueError("Original popup process changed")
        if re.findall(FOCUS, self.adb("shell", "dumpsys", "window", "displays")) != focused:
            raise ValueError("Original popup focus changed")
        self.adb("shell", "input", "keyevent", "4")
        self.record["popup_dismissed"] = True
        remaining = re.findall(FOCUS, self.adb("shell", "dumpsys", "window", "displays"))
        if len(remaining) != 1 or remaining[0][2] != PACKAGE + "/org.telegram.ui.LaunchActivity":
            raise ValueError("Original chat did not regain focus")

    def run(self, name: str, expected: str) -> None:
        if name == "row_disabled":
            self.dismiss_popup()
        self.capture("empty", "Message")
        self.adb("shell", "input", "keyevent", "279")
        self.capture("pasted", expected)
        self.record["pasted_text"] = expected
        # Ordinary end/delete events; exact fixture strings contain only BMP code points.
        self.adb("shell", "input", "keyevent", "123")
        self.adb("shell", "input", "keyevent", *(["67"] * len(expected)))
        self.capture("cleared", "Message")
        self.record["cleared"] = True


def retain(directory: Path, record: dict[str, Any], secrets: list[str]) -> None:
    body = json.dumps(_Redactor(secrets).clean(record), ensure_ascii=True).encode()
    if len(body) > 4 * LIMIT:
        raise ValueError("Clipboard evidence exceeds bound")
    with (directory / "result.json").open("xb") as stream:
        stream.write(body)


def install_fresh_diagnostic() -> None:
    """Observe an original failure using its traceback; no extra guest or World reads."""
    original = AndroidRichInput._fresh
    code = original.__code__
    source = {
        "file": Path(code.co_filename).name,
        "sha256": hashlib.sha256(Path(code.co_filename).read_bytes()).hexdigest(),
    }

    def fresh(self: AndroidRichInput, state: dict[str, Any]) -> dict[str, Any]:
        try:
            return original(self, state)
        except BaseException as error:
            try:
                operation = state.get("arm", {}).get("operation_id", "")
                directory = state.get("directory")
                if (
                    re.fullmatch(r"[a-f0-9]{32}", operation) is not None
                    and isinstance(directory, Path)
                    and directory == Path("rich-buttons") / operation
                ):
                    cursor = error.__traceback__
                    frame = None
                    frames: list[dict[str, Any]] = []
                    while cursor is not None and len(frames) < 16:
                        if cursor.tb_frame.f_code is code and frame is None:
                            frame = cursor
                        if frame is not None:
                            frames.append(
                                {
                                    "file": Path(cursor.tb_frame.f_code.co_filename).name,
                                    "function": cursor.tb_frame.f_code.co_name,
                                    "line": cursor.tb_lineno,
                                }
                            )
                        cursor = cursor.tb_next
                    values = frame.tb_frame.f_locals if frame is not None else {}
                    names = ("sample", "pid", "now")
                    state_names = ("arm", "target", "pid", "geometry", "dispatched", "mismatch")
                    record = {
                        "schema": 1,
                        "operation_id": operation,
                        "exception_class": type(error).__name__,
                        "source": source,
                        "line": frame.tb_lineno if frame is not None else None,
                        "frame_present": frame is not None,
                        "traceback": frames,
                        "locals": {
                            key: copy.deepcopy(values[key]) for key in names if key in values
                        },
                        "missing_locals": [key for key in names if key not in values],
                        "state": {
                            key: copy.deepcopy(state[key]) for key in state_names if key in state
                        },
                        "missing_state": [key for key in state_names if key not in state],
                    }
                    redactor = _Redactor(self.android.secrets)
                    body = json.dumps(redactor.clean(record), ensure_ascii=True).encode()
                    if len(body) > 128 * 1024:
                        for key in ("locals", "state"):
                            record.pop(key)
                        record["details_omitted"] = "record_exceeds_bound"
                        body = json.dumps(redactor.clean(record), ensure_ascii=True).encode()
                    if len(body) <= 128 * 1024:
                        with (directory / "fresh-failure.json").open("xb") as stream:
                            stream.write(body)
            except Exception as diagnostic_error:
                print(
                    "Fresh failure diagnostic unavailable: " + type(diagnostic_error).__name__,
                    file=sys.stderr,
                )
            raise

    AndroidRichInput._fresh = fresh  # type: ignore[method-assign]


def install() -> None:
    original = AndroidRichInput.dispatch
    completed: list[str] = []

    def dispatch(
        self: AndroidRichInput, receipt: dict[str, Any], prepared: dict[str, Any]
    ) -> dict[str, Any]:
        # Nothing runs before original dispatch; preparation and its freshness budget are untouched.
        try:
            result = original(self, receipt, prepared)
        except BaseException as error:
            try:
                operation = receipt.get("operation_id", "")
                if re.fullmatch(r"[a-f0-9]{32}", operation) is not None:
                    failed_directory = Path("clipboard-probes") / operation
                    failed_directory.mkdir(parents=True, exist_ok=False)
                    retain(
                        failed_directory,
                        {
                            "schema": 1,
                            "operation_id": operation,
                            "target": receipt.get("target"),
                            "status": "failed",
                            "phase": "original_dispatch",
                            "exception_class": type(error).__name__,
                        },
                        self.android.secrets,
                    )
            except Exception:
                print("Original dispatch failure evidence unavailable", file=sys.stderr)
            raise
        selected = next((case for case in CASES if case[1] == receipt["target"]["path"]), None)
        if selected is None:
            return result
        name, _path, text = selected
        directory: Path | None = None
        record: dict[str, Any] = {
            "schema": 1,
            "name": name,
            "operation_id": receipt["operation_id"],
            "target": copy.deepcopy(receipt["target"]),
            "dispatch_result": copy.deepcopy(result),
            "started_ns": time.monotonic_ns(),
            "status": "failed",
            "phase": "validation",
        }
        try:
            operation = receipt["operation_id"]
            if re.fullmatch(r"[a-f0-9]{32}", operation) is None:
                raise ValueError("Invalid clipboard operation ID")
            directory = Path("clipboard-probes") / operation
            directory.mkdir(parents=True, exist_ok=False)
            expected_effect = (
                {"kind": "copy", "text": text}
                if name.endswith("copy")
                else {"kind": "none", "reason": "disabled"}
            )
            if (
                completed != [case[0] for case in CASES[: len(completed)]]
                or len(completed) >= 4
                or name != CASES[len(completed)][0]
                or result["status"] != "succeeded"
                or result["dispatch"] != "dispatched"
                or result["effect"] != expected_effect
                or result["reason"] is not None
            ):
                raise ValueError("Clipboard probe requires the exact ordered confirmed effect")
            record["before"] = semantic_state(Path("world"))
            try:
                ClipboardProbe(self, directory, record).run(name, text)
            finally:
                record["after"] = semantic_state(Path("world"))
            if record["before"] != record["after"]:
                raise ValueError("Paste or clear changed authoritative semantic state")
            completed.append(name)
            record["status"] = "passed"
        except Exception as error:
            record["exception_class"] = type(error).__name__
        finally:
            record["finished_ns"] = time.monotonic_ns()
            if directory is not None:
                try:
                    retain(directory, record, self.android.secrets)
                except Exception as error:
                    print(
                        "Clipboard evidence retention failed: " + type(error).__name__,
                        file=sys.stderr,
                    )
        return result

    AndroidRichInput.dispatch = dispatch  # type: ignore[method-assign]


if __name__ == "__main__":
    Path("clipboard-probe-source.sha256").write_text(
        hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    )
    install_fresh_diagnostic()
    install()
    runpy.run_module("gramlab._run", run_name="__main__")
