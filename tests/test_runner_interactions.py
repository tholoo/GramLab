"""Consumer inline input selects a real bot keyboard and preserves callback semantics."""

import json
import os
from pathlib import Path

import pytest
from test_runner import invoke

from gramlab.runner import run
from gramlab.runtime import RuntimeProfile


def inline_project(directory: Path) -> Path:
    directory.mkdir()
    for name in ("run.toml", "bot.py", "scenario.py"):
        (directory / name).write_bytes((Path("examples/inline") / name).read_bytes())
    return directory / "run.toml"


@pytest.mark.parametrize("entrypoint", ["cli", "python"])
def test_inline_selection_drives_bot_edit_and_rejects_invalid_targets(
    tmp_path: Path, trace_runner, entrypoint: str
):
    manifest = inline_project(tmp_path / "project")
    scenario = manifest.parent / "scenario.py"
    source = scenario.read_text()
    source = source.replace(
        "callback = message.inline_button(1, 0).tap().callback",
        """from gramlab.scenario import ScenarioError
before = lab.events()
for arguments in (
    {"chat_id": 999, "message_id": message.id, "row": 1, "column": 0},
    {"chat_id": chat.id, "message_id": 1, "row": 0, "column": 0},
    {"chat_id": chat.id, "message_id": message.id, "row": -1, "column": 0},
    {"chat_id": chat.id, "message_id": message.id, "row": True, "column": 0},
    {"chat_id": chat.id, "message_id": message.id, "row": 1, "column": 1},
):
    try:
        lab.tap_inline_button(**arguments)
    except ScenarioError as error:
        assert error.code == "invalid_request" and not error.outcome_uncertain
    else:
        raise AssertionError("Invalid target accepted")
assert lab.events() == before
callback = message.inline_button(1, 0).tap().callback""",
    )
    source += """
try:
    lab.tap_inline_button(chat_id=chat.id, message_id=message.id, row=1, column=0)
except ScenarioError as error:
    assert error.code == "invalid_request" and not error.outcome_uncertain
else:
    raise AssertionError("Removed keyboard accepted")
"""
    scenario.write_text(source)
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
    assert len(recorded["interactions"]) == 1
    interaction = recorded["interactions"][0]
    assert {
        key: interaction[key] for key in ("chat_id", "message_id", "row", "column", "native")
    } == {
        "chat_id": 1,
        "message_id": 2,
        "row": 1,
        "column": 0,
        "native": False,
    }
    assert interaction["callback"]["data"] == "confirm"
    assert len([event for event in recorded["events"] if event["type"] == "callback.created"]) == 1
    assert recorded["histories"]["1"][1]["text"] == "Selected: confirm ✓"
    assert "Scenario interactions" in (output / "report.html").read_text()


def test_lost_inline_response_does_not_repeat_the_callback(tmp_path: Path):
    import http.client
    import threading
    from http.server import BaseHTTPRequestHandler
    from urllib.parse import urlsplit

    from test_scenario_client import serve

    from gramlab._control import WorldControl
    from gramlab._interactions import Interactions
    from gramlab.scenario import Scenario, ScenarioError
    from gramlab.world import World

    directory = tmp_path / "world"
    with World.create(directory, seed=7, now=100) as world:
        world.create_user(first_name="Sara")
        world.create_user(first_name="Bot", is_bot=True)
        world.open_private_chat(user_id=1, bot_id=2)
        message = world.send_message(
            chat_id=1,
            sender_id=2,
            text="Choose",
            reply_markup={
                "inline_keyboard": [[{"text": "Confirm", "callback_data": "confirm"}]],
            },
        )
    interactions = Interactions(directory, lock=threading.Lock())
    forwarded = []
    with WorldControl(directory, tap_inline_button=interactions.tap_inline_button) as control:
        target = urlsplit(control.base_url)

        class DropAfterCommit(BaseHTTPRequestHandler):
            def do_POST(self):
                payload = self.rfile.read(int(self.headers["Content-Length"]))
                connection = http.client.HTTPConnection(target.hostname, target.port, timeout=5)
                try:
                    connection.request(
                        "POST",
                        "/v1/world",
                        payload,
                        {
                            "Content-Type": "application/json",
                            "Authorization": self.headers["Authorization"],
                        },
                    )
                    response = connection.getresponse()
                    forwarded.append((response.status, json.loads(response.read())))
                finally:
                    connection.close()
                # Intentionally drop the response after the real world mutation committed.

            def log_message(self, *args):
                pass

        with serve(DropAfterCommit) as endpoint:
            lab = Scenario(endpoint, capability=control.capability, world_id=control.world_id)
            with pytest.raises(ScenarioError) as failure:
                lab.tap_inline_button(chat_id=1, message_id=1, row=0, column=0)
        assert failure.value.code == "transport_error" and failure.value.outcome_uncertain
        assert failure.value.operation == "tap_inline_button"
    with World.open(directory) as world:
        callbacks = [
            event["data"] for event in world.events() if event["type"] == "callback.created"
        ]
        assert len(callbacks) == 1
        assert callbacks[0]["message"] == message and callbacks[0]["data"] == "confirm"
        assert world.poll_updates(2) == [{"update_id": 1, "callback_query": callbacks[0]}]
    assert len(forwarded) == 1 and forwarded[0][0] == 200
    assert forwarded[0][1]["result"]["callback"] == callbacks[0] | {"answer": None}
    assert len(interactions.records) == 1


def test_concurrent_inline_actions_have_distinct_callbacks_and_a_shared_limit(tmp_path: Path):
    import threading
    from concurrent.futures import ThreadPoolExecutor

    from gramlab._control import WorldControl
    from gramlab._interactions import Interactions
    from gramlab.scenario import Scenario, ScenarioError
    from gramlab.world import World

    directory = tmp_path / "world"
    with World.create(directory, seed=7, now=100) as world:
        world.create_user(first_name="Sara")
        world.create_user(first_name="Bot", is_bot=True)
        world.open_private_chat(user_id=1, bot_id=2)
        message = world.send_message(
            chat_id=1,
            sender_id=2,
            text="Choose",
            reply_markup={
                "inline_keyboard": [[{"text": "Confirm", "callback_data": "confirm"}]],
            },
        )
    interactions = Interactions(directory, lock=threading.Lock())
    with WorldControl(directory, tap_inline_button=interactions.tap_inline_button) as control:
        lab = Scenario(control.base_url, capability=control.capability, world_id=control.world_id)
        ready = threading.Barrier(4)

        def actor():
            ready.wait(timeout=5)
            return [
                lab.tap_inline_button(chat_id=1, message_id=1, row=0, column=0) for _ in range(16)
            ]

        with ThreadPoolExecutor(max_workers=4) as workers:
            futures = [workers.submit(actor) for _ in range(4)]
            results = [record for future in futures for record in future.result(timeout=15)]
        with pytest.raises(ScenarioError) as failure:
            lab.tap_inline_button(chat_id=1, message_id=1, row=0, column=0)
        assert failure.value.code == "invalid_request" and not failure.value.outcome_uncertain
    callbacks = [record["callback"] for record in results]
    assert len({callback["id"] for callback in callbacks}) == 64
    for callback in callbacks:
        assert callback["data"] == "confirm" and callback["message"] == message
        assert callback["user_id"] == 1 and callback["answer"] is None
    with World.open(directory) as world:
        updates = world.poll_updates(2)
        assert [update["update_id"] for update in updates] == list(range(1, 65))
        assert {update["callback_query"]["id"] for update in updates} == {
            callback["id"] for callback in callbacks
        }
    assert len(interactions.records) == 64
