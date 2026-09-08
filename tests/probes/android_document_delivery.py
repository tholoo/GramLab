"""Retain actual bridge/loader cases and a second native process's cache results."""

from __future__ import annotations

import gzip
import hashlib
import io
import json
import shlex
import subprocess
import tarfile
from collections.abc import Callable
from pathlib import Path, PurePosixPath
from typing import Any

from android_guest import main

_PACKAGE = "org.gramlab.android"
_REMOTE = "/data/local/tmp/gramlab-document-delivery"
_INSTRUMENTATION = (
    "org.gramlab.documentdeliveryprobe/org.telegram.gramlab.DocumentDeliveryInstrumentation"
)
_SECRET = "gramlab-client_ddddddddddddddddddddddddddddddddddddddddddd"  # noqa: S105 — fixture only
_PROCESS_LIMIT = 1024 * 1024
_ARCHIVE_LIMIT = 4 * 1024 * 1024
_EXPANDED_LIMIT = 16 * 1024 * 1024
_ROOTS = {"document-delivery-probe", "account3", "gramlab"}


def unpack_evidence(archive: Path, destination: Path) -> None:
    """Publish only a fully checked bounded archive from the dedicated app UID."""
    if archive.stat().st_size > _ARCHIVE_LIMIT:
        raise ValueError("Native archive exceeds compressed bound")
    with gzip.open(archive, "rb") as source:
        data = source.read(_EXPANDED_LIMIT + 1)
    if len(data) > _EXPANDED_LIMIT:
        raise ValueError("Native archive exceeds expanded bound")
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:") as source:
        members = source.getmembers()
        if len(members) > 512:
            raise ValueError("Native archive exceeds member bound")
        names: set[str] = set()
        retained: list[tuple[PurePosixPath, bytes]] = []
        for member in members:
            path = PurePosixPath(member.name)
            if (
                path.is_absolute()
                or not path.parts
                or path.parts[0] not in _ROOTS
                or any(part in ("", ".", "..") for part in member.name.rstrip("/").split("/"))
                or "\\" in member.name
                or path.as_posix() in names
                or not (member.isfile() or member.isdir())
            ):
                raise ValueError("Native archive has unsafe or duplicate member")
            names.add(path.as_posix())
            if member.isfile():
                stream = source.extractfile(member)
                if stream is None:
                    raise ValueError("Native archive member is unavailable")
                with stream:
                    payload = stream.read()
                if len(payload) != member.size or _SECRET.encode() in payload:
                    raise ValueError("Native archive has invalid or secret-bearing payload")
                retained.append((path, payload))
        files = {path for path, _ in retained}
        if any(parent in files for path in files for parent in path.parents):
            raise ValueError("Native archive has conflicting file and directory paths")
        # Validation precedes publication; a malformed member cannot leave an accepted prefix.
        destination.mkdir()
        for path, payload in retained:
            target = destination.joinpath(*path.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as output:
                output.write(payload)


def instrumentation_result(stdout: str) -> tuple[int, dict[str, Any]]:
    """Require the complete platform -w/-r result emitted by this exact probe."""
    if len(stdout.encode()) > _PROCESS_LIMIT:
        raise ValueError("Instrumentation output exceeds bound")
    lines = stdout.splitlines()
    prefix = "INSTRUMENTATION_RESULT: document_delivery="
    code_prefix = "INSTRUMENTATION_CODE: "
    if len(lines) != 2 or not lines[0].startswith(prefix) or not lines[1].startswith(code_prefix):
        raise ValueError("Malformed instrumentation result framing")
    code_text = lines[1][len(code_prefix) :]
    if code_text not in ("0", "1", "2"):
        raise ValueError("Unknown instrumentation result code")
    value = json.loads(lines[0][len(prefix) :])
    if not isinstance(value, dict):
        raise ValueError("Instrumentation result must be an object")
    return int(code_text), value


def probe(guest: Callable[..., subprocess.CompletedProcess[str]]) -> dict[str, object]:
    def command(*args: str, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        result = guest(*args, **kwargs)
        if result.returncode:
            raise RuntimeError(f"Dedicated document-delivery command failed: {args[0]}")
        return result

    def shell(*args: str, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        return command("shell", "-T", shlex.join(args), **kwargs)

    command("install", "-r", "/work/client.apk", timeout=60)
    command("install", "-t", "-r", "/work/document-delivery-probe.apk", timeout=60)
    shell("mkdir", _REMOTE)
    shell("chmod", "777", _REMOTE)
    command("push", "/work/emoji-static.webp", f"{_REMOTE}/emoji.webp", timeout=30)
    shell("run-as", _PACKAGE, "mkdir", "-p", "files")
    shell("run-as", _PACKAGE, "cp", f"{_REMOTE}/emoji.webp", "files/delivery-emoji.webp")
    results: dict[str, object] = {}
    try:
        for mode in ("suite", "restart"):
            result = guest(
                "shell",
                "-T",
                shlex.join(
                    [
                        "am",
                        "instrument",
                        "-w",
                        "-r",
                        "-e",
                        "mode",
                        mode,
                        _INSTRUMENTATION,
                    ]
                ),
                timeout=240,
            )
            if max(len(result.stdout.encode()), len(result.stderr.encode())) > _PROCESS_LIMIT:
                raise RuntimeError("Native document-delivery output exceeds bound")
            safe_stdout = result.stdout.replace(_SECRET, "[REDACTED]")
            safe_stderr = result.stderr.replace(_SECRET, "[REDACTED]")
            Path(f"document-delivery-{mode}-process.json").write_text(
                json.dumps(
                    {
                        "returncode": result.returncode,
                        "stdout": safe_stdout,
                        "stderr": safe_stderr,
                    },
                    indent=2,
                )
                + "\n"
            )
            code, decoded = instrumentation_result(safe_stdout)
            results[mode] = {
                "returncode": result.returncode,
                "instrumentation_code": code,
                "result": decoded,
            }
            if result.returncode or code:
                break
    finally:
        # Retain partial original evidence on failure. Missing outputs cannot become success.
        packed = guest(
            "shell",
            "-T",
            shlex.join(
                [
                    "run-as",
                    _PACKAGE,
                    "tar",
                    "-czf",
                    f"{_REMOTE}/evidence.tar.gz",
                    "-C",
                    "files",
                    "document-delivery-probe",
                    "account3",
                    "gramlab",
                ]
            ),
            timeout=30,
        )
        Path("document-delivery-archive-status.json").write_text(
            json.dumps({"returncode": packed.returncode}) + "\n"
        )
        pulled = guest("pull", f"{_REMOTE}/evidence.tar.gz", "/work/native.tar.gz", timeout=30)
        if pulled.returncode == 0 and Path("native.tar.gz").is_file():
            unpack_evidence(Path("native.tar.gz"), Path("document-delivery-native"))
    for mode, value in results.items():
        if not isinstance(value, dict):
            raise RuntimeError("Native result has invalid shape")
        retained = Path(f"document-delivery-native/document-delivery-probe/{mode}-summary.json")
        if not retained.is_file() or retained.stat().st_size > _PROCESS_LIMIT:
            raise RuntimeError("Native summary is missing or exceeds bound")
        if json.loads(retained.read_text()) != value["result"]:
            raise RuntimeError("Native summary disagrees with original process output")
    return {
        "processes": results,
        "bootstrap_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "archive_sha256": hashlib.sha256(Path("native.tar.gz").read_bytes()).hexdigest(),
    }


if __name__ == "__main__":
    main(probe)
