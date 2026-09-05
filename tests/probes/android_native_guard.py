"""Run the real native request boundary without installing or starting the client application."""

import subprocess
from collections.abc import Callable
from pathlib import Path

from android_guest import main


def probe(adb: Callable[..., subprocess.CompletedProcess[str]]) -> dict[str, object]:
    for command in [
        ("shell", "mkdir", "-p", "/data/local/tmp/gramlab-probe"),
        ("push", "/work/client.apk", "/data/local/tmp/gramlab-probe/client.apk"),
        ("push", "/work/libtmessages.49.so", "/data/local/tmp/gramlab-probe/libtmessages.49.so"),
        (
            "shell",
            "chmod",
            "0444",
            "/data/local/tmp/gramlab-probe/client.apk",
            "/data/local/tmp/gramlab-probe/libtmessages.49.so",
        ),
    ]:
        result = adb(*command, timeout=30)
        if result.returncode:
            raise RuntimeError(f"Native probe preparation failed: {result.stderr}")
    result = adb(
        "shell",
        "CLASSPATH=/data/local/tmp/gramlab-probe/client.apk",
        "/system/bin/app_process",
        "/system/bin",
        "org.telegram.tgnet.NativeGuardProbe",
        "/data/local/tmp/gramlab-probe/libtmessages.49.so",
        timeout=30,
    )
    Path("native-probe.log").write_text(result.stdout + result.stderr)
    diagnostics = adb("logcat", "-d", "-v", "brief", timeout=15)
    Path("native-probe-logcat.txt").write_text(diagnostics.stdout + diagnostics.stderr)
    return {"returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr}


if __name__ == "__main__":
    main(probe)
