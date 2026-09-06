"""Test-only line observation for the real trusted supervisor, without extra dependencies."""

import json
import runpy
import sys
import threading
from pathlib import Path
from types import FrameType
from typing import Any

executed: dict[str, set[int]] = {}


def observe(frame: FrameType, event: str, argument: Any) -> Any:
    filename = frame.f_code.co_filename
    if not filename.startswith("/work/gramlab/"):
        return None
    if event == "line":
        executed.setdefault(filename.removeprefix("/work/gramlab/"), set()).add(frame.f_lineno)
    return observe


sys.settrace(observe)
threading.settrace(observe)
try:
    runpy.run_module("gramlab._run", run_name="__main__")
finally:
    sys.settrace(None)
    threading.settrace(None)
    Path("supervisor-lines.json").write_text(
        json.dumps({name: sorted(lines) for name, lines in executed.items()})
    )
