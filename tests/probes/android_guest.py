"""Trusted guest-startup probe, executed only inside GramLab's process boundary."""

import json
import os
import socket
import socketserver
import subprocess
import sys
import threading
import time
from collections.abc import Callable
from pathlib import Path


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


def main(
    extra_probe: Callable[[Callable[..., subprocess.CompletedProcess[str]]], dict[str, object]]
    | None = None,
) -> None:
    emulator, adb, avdmanager, image_package = sys.argv[1:]
    for variable in ("HOME", "ANDROID_USER_HOME", "ANDROID_AVD_HOME", "XDG_CACHE_HOME"):
        Path(os.environ[variable]).mkdir(parents=True, exist_ok=True)
    print("Creating dedicated AVD from the cached system image", file=sys.stderr, flush=True)
    prepared = subprocess.run(  # noqa: S603 — trusted profile executables
        [
            avdmanager,
            "create",
            "avd",
            "--name",
            "gramlab-probe",
            "--package",
            image_package,
            "--path",
            "/work/avd",
        ],
        input="no\n",
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    Path("avdmanager.log").write_text(prepared.stdout + prepared.stderr)
    if prepared.returncode:
        raise RuntimeError(f"AVD creation failed: {prepared.stdout}\n{prepared.stderr}")
    command = [
        emulator,
        "-avd",
        "gramlab-probe",
        "-no-window",
        "-no-audio",
        "-no-boot-anim",
        "-no-snapshot",
        "-gpu",
        "swiftshader",
        "-accel",
        "on",
        "-cores",
        "2",
        "-memory",
        "2048",
        "-port",
        "5554",
        "-camera-back",
        "none",
        "-camera-front",
        "none",
        "-dns-server",
        "192.0.2.53",
        "-no-metrics",
    ]
    print("Starting the isolated AOSP guest", file=sys.stderr, flush=True)
    started = time.monotonic()
    with Path("emulator.log").open("w") as log:
        with subprocess.Popen(  # noqa: S603 — trusted profile, fixed emulator arguments
            command, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT
        ) as guest:
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
                            + Path("emulator.log").read_text()
                        )
                    boot = adb_command("shell", "getprop", "sys.boot_completed")
                    if boot.returncode == 0 and boot.stdout.strip() == "1":
                        ready = True
                        break
                    time.sleep(1)
                if not ready:
                    raise RuntimeError("Guest did not complete boot within 120 seconds")
                observations: dict[str, object] = {}
                for name, arguments in {
                    "api": ("shell", "getprop", "ro.build.version.sdk"),
                    "abi": ("shell", "getprop", "ro.product.cpu.abi"),
                    "fingerprint": ("shell", "getprop", "ro.build.fingerprint"),
                    "nc_help": ("shell", "toybox", "nc", "--help"),
                    "accounts": ("shell", "dumpsys", "account"),
                }.items():
                    observation = adb_command(*arguments)
                    if observation.returncode:
                        raise RuntimeError(f"Guest observation {name} failed: {observation.stderr}")
                    observations[name] = observation.stdout.strip()
                observations["network"] = probe_network(adb_command)
                observations["routes"] = adb_command(
                    "shell", "ip", "route", "show", "table", "all"
                ).stdout
                observations["interfaces"] = adb_command("shell", "ip", "address").stdout
                observations["host_interfaces"] = socket.if_nameindex()
                if extra_probe is not None:
                    observations["extra_probe"] = extra_probe(adb_command)
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
            finally:
                if guest.poll() is None:
                    guest.terminate()
                    try:
                        guest.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        guest.kill()
                        guest.wait()


if __name__ == "__main__":
    main()
