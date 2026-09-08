"""Collect the actual native rich-button disarm reflection probe."""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

from android_guest import main

_CLIENT = "/data/local/tmp/gramlab-button-disarm-client.apk"
_PROBE = "/data/local/tmp/gramlab-button-disarm-probe.apk"
_OUTPUT = "/data/local/tmp/gramlab-button-disarm-output"
_LIMIT = 1024 * 1024


def probe(guest: Callable[..., subprocess.CompletedProcess[str]]) -> dict[str, object]:
    def require_success(*arguments: str, **kwargs: Any) -> None:
        result = guest(*arguments, **kwargs)
        if result.returncode:
            raise RuntimeError(f"Dedicated button-disarm command failed: {arguments[0]}")

    require_success("push", "/work/client.apk", _CLIENT, timeout=30)
    require_success("push", "/work/button-disarm-probe.apk", _PROBE, timeout=30)
    require_success("shell", "rm", "-rf", _OUTPUT)
    try:
        result = guest(
            "shell",
            f"CLASSPATH={_PROBE}:{_CLIENT}",
            "/system/bin/app_process",
            "/system/bin",
            "org.telegram.gramlab.ButtonDisarmProbe",
            _OUTPUT,
            timeout=30,
        )
        if len(result.stdout.encode()) > _LIMIT or len(result.stderr.encode()) > _LIMIT:
            raise RuntimeError("Native button-disarm process output exceeds the retained bound")
        Path("button-disarm-process.json").write_text(
            json.dumps(
                {
                    "returncode": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                },
                indent=2,
            )
            + "\n"
        )
        try:
            decoded = json.loads(result.stdout)
        except json.JSONDecodeError as error:
            raise RuntimeError("Native button-disarm probe returned invalid JSON") from error
        require_success("pull", _OUTPUT, "/work/button-disarm-native", timeout=30)
        return {"returncode": result.returncode, "result": decoded}
    finally:
        guest("shell", "rm", "-rf", _OUTPUT, _CLIENT, _PROBE)


if __name__ == "__main__":
    main(probe)
