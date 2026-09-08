"""Test-only native UI barrier before rich-target preparation."""

import hashlib
import json
import runpy
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from gramlab._android_rich_buttons import AndroidRichInput
from gramlab.reports import _Redactor

original_observe = AndroidRichInput.observe
original_fresh = AndroidRichInput._fresh
original_prepare = AndroidRichInput.prepare
original_dispatch = AndroidRichInput.dispatch
barrier_used = False
prepared_guest_calls: int | None = None
guest_calls = 0
input_taps: list[dict[str, Any]] = []
record: dict[str, Any] = {
    "schema": 1,
    "bootstrap_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    "events": [],
}
original_native_observation: dict[str, Any] | None = None


def persist(secrets: list[str]) -> None:
    body = json.dumps(_Redactor(secrets).clean(record), ensure_ascii=True, indent=2).encode()
    if len(body) > 128 * 1024:
        raise RuntimeError("Unrelated-target barrier evidence exceeds bound")
    temporary = Path("unrelated-target-barrier.json.tmp")
    temporary.write_bytes(body)
    temporary.replace("unrelated-target-barrier.json")


def fresh(self: AndroidRichInput, state: dict[str, Any]) -> dict[str, Any]:
    """Retain the original failing frame without another guest, World or clock read."""
    try:
        return original_fresh(self, state)
    except BaseException as error:
        try:
            code = original_fresh.__code__
            cursor = error.__traceback__
            frame = None
            traceback: list[dict[str, Any]] = []
            while cursor is not None and len(traceback) < 16:
                if cursor.tb_frame.f_code is code and frame is None:
                    frame = cursor
                if frame is not None:
                    traceback.append(
                        {
                            "file": Path(cursor.tb_frame.f_code.co_filename).name,
                            "function": cursor.tb_frame.f_code.co_name,
                            "line": cursor.tb_lineno,
                        }
                    )
                cursor = cursor.tb_next
            values = frame.tb_frame.f_locals if frame is not None else {}
            sample = values.get("sample")
            sample_fields = (
                "schema",
                "nonce",
                "client_nonce",
                "world_id",
                "user_id",
                "chat_id",
                "message_id",
                "revision",
                "pid",
                "generation",
                "drawn_uptime_ms",
                "available",
                "reason",
                "targets",
            )
            record["events"].append(
                {
                    "kind": "fresh_failed",
                    "operation_id": state.get("arm", {}).get("operation_id"),
                    "exception_class": type(error).__name__,
                    "source": {
                        "file": Path(code.co_filename).name,
                        "sha256": hashlib.sha256(Path(code.co_filename).read_bytes()).hexdigest(),
                    },
                    "line": frame.tb_lineno if frame is not None else None,
                    "frame_present": frame is not None,
                    "traceback": traceback,
                    "locals": {
                        **{key: values[key] for key in ("pid", "now") if key in values},
                        **(
                            {"sample": {key: sample[key] for key in sample_fields if key in sample}}
                            if isinstance(sample, dict)
                            else {}
                        ),
                    },
                    "missing_locals": [
                        key for key in ("sample", "pid", "now") if key not in values
                    ],
                    "state": {
                        key: state[key]
                        for key in ("arm", "target", "pid", "geometry", "dispatched", "mismatch")
                        if key in state
                    },
                }
            )
            persist(self.android.secrets)
        except Exception as diagnostic_error:
            print(
                "Unrelated-target fresh diagnostic unavailable: " + type(diagnostic_error).__name__,
                file=sys.stderr,
            )
        raise


def counted_adb(self: Any, *arguments: str, **keywords: Any) -> Any:
    global guest_calls
    guest_calls += 1
    if len(arguments) == 5 and arguments[:3] == ("shell", "input", "tap"):
        input_taps.append({"guest_call": guest_calls, "arguments": list(arguments)})
    return self.__class__._unrelated_original_adb(self, *arguments, **keywords)


def observe(self: AndroidRichInput, message: dict[str, Any]) -> str:
    global original_native_observation
    nonce = original_observe(self, message)
    if original_native_observation is None:
        sample = self._observation(self._read("rich-button-observation.json"), nonce=nonce)
        selected = next(
            item for item in sample["targets"] if item["path"] == ["blocks", 1, "buttons", 0]
        )
        accounts = self.android._adb("shell", "dumpsys", "account").stdout
        if "Accounts: 0" not in accounts:
            raise RuntimeError("Dedicated guest must have no Android accounts")
        original_native_observation = {
            "kind": "observation_complete",
            "world_id": sample["world_id"],
            "persona": sample["user_id"],
            "chat_id": sample["chat_id"],
            "message_id": sample["message_id"],
            "revision": sample["revision"],
            "activation_nonce": sample["nonce"],
            "client_nonce": nonce,
            "pid": sample["pid"],
            "generation": sample["generation"],
            "drawn_uptime_ms": sample["drawn_uptime_ms"],
            "geometry": {key: selected[key] for key in ("local_bounds", "origin", "screen_bounds")},
            "accounts": "Accounts: 0",
            "guest_calls": guest_calls,
        }
        record["events"].append(original_native_observation)
        persist(self.android.secrets)
    return nonce


def prepare(
    self: AndroidRichInput, receipt: dict[str, Any], *, client_nonce: str
) -> dict[str, Any]:
    global barrier_used, prepared_guest_calls
    if not barrier_used:
        barrier_used = True
        original = original_native_observation
        if original is None:
            raise RuntimeError("Original native observation was not retained")
        before_persona = self.android._persona
        before_chat = self.android._active_chat
        ui = self.android._wait_ui(["Unrelated bravo / حالت ب"])
        nodes = list(ET.fromstring(ui).iter("node"))  # noqa: S314 — dedicated UIAutomator XML
        redactor = _Redactor(self.android.secrets)
        if any(redactor.text(value) != value for node in nodes for value in node.attrib.values()):
            raise RuntimeError("UI barrier contains credential-shaped text")
        Path("unrelated-target-ui.xml").write_text(ui)
        if self.android._persona != before_persona or self.android._active_chat != before_chat:
            raise RuntimeError("UI barrier changed the selected persona or chat")
        record["events"].append(
            {
                "kind": "ui_barrier_before_prepare",
                "persona": before_persona,
                "chat_id": before_chat,
                "target_id": receipt["target"]["target_id"],
                "world_id": original["world_id"],
                "client_nonce": client_nonce,
                "pid": original["pid"],
                "generation": original["generation"],
                "xml_sha256": hashlib.sha256(ui.encode()).hexdigest(),
                "xml_bytes": len(ui.encode()),
                "guest_calls": guest_calls,
            }
        )
        persist(self.android.secrets)
    try:
        prepared = original_prepare(self, receipt, client_nonce=client_nonce)
    except BaseException as error:
        record["events"].append(
            {
                "kind": "prepare_failed",
                "target_id": receipt["target"]["target_id"],
                "operation_id": receipt["operation_id"],
                "exception_class": type(error).__name__,
                "guest_calls": guest_calls,
            }
        )
        persist(self.android.secrets)
        raise
    prepared_guest_calls = guest_calls
    state = prepared["context"]
    if original_native_observation is None:
        raise RuntimeError("Original native observation was not retained")
    if (
        state["pid"] != original_native_observation["pid"]
        or client_nonce != original_native_observation["client_nonce"]
        or state["geometry"] != original_native_observation["geometry"]
    ):
        raise RuntimeError("Unrelated edit changed target geometry or native lifetime")
    captures = state["evidence"]["native"]["captures"]
    expected_capture = Path("rich-buttons") / receipt["operation_id"] / "before.png"
    if captures != [expected_capture.as_posix()] or not expected_capture.is_file():
        raise RuntimeError("Original preparation capture is missing or unrelated")
    capture = expected_capture.read_bytes()
    record["events"].append(
        {
            "kind": "prepare_complete",
            "target_id": receipt["target"]["target_id"],
            "world_id": state["arm"]["world_id"],
            "persona": state["arm"]["user_id"],
            "chat_id": state["arm"]["chat_id"],
            "message_id": state["arm"]["message_id"],
            "revision": state["arm"]["revision"],
            "activation_nonce": state["arm"]["nonce"],
            "client_nonce": client_nonce,
            "pid": state["pid"],
            "geometry": state["geometry"],
            "observation_generation": state["observation"]["generation"],
            "drawn_uptime_ms": state["observation"]["drawn_uptime_ms"],
            "ui_xml_sha256": record["events"][1]["xml_sha256"],
            "before_png": expected_capture.as_posix(),
            "before_png_sha256": hashlib.sha256(capture).hexdigest(),
            "before_png_bytes": len(capture),
            "guest_calls": guest_calls,
        }
    )
    persist(self.android.secrets)
    return prepared


def dispatch(
    self: AndroidRichInput, receipt: dict[str, Any], prepared: dict[str, Any]
) -> dict[str, Any]:
    if prepared_guest_calls is None or guest_calls != prepared_guest_calls:
        raise RuntimeError("Guest call occurred between original prepare and dispatch")
    record["events"].append(
        {
            "kind": "dispatch_started",
            "target_id": receipt["target"]["target_id"],
            "world_id": prepared["context"]["arm"]["world_id"],
            "persona": prepared["context"]["arm"]["user_id"],
            "chat_id": prepared["context"]["arm"]["chat_id"],
            "message_id": prepared["context"]["arm"]["message_id"],
            "revision": prepared["context"]["arm"]["revision"],
            "activation_nonce": prepared["context"]["arm"]["nonce"],
            "client_nonce": prepared["context"]["arm"]["client_nonce"],
            "pid": prepared["context"]["pid"],
            "geometry": prepared["context"]["geometry"],
            "observation_generation": prepared["context"]["arm"]["observation_generation"],
            "guest_calls": guest_calls,
        }
    )
    outcome = original_dispatch(self, receipt, prepared)
    record["events"].append(
        {
            "kind": "dispatch_complete",
            "status": outcome["status"],
            "dispatch": outcome["dispatch"],
            "input_taps": input_taps,
        }
    )
    persist(self.android.secrets)
    return outcome


def install() -> None:
    from gramlab._android import Android

    Android._unrelated_original_adb = Android._adb  # type: ignore[attr-defined]
    Android._adb = counted_adb  # type: ignore[method-assign]
    AndroidRichInput.observe = observe  # type: ignore[assignment,method-assign]
    AndroidRichInput._fresh = fresh  # type: ignore[method-assign]
    AndroidRichInput.prepare = prepare  # type: ignore[method-assign]
    AndroidRichInput.dispatch = dispatch  # type: ignore[method-assign]


if __name__ == "__main__":
    install()
    runpy.run_module("gramlab._run", run_name="__main__")
