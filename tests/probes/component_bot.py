"""Trusted fixture setup; every bot launch uses a private runtime component."""

import json
import shutil
import subprocess
from collections.abc import Mapping
from contextlib import AbstractContextManager
from pathlib import Path

from gramlab.runtime import RuntimeProfile, Sandbox


class FixtureBot:
    def __init__(self, filename: str) -> None:
        profile = RuntimeProfile(**json.loads(Path("component-profile.json").read_text()))
        self.sandbox = Sandbox(profile)
        self.data = Path("bot")
        # Create and populate once, before any bot executes. Restarts retain private state;
        # never follow a bot-created symlink while reinstalling fixture code.
        self.data.mkdir()
        source = Path(filename)
        shutil.copy2(source, self.data / source.name)
        self.command = [profile.python, "/work/" + source.name]

    def start(
        self, environment: Mapping[str, str]
    ) -> AbstractContextManager[subprocess.Popen[str]]:
        return self.sandbox.component(self.command, data=self.data, environment=environment)

    def run(
        self, environment: Mapping[str, str], *, timeout: float = 10
    ) -> subprocess.CompletedProcess[str]:
        with self.start(environment) as process:
            stdout, stderr = process.communicate(timeout=timeout)
            return subprocess.CompletedProcess(self.command, process.returncode, stdout, stderr)
