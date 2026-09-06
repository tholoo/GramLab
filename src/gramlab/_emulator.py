"""Prepare and execute one emulator entirely within its private runtime component."""

import os
import subprocess
import sys
from pathlib import Path


def main() -> None:
    emulator, avdmanager, image_package = sys.argv[1:]
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
        "swangle",
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
        # The pinned Netsim forwarding path stalls local TCP handshakes. Keep
        # Virtio Wi-Fi, using the emulator's built-in forwarding implementation.
        "-feature",
        "-WiFiPacketStream",
    ]
    with Path("emulator.log").open("w") as log:
        os.dup2(log.fileno(), 1)
        os.dup2(log.fileno(), 2)
        os.execv(command[0], command)  # noqa: S606 — pinned executable and fixed emulator arguments


if __name__ == "__main__":
    main()
