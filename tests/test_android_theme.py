"""Explicit Android appearance is applied before consumer UI evidence."""

from __future__ import annotations

import subprocess
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Literal

import pytest

from gramlab._android import Android


@pytest.mark.parametrize(("theme", "night_mode"), [("light", "no"), ("dark", "yes")])
def test_android_applies_and_records_requested_system_theme(
    theme: Literal["light", "dark"], night_mode: str
) -> None:
    android: Any = object.__new__(Android)
    android._theme = theme
    android.observations = {}
    calls: list[tuple[str, ...]] = []

    def adb(*arguments: str, **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append(arguments)
        return subprocess.CompletedProcess(arguments, 0, stdout=f"Night mode: {night_mode}\n")

    android._adb = adb

    android._apply_theme()

    assert calls == [("shell", "cmd", "uimode", "night", night_mode)]
    assert android.observations["theme"] == theme


def test_android_ui_wait_records_crash_buffer_when_client_exits() -> None:
    android: Any = object.__new__(Android)
    android.deadline = time.monotonic() + 10
    android.secrets = []
    android.observations = {}
    android._guest = SimpleNamespace(poll=lambda: None)
    calls: list[tuple[str, ...]] = []

    def adb(*arguments: str, **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append(arguments)
        if arguments == ("shell", "pidof", "org.gramlab.android"):
            return subprocess.CompletedProcess(arguments, 1, stdout="")
        if arguments[:3] == ("logcat", "-b", "crash"):
            return subprocess.CompletedProcess(arguments, 0, stdout="native crash detail")
        return subprocess.CompletedProcess(arguments, 0, stdout="recent main log")

    android._adb = adb

    with pytest.raises(RuntimeError, match="exited while waiting for UI"):
        android._wait_ui(["Expected"])

    assert android.observations["client_exit_failure"] == (
        "Dedicated Android client exited while waiting for UI"
    )
    assert android.observations["failure_crash_log"] == "native crash detail"
    assert ("shell", "uiautomator", "dump", "/data/local/tmp/gramlab-capture.xml") not in calls


def test_failed_capture_retains_a_native_screen_recording(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    Path("captures").mkdir()
    android: Any = object.__new__(Android)
    android.deadline = time.monotonic() + 10
    android.secrets = []
    android.observations = {}
    android._guest = SimpleNamespace(poll=lambda: None)
    android.profile = SimpleNamespace(executables={"adb": "/trusted/adb"})

    class Recording:
        returncode: int | None = None

        def poll(self) -> int | None:
            return self.returncode

        def wait(self, timeout: float) -> int:
            self.returncode = 0
            return 0

    def popen(*_args: Any, **_kwargs: Any) -> Recording:
        return Recording()

    monkeypatch.setattr(subprocess, "Popen", popen)

    def adb(*arguments: str, **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        if arguments[0] == "pull":
            Path(arguments[2]).write_bytes(b"\0\0\0\x18ftypisom" + b"recorded-frame")
        if arguments[:3] == ("logcat", "-b", "crash"):
            return subprocess.CompletedProcess(arguments, 0, stdout="native crash detail")
        return subprocess.CompletedProcess(arguments, 0, stdout="recent main log")

    android._adb = adb
    android._capture = lambda *_args, **_kwargs: (_ for _ in ()).throw(
        RuntimeError("capture broke")
    )

    with pytest.raises(RuntimeError, match="capture broke"):
        android.capture({"id": 1}, "broken", ["Expected"])

    video = Path("captures/failure-capture.mp4")
    assert video.read_bytes()[4:8] == b"ftyp"
    assert android.observations["failure_video"] == video.as_posix()
    assert android.observations["capture_failure"] == "capture broke"
