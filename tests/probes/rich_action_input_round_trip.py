"""Real bot controller; simulation explicitly creates callbacks, native mode only observes."""

import json
import selectors
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from component_bot import FixtureBot

from gramlab.bot_api import BotAPIServer
from gramlab.client_bridge import ClientBridge
from gramlab.world import World


def before_action(index: int) -> dict[str, Any]:
    expected = json.loads(Path("action-expected.json").read_text())
    with World.open(Path("world")) as world:
        events = world.events()
        created = [event["data"] for event in events if event["type"] == "callback.created"]
        answered = [event for event in events if event["type"] == "callback.answered"]
        if len(created) != index or len(answered) != index:
            raise RuntimeError("Unexpected callback count before ordinary input")
        message = world.get_message(1, 2)
        if message != expected["world_initial"]:
            raise RuntimeError("Rich action content changed before ordinary input")
        now = world.advance_time(5)
        return {
            "world_id": world.world_id,
            "message": message,
            "now": now,
            "previous_callbacks": created,
        }


def wait_answer(index: int) -> dict[str, Any]:
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        with World.open(Path("world")) as world:
            events = world.events()
            created = [event["data"] for event in events if event["type"] == "callback.created"]
            if len(created) > index + 1:
                raise RuntimeError("Unexpected extra native callbacks")
            if len(created) == index + 1:
                callback = world.get_callback(user_id=1, callback_id=created[index]["id"])
                if callback["answer"] is not None and world.poll_updates(2) == []:
                    return callback
        time.sleep(0.05)
    raise RuntimeError("Real bot did not answer the single input; input is never retried")


def run(
    show: Callable[[dict[str, Any]], str] | None = None,
    observe: Callable[[], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    directory = Path("world")
    with World.create(directory, seed=19, now=1700000000) as world:
        world.create_user(first_name="Sara", language_code="en")
        world.create_user(first_name="Echo", username="gramlab_echo_bot", is_bot=True)
        world.open_private_chat(user_id=1, bot_id=2)
        world.send_message(chat_id=1, sender_id=1, text="Show rich actions")
        token, capability = world.issue_bot_token(2), world.issue_client_token(1)
        world_id = world.world_id
    client: dict[str, Any] = {}
    with BotAPIServer(directory) as server, ClientBridge(directory) as bridge:
        with FixtureBot("rich_action_input_bot.py").start(
            {"GRAMLAB_BOT_API": server.base_url, "GRAMLAB_BOT_TOKEN": token}
        ) as bot:
            assert bot.stdout is not None
            with selectors.DefaultSelector() as ready:
                ready.register(bot.stdout, selectors.EVENT_READ)
                if not ready.select(timeout=10):
                    raise RuntimeError("Real bot did not send its action message")
            first = bot.stdout.readline()
            if not first:
                raise RuntimeError("Real action bot exited before the initial message")
            initial = json.loads(first)
            if show is None:
                for index, data in enumerate(("row:1", "inline:1")):
                    before_action(index)
                    with World.open(directory) as world:
                        world.create_callback(
                            user_id=1,
                            chat_id=1,
                            message_id=2,
                            data=data,
                            request_id=f"simulation-action-{index}",
                        )
                    wait_answer(index)
            else:
                client["initial"] = show(
                    {
                        "endpoint": bridge.base_url,
                        "capability": capability,
                        "world_id": world_id,
                        "user_id": 1,
                    }
                )
            stdout, stderr = bot.communicate(timeout=15)
            if bot.returncode != 0 or stderr:
                raise RuntimeError(
                    "Real action bot failed; retained API evidence identifies progress"
                )
            actions = [json.loads(line) for line in stdout.splitlines()]
        if observe is not None:
            client.update(observe())
    with World.open(directory) as world:
        events = world.events()
        callbacks = [
            world.get_callback(user_id=1, callback_id=event["data"]["id"])
            for event in events
            if event["type"] == "callback.created"
        ]
        result = {
            "mode": "simulation" if show is None else "native-input",
            "world_id": world_id,
            "initial": initial,
            "actions": actions,
            "callbacks": callbacks,
            "history": world.history(1),
            "events": events,
            "pending": world.poll_updates(2),
            "api": [json.loads(line) for line in Path("bot/api.jsonl").read_text().splitlines()],
            "client": client,
        }
    evidence = json.dumps(result)
    if token in evidence or capability in evidence:
        raise RuntimeError("Rich action evidence contains a capability")
    Path("action-round-trip.json").write_text(evidence)
    return result


if __name__ == "__main__":
    print(json.dumps(run()))
