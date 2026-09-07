"""Real-process checks for bounded guest startup log collection."""

import os
import sys
import time

import pytest
from probes.android_guest import StartupLogCollector, startup_log_command


def child(source: str) -> list[str]:
    return [sys.executable, "-u", "-c", source]


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
    assert "BugreportManagerService:I" in command
    assert all("gramlab" not in argument.lower() for argument in command)


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
    assert_reaped(pid)


def test_collector_drains_overflow_but_retains_exact_prefix() -> None:
    collector = StartupLogCollector(
        child("import sys,time; sys.stdout.write('A' * 8192); sys.stdout.flush(); time.sleep(30)"),
        max_bytes=37,
    )
    with collector:
        assert collector.pid is not None
        pid = collector.pid
        wait_for_bytes(collector, 37)
    assert collector.result["status"] == "truncated"
    assert collector.result["truncated"] is True
    assert collector.result["retained_bytes"] == 37
    assert collector.result["log"] == "A" * 37
    assert collector.result["returncode"] == -15
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
    assert_reaped(pid)
