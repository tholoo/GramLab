"""Opt-in staging for the real contained clipboard acceptance supervisor."""

import subprocess
from pathlib import Path

import pytest

from gramlab.runtime import Sandbox


def stage(command: list[str], data: Path, python: str) -> list[str]:
    if command != [python, "-m", "gramlab._run"]:
        raise ValueError("Clipboard acceptance requires the public contained supervisor")
    name = "rich_native_clipboard_supervisor.py"
    source = Path(__file__).with_name("probes") / name
    with (data / name).open("xb") as stream:
        stream.write(source.read_bytes())
    return [python, "/work/" + name]


@pytest.fixture
def clipboard_supervisor(monkeypatch: pytest.MonkeyPatch) -> None:
    original = Sandbox.supervise

    def supervise(
        self: Sandbox, command: list[str], *, data: Path, timeout: float = 30, kvm: bool = False
    ) -> subprocess.CompletedProcess[str]:
        return original(
            self, stage(command, data, self.profile.python), data=data, timeout=timeout, kvm=kvm
        )

    monkeypatch.setattr(Sandbox, "supervise", supervise)
