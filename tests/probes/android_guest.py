"""Trusted guest-startup probe, executed only inside GramLab's process boundary."""

import json
import os
import shutil
import socket
import socketserver
import subprocess
import sys
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypedDict

from gramlab.runtime import RuntimeProfile, Sandbox

_STARTUP_LOG_LIMIT = 256 * 1024


class SystemReportWait(TypedDict):
    observed: bool
    elapsed_ms: float
    quiet_ms: int


def startup_log_command(adb: str) -> list[str]:
    """Return the fixed dedicated-device system log command used by this probe."""
    return [
        adb,
        "-s",
        "emulator-5554",
        "logcat",
        "-b",
        "system",
        "-b",
        "main",
        "-v",
        "threadtime",
        "ActivityManager:I",
        "ActivityTaskManager:I",
        "WindowManager:I",
        "InputDispatcher:I",
        "InputReader:I",
        "UwbService:I",
        "UwbServiceCore:I",
        "UwbSettingsStore:I",
        "UwbCountryCode:I",
        "UwbContext:I",
        "uwb:I",
        "android.hardware.uwb:I",
        "android.hardware.uwb-service:I",
        "UwbSessionManager:I",
        "BugreportManagerService:I",
        "DumpstateListener:I",
        "dumpstate:I",
        "*:S",
    ]


def reset_adb_server(adb: str) -> None:
    """Discard transports retained from an earlier guest using the fixed serial."""
    result = subprocess.run(  # noqa: S603 — pinned supervisor-provided adb path.
        [adb, "kill-server"], capture_output=True, text=True, timeout=10, check=False
    )
    if result.returncode:
        raise RuntimeError(f"Failed to reset the dedicated ADB server: {result.stderr}")


class StartupLogCollector:
    """Drain an owned child while retaining a bounded prefix of its merged output."""

    def __init__(self, command: list[str], *, max_bytes: int = _STARTUP_LOG_LIMIT) -> None:
        if max_bytes <= 0:
            raise ValueError("Startup log byte limit must be positive")
        self._command = command
        self._max_bytes = max_bytes
        self._process: subprocess.Popen[bytes] | None = None
        self._reader: threading.Thread | None = None
        self._retained = bytearray()
        self._truncated = False
        self._error: str | None = None
        self.result: dict[str, Any] = {}

    @property
    def pid(self) -> int | None:
        return self._process.pid if self._process is not None else None

    @property
    def running(self) -> bool:
        return self._process is not None and self._process.poll() is None

    @property
    def retained_bytes(self) -> int:
        return len(self._retained)

    @property
    def reader_running(self) -> bool:
        return self._reader is not None and self._reader.is_alive()

    def start(self) -> "StartupLogCollector":
        if self._process is not None or self._error is not None:
            return self
        try:
            self._process = subprocess.Popen(  # noqa: S603 — fixed probe command or test-owned child
                self._command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
        except OSError:
            self._error = "start_failed"
            return self
        self._reader = threading.Thread(target=self._drain, name="guest-startup-log", daemon=True)
        self._reader.start()
        return self

    def _drain(self) -> None:
        assert self._process is not None and self._process.stdout is not None
        try:
            while chunk := os.read(self._process.stdout.fileno(), 4096):
                remaining = self._max_bytes - len(self._retained)
                if remaining > 0:
                    self._retained.extend(chunk[:remaining])
                if len(chunk) > remaining:
                    self._truncated = True
        except OSError:
            self._error = "read_failed"

    def finish(self) -> dict[str, Any]:
        if self.result:
            return self.result
        process = self._process
        early_exit = process is not None and process.poll() is not None
        if process is not None:
            if process.poll() is None:
                try:
                    process.terminate()
                except ProcessLookupError:
                    pass
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
            if self._reader is not None:
                self._reader.join(timeout=5)
                if self._reader.is_alive():
                    self._error = "reader_did_not_stop"
            if process.stdout is not None:
                process.stdout.close()
            if process.returncode is not None and process.returncode >= 0:
                early_exit = True
        if self._error is not None:
            status = "error"
        elif early_exit:
            status = "early_exit"
        elif self._truncated:
            status = "truncated"
        else:
            status = "complete"
        self.result = {
            "status": status,
            "truncated": self._truncated,
            "retained_bytes": len(self._retained),
            "returncode": process.returncode if process is not None else None,
            "log": self._retained.decode("utf-8", errors="replace"),
        }
        if self._error is not None:
            self.result["error"] = self._error
        return self.result

    def __enter__(self) -> "StartupLogCollector":
        return self.start()

    def __exit__(self, exception_type: object, exception: object, traceback: object) -> None:
        self.finish()


def probe_emulator_filesystem() -> dict[str, object]:
    """Observe the running QEMU process through this trusted supervisor's /proc."""
    processes = []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdecimal():
            continue
        try:
            executable = (entry / "exe").readlink()
        except FileNotFoundError:
            continue
        if executable.name in ("qemu-system-x86_64", "qemu-system-x86_64-headless"):
            processes.append(entry)
    if len(processes) != 1:
        raise RuntimeError(f"Expected one dedicated QEMU process, found {len(processes)}")
    process = processes[0]
    root = process / "root"
    return {
        "world_visible": any(
            (root / name).exists() for name in ("work/world-secret", "work/world")
        ),
        "bot_visible": any((root / name).exists() for name in ("work/bot-secret", "work/bot")),
        "private_avd_visible": (root / "work/avd/config.ini").is_file(),
        "same_pid_namespace": (process / "ns/pid").readlink()
        == Path("/proc/self/ns/pid").readlink(),
        "same_network": (process / "ns/net").readlink() == Path("/proc/self/ns/net").readlink(),
    }


def probe_network(
    adb_command: Callable[..., subprocess.CompletedProcess[str]],
) -> dict[str, object]:
    class Reply(socketserver.BaseRequestHandler):
        def handle(self) -> None:
            if self.request.makefile("rb").readline(64) == b"gramlab-probe\n":
                self.request.sendall(b"gramlab-local-reply\n")

    network: dict[str, object] = {}
    with socketserver.TCPServer(("127.0.0.1", 0), Reply) as server:
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            port = server.server_address[1]
            deadline = time.monotonic() + 30
            while True:
                local = adb_command(
                    "shell", f"printf 'gramlab-probe\\n' | toybox nc -4 -w 2 -W 2 10.0.2.2 {port}"
                )
                if local.returncode == 0 or time.monotonic() >= deadline:
                    break
                time.sleep(0.5)
            network["local"] = local.stdout
            network["local_error"] = local.stderr
        finally:
            server.shutdown()
            worker.join()
    for family, flag, address in (("ipv4", "-4", "192.0.2.1"), ("ipv6", "-6", "2001:db8::1")):
        attempted = adb_command("shell", "toybox", "nc", flag, "-z", "-w", "2", address, "443")
        network[family] = {
            "returncode": attempted.returncode,
            "stdout": attempted.stdout,
            "stderr": attempted.stderr,
        }
    return network


def wait_for_system_report(
    adb_command: Callable[..., subprocess.CompletedProcess[str]],
    *,
    timeout: float = 60,
    quiet: float = 1,
) -> SystemReportWait:
    """Wait for an AOSP dumpstate report and a bounded report-free interval."""
    if timeout <= 0 or quiet < 0 or quiet >= timeout:
        raise ValueError("System report bounds are invalid")
    started = time.monotonic()
    deadline = started + timeout
    quiet_since: float | None = None
    observed = False
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("System bugreport did not settle before native capture")
        status = adb_command(
            "shell",
            "pidof",
            "dumpstate",
            timeout=min(5, remaining),
        )
        pids = status.stdout.strip()
        if status.returncode == 0 and pids and all(pid.isdecimal() for pid in pids.split()):
            observed = True
            quiet_since = None
        elif status.returncode == 1 and not pids:
            now = time.monotonic()
            if quiet_since is None:
                quiet_since = now
            if now - quiet_since >= quiet:
                return SystemReportWait(
                    observed=observed,
                    elapsed_ms=(now - started) * 1_000,
                    quiet_ms=int(quiet * 1_000),
                )
        else:
            raise RuntimeError("System bugreport status was unavailable")
        time.sleep(min(0.2, max(0, deadline - time.monotonic())))


def main(
    extra_probe: Callable[[Callable[..., subprocess.CompletedProcess[str]]], dict[str, object]]
    | None = None,
) -> None:
    emulator, adb, avdmanager, image_package = sys.argv[1:]
    for variable in ("HOME", "ANDROID_USER_HOME", "ANDROID_AVD_HOME", "XDG_CACHE_HOME"):
        Path(os.environ[variable]).mkdir(parents=True, exist_ok=True)
    profile = RuntimeProfile(**json.loads(Path("emulator-profile.json").read_text()))
    data = Path("emulator")
    data.mkdir()
    shutil.copy2("emulator_process.py", data / "emulator_process.py")
    command = [profile.python, "/work/emulator_process.py", emulator, avdmanager, image_package]
    print("Starting the isolated AOSP guest", file=sys.stderr, flush=True)
    started = time.monotonic()
    observations: dict[str, object] = {}
    startup_log: StartupLogCollector | None = None
    # A serial Android gate reuses emulator-5554 across tests in one network
    # namespace. Do not let the ADB daemon retain the preceding guest's transport.
    reset_adb_server(adb)
    with Sandbox(profile).component(command, data=data, kvm=True) as guest:
        try:

            def adb_command(
                *arguments: str, timeout: float = 10, input: str | None = None
            ) -> subprocess.CompletedProcess[str]:
                return subprocess.run(  # noqa: S603 — dedicated namespace/serial only
                    [adb, "-s", "emulator-5554", *arguments],
                    capture_output=True,
                    text=True,
                    input=input,
                    timeout=timeout,
                    check=False,
                )

            ready = False
            while time.monotonic() - started < 120:
                if guest.poll() is not None:
                    raise RuntimeError(
                        f"Emulator exited {guest.returncode}:\n"
                        + (
                            (data / "emulator.log").read_text()
                            if (data / "emulator.log").exists()
                            else guest.communicate(timeout=5)[1]
                        )
                    )
                boot = adb_command("shell", "getprop", "sys.boot_completed")
                if boot.returncode == 0 and startup_log is None:
                    startup_log = StartupLogCollector(startup_log_command(adb)).start()
                    observations["startup_log_started_seconds"] = time.monotonic() - started
                if boot.returncode == 0 and boot.stdout.strip() == "1":
                    ready = True
                    break
                time.sleep(1)
            if not ready:
                raise RuntimeError("Guest did not complete boot within 120 seconds")
            observations["boot_ready_seconds"] = time.monotonic() - started
            for name, arguments in {
                "api": ("shell", "getprop", "ro.build.version.sdk"),
                "abi": ("shell", "getprop", "ro.product.cpu.abi"),
                "fingerprint": ("shell", "getprop", "ro.build.fingerprint"),
                "nc_help": ("shell", "toybox", "nc", "--help"),
                "accounts": ("shell", "dumpsys", "account"),
                "graphics": ("shell", "dumpsys", "SurfaceFlinger"),
            }.items():
                observation = adb_command(*arguments)
                if observation.returncode:
                    raise RuntimeError(f"Guest observation {name} failed: {observation.stderr}")
                if name == "graphics":
                    observations[name] = next(
                        line for line in observation.stdout.splitlines() if line.startswith("GLES:")
                    )
                else:
                    observations[name] = observation.stdout.strip()
            observations["network"] = probe_network(adb_command)
            observations["routes"] = adb_command(
                "shell", "ip", "route", "show", "table", "all"
            ).stdout
            observations["interfaces"] = adb_command("shell", "ip", "address").stdout
            observations["host_interfaces"] = socket.if_nameindex()
            if extra_probe is not None:
                probe_started = time.monotonic()
                try:
                    observations["extra_probe"] = extra_probe(adb_command)
                finally:
                    observations["extra_probe_seconds"] = time.monotonic() - probe_started
            if startup_log is not None:
                observations["startup_log"] = startup_log.finish()
            observations["emulator_filesystem"] = probe_emulator_filesystem()
            screenshot = subprocess.run(  # noqa: S603 — dedicated namespace/serial only
                [adb, "-s", "emulator-5554", "exec-out", "screencap", "-p"],
                capture_output=True,
                timeout=10,
                check=True,
            )
            Path("guest.png").write_bytes(screenshot.stdout)
            observations["boot_seconds"] = time.monotonic() - started
            Path("guest.json").write_text(json.dumps(observations, indent=2) + "\n")
            print(json.dumps(observations), flush=True)
        except BaseException:
            if startup_log is not None:
                observations["startup_log"] = startup_log.finish()
            else:
                observations["startup_log"] = {
                    "status": "error",
                    "truncated": False,
                    "retained_bytes": 0,
                    "returncode": None,
                    "log": "",
                    "error": "adb_unavailable",
                }
            observations["boot_seconds"] = time.monotonic() - started
            observations["failure"] = "guest_probe_failed"
            Path("guest.json").write_text(json.dumps(observations, indent=2) + "\n")
            print(f"Dedicated guest exit on failure: {guest.poll()}", file=sys.stderr)
            raise
        finally:
            if startup_log is not None:
                startup_log.finish()
            if guest.poll() is None:
                guest.terminate()
                try:
                    guest.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    guest.kill()
                    guest.wait()


if __name__ == "__main__":
    main()
