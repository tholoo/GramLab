"""Trusted persistent playground owner. Never import consumer code in this process."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, cast

from gramlab._android import Android
from gramlab._captures import Captures
from gramlab._control import WorldControl
from gramlab._interactions import Interactions
from gramlab._processes import Processes, Program
from gramlab._rich_buttons import occurrences
from gramlab._rich_interactions import RichInteractions
from gramlab.bot_api import BotAPIServer
from gramlab.playground import PlaygroundControl
from gramlab.reports import _Redactor
from gramlab.runtime import RuntimeProfile, Sandbox
from gramlab.world import World

_PLAYGROUND_SECONDS = 24 * 60 * 60


def _state_digest(root: Path) -> str:
    with World.open(root / "world") as world:
        snapshot = world.snapshot()
        value = {
            "world": snapshot,
            "histories": {str(chat["id"]): world.history(chat["id"]) for chat in snapshot["chats"]},
            "events": world.events(),
        }
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _copy_state(source: Path, destination: Path) -> None:
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination, symlinks=True)


def _world_status(bots: dict[str, int], baseline_digest: str) -> dict[str, Any]:
    with World.open(Path("world")) as world:
        snapshot = world.snapshot()
        histories = {str(chat["id"]): world.history(chat["id"]) for chat in snapshot["chats"]}
        run_id = world.world_id
    return {
        "schema": 1,
        "state": "running",
        "run_id": run_id,
        "bots": bots,
        "at_baseline": _state_digest(Path(".")) == baseline_digest,
        "world": snapshot,
        "histories": histories,
    }


def _named_group(world: World, title: Any) -> dict[str, Any]:
    if not isinstance(title, str) or not 1 <= len(title) <= 255:
        raise ValueError("Group title must be nonempty text")
    matches = [
        chat
        for chat in world.snapshot()["chats"]
        if chat["type"] == "supergroup" and chat["title"] == title
    ]
    if len(matches) != 1:
        raise ValueError("Group title must identify exactly one seeded group")
    return cast(dict[str, Any], matches[0])


def _named_actor(world: World, username: Any) -> dict[str, Any]:
    if not isinstance(username, str) or not username:
        raise ValueError("Actor must be a seeded username")
    matches = [
        user
        for user in world.snapshot()["users"]
        if not user["is_bot"] and user.get("username") == username
    ]
    if len(matches) != 1:
        raise ValueError("Actor username must identify exactly one seeded user")
    return cast(dict[str, Any], matches[0])


def execute() -> None:
    config = json.loads(Path("run-input.json").read_text())
    profile = RuntimeProfile(**json.loads(Path("profile.json").read_text()))
    sandbox = Sandbox(profile)
    setup_deadline = time.monotonic() + config["timeout"]
    runtime_deadline = time.monotonic() + _PLAYGROUND_SECONDS
    tokens: dict[str, str] = {}
    bots: dict[str, int] = {}
    with World.create(Path("world"), seed=config["seed"], now=config["now"]) as world:
        for alias in config["bots"]:
            bot = world.create_user(first_name=alias, is_bot=True)
            bots[alias] = bot["id"]
            tokens[alias] = world.issue_bot_token(bot["id"])
        run_id = world.world_id
    bot_profiles_path = Path("bot-profiles.json")
    bot_profiles = (
        {
            alias: RuntimeProfile(**value)
            for alias, value in json.loads(bot_profiles_path.read_text()).items()
        }
        if bot_profiles_path.exists()
        else {}
    )
    secrets = list(tokens.values())
    failure: str | None = None
    android = None
    if config["mode"] in ("headless-android", "interactive-android"):
        android = Android(
            RuntimeProfile(**json.loads(Path("android-profile.json").read_text())),
            deadline=runtime_deadline,
            secrets=secrets,
            bridge_version=config["android"]["bridge_version"],
            theme=config["android"]["theme"],
            interactive=config["mode"] == "interactive-android",
        )
    renderer_lock = threading.Lock()
    captures = Captures(
        Path("world"), lock=renderer_lock, render=android.capture if android is not None else None
    )
    interactions = Interactions(
        Path("world"),
        lock=renderer_lock,
        bridge_version=config["bridge_version"],
        tap=android.tap_inline_button if android is not None else None,
        compose=android.type_message if android is not None else None,
        start_chat=android.start_bot_chat if android is not None else None,
    )
    rich = None
    process_epochs: list[dict[str, Any]] = []
    playground_lifecycle: list[dict[str, Any]] = []
    processes: Processes | None = None

    def make_processes(deadline: float) -> Processes:
        return Processes(
            sandbox,
            deadline=deadline,
            bots=set(bots),
            bot_sandboxes={alias: Sandbox(item) for alias, item in bot_profiles.items()},
        )

    try:
        native_rich = None
        if android is not None:
            from gramlab._android_rich_buttons import AndroidRichInput

            native_rich = AndroidRichInput(android)
        rich = RichInteractions(
            Path("world"), lock=renderer_lock, interactions=interactions, native=native_rich
        )
        if android is not None:
            android.start()
        with BotAPIServer(Path("world")) as api:
            bot_programs: dict[str, Program] = {
                f"bot:{alias}": (
                    Path("bots") / alias,
                    program,
                    {"GRAMLAB_BOT_API": api.base_url, "GRAMLAB_BOT_TOKEN": tokens[alias]},
                )
                for alias, program in config["bots"].items()
            }
            processes = make_processes(setup_deadline)
            with WorldControl(
                Path("world"),
                bots=bots,
                capture_chat=captures.capture_chat,
                tap_inline_button=interactions.tap_inline_button,
                rich_buttons=rich.rich_buttons,
                tap_rich_button=rich.tap_rich_button,
                type_message=interactions.type_message,
                start_bot_chat=interactions.start_bot_chat,
                bot_status=processes.bot_status,
                stop_bot=processes.stop_bot,
                start_bot=processes.start_bot,
            ) as setup_control:
                secrets.append(setup_control.capability)
                programs = dict(bot_programs)
                programs["scenario"] = (
                    Path("scenario"),
                    config["scenario"],
                    {
                        "GRAMLAB_CONTROL_ENDPOINT": setup_control.base_url,
                        "GRAMLAB_CONTROL_CAPABILITY": setup_control.capability,
                        "GRAMLAB_WORLD_ID": setup_control.world_id,
                    },
                )
                processes.wait_for_scenario(programs)
            failure = processes.failure
            processes.close()
            process_epochs.append({"phase": "setup", "processes": processes.records})
            if failure:
                raise RuntimeError("Playground setup failed")

            baseline = Path(".playground-baseline")
            baseline.mkdir(mode=0o700)
            _copy_state(Path("world"), baseline / "world")
            _copy_state(Path("bots"), baseline / "bots")
            baseline_digest = _state_digest(baseline)

            processes = make_processes(runtime_deadline)
            processes.start(bot_programs)

            def dispatch(operation: str, parameters: dict[str, Any]) -> dict[str, Any]:
                nonlocal processes
                if processes is None:
                    raise RuntimeError("Playground consumer owner is unavailable")
                if operation == "status":
                    if parameters:
                        raise ValueError("Status takes no parameters")
                    return _world_status(bots, baseline_digest)
                if operation == "add_bot":
                    if parameters.keys() != {"group", "bot", "actor"}:
                        raise ValueError("Add bot requires group, bot and actor")
                    alias = parameters["bot"]
                    if not isinstance(alias, str) or alias not in bots:
                        raise ValueError("Bot must be a configured alias")
                    with World.open(Path("world")) as world:
                        group = _named_group(world, parameters["group"])
                        actor = _named_actor(world, parameters["actor"])
                        changed = world.add_bot_to_group(
                            chat_id=group["id"], bot_id=bots[alias], actor_id=actor["id"]
                        )
                    if android is not None:
                        android.refresh_active_chat()
                    playground_lifecycle.append(
                        {
                            "operation": "add_bot",
                            "group_id": changed["id"],
                            "bot": alias,
                            "actor_id": actor["id"],
                        }
                    )
                    return {"group": changed, "bot": alias}
                if operation == "send":
                    if parameters.keys() != {"chat_id", "actor_id", "text"}:
                        raise ValueError("Send requires chat_id, actor_id and text")
                    chat_id = parameters["chat_id"]
                    actor_id = parameters["actor_id"]
                    text = parameters["text"]
                    if (
                        type(chat_id) is not int
                        or type(actor_id) is not int
                        or not isinstance(text, str)
                        or not 1 <= len(text) <= 4096
                    ):
                        raise ValueError("Send parameters are invalid")
                    receipt = interactions.type_message(
                        chat_id=chat_id, user_id=actor_id, text=text
                    )
                    playground_lifecycle.append(
                        {"operation": "send", "chat_id": chat_id, "actor_id": actor_id}
                    )
                    return receipt
                if operation == "tap":
                    if parameters.keys() != {"chat_id", "actor_id", "label"}:
                        raise ValueError("Tap requires chat_id, actor_id and label")
                    chat_id = parameters["chat_id"]
                    actor_id = parameters["actor_id"]
                    label = parameters["label"]
                    if (
                        type(chat_id) is not int
                        or type(actor_id) is not int
                        or not isinstance(label, str)
                        or not 1 <= len(label) <= 256
                    ):
                        raise ValueError("Tap parameters are invalid")
                    with World.open(Path("world")) as world:
                        messages = list(reversed(world.history(chat_id)))
                    selected = None
                    for message in messages:
                        if "rich_message" not in message:
                            continue
                        labels = [
                            occurrence["label"]
                            for occurrence in occurrences(message["rich_message"])
                        ]
                        if label not in labels:
                            continue
                        observed = rich.rich_buttons(
                            chat_id=chat_id,
                            message_id=message["id"],
                            user_id=actor_id,
                        )
                        matches = [
                            target for target in observed["targets"] if target["label"] == label
                        ]
                        if matches:
                            if len(matches) != 1:
                                raise ValueError("Button label is ambiguous in the latest message")
                            selected = matches[0]
                            break
                    if selected is None:
                        raise ValueError("No current rich button has that label")
                    receipt = rich.tap_rich_button(target_id=selected["target_id"])
                    playground_lifecycle.append(
                        {"operation": "tap", "chat_id": chat_id, "actor_id": actor_id}
                    )
                    return receipt
                if operation == "capture":
                    if parameters.keys() != {"chat_id", "actor_id", "label", "contains"}:
                        raise ValueError("Capture requires chat_id, actor_id, label and contains")
                    chat_id = parameters["chat_id"]
                    actor_id = parameters["actor_id"]
                    label = parameters["label"]
                    contains = parameters["contains"]
                    if type(chat_id) is not int or type(actor_id) is not int:
                        raise ValueError("Capture identities are invalid")
                    result = captures.capture_chat(
                        chat_id=chat_id,
                        user_id=actor_id,
                        label=label,
                        contains=contains,
                    )
                    playground_lifecycle.append(
                        {"operation": "capture", "chat_id": chat_id, "actor_id": actor_id}
                    )
                    return result
                if operation == "reset":
                    if parameters:
                        raise ValueError("Reset takes no parameters")
                    if android is not None:
                        android.pause_client()
                    processes.close()
                    process_epochs.append({"phase": "before_reset", "processes": processes.records})
                    _copy_state(baseline / "world", Path("world"))
                    _copy_state(baseline / "bots", Path("bots"))
                    processes = make_processes(runtime_deadline)
                    processes.start(bot_programs)
                    if android is not None:
                        android.refresh_active_chat()
                    playground_lifecycle.append({"operation": "reset"})
                    return _world_status(bots, baseline_digest)
                if operation == "stop":
                    if parameters:
                        raise ValueError("Stop takes no parameters")
                    playground_lifecycle.append({"operation": "stop"})
                    return {"state": "stopping", "run_id": run_id}
                raise ValueError("Unknown playground operation")

            with PlaygroundControl(Path("."), run_id=run_id, dispatch=dispatch) as control:
                secrets.append(control.capability)
                while True:
                    processes.poll()
                    if processes.failure:
                        failure = processes.failure
                        break
                    if control.poll():
                        break
    except (TimeoutError, subprocess.TimeoutExpired):
        failure = failure or "timeout"
    except (OSError, RuntimeError, ValueError):
        failure = failure or "component_startup_failed"
    finally:
        if processes is not None:
            processes.close()
            process_epochs.append({"phase": "final", "processes": processes.records})
        if rich is not None:
            try:
                rich.close()
            except OSError:
                failure = failure or "rich_button_journal_failed"
        if android is not None:
            try:
                android.close(retain_failure=failure is not None)
            except (OSError, RuntimeError):
                failure = failure or "android_cleanup_failed"
    if interactions.failed:
        failure = failure or "interaction_failed"
    if rich is not None and rich.failed:
        failure = failure or rich.failure or "rich_button_component_failed"
    if captures.failed:
        failure = failure or "capture_failed"
    observation = _Redactor(secrets).clean(
        {
            "failure": failure,
            "processes": {str(index): item for index, item in enumerate(process_epochs)},
            "lifecycle": [],
            "captures": captures.records,
            "interactions": interactions.records,
            "android": android.observations if android is not None else {},
            "playground": {"lifecycle": playground_lifecycle},
        }
    )
    Path("observation.json").write_text(json.dumps(observation, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    execute()
