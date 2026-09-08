"""Public runner recovery survives actual supervisor death at durable IO boundaries."""

import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any

import pytest

from gramlab.runner import run
from gramlab.runtime import RuntimeProfile, Sandbox


@pytest.mark.parametrize(
    "phase", ["observation", "claim", "intent", "receipt", "corrupt", "nested_corrupt"]
)
def test_runner_retains_offline_recovery_after_abrupt_supervisor_exit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, phase: str
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    manifest = project / "run.toml"
    manifest.write_text(
        'schema = 1\nmode = "simulation-only"\nseed = 41\nnow = 1700000000\ntimeout = 15\n'
        '[scenario]\nentry = "scenario.py"\nfiles = ["scenario.py", "fixture-variant.json"]\n'
        '[bots.targets]\nentry = "bot.py"\nfiles = ["bot.py"]\n'
    )
    (project / "scenario.py").write_bytes(Path("tests/rich_targets_scenario.py").read_bytes())
    (project / "bot.py").write_bytes(Path("tests/fixtures/rich_targets_bot.py").read_bytes())
    (project / "fixture-variant.json").write_text(json.dumps("full"))
    bootstrap = Path("tests/probes/rich_button_interruption.py").read_bytes()
    original = Sandbox.supervise
    terminated_journal: list[bytes] = []

    def interrupt(
        self: Sandbox, command: list[str], *, data: Path, timeout: float = 30, kvm: bool = False
    ) -> subprocess.CompletedProcess[str]:
        assert command == [self.profile.python, "-m", "gramlab._run"]
        (data / "rich_button_interruption.py").write_bytes(bootstrap)
        result = original(
            self,
            [self.profile.python, "/work/rich_button_interruption.py", phase],
            data=data,
            timeout=timeout,
            kvm=kvm,
        )
        assert result.returncode == 71, (result.returncode, result.stderr)
        terminated_journal.append((data / "rich-button-journal.jsonl").read_bytes())
        return result

    monkeypatch.setattr(Sandbox, "supervise", interrupt)
    output = tmp_path / "run"
    assert (
        run(
            manifest,
            output,
            profile=RuntimeProfile.load(Path(os.environ["GRAMLAB_RUNTIME_PROFILE"])),
        )
        == "failed"
    )
    recorded = json.loads((output / "result.json").read_text())
    assert recorded["failure"] == "supervisor_failed"
    assert not (output / "observation.json").exists()
    assert (output / "rich-button-journal.jsonl").read_bytes() == terminated_journal[0]
    assert json.loads((output / "interruption.json").read_text())["phase"] == phase
    assert (output / "report.html").is_file()
    callback_events = [event for event in recorded["events"] if event["type"] == "callback.created"]
    if phase in {"corrupt", "nested_corrupt"}:
        assert recorded["rich_button_recovery"] == {
            "artifact": None,
            "failure": "invalid_or_unreadable_journal",
        }
        assert not (output / "rich-button-recovery.json").exists()
        assert callback_events == []
        return
    assert recorded["rich_button_recovery"] == {
        "artifact": "rich-button-recovery.json",
        "failure": None,
    }
    recovery = json.loads((output / "rich-button-recovery.json").read_text())
    assert recovery.keys() == {
        "schema",
        "run_id",
        "world_id",
        "incomplete_tail",
        "receipts",
        "unclaimed_target_ids",
    }
    assert recovery["schema"] == 1
    assert recovery["world_id"] == recorded["run_id"]
    assert recovery["incomplete_tail"] is False
    if phase == "observation":
        assert recovery["receipts"] == []
        assert len(recovery["unclaimed_target_ids"]) == 8
        assert callback_events == []
        return
    assert len(recovery["receipts"]) == 1
    assert len(recovery["unclaimed_target_ids"]) == 7
    receipt: dict[str, Any] = recovery["receipts"][0]
    assert receipt["target"] == {
        "target_id": receipt["target"]["target_id"],
        "chat_id": 1,
        "message_id": 2,
        "message_revision": 5,
        "path": ["blocks", 16, "buttons", 0],
        "button": {"text": "Same / همان", "callback_data": "same:payload"},
        "label": "Same / همان",
    }
    if phase == "receipt":
        assert receipt["status"] == "succeeded"
        assert receipt["dispatch"] == "dispatched"
        assert receipt["reason"] is None
        assert len(callback_events) == 1
        callback = callback_events[0]["data"] | {"answer": None}
        assert (
            callback["chat_instance"]
            == hashlib.sha256(f"{recorded['run_id']}:1".encode()).hexdigest()
        )
        assert receipt["effect"] == {"kind": "callback", "callback": callback, "event_sequence": 7}
    else:
        assert receipt["status"] == (
            "rejected_before_dispatch" if phase == "claim" else "uncertain"
        )
        assert receipt["dispatch"] == ("not_dispatched" if phase == "claim" else "intent_recorded")
        assert receipt["reason"] == {"code": "component_stopped"}
        assert receipt["effect"] is None
        assert callback_events == []
