"""Trusted orchestration: scenario and bot use separate private runtime components."""

import json
import selectors
import shutil
from pathlib import Path

from component_bot import FixtureBot

from gramlab._control import WorldControl
from gramlab.bot_api import BotAPIServer
from gramlab.runtime import RuntimeProfile, Sandbox
from gramlab.world import World

profile = RuntimeProfile(**json.loads(Path("component-profile.json").read_text()))
directory = Path("world")
with World.create(directory, seed=7, now=1700000000):
    pass
scenario = Path("scenario")
scenario.mkdir()
shutil.copy2("scenario_actor.py", scenario / "scenario_actor.py")
# Prepare bot files before the scenario's isolation observations, so absence is meaningful.
bot_fixture = FixtureBot("echo_bot.py")
with WorldControl(directory) as control, BotAPIServer(directory) as api:
    with Sandbox(profile).component(
        [profile.python, "/work/scenario_actor.py"],
        data=scenario,
        environment={
            "GRAMLAB_CONTROL_ENDPOINT": control.base_url,
            "GRAMLAB_CONTROL_CAPABILITY": control.capability,
            "GRAMLAB_WORLD_ID": control.world_id,
        },
    ) as actor:
        assert actor.stdout is not None
        with selectors.DefaultSelector() as ready:
            ready.register(actor.stdout, selectors.EVENT_READ)
            if not ready.select(timeout=10):
                raise TimeoutError("Scenario did not prepare participants")
        isolation = json.loads(actor.stdout.readline())
        with World.open(directory) as world:
            token = world.issue_bot_token(2)
        with bot_fixture.start(
            {"GRAMLAB_BOT_API": api.base_url, "GRAMLAB_BOT_TOKEN": token}
        ) as bot:
            stdout, stderr = actor.communicate(input="go\n", timeout=15)
            assert actor.returncode == 0, stderr
            bot_stdout, bot_stderr = bot.communicate(timeout=10)
            assert bot.returncode == 0, bot_stderr
            assert control.capability not in stdout + stderr + bot_stdout + bot_stderr
with World.open(directory) as world:
    print(
        json.dumps(
            {
                "isolation": isolation,
                "scenario": json.loads(stdout),
                "bot": json.loads(bot_stdout),
                "history": world.history(1),
                "pending": world.poll_updates(2),
            }
        )
    )
