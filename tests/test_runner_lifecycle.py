"""Real consumer bot generations recover pending updates across explicit scenario faults."""

import json
import os
from pathlib import Path

import pytest
from test_runner import invoke

from gramlab.runner import run
from gramlab.runtime import RuntimeProfile


def recovery_project(directory: Path) -> Path:
    directory.mkdir()
    for name in ("run.toml", "bot.py", "scenario.py"):
        (directory / name).write_bytes((Path("examples/recovery") / name).read_bytes())
    return directory / "run.toml"


@pytest.mark.parametrize("entrypoint", ["cli", "python"])
def test_consumer_restarts_a_bot_after_unacknowledged_callback_receipt(
    tmp_path: Path, trace_runner, entrypoint: str
):
    manifest = recovery_project(tmp_path / "project")
    output = tmp_path / "run"
    if entrypoint == "cli":
        result = invoke(manifest, output)
        assert result.returncode == 0, (output / "result.json").read_text()
    else:
        assert (
            run(
                manifest,
                output,
                profile=RuntimeProfile.load(Path(os.environ["GRAMLAB_RUNTIME_PROFILE"])),
            )
            == "passed"
        ), (output / "result.json").read_text()
    recorded = json.loads((output / "result.json").read_text())
    assert recorded["outcome"] == "passed"
    assert [record["operation"] for record in recorded["lifecycle"]] == ["stop_bot", "start_bot"]
    assert [record["result"]["generation"] for record in recorded["lifecycle"]] == [1, 2]
    assert recorded["histories"]["1"] == [
        {"id": 1, "chat_id": 1, "sender_id": 2, "date": 1700000000, "text": "سلام hello"},
        {
            "id": 2,
            "chat_id": 1,
            "sender_id": 1,
            "date": 1700000000,
            "edit_date": 1700000000,
            "text": "Recovered — بازیابی شد ✓",
        },
        {
            "id": 3,
            "chat_id": 1,
            "sender_id": 1,
            "date": 1700000000,
            "text": "Callback received; restart me",
        },
    ]
    first = recorded["processes"]["bot:recovery"]
    second = recorded["processes"]["bot:recovery#2"]
    assert first["stopped_by_scenario"] and not first["stopped_by_runner"]
    assert first["exit_code"] != 0
    assert "Bot generation 1" in first["stdout"]
    assert "Bot generation 2" in second["stdout"]
    assert first["stdout_complete"] and first["stderr_complete"]
    assert second["stopped_by_runner"]
    assert "Bot lifecycle" in (output / "report.html").read_text()


def test_generation_guards_and_descendant_cleanup_survive_concurrent_stops(tmp_path: Path):
    manifest = recovery_project(tmp_path / "project")
    bot = manifest.parent / "bot.py"
    bot.write_text(
        """import fcntl
import signal
lock = open("generation.lock", "a")
fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
import os
reader, writer = os.pipe()
if os.fork() == 0:
    os.close(reader)
    os.setsid()
    os.write(writer, b"ready")
    os.close(writer)
    while True:
        signal.pause()
os.close(writer)
if os.read(reader, 5) != b"ready":
    raise RuntimeError("Detached child did not acquire the inherited generation lock")
os.close(reader)
"""
        + bot.read_text()
    )
    scenario = manifest.parent / "scenario.py"
    source = scenario.read_text().replace(
        "stopped = lab.stop_bot",
        """from gramlab.scenario import ScenarioError
for operation, arguments in (
    (lab.bot_status, {"name": "scenario"}),
    (lab.stop_bot, {"name": "../recovery", "generation": 1}),
    (lab.stop_bot, {"name": "recovery", "generation": True}),
    (lab.stop_bot, {"name": "recovery", "generation": 2}),
    (lab.start_bot, {"name": "recovery", "generation": 1}),
):
    try:
        operation(**arguments)
    except ScenarioError as error:
        assert error.code == "invalid_request" and not error.outcome_uncertain
    else:
        raise AssertionError("Invalid lifecycle request accepted")
assert lab.bot_status("recovery") == status
stopped = lab.stop_bot""",
    )
    source += """
try:
    lab.stop_bot("recovery", generation=1)
except ScenarioError as error:
    assert error.code == "invalid_request" and not error.outcome_uncertain
else:
    raise AssertionError("Stale stop killed replacement generation")
assert lab.bot_status("recovery")["generation"] == 2
from concurrent.futures import ThreadPoolExecutor
import threading
barrier = threading.Barrier(2)
def stop():
    barrier.wait(timeout=5)
    try:
        return lab.stop_bot("recovery", generation=2)
    except ScenarioError as error:
        assert error.code == "invalid_request" and not error.outcome_uncertain
        return None
with ThreadPoolExecutor(max_workers=2) as actors:
    futures = [actors.submit(stop) for _ in range(2)]
    results = [future.result(timeout=15) for future in futures]
assert sum(result is not None for result in results) == 1
assert lab.bot_status("recovery")["state"] == "stopped"
"""
    scenario.write_text(source)
    output = tmp_path / "run"
    result = invoke(manifest, output)
    recorded = json.loads((output / "result.json").read_text())
    assert result.returncode == 0, recorded
    assert [event["operation"] for event in recorded["lifecycle"]] == [
        "stop_bot",
        "start_bot",
        "stop_bot",
    ]
    assert json.loads((output / "bots/recovery/state.json").read_text())["generation"] == 2
    for key in ("bot:recovery", "bot:recovery#2"):
        assert recorded["processes"][key]["stopped_by_scenario"]
        assert recorded["processes"][key]["stdout_complete"]
        assert recorded["processes"][key]["stderr_complete"]


def test_restarts_share_the_run_log_budget(tmp_path: Path):
    manifest = recovery_project(tmp_path / "project")
    bot = manifest.parent / "bot.py"
    source = Path("examples/echo/bot.py").read_text().split("offset = 0")[0]
    source += """updates = call("getUpdates", {"timeout": 30})
print("x" * 800000, end="", flush=True)
call("sendMessage", {"chat_id": updates[0]["message"]["chat"]["id"], "text": "Ready"})
import time
while True:
    time.sleep(60)
"""
    bot.write_text(source)
    (manifest.parent / "scenario.py").write_text("""import time
from gramlab.scenario import Scenario
lab = Scenario.from_environment()
user = lab.create_user(first_name="Sara")
chat = lab.open_private_chat(user_id=user["id"], bot_id=lab.bots()["recovery"])
lab.send_message(chat_id=chat["id"], sender_id=user["id"], text="Ready")
for generation in range(1, 5):
    while len(lab.history(chat["id"])) != generation + 1:
        time.sleep(0.02)
    lab.stop_bot("recovery", generation=generation)
    lab.start_bot("recovery", generation=generation)
""")
    output = tmp_path / "run"
    result = invoke(manifest, output)
    recorded = json.loads((output / "result.json").read_text())
    assert result.returncode == 1 and recorded["failure"] == "output_limit", recorded
    assert (
        sum(
            len(record[stream].encode())
            for record in recorded["processes"].values()
            for stream in ("stdout", "stderr")
        )
        == 2 * 1024 * 1024
    )
    assert len(recorded["processes"]["bot:recovery"]["stdout"]) == 800000
    assert len(recorded["processes"]["bot:recovery#2"]["stdout"]) == 800000
    assert "bot:recovery#3" in recorded["processes"]
    assert "bot:recovery#4" not in recorded["processes"]
