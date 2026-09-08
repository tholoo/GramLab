"""Original native clipboard acceptance; XML controls are host-only external evidence."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
import sqlite3
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
    EXPECTED_SNAPSHOT,
    PRIMARY_MESSAGE,
    UNRELATED_MESSAGE,
    api_message,
    assert_native_evidence,
    assert_observation,
    expected_receipt_target,
    initial_events,
    initial_history,
    ordinary_message,
    process_json,
    project,
    token,
)

from gramlab._android import Android
from gramlab._android_rich_buttons import AndroidRichInput
from gramlab.runner import run
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


def execute_clipboard(directory: Path, *, native: bool) -> dict[str, Any]:
    mode = "headless-android" if native else "simulation-only"
    arguments: dict[str, Any] = {}
    if native:
        profile, apk = (
            os.environ.get("GRAMLAB_ANDROID_RUNTIME_PROFILE"),
            os.environ.get("GRAMLAB_ANDROID_PROBE_APK"),
        )
        if profile is None or apk is None or not os.access("/dev/kvm", os.R_OK | os.W_OK):
            pytest.skip("Requires reviewed Android profile/APK and accessible KVM")
        arguments = {
            "android_profile": RuntimeProfile.load(Path(profile)),
            "android_apk": Path(apk),
            "bridge_version": 4,
        }
    manifest = project(directory, mode=mode, variant="clipboard-four-phases")
    shutil.copy2("tests/rich_clipboard_scenario.py", directory / "scenario.py")
    output = directory.parent / (mode + "-run")
    outcome = run(
        manifest,
        output,
        profile=RuntimeProfile.load(Path(os.environ["GRAMLAB_RUNTIME_PROFILE"])),
        **arguments,
    )
    recorded: dict[str, Any] = json.loads((output / "result.json").read_text())
    assert outcome == "passed", recorded
    return recorded


# Independently authored scenario expectations; do not import the executing phase plan.
EXPECTED_PHASES = [
    ("row_copy", [("row_copy", 2, "row copied / ردیف")]),
    ("inline_copy", [("inline_copy", 5, "inline copied / درون")]),
    (
        "inline_disabled",
        [
            ("inline_baseline", 5, "inline copied / درون"),
            ("inline_disabled", 6, "inline copied / درون"),
        ],
    ),
    (
        "row_disabled",
        [("row_baseline", 2, "row copied / ردیف"), ("row_disabled", 3, "row copied / ردیف")],
    ),
]


def assert_clipboard_exchange(api: list[dict[str, Any]]) -> None:
    def entry(method: str, parameters: dict[str, Any], result: Any) -> dict[str, Any]:
        return {
            "method": method,
            "parameters": parameters,
            "status": 200,
            "body": {"ok": True, "result": result},
        }

    assert api[:3] == [
        entry(
            "getUpdates",
            {"timeout": 10},
            [{"update_id": 1, "message": api_message(initial_history()[0])}],
        ),
        *[
            entry(
                "sendRichMessage",
                {
                    "chat_id": 2,
                    "rich_message": message["rich_message"] | {"skip_entity_detection": True},
                },
                api_message(message),
            )
            for message in (PRIMARY_MESSAGE, UNRELATED_MESSAGE)
        ],
    ]
    # Only empty polls at offset2 can intervene before the sole finish delivery.
    position = 3
    empty = entry("getUpdates", {"offset": 2, "timeout": 10}, [])
    while position < len(api) and api[position] == empty:
        position += 1
    assert api[position:] == [
        entry(
            "getUpdates",
            {"offset": 2, "timeout": 10},
            [
                {
                    "update_id": 2,
                    "message": api_message(ordinary_message(4, 2, "finish rich targets")),
                }
            ],
        ),
        entry("getUpdates", {"offset": 3}, []),
    ]


def assert_clipboard_endpoint(
    recorded: dict[str, Any], directory: Path, *, native: bool
) -> dict[str, Any]:
    assert recorded["outcome"] == "passed" and recorded["failure"] is None
    assert recorded["mode"] == ("headless-android" if native else "simulation-only")
    assert recorded["world"] == EXPECTED_SNAPSHOT
    assert set(recorded["processes"]) == {"scenario", "bot:targets"}
    for process in recorded["processes"].values():
        assert {key: value for key, value in process.items() if key != "stdout"} == {
            "exit_code": 0,
            "stderr": "",
            "stopped_by_runner": False,
            "stopped_by_scenario": False,
            "generation": 1,
            "stdout_complete": True,
            "stderr_complete": True,
        }
    assert recorded["sources"] == {
        "scenario": {
            "scenario.py": hashlib.sha256(
                Path("tests/rich_clipboard_scenario.py").read_bytes()
            ).hexdigest(),
            "fixture-variant.json": hashlib.sha256(
                json.dumps("clipboard-four-phases").encode()
            ).hexdigest(),
        },
        "bots/targets": {
            "bot.py": hashlib.sha256(
                Path("tests/fixtures/rich_targets_bot.py").read_bytes()
            ).hexdigest()
        },
    }
    output = process_json(recorded, "scenario")
    assert len(output) == 1
    scenario = output[0]
    assert scenario.keys() == {"variant", "phases", "final"}
    assert scenario["variant"] == "clipboard-four-phases"
    quiet = {
        "snapshot": EXPECTED_SNAPSHOT,
        "events": initial_events(),
        "history": initial_history(),
    }
    target_ids: set[str] = set()
    operation_ids: set[str] = set()
    identities = []
    assert len(scenario["phases"]) == 4
    clipboard: str | None = None
    for phase, (name, actions) in zip(scenario["phases"], EXPECTED_PHASES, strict=True):
        assert phase.keys() == {"name", "observation", "before", "observed", "actions", "after"}
        assert phase["name"] == name
        assert phase["before"] == phase["observed"] == phase["after"] == quiet
        observation = phase["observation"]
        assert_observation(observation, revision=5)
        new_ids = {target["target_id"] for target in observation["targets"]}
        assert target_ids.isdisjoint(new_ids)
        target_ids.update(new_ids)
        phase_identity = set()
        assert len(phase["actions"]) == len(actions)
        for action, (action_name, index, text) in zip(phase["actions"], actions, strict=True):
            assert action.keys() == {"name", "receipt", "before", "after"}
            assert action["name"] == action_name and action["before"] == action["after"] == quiet
            receipt = action["receipt"]
            assert receipt.keys() == {
                "operation_id",
                "target",
                "status",
                "dispatch",
                "effect",
                "reason",
                "evidence",
            }
            token(receipt["operation_id"])
            assert receipt["operation_id"] not in operation_ids
            operation_ids.add(receipt["operation_id"])
            assert receipt["target"] == expected_receipt_target(observation["targets"][index], 5)
            assert (
                receipt["status"] == "succeeded"
                and receipt["dispatch"] == "dispatched"
                and receipt["reason"] is None
            )
            disabled = action_name.endswith("disabled")
            assert receipt["effect"] == (
                {"kind": "none", "reason": "disabled"}
                if disabled
                else {"kind": "copy", "text": text}
            )
            pair = receipt["evidence"]["clipboard_observation"]
            assert type(pair) is dict and pair.keys() == {"before", "after"}
            # Across cold launches only the actual baseline is evidence; disabled pairs must
            # preserve this phase's established exact copy, not a previous phase's clipboard.
            assert pair["before"] is None or type(pair["before"]) is str
            assert pair["after"] == text
            if disabled:
                assert pair == {"before": text, "after": text}
            elif not native:
                assert pair["before"] == clipboard
            clipboard = text
            assert receipt["evidence"]["world_event_sequences"] == []
            if native:
                phase_identity.add(assert_native_evidence(directory, receipt, clipboard=pair))
            else:
                assert receipt["evidence"] == {
                    "mode": "simulation",
                    "world_event_sequences": [],
                    "clipboard_observation": pair,
                }
        if native:
            assert len(phase_identity) == 1
            identities.append(phase_identity.pop())
    assert len(target_ids) == 32 and len(operation_ids) == 6
    finish = ordinary_message(4, 2, "finish rich targets")
    history = [*initial_history(), finish]
    events = [*initial_events(), {"sequence": 7, "type": "message.created", "data": finish}]
    assert scenario["final"] == {
        "snapshot": EXPECTED_SNAPSHOT,
        "events": events,
        "history": history,
    }
    assert recorded["histories"] == {"1": history} and recorded["events"] == events
    actual = json.loads(json.dumps(semantic_state(directory / "world")))
    assert actual == {
        "snapshot": EXPECTED_SNAPSHOT,
        "histories": {"1": history},
        "events": events,
        "callbacks": [],
        "client_sends": [],
        "update_counters": [[1, 3]],
    }
    if native:
        database = sqlite3.connect(
            (directory / "world/world.sqlite3").as_uri() + "?mode=ro", uri=True
        )
        try:
            world_id = database.execute("SELECT world_id FROM configuration").fetchone()[0]
        finally:
            database.close()
        assert {identity[0] for identity in identities} == {world_id}
        assert (
            len({identity[1] for identity in identities})
            == len({identity[2] for identity in identities})
            == 4
        )
    bot = process_json(recorded, "bot:targets")
    assert len(bot) == 2 and bot[0] == {
        "event": "published",
        "primary": api_message(PRIMARY_MESSAGE),
        "unrelated": api_message(UNRELATED_MESSAGE),
    }
    assert bot[1].keys() == {"event", "callbacks", "api"}
    assert bot[1]["event"] == "finished" and bot[1]["callbacks"] == []
    assert_clipboard_exchange(bot[1]["api"])
    return scenario


def test_real_contained_clipboard_phases_have_exact_effects_and_quiet_state(
    tmp_path: Path, trace_runner: Any
) -> None:
    recorded = execute_clipboard(tmp_path / "project", native=False)
    assert_clipboard_endpoint(recorded, tmp_path / "simulation-only-run", native=False)
    # Mutate this real contained result, never generate or relabel native evidence.
    for defect in (
        "reused_targets",
        "extra_action",
        "wrong_copy",
        "wrong_disabled_baseline",
        "history_mutation",
    ):
        corrupted = copy.deepcopy(recorded)
        scenario = process_json(corrupted, "scenario")[0]
        phases = scenario["phases"]
        if defect == "reused_targets":
            phases[1]["observation"] = copy.deepcopy(phases[0]["observation"])
        elif defect == "extra_action":
            phases[2]["actions"].append(copy.deepcopy(phases[2]["actions"][0]))
        elif defect == "wrong_copy":
            phases[0]["actions"][0]["receipt"]["effect"]["text"] = "inline copied / درون"
        elif defect == "wrong_disabled_baseline":
            phases[3]["actions"][1]["receipt"]["evidence"]["clipboard_observation"] = {
                "before": "inline copied / درون",
                "after": "inline copied / درون",
            }
        else:
            phases[2]["actions"][0]["after"]["history"][1]["text"] = "unexpected edit"
        corrupted["processes"]["scenario"]["stdout"] = json.dumps(scenario)
        with pytest.raises(AssertionError):
            assert_clipboard_endpoint(corrupted, tmp_path / "simulation-only-run", native=False)
    api = process_json(recorded, "bot:targets")[-1]["api"]
    for defect in ("poll_before_publication", "wrong_offset", "callback_update", "extra_write"):
        corrupted_api = copy.deepcopy(api)
        if defect == "poll_before_publication":
            corrupted_api[1], corrupted_api[3] = corrupted_api[3], corrupted_api[1]
        elif defect == "wrong_offset":
            corrupted_api[3]["parameters"]["offset"] = 1
        elif defect == "callback_update":
            corrupted_api[-2]["body"]["result"] = [
                {"update_id": 2, "callback_query": {"data": "unexpected"}}
            ]
        else:
            corrupted_api.insert(-1, copy.deepcopy(corrupted_api[1]))
        with pytest.raises(AssertionError):
            assert_clipboard_exchange(corrupted_api)


@pytest.mark.android
@pytest.mark.usefixtures("clipboard_supervisor")
def test_public_native_rich_clipboard_paste_clear_and_disabled_preservation(tmp_path: Path) -> None:
    recorded = execute_clipboard(tmp_path / "project", native=True)
    directory = tmp_path / "headless-android-run"
    scenario = assert_clipboard_endpoint(recorded, directory, native=True)
    source = Path("tests/probes/rich_native_clipboard_supervisor.py").read_bytes()
    assert (directory / "rich_native_clipboard_supervisor.py").read_bytes() == source
    assert (directory / "clipboard-probe-source.sha256").read_text() == hashlib.sha256(
        source
    ).hexdigest()
    paths = list((directory / "clipboard-probes").glob("*/result.json"))
    assert len(paths) == 6
    quiet = {
        "snapshot": EXPECTED_SNAPSHOT,
        "histories": {"1": initial_history()},
        "events": initial_events(),
        "callbacks": [],
        "client_sends": [],
        "update_counters": [[1, 2]],
    }
    terminal_count = 0
    for phase_index, (phase, (_, actions)) in enumerate(
        zip(scenario["phases"], EXPECTED_PHASES, strict=True)
    ):
        for action, (name, _, text) in zip(phase["actions"], actions, strict=True):
            receipt = action["receipt"]
            operation = directory / "clipboard-probes" / receipt["operation_id"]
            evidence = json.loads((operation / "result.json").read_text())
            assert evidence["name"] == name and evidence["phase_index"] == phase_index
            assert (
                evidence["operation_id"] == receipt["operation_id"]
                and evidence["target"] == receipt["target"]
            )
            assert evidence["dispatch_result"] == {
                key: receipt[key] for key in ("status", "dispatch", "effect", "reason", "evidence")
            }
            assert evidence["status"] == "passed"
            assert evidence["action_before"] == evidence["action_after"] == quiet
            identity = assert_native_evidence(
                directory, receipt, clipboard=receipt["evidence"]["clipboard_observation"]
            )
            assert evidence["client_nonce"] == identity[2]
            terminal = not name.endswith("baseline")
            assert evidence["terminal"] is terminal
            if not terminal:
                assert {p.name for p in operation.iterdir()} == {"result.json"}
                assert (
                    not {"commands", "before", "after", "pasted_text", "cleared"} & evidence.keys()
                )
                continue
            terminal_count += 1
            assert evidence["ui_representation"] == "xml_with_redacted_attribute_and_text_values"
            assert evidence["pasted_text"] == text and evidence["cleared"] is True
            assert evidence["before"] == evidence["after"] == quiet
            commands = evidence["commands"]
            assert len(commands) <= 32
            inputs = [
                command["arguments"]
                for command in commands
                if command["arguments"][:2] == ["shell", "input"]
            ]
            keys = [
                ["shell", "input", "keyevent", "279"],
                ["shell", "input", "keyevent", "123"],
                ["shell", "input", "keyevent", *(["67"] * len(text))],
            ]
            if name == "row_disabled" and inputs[:1] == [["shell", "input", "keyevent", "4"]]:
                keys.insert(0, ["shell", "input", "keyevent", "4"])
                assert evidence["popup_back_issued"] is True
                assert evidence["popup_dismissed"] is True
            else:
                assert not {"popup_back_issued", "popup_dismissed"} & evidence.keys()
            assert inputs == keys
            assert {p.name for p in operation.iterdir()} == {
                "result.json",
                "empty.xml",
                "empty.png",
                "pasted.xml",
                "pasted.png",
                "cleared.xml",
                "cleared.png",
            }
            for stage, value in (("empty", "Message"), ("pasted", text), ("cleared", "Message")):
                assert composer((operation / f"{stage}.xml").read_text(), value)["text"] == value
                from PIL import Image

                with Image.open(operation / f"{stage}.png") as image:
                    assert image.format == "PNG" and image.size == (320, 640)
                    image.verify()
    assert terminal_count == 4


@pytest.fixture
def native_host(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AndroidRichInput:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(AndroidRichInput, "observe", AndroidRichInput.observe)
    monkeypatch.setattr(AndroidRichInput, "prepare", AndroidRichInput.prepare)
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
    prepared = {"control": "original preparation", "context": {"arm": {"client_nonce": "first"}}}
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
    monkeypatch.setattr(AndroidRichInput, "observe", lambda self, record: "first")
    monkeypatch.setattr(ClipboardProbe, "run", external_ui)
    install()
    assert native_host.observe({}) == "first"
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


@pytest.mark.parametrize("mode", ["returned", "raised", "missing", "oversized"])
def test_fresh_diagnostic_preserves_actual_frame_return_exception_and_existing_evidence(
    native_host: AndroidRichInput, monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    from probes.rich_native_clipboard_supervisor import install_fresh_diagnostic

    directory = Path("rich-buttons") / ("5" * 32)
    directory.mkdir(parents=True)
    state: dict[str, Any] = {
        "directory": directory,
        "arm": {"operation_id": "5" * 32, "chat_id": 1, "message_id": 2},
        "target": {"path": ["blocks", 16, "buttons", 1], "label": SECRET},
        "pid": 4321,
        "record": {"never_retained_world": "private World record"},
    }
    returned = {"original": "same object"}
    failure = ValueError("original failure " + SECRET)
    calls = 0

    def original(self: AndroidRichInput, actual: dict[str, Any]) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        assert actual is state
        if mode == "missing":
            raise failure
        sample: dict[str, Any] = {"generation": 37, "drawn_uptime_ms": 82603, "label": SECRET}
        if mode == "oversized":
            sample["padding"] = "x" * (256 * 1024)
        pid, now = 4321, 103000
        if mode == "returned":
            return returned
        assert pid == state["pid"] and now - int(sample["drawn_uptime_ms"]) > 5000
        raise failure

    monkeypatch.setattr(AndroidRichInput, "_fresh", original)
    install_fresh_diagnostic()
    path = directory / "fresh-failure.json"
    if mode == "returned":
        assert native_host._fresh(state) is returned
        assert calls == 1 and not path.exists()
        return
    with pytest.raises(ValueError) as caught:
        native_host._fresh(state)
    assert caught.value is failure and calls == 1
    raw = path.read_bytes()
    evidence = json.loads(raw)
    assert len(raw) <= 128 * 1024
    assert SECRET.encode() not in raw and b"private World record" not in raw
    assert evidence["operation_id"] == "5" * 32
    assert evidence["exception_class"] == "ValueError"
    assert evidence["source"] == {
        "file": Path(original.__code__.co_filename).name,
        "sha256": hashlib.sha256(Path(original.__code__.co_filename).read_bytes()).hexdigest(),
    }
    traceback = caught.value.__traceback__
    while traceback is not None and traceback.tb_frame.f_code is not original.__code__:
        traceback = traceback.tb_next
    assert traceback is not None and evidence["line"] == traceback.tb_lineno
    if mode == "oversized":
        assert evidence["details_omitted"] == "record_exceeds_bound"
    elif mode == "missing":
        assert evidence["locals"] == {}
        assert evidence["missing_locals"] == ["sample", "pid", "now"]
    else:
        assert evidence["locals"] == {
            "sample": {"generation": 37, "drawn_uptime_ms": 82603, "label": "[REDACTED]"},
            "pid": 4321,
            "now": 103000,
        }
        assert evidence["missing_locals"] == []
        assert evidence["state"]["target"]["label"] == "[REDACTED]"
        assert "record" not in evidence["state"]
    with pytest.raises(ValueError) as repeated:
        native_host._fresh(state)
    assert repeated.value is failure and calls == 2 and path.read_bytes() == raw


@pytest.mark.parametrize("fault", [None, "same_lifetime", "wrong_order", "baseline_mutation"])
def test_four_phases_keep_baselines_unprobed_and_reject_invalid_progression(
    native_host: AndroidRichInput, monkeypatch: pytest.MonkeyPatch, fault: str | None
) -> None:
    # Only native observation/dispatch/UI evidence is substituted; World/retention are real.
    phase = 0
    probes: list[str] = []
    outcomes: list[dict[str, Any]] = []
    plan = [
        [("row_copy", ["blocks", 16, "buttons", 1], "row copied / ردیف")],
        [("inline_copy", ["blocks", 17, "text", 1, "text", 2, "button"], "inline copied / درون")],
        [
            (
                "inline_baseline",
                ["blocks", 17, "text", 1, "text", 2, "button"],
                "inline copied / درون",
            ),
            ("inline_disabled", ["blocks", 17, "text", 2, "button"], "inline copied / درون"),
        ],
        [
            ("row_baseline", ["blocks", 16, "buttons", 1], "row copied / ردیف"),
            ("row_disabled", ["blocks", 16, "buttons", 2], "row copied / ردیف"),
        ],
    ]

    def observation(self: AndroidRichInput, record: dict[str, Any]) -> str:
        return "lifetime-0" if fault == "same_lifetime" else f"lifetime-{phase}"

    def original(
        self: AndroidRichInput, receipt: dict[str, Any], prepared: dict[str, Any]
    ) -> dict[str, Any]:
        if fault == "baseline_mutation" and len(outcomes) == 2:
            with World.open(Path("world")) as world:
                world.send_message(chat_id=1, sender_id=1, text="unexpected baseline send")
        return prepared["outcome"]  # type: ignore[no-any-return]

    def external_ui(self: ClipboardProbe, name: str, expected: str) -> None:
        probes.append(name)
        self.record.update(pasted_text=expected, cleared=True)

    monkeypatch.setattr(AndroidRichInput, "observe", observation)
    monkeypatch.setattr(AndroidRichInput, "dispatch", original)
    monkeypatch.setattr(ClipboardProbe, "run", external_ui)
    install()
    for phase, actions in enumerate(plan):
        if fault == "same_lifetime" and phase == 1:
            with pytest.raises(ValueError):
                native_host.observe({})
            break
        lifetime = native_host.observe({})
        for name, path, expected in actions:
            receipt: dict[str, Any] = {
                "operation_id": f"{len(outcomes) + 1:032x}",
                "target": {"path": path},
            }
            if fault == "wrong_order":
                receipt["target"]["path"] = ["blocks", 16, "buttons", 2]
            result = {
                "status": "succeeded",
                "dispatch": "dispatched",
                "reason": None,
                "effect": {"kind": "none", "reason": "disabled"}
                if name.endswith("disabled")
                else {"kind": "copy", "text": expected},
                "evidence": {},
            }
            prepared = {"outcome": result, "context": {"arm": {"client_nonce": lifetime}}}
            assert native_host.dispatch(receipt, prepared) is result
            evidence = json.loads(
                Path("clipboard-probes", receipt["operation_id"], "result.json").read_text()
            )
            failed = fault == "wrong_order" or (
                fault == "baseline_mutation" and name == "inline_baseline"
            )
            assert evidence["status"] == ("failed" if failed else "passed")
            if failed:
                with pytest.raises(ValueError):
                    native_host.observe({})
                return
            assert evidence["name"] == name
            assert evidence["terminal"] is (not name.endswith("baseline"))
            assert evidence["action_before"] == evidence["action_after"]
            if name.endswith("baseline"):
                assert "commands" not in evidence and "pasted_text" not in evidence
            outcomes.append(result)
    if fault is None:
        assert len(outcomes) == 6
        assert probes == ["row_copy", "inline_copy", "inline_disabled", "row_disabled"]


def test_original_observation_failure_is_not_retried(
    native_host: AndroidRichInput, monkeypatch: pytest.MonkeyPatch
) -> None:
    failure = RuntimeError("Original observation failure")
    calls = 0

    def original(self: AndroidRichInput, record: dict[str, Any]) -> str:
        nonlocal calls
        calls += 1
        raise failure

    monkeypatch.setattr(AndroidRichInput, "observe", original)
    monkeypatch.setattr(AndroidRichInput, "dispatch", AndroidRichInput.dispatch)
    install()
    with pytest.raises(RuntimeError) as raised:
        native_host.observe({})
    assert raised.value is failure and calls == 1
    with pytest.raises(ValueError):
        native_host.observe({})
    assert calls == 1


@pytest.mark.parametrize("mode", ["returned", "raised", "missing", "oversized"])
def test_prepare_diagnostic_retains_actual_pending_frame_without_changing_outcome(
    native_host: AndroidRichInput, monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    from probes.rich_native_clipboard_supervisor import install_fresh_diagnostic

    directory = Path("rich-buttons") / ("6" * 32)
    directory.mkdir(parents=True)
    failure = ValueError("Original prepare failure " + SECRET)
    returned: dict[str, Any] = {"context": "original object"}
    receipt: dict[str, Any] = {"operation_id": "6" * 32}
    calls = 0

    def original(
        self: AndroidRichInput, actual: dict[str, Any], *, client_nonce: str
    ) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        assert actual is receipt and client_nonce == "actual-client"
        state: dict[str, Any] = {
            "directory": directory,
            "arm": {"operation_id": actual["operation_id"]},
            "target": {"label": SECRET},
            "record": {"must_not_retain": "private World"},
        }
        if mode == "missing":
            raise failure
        sample = {"generation": 5, "available": True}
        pending = {"operation_id": "previous-operation", "private": SECRET}
        if mode == "oversized":
            pending["padding"] = "x" * (256 * 1024)
        effect = None
        if mode == "returned":
            return returned
        assert (
            state["arm"]["operation_id"] == actual["operation_id"]
            and sample["available"]
            and effect is None
        )
        raise failure

    monkeypatch.setattr(AndroidRichInput, "prepare", original)
    monkeypatch.setattr(AndroidRichInput, "_fresh", AndroidRichInput._fresh)
    install_fresh_diagnostic()
    path = directory / "prepare-failure.json"
    if mode == "returned":
        assert native_host.prepare(receipt, client_nonce="actual-client") is returned
        assert calls == 1 and not path.exists()
        return
    with pytest.raises(ValueError) as caught:
        native_host.prepare(receipt, client_nonce="actual-client")
    assert caught.value is failure and calls == 1
    raw = path.read_bytes()
    assert len(raw) <= 128 * 1024 and SECRET.encode() not in raw and b"private World" not in raw
    evidence = json.loads(raw)
    assert evidence["source"] == {
        "file": Path(original.__code__.co_filename).name,
        "sha256": hashlib.sha256(Path(original.__code__.co_filename).read_bytes()).hexdigest(),
    }
    cursor = caught.value.__traceback__
    while cursor is not None and cursor.tb_frame.f_code is not original.__code__:
        cursor = cursor.tb_next
    assert cursor is not None and evidence["line"] == cursor.tb_lineno
    assert evidence["operation_id"] == receipt["operation_id"]
    if mode == "missing":
        assert evidence["locals"] == {} and evidence["missing_locals"] == [
            "sample",
            "pending",
            "effect",
        ]
    elif mode == "oversized":
        assert evidence["details_omitted"] == "record_exceeds_bound"
    else:
        assert evidence["locals"] == {
            "sample": {"generation": 5, "available": True},
            "pending": {"operation_id": "previous-operation", "private": "[REDACTED]"},
            "effect": None,
        }
        assert evidence["state"]["target"] == {"label": "[REDACTED]"}
    with pytest.raises(ValueError) as repeated:
        native_host.prepare(receipt, client_nonce="actual-client")
    assert repeated.value is failure and calls == 2 and path.read_bytes() == raw


@pytest.mark.parametrize(
    "mode",
    [
        "native06_prefix",
        "immediate",
        "settles",
        "persistent",
        "deadline",
        "budget",
        "wrong_pid",
        "unrelated",
        "ambiguous",
        "different_popup",
    ],
)
def test_popup_settling_replays_native_prefix_and_never_retries_input(
    native_host: AndroidRichInput, monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    # Native06 op699e6d9dba6c4345a26645a83a8caf6a retained result SHA256:
    # bc0ad7a495e9e160254cd81668c5ebc6b44ddb92f901cf9d665f1b5f13ed9b69.
    # These are exact focus/PID projections of its six rc0 commands. Later transitions
    # are independently scheduled external controls, not a claim about that guest's future.
    popup = (
        "  mCurrentFocus=Window{d7a2043 u0 PopupWindow:cbc808}\n"
        "  mFocusedApp=ActivityRecord{211137882 u0 "
        "org.gramlab.android/org.telegram.ui.LaunchActivity t11}\n"
    )
    chat = "mCurrentFocus=Window{d7ef034 u0 org.gramlab.android/org.telegram.ui.LaunchActivity}\n"
    focus = ("shell", "dumpsys", "window", "displays")
    pid = ("shell", "pidof", "org.gramlab.android")
    back = ("shell", "input", "keyevent", "4")
    calls: list[tuple[tuple[str, ...], str]] = []
    captures: list[str] = []
    ownership: list[tuple[tuple[str, str, str], int]] = []
    sent_back = False
    polls = 0

    def external_adb(*arguments: str) -> subprocess.CompletedProcess[str]:
        nonlocal sent_back, polls
        output = ""
        if arguments == focus:
            if sent_back:
                polls += 1
            output = popup
            if sent_back and (
                mode in {"immediate", "wrong_pid"} or (mode == "settles" and polls > 1)
            ):
                output = chat
            elif sent_back and mode == "unrelated":
                output = "mCurrentFocus=Window{abcd u0 other.application/Activity}\n"
            elif sent_back and mode == "ambiguous":
                output = popup + chat
            elif sent_back and mode == "different_popup":
                output = popup.replace("d7a2043", "abcd")
        elif arguments == pid:
            output = "9999\n" if sent_back and mode == "wrong_pid" else "3722\n"
        elif arguments == back:
            assert not sent_back
            sent_back = True
        else:
            assert mode in {"immediate", "settles"}
            assert arguments[:3] == ("shell", "input", "keyevent")
        calls.append((arguments, output))
        if (mode == "native06_prefix" and sent_back and arguments == focus) or (
            mode == "deadline" and sent_back and arguments == pid
        ):
            native_host.android.deadline = time.monotonic() - 1
        return subprocess.CompletedProcess(arguments, 0, stdout=output, stderr="")

    def external_ownership(focused: tuple[str, str, str], process: int) -> None:
        # The host ownership validator's independent suite owns PID/UID/parent/surface evidence.
        ownership.append((focused, process))

    class ExternalCapture(ClipboardProbe):
        def capture(self, phase: str, expected: str) -> None:
            captures.append(phase)
            composer(editor(expected), expected)

    monkeypatch.setattr(native_host.android, "_adb", external_adb)
    monkeypatch.setattr(native_host, "_owned_popup", external_ownership)
    probe = ExternalCapture(native_host, Path.cwd(), {"operation_id": "7" * 32})
    initial_calls = 24 if mode == "budget" else 0
    probe.calls = initial_calls
    if mode in {"immediate", "settles"}:
        probe.run("row_disabled", "row copied / ردیف")
        assert captures == ["empty", "pasted", "cleared"]
        assert probe.record["popup_dismissed"] is True
        assert probe.record["cleared"] is True
    else:
        failure = TimeoutError if mode in {"native06_prefix", "deadline"} else ValueError
        with pytest.raises(failure):
            probe.run("row_disabled", "row copied / ردیف")
        assert captures == []
        assert "popup_dismissed" not in probe.record
        assert "cleared" not in probe.record
    assert probe.record["popup_back_issued"] is True
    assert ownership == [(("d7a2043", "0", "PopupWindow:cbc808"), 3722)]
    assert calls[:5] == [
        (focus, popup),
        (pid, "3722\n"),
        (pid, "3722\n"),
        (focus, popup),
        (back, ""),
    ]
    if mode == "native06_prefix":
        assert calls == [*calls[:5], (focus, popup)]
    if mode in {"unrelated", "ambiguous", "different_popup"}:
        assert len(calls) == 6
    if mode == "wrong_pid":
        assert calls[5:] == [(focus, chat), (pid, "9999\n")]
    if mode == "settles":
        assert [value for arguments, value in calls if arguments == focus] == [
            popup,
            popup,
            popup,
            chat,
        ]
    assert sum(arguments == back for arguments, _ in calls) == 1
    inputs = [arguments for arguments, _ in calls if arguments[:2] == ("shell", "input")]
    assert inputs == (
        [
            back,
            ("shell", "input", "keyevent", "279"),
            ("shell", "input", "keyevent", "123"),
            ("shell", "input", "keyevent", *(["67"] * len("row copied / ردیف"))),
        ]
        if mode in {"immediate", "settles"}
        else [back]
    )
    assert probe.calls == len(calls) + initial_calls <= 32
    if mode in {"persistent", "budget"}:
        assert probe.calls == 32
