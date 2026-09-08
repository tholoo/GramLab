"""Terminate the actual trusted supervisor immediately after a chosen durable write."""

import json
import os
import runpy
import sys
from pathlib import Path
from typing import Protocol

phase = sys.argv[1]
if phase not in {"observation", "claim", "intent", "receipt", "corrupt", "nested_corrupt"}:
    raise ValueError("Unknown journal interruption phase")
original_fsync = os.fsync
journal = Path("rich-button-journal.jsonl")


class FileDescriptor(Protocol):
    def fileno(self) -> int: ...


def interrupt_after_durable_write(fd: int | FileDescriptor) -> None:
    original_fsync(fd)
    descriptor = fd if isinstance(fd, int) else fd.fileno()
    if os.readlink(f"/proc/self/fd/{descriptor}") != "/work/rich-button-journal.jsonl":
        return
    last = json.loads(journal.read_bytes().splitlines()[-1])
    if last["kind"] != ("claim" if phase in {"corrupt", "nested_corrupt"} else phase):
        return
    if phase in {"corrupt", "nested_corrupt"}:
        with journal.open("ab") as stream:
            stream.write(
                b'{"schema":1,}\n'
                if phase == "corrupt"
                else b'{"nested":' + b"[" * 2000 + b"0" + b"]" * 2000 + b"}\n"
            )
            stream.flush()
            original_fsync(stream.fileno())
    Path("interruption.json").write_text(json.dumps({"phase": phase, "sequence": last["sequence"]}))
    os._exit(71)  # Real abrupt process termination; no supervisor cleanup or observation write.


os.fsync = interrupt_after_durable_write
runpy.run_module("gramlab._run", run_name="__main__")
