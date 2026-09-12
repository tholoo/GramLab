"""Real-process checks for bounded guest startup log collection."""

import os
import subprocess
import sys
import time
from pathlib import Path

import pytest
from probes.android_guest import (
    StartupLogCollector,
    reset_adb_server,
    startup_log_command,
    wait_for_system_report,
)


def child(source: str, *arguments: str) -> list[str]:
    return [sys.executable, "-u", "-c", source, *arguments]


def wait_for_bytes(collector: StartupLogCollector, count: int) -> None:
    deadline = time.monotonic() + 2
    while collector.retained_bytes < count and collector.running and time.monotonic() < deadline:
        time.sleep(0.01)
    assert collector.retained_bytes >= count


def assert_reaped(pid: int) -> None:
    with pytest.raises(ProcessLookupError):
        os.kill(pid, 0)


def test_startup_log_command_uses_dedicated_serial_and_system_tag_allowlist() -> None:
    command = startup_log_command("/tools/adb")
    assert command[:7] == [
        "/tools/adb",
        "-s",
        "emulator-5554",
        "logcat",
        "-b",
        "system",
        "-b",
    ]
    assert command[7:10] == ["main", "-v", "threadtime"]
    assert command[-1] == "*:S"
    assert "ActivityManager:I" in command
    assert "ActivityTaskManager:I" in command
    assert "WindowManager:I" in command
    assert "InputDispatcher:I" in command
    assert "InputReader:I" in command
    assert "UwbService:I" in command
    assert "UwbServiceCore:I" in command
    assert "UwbSettingsStore:I" in command
    assert "UwbCountryCode:I" in command
    assert "UwbContext:I" in command
    assert "uwb:I" in command
    assert "android.hardware.uwb:I" in command
    assert "android.hardware.uwb-service:I" in command
    assert "BugreportManagerService:I" in command
    assert all("gramlab" not in argument.lower() for argument in command)


def test_reset_adb_server_discards_a_preceding_fixed_serial_transport(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[list[str], dict[str, object]]] = []

    def run(command: list[str], **options: object) -> subprocess.CompletedProcess[str]:
        calls.append((command, options))
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(subprocess, "run", run)
    reset_adb_server("/tools/adb")

    assert calls == [
        (
            ["/tools/adb", "kill-server"],
            {"capture_output": True, "text": True, "timeout": 10, "check": False},
        )
    ]


def test_collector_retains_beginning_and_reaps_live_child() -> None:
    collector = StartupLogCollector(
        child(
            "import time; "
            "print('01-01 00:00:00.000 I ActivityManager: start', flush=True); "
            "time.sleep(30)"
        ),
        max_bytes=256,
    )
    with collector:
        assert collector.pid is not None
        pid = collector.pid
        wait_for_bytes(collector, 20)
    assert collector.result == {
        "status": "complete",
        "truncated": False,
        "retained_bytes": 44,
        "returncode": -15,
        "log": "01-01 00:00:00.000 I ActivityManager: start\n",
    }
    assert not collector.reader_running
    assert_reaped(pid)


def test_collector_drains_pipe_scale_overflow_before_cleanup(tmp_path: Path) -> None:
    completed = tmp_path / "emitter-complete"
    collector = StartupLogCollector(
        child(
            "import os,pathlib,sys,time; "
            "[os.write(1, b'A' * 65536) for _ in range(128)]; "
            "pathlib.Path(sys.argv[1]).write_text('complete'); "
            "time.sleep(30)",
            str(completed),
        ),
        max_bytes=37,
    )
    with collector:
        assert collector.pid is not None
        pid = collector.pid
        deadline = time.monotonic() + 5
        while not completed.exists() and collector.running and time.monotonic() < deadline:
            time.sleep(0.01)
        assert completed.read_text() == "complete"
    assert collector.result["status"] == "truncated"
    assert collector.result["truncated"] is True
    assert collector.result["retained_bytes"] == 37
    assert collector.result["log"] == "A" * 37
    assert collector.result["returncode"] == -15
    assert not collector.reader_running
    assert_reaped(pid)


def test_collector_reports_early_exit_and_start_error() -> None:
    collector = StartupLogCollector(child("print('partial', flush=True); raise SystemExit(7)"))
    with collector:
        assert collector.pid is not None
        pid = collector.pid
        deadline = time.monotonic() + 2
        while collector.running and time.monotonic() < deadline:
            time.sleep(0.01)
        assert not collector.running
    assert collector.result == {
        "status": "early_exit",
        "truncated": False,
        "retained_bytes": 8,
        "returncode": 7,
        "log": "partial\n",
    }
    assert not collector.reader_running
    assert_reaped(pid)

    unavailable = StartupLogCollector(["/definitely/absent/gramlab-log-emitter"])
    with unavailable:
        assert unavailable.pid is None
    assert unavailable.result == {
        "status": "error",
        "truncated": False,
        "retained_bytes": 0,
        "returncode": None,
        "log": "",
        "error": "start_failed",
    }


def test_collector_reaps_child_on_exceptional_context_exit() -> None:
    collector = StartupLogCollector(
        child("import time; print('ready', flush=True); time.sleep(30)")
    )
    with pytest.raises(RuntimeError, match="probe failed"):
        with collector:
            assert collector.pid is not None
            pid = collector.pid
            wait_for_bytes(collector, 6)
            raise RuntimeError("probe failed")
    assert collector.result["status"] == "complete"
    assert collector.result["log"] == "ready\n"
    assert not collector.reader_running
    assert_reaped(pid)


def test_system_report_barrier_waits_for_dumpstate_and_a_quiet_interval(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import subprocess

    now = [10.0]
    responses = iter(("2292\n", "2292\n", "", "", "", ""))
    calls = []

    def adb(*arguments: str, **options: float) -> subprocess.CompletedProcess[str]:
        calls.append((arguments, options))
        stdout = next(responses)
        return subprocess.CompletedProcess(arguments, 0 if stdout else 1, stdout=stdout, stderr="")

    monkeypatch.setattr(time, "monotonic", lambda: now[0])
    monkeypatch.setattr(time, "sleep", lambda delay: now.__setitem__(0, now[0] + delay))

    result = wait_for_system_report(adb, timeout=5, quiet=0.5)
    assert result["observed"] is True
    assert 500 <= result["elapsed_ms"] < 5_000
    assert result["quiet_ms"] == 500
    assert calls and all(call[0] == ("shell", "pidof", "dumpstate") for call in calls)
