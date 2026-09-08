"""Original native clipboard acceptance; XML controls are host-only external evidence."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import pytest
from probes.rich_native_clipboard_supervisor import (
    ClipboardProbe,
    composer,
    install,
    retain,
    semantic_state,
)
from test_runner_rich_targets import (
    assert_complete_endpoint,
    assert_native_prefix,
    execute,
    process_json,
)

from gramlab._android import Android
from gramlab._android_rich_buttons import AndroidRichInput
from gramlab.runtime import RuntimeProfile
from gramlab.world import World

pytest_plugins = ["rich_native_clipboard_plugin"]


def editor(
    text: str = "Message", *, focused: str = "true", package: str = "org.gramlab.android"
) -> str:
    return (
        '<hierarchy><node class="android.widget.EditText" '
        f'package="{package}" text="{text}" focused="{focused}" enabled="true" '
        'bounds="[50,540][260,585]"/></hierarchy>'
    )


def test_composer_requires_exact_unique_focused_original_editor() -> None:
    assert composer(editor(), "Message")["text"] == "Message"
    for xml in (
        "<hierarchy/>",
        editor("unexpected draft"),
        editor(focused="false"),
        editor(package="other.application"),
        editor().replace("</hierarchy>", editor() + "</hierarchy>"),
        editor().replace("[50,540][260,585]", "[0,0][500,800]"),
    ):
        with pytest.raises(ValueError):
            composer(xml, "Message")


def test_staging_preserves_actual_bootstrap_and_rejects_other_supervisors(tmp_path: Path) -> None:
    from rich_native_clipboard_plugin import stage

    command = ["/pinned/python", "-m", "gramlab._run"]
    assert stage(command, tmp_path, "/pinned/python") == [
        "/pinned/python",
        "/work/rich_native_clipboard_supervisor.py",
    ]
    assert (tmp_path / "rich_native_clipboard_supervisor.py").read_bytes() == Path(
        "tests/probes/rich_native_clipboard_supervisor.py"
    ).read_bytes()
    with pytest.raises(ValueError):
        stage(["/pinned/python", "another.py"], tmp_path, "/pinned/python")
    with pytest.raises(FileExistsError):
        stage(command, tmp_path, "/pinned/python")


def test_semantic_snapshot_detects_real_world_messages_and_updates(tmp_path: Path) -> None:
    with World.create(tmp_path / "world", seed=41, now=1700000000) as world:
        user = world.create_user(first_name="Sara")
        bot = world.create_user(username="targets_bot", first_name="Targets", is_bot=True)
        chat = world.open_private_chat(user_id=user["id"], bot_id=bot["id"])
        before = semantic_state(tmp_path / "world")
        assert semantic_state(tmp_path / "world") == before
        world.send_message(chat_id=chat["id"], sender_id=user["id"], text="unintended send")
        after = semantic_state(tmp_path / "world")
        assert after["events"] != before["events"]
        assert after["histories"] != before["histories"]
        assert after["update_counters"] != before["update_counters"]


@pytest.mark.android
@pytest.mark.usefixtures("clipboard_supervisor")
def test_public_native_rich_clipboard_paste_clear_and_disabled_preservation(tmp_path: Path) -> None:
    recorded = execute(tmp_path / "project", mode="headless-android")
    scenario = process_json(recorded, "scenario")[-1]
    directory = tmp_path / "headless-android-run"
    callbacks, events = assert_native_prefix(scenario, directory)
    assert_complete_endpoint(recorded, scenario, callbacks, events)
    source = Path("tests/probes/rich_native_clipboard_supervisor.py").read_bytes()
    staged = (directory / "rich_native_clipboard_supervisor.py").read_bytes()
    assert staged == source
    assert (directory / "clipboard-probe-source.sha256").read_text() == hashlib.sha256(
        source
    ).hexdigest()
    expected = [
        ("row_copy", "row copied / ردیف"),
        ("inline_copy", "inline copied / درون"),
        ("inline_disabled", "inline copied / درون"),
        ("row_disabled", "inline copied / درون"),
    ]
    paths = list((directory / "clipboard-probes").glob("*/result.json"))
    assert len(paths) == 4
    for name, text in expected:
        receipt = scenario["receipts"][name]
        operation = directory / "clipboard-probes" / receipt["operation_id"]
        evidence: dict[str, Any] = json.loads((operation / "result.json").read_text())
        assert evidence["name"] == name
        assert evidence["operation_id"] == receipt["operation_id"]
        assert evidence["target"] == receipt["target"]
        assert evidence["dispatch_result"] == {
            key: receipt[key] for key in ("status", "dispatch", "effect", "reason", "evidence")
        }
        assert evidence["status"] == "passed"
        assert evidence["ui_representation"] == "xml_with_redacted_attribute_and_text_values"
        assert evidence["pasted_text"] == text and evidence["cleared"] is True
        assert evidence["before"] == evidence["after"]
        for phase, value in (("empty", "Message"), ("pasted", text), ("cleared", "Message")):
            assert composer((operation / f"{phase}.xml").read_text(), value)["text"] == value
            from PIL import Image

            with Image.open(operation / f"{phase}.png") as image:
                assert image.format == "PNG" and image.size == (320, 640)
                image.verify()


@pytest.fixture
def native_host(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AndroidRichInput:
    monkeypatch.chdir(tmp_path)
    with World.create(tmp_path / "world", seed=41, now=1700000000) as world:
        user = world.create_user(first_name="Sara")
        bot = world.create_user(first_name="Targets", is_bot=True)
        world.open_private_chat(user_id=user["id"], bot_id=bot["id"])
    profile = RuntimeProfile.load(Path(os.environ["GRAMLAB_RUNTIME_PROFILE"]))
    return AndroidRichInput(Android(profile, deadline=time.monotonic() + 60, secrets=[SECRET]))


SECRET = "gramlab-client_" + "q" * 43


@pytest.mark.parametrize("mode", ["success", "wrong_text", "uncertain", "mutation", "ui_failure"])
def test_post_probe_preserves_original_return_and_fails_incorrect_effects(
    native_host: AndroidRichInput, monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    outcome: dict[str, Any] = {
        "status": "succeeded",
        "dispatch": "dispatched",
        "reason": None,
        "effect": {"kind": "copy", "text": "row copied / ردیف"},
        "evidence": {},
    }
    if mode == "wrong_text":
        outcome["effect"]["text"] = "inline copied / درون"
    if mode == "uncertain":
        outcome.update(status="uncertain", effect=None, reason={"code": "effect_timeout"})
    receipt = {"operation_id": "1" * 32, "target": {"path": ["blocks", 16, "buttons", 1]}}
    prepared = {"control": "original preparation"}
    order: list[str] = []

    def original(
        self: AndroidRichInput, actual: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        assert self is native_host and actual is receipt and context is prepared
        assert order == []
        order.append("dispatch")
        return outcome

    def external_ui(self: ClipboardProbe, name: str, expected: str) -> None:
        assert order == ["dispatch"] and name == "row_copy" and expected == "row copied / ردیف"
        order.append("external_ui")
        if mode == "ui_failure":
            raise ValueError("Private diagnostic " + SECRET)
        if mode == "mutation":
            with World.open(Path("world")) as world:
                world.send_message(chat_id=1, sender_id=1, text="unintended composer send")
        self.record.update(pasted_text=expected, cleared=True)

    monkeypatch.setattr(AndroidRichInput, "dispatch", original)
    monkeypatch.setattr(ClipboardProbe, "run", external_ui)
    install()
    assert native_host.dispatch(receipt, prepared) is outcome
    raw = Path("clipboard-probes", "1" * 32, "result.json").read_text()
    assert SECRET not in raw
    evidence = json.loads(raw)
    assert evidence["dispatch_result"] == outcome
    assert evidence["status"] == ("passed" if mode == "success" else "failed")
    assert order == (
        ["dispatch"] if mode in {"wrong_text", "uncertain"} else ["dispatch", "external_ui"]
    )
    if mode == "mutation":
        assert evidence["before"] != evidence["after"]
    if mode == "ui_failure":
        assert evidence["exception_class"] == "ValueError" and "Private diagnostic" not in raw


def test_original_dispatch_exception_propagates_without_probe(
    native_host: AndroidRichInput, monkeypatch: pytest.MonkeyPatch
) -> None:
    failure = RuntimeError("Original dispatch failure")
    calls = 0

    def original(
        self: AndroidRichInput, receipt: dict[str, Any], prepared: dict[str, Any]
    ) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        raise failure

    monkeypatch.setattr(AndroidRichInput, "dispatch", original)
    install()
    with pytest.raises(RuntimeError) as raised:
        native_host.dispatch({"operation_id": "3" * 32, "target": {"path": []}}, {})
    assert raised.value is failure and calls == 1
    record = json.loads(Path("clipboard-probes", "3" * 32, "result.json").read_text())
    assert record["phase"] == "original_dispatch"
    assert record["exception_class"] == "RuntimeError"
    assert record["status"] == "failed" and "commands" not in record


def test_exhausted_deadline_prevents_any_guest_command(native_host: AndroidRichInput) -> None:
    native_host.android.deadline = time.monotonic() - 1
    probe = ClipboardProbe(native_host, Path.cwd(), {})
    with pytest.raises(TimeoutError):
        probe.adb("shell", "input", "keyevent", "279")
    assert probe.calls == 0


@pytest.mark.parametrize("incorrect", [False, True])
def test_paste_clear_uses_only_ordinary_keys_and_stops_on_wrong_text(
    native_host: AndroidRichInput, incorrect: bool
) -> None:
    calls: list[tuple[str, ...]] = []

    class ExternalUI(ClipboardProbe):
        def adb(self, *arguments: str) -> str:
            calls.append(arguments)
            return ""

        def capture(self, phase: str, expected: str) -> None:
            # Explicitly substituted external XML; no generated PNG or native evidence.
            observed = "wrong clipboard" if incorrect and phase == "pasted" else expected
            composer(editor(observed), expected)

    probe = ExternalUI(native_host, Path.cwd(), {"operation_id": "2" * 32})
    if incorrect:
        with pytest.raises(ValueError):
            probe.run("row_copy", "row copied / ردیف")
        assert calls == [("shell", "input", "keyevent", "279")]
    else:
        probe.run("row_copy", "row copied / ردیف")
        assert calls == [
            ("shell", "input", "keyevent", "279"),
            ("shell", "input", "keyevent", "123"),
            ("shell", "input", "keyevent", *(["67"] * len("row copied / ردیف"))),
        ]
        assert probe.record["cleared"] is True


def test_unrelated_foreground_is_never_dismissed(native_host: AndroidRichInput) -> None:
    calls: list[tuple[str, ...]] = []

    class UnrelatedUI(ClipboardProbe):
        def adb(self, *arguments: str) -> str:
            calls.append(arguments)
            return "mCurrentFocus=Window{aaaa u0 another.application/Activity}"

    with pytest.raises(ValueError, match="Unrelated"):
        UnrelatedUI(native_host, Path.cwd(), {}).dismiss_popup()
    assert calls == [("shell", "dumpsys", "window", "displays")]


def test_retention_redacts_known_capabilities_and_preserves_prior_evidence(tmp_path: Path) -> None:
    retain(tmp_path, {"original_output": SECRET, "nested": [SECRET]}, [SECRET])
    path = tmp_path / "result.json"
    original = path.read_bytes()
    assert SECRET.encode() not in original
    assert json.loads(original) == {"original_output": "[REDACTED]", "nested": ["[REDACTED]"]}
    with pytest.raises(FileExistsError):
        retain(tmp_path, {"replacement": True}, [SECRET])
    assert path.read_bytes() == original
    with pytest.raises(ValueError, match="bound"):
        retain(tmp_path, {"oversize": "x" * (4 * 1024 * 1024)}, [SECRET])


@pytest.mark.parametrize("editor_flag", ["false", "true"])
def test_capture_redaction_preserves_xml_and_native_password_flag(
    native_host: AndroidRichInput, monkeypatch: pytest.MonkeyPatch, editor_flag: str
) -> None:
    # Native UIAutomator attribute shape; external XML and capture boundary only.
    # Do not manufacture an original PNG for this host regression.
    xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<hierarchy rotation="0"><node class="android.widget.EditText" '
        'package="org.gramlab.android" text="Message" enabled="true" focused="true" '
        f'password="{editor_flag}" bounds="[50,540][260,585]"/>'
        f'<node class="android.widget.TextView" text="{SECRET}" '
        f'content-desc="private {SECRET} &quot;quoted&quot; &amp; shown">{SECRET}</node>'
        f"{SECRET}</hierarchy>"
    )
    commands: list[tuple[str, ...]] = []
    captures: list[Path] = []

    def external_adb(
        self: Android, *arguments: str, **options: Any
    ) -> subprocess.CompletedProcess[str]:
        commands.append(arguments)
        output = xml if arguments[:2] == ("shell", "cat") else "UI hierarchy dumped"
        return subprocess.CompletedProcess(arguments, 0, output, "")

    def external_capture(self: AndroidRichInput, path: Path) -> None:
        captures.append(path)

    monkeypatch.setattr(Android, "_adb", external_adb)
    monkeypatch.setattr(AndroidRichInput, "_capture_original", external_capture)
    directory = Path.cwd() / "capture-control"
    directory.mkdir()
    record: dict[str, Any] = {"operation_id": "4" * 32}
    probe = ClipboardProbe(native_host, directory, record)
    if editor_flag == "false":
        probe.capture("empty", "Message")
    else:
        with pytest.raises(ValueError, match="composer state"):
            probe.capture("empty", "Message")
    retained = (directory / "empty.xml").read_text()
    root = ET.fromstring(retained)  # noqa: S314 — retained literal host-control XML
    node = root.find("node")
    assert node is not None and node.get("password") == editor_flag
    assert root.findall("node")[1].attrib == {
        "class": "android.widget.TextView",
        "text": "[REDACTED]",
        "content-desc": 'private [REDACTED] "quoted" & shown',
    }
    assert root.findall("node")[1].text == "[REDACTED]"
    assert root.findall("node")[1].tail == "[REDACTED]"
    retain(directory, record, native_host.android.secrets)
    assert SECRET not in retained and SECRET not in (directory / "result.json").read_text()
    assert len(commands) == 2 and commands[0][:3] == ("shell", "uiautomator", "dump")
    assert captures == [directory / "empty.png"]
    assert record["ui_representation"] == "xml_with_redacted_attribute_and_text_values"
