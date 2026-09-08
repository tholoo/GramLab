"""Collect the actual ordinary-document codec and NativeByteBuffer probe."""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

from android_guest import main

_CLIENT = "/data/local/tmp/gramlab-document-codec-client.apk"
_PROBE = "/data/local/tmp/gramlab-document-codec-probe.apk"
_NATIVE = "/data/local/tmp/libtmessages.49.so"
_OUTPUT = "/data/local/tmp/gramlab-document-codec-output"
_LIMIT = 1024 * 1024


def probe(guest: Callable[..., subprocess.CompletedProcess[str]]) -> dict[str, object]:
    def require_success(*arguments: str, **kwargs: Any) -> None:
        result = guest(*arguments, **kwargs)
        if result.returncode:
            raise RuntimeError(f"Dedicated document-codec command failed: {arguments[0]}")

    require_success("push", "/work/client.apk", _CLIENT, timeout=30)
    require_success("push", "/work/document-codec-probe.apk", _PROBE, timeout=30)
    require_success("push", "/work/libtmessages.49.so", _NATIVE, timeout=30)
    require_success("shell", "rm", "-rf", _OUTPUT)
    try:
        result = guest(
            "shell",
            f"CLASSPATH={_PROBE}:{_CLIENT}",
            "/system/bin/app_process",
            "/system/bin",
            "org.telegram.gramlab.DocumentCodecProbe",
            _OUTPUT,
            _NATIVE,
            timeout=30,
        )
        if len(result.stdout.encode()) > _LIMIT or len(result.stderr.encode()) > _LIMIT:
            raise RuntimeError("Native document-codec process output exceeds the retained bound")
        Path("document-codec-process.json").write_text(
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
            raise RuntimeError("Native document-codec probe returned invalid JSON") from error
        require_success("pull", _OUTPUT, "/work/document-codec-native", timeout=30)
        retained_path = Path("document-codec-native/summary.json")
        if not retained_path.is_file() or retained_path.stat().st_size > _LIMIT:
            raise RuntimeError("Pulled native document-codec summary is missing or too large")
        try:
            retained = json.loads(retained_path.read_text())
        except json.JSONDecodeError as error:
            raise RuntimeError("Pulled native document-codec summary is invalid JSON") from error
        if retained != decoded:
            raise RuntimeError("Pulled native document-codec summary disagrees with process output")
        return {"returncode": result.returncode, "result": decoded}
    finally:
        guest("shell", "rm", "-rf", _OUTPUT, _CLIENT, _PROBE, _NATIVE)


if __name__ == "__main__":
    main(probe)
