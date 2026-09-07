"""Explicit test instrumentation; production runs never acquire tracing dependencies."""

import json
from pathlib import Path

import coverage
import pytest

import gramlab
from gramlab.runtime import Sandbox


def pytest_sessionstart(session: pytest.Session) -> None:
    """Reject an editable install from another worktree before any test can run."""
    del session
    expected = Path(__file__).resolve().parents[1] / "src" / "gramlab"
    if Path(gramlab.__file__).resolve().parent != expected:
        raise pytest.UsageError(
            "GramLab imports from another checkout. Reinstall this checkout with "
            "tools/dev default --command uv sync --locked --reinstall-package gramlab."
        )


@pytest.fixture
def trace_runner(monkeypatch):
    """Observe actual contained source lines for tests of the public Python runner API."""
    current = coverage.Coverage.current()
    if current is None:
        return
    source = Path("src/gramlab").absolute()
    bootstrap = Path("tests/probes/trace_runner.py").read_bytes()
    original = Sandbox.supervise

    def traced(self, command, *, data, **kwargs):
        assert command == [self.profile.python, "-m", "gramlab._run"]
        (data / "trace_runner.py").write_bytes(bootstrap)
        try:
            return original(
                self, [self.profile.python, "/work/trace_runner.py"], data=data, **kwargs
            )
        finally:
            recorded = data / "supervisor-lines.json"
            if recorded.is_file():
                observations = json.loads(recorded.read_text())
                lines = {}
                for name, visited in observations.items():
                    assert Path(name).name == name and (source / name).is_file()
                    assert all(type(line) is int and line > 0 for line in visited)
                    lines[str(source / name)] = set(visited)
                current.get_data().add_lines(lines)

    monkeypatch.setattr(Sandbox, "supervise", traced)
