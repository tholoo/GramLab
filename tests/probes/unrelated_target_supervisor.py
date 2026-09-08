"""Test-only native UI barrier before rich-target preparation."""

import hashlib
import json
import runpy
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from gramlab._android_rich_buttons import AndroidRichInput
from gramlab.reports import _png, _Redactor

original_observe = AndroidRichInput.observe
original_prepare = AndroidRichInput.prepare
original_dispatch = AndroidRichInput.dispatch
barrier_used = False
prepared_guest_calls: int | None = None
guest_calls = 0
record: dict[str, Any] = {"schema": 1, "events": []}
original_native_observation: dict[str, Any] | None = None


def counted_adb(self: Any, *arguments: str, **keywords: Any) -> Any:
    global guest_calls
    guest_calls += 1
    return self.__class__._unrelated_original_adb(self, *arguments, **keywords)


def observe(self: AndroidRichInput, message: dict[str, Any]) -> str:
    global original_native_observation
    nonce = original_observe(self, message)
    if original_native_observation is None:
        sample = self._observation(self._read("rich-button-observation.json"), nonce=nonce)
        selected = next(
            item for item in sample["targets"] if item["path"] == ["blocks", 1, "buttons", 0]
        )
        original_native_observation = {
            "kind": "observation_complete",
            "world_id": sample["world_id"],
            "persona": sample["user_id"],
            "chat_id": sample["chat_id"],
            "message_id": sample["message_id"],
            "revision": sample["revision"],
            "client_nonce": nonce,
            "pid": sample["pid"],
            "generation": sample["generation"],
            "geometry": {key: selected[key] for key in ("local_bounds", "origin", "screen_bounds")},
            "guest_calls": guest_calls,
        }
        record["events"].append(original_native_observation)
    return nonce


def prepare(
    self: AndroidRichInput, receipt: dict[str, Any], *, client_nonce: str
) -> dict[str, Any]:
    global barrier_used, prepared_guest_calls
    if not barrier_used:
        barrier_used = True
        before_persona = self.android._persona
        before_chat = self.android._active_chat
        ui = self.android._wait_ui(["Unrelated bravo / حالت ب"])
        nodes = list(ET.fromstring(ui).iter("node"))  # noqa: S314 — dedicated UIAutomator XML
        redactor = _Redactor(self.android.secrets)
        if any(redactor.text(value) != value for node in nodes for value in node.attrib.values()):
            raise RuntimeError("UI barrier contains credential-shaped text")
        Path("unrelated-target-ui.xml").write_text(ui)
        accounts = self.android._adb("shell", "dumpsys", "account").stdout
        if "Accounts: 0" not in accounts:
            raise RuntimeError("Dedicated guest must have no Android accounts")
        screenshot = subprocess.run(  # noqa: S603 — fixed dedicated guest and original PNG
            [
                self.android.profile.executables["adb"],
                "-s",
                "emulator-5554",
                "exec-out",
                "screencap",
                "-p",
            ],
            capture_output=True,
            timeout=self.android._remaining(15),
            check=True,
        ).stdout
        _png(screenshot, redactor)
        Path("unrelated-target-ui.png").write_bytes(screenshot)
        if self.android._persona != before_persona or self.android._active_chat != before_chat:
            raise RuntimeError("UI barrier changed the selected persona or chat")
        record["events"].append(
            {
                "kind": "ui_barrier_before_prepare",
                "persona": before_persona,
                "chat_id": before_chat,
                "target_id": receipt["target"]["target_id"],
                "client_nonce": client_nonce,
                "xml_sha256": hashlib.sha256(ui.encode()).hexdigest(),
                "png_sha256": hashlib.sha256(screenshot).hexdigest(),
                "accounts": "Accounts: 0",
                "guest_calls": guest_calls,
            }
        )
    prepared = original_prepare(self, receipt, client_nonce=client_nonce)
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
    record["events"].append(
        {
            "kind": "prepare_complete",
            "target_id": receipt["target"]["target_id"],
            "client_nonce": client_nonce,
            "pid": state["pid"],
            "geometry": state["geometry"],
            "observation_generation": state["observation"]["generation"],
            "guest_calls": guest_calls,
        }
    )
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
            "client_nonce": prepared["context"]["arm"]["client_nonce"],
            "pid": prepared["context"]["pid"],
            "geometry": prepared["context"]["geometry"],
            "guest_calls": guest_calls,
        }
    )
    outcome = original_dispatch(self, receipt, prepared)
    record["events"].append(
        {
            "kind": "dispatch_complete",
            "status": outcome["status"],
            "dispatch": outcome["dispatch"],
        }
    )
    Path("unrelated-target-barrier.json").write_text(json.dumps(record, indent=2))
    return outcome


from gramlab._android import Android  # noqa: E402 — patch immediately before supervisor entry

Android._unrelated_original_adb = Android._adb  # type: ignore[attr-defined]
Android._adb = counted_adb  # type: ignore[method-assign]
AndroidRichInput.observe = observe  # type: ignore[assignment,method-assign]
AndroidRichInput.prepare = prepare  # type: ignore[method-assign]
AndroidRichInput.dispatch = dispatch  # type: ignore[method-assign]
runpy.run_module("gramlab._run", run_name="__main__")
