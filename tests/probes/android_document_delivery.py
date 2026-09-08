"""Retain actual bridge/loader cases and a second native process's cache results."""

from __future__ import annotations

import base64
import gzip
import hashlib
import io
import json
import shlex
import subprocess
import sys
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
_ROOTS = {"document-delivery-probe", "document-delivery-diagnostics", "account3", "gramlab"}


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


def _safe_text(value: str | bytes | None) -> str:
    text = value.decode("utf-8", errors="replace") if isinstance(value, bytes) else value or ""
    return (
        text.replace(_SECRET, "[REDACTED]")
        .encode("utf-8", errors="replace")[:_PROCESS_LIMIT]
        .decode("utf-8", errors="ignore")
    )


def _record(path: str, value: dict[str, Any]) -> None:
    with Path(path).open("x") as output:
        output.write(json.dumps(value, indent=2) + "\n")


def decoded_archive(stdout: str) -> bytes:
    # head bounds compressed bytes before base64; allow its standard wrapped output.
    encoded_limit = ((_ARCHIVE_LIMIT + 3) // 3) * 4
    if len(stdout) > encoded_limit + (encoded_limit + 63) // 64 + 4:
        raise ValueError("Native archive exceeds encoded bound")
    encoded = stdout.replace("\r", "").replace("\n", "").encode("ascii", errors="strict")
    data = base64.b64decode(encoded, validate=True)
    if len(data) > _ARCHIVE_LIMIT:
        raise ValueError("Native archive exceeds compressed bound")
    return data


def _stdout_record(value: str | bytes | None, opaque: bool) -> dict[str, Any]:
    if not opaque:
        return {"stdout": _safe_text(value)}
    data = value if isinstance(value, bytes) else (value or "").encode("utf-8", errors="replace")
    return {"stdout_encoded_bytes": len(data), "stdout_sha256": hashlib.sha256(data).hexdigest()}


def _observed_command(
    guest: Callable[..., subprocess.CompletedProcess[str]],
    path: str,
    *args: str,
    timeout: int,
    opaque_stdout: bool = False,
) -> subprocess.CompletedProcess[str]:
    try:
        result = guest(*args, timeout=timeout)
    except subprocess.TimeoutExpired as error:
        try:
            _record(
                path,
                {
                    "exception": "TimeoutExpired",
                    "timeout": error.timeout,
                    **_stdout_record(error.stdout, opaque_stdout),
                    "stderr": _safe_text(error.stderr),
                },
            )
        except Exception:  # noqa: S110 — preserve the original timeout when retention is unwritable.
            pass
        raise
    except Exception as error:
        try:
            _record(path, {"exception": type(error).__name__, "message": _safe_text(str(error))})
        except Exception:  # noqa: S110 — preserve the original command error if retention fails.
            pass
        raise
    _record(
        path,
        {
            "returncode": result.returncode,
            **_stdout_record(result.stdout, opaque_stdout),
            "stderr": _safe_text(result.stderr),
            "stdout_truncated": len(result.stdout.encode()) > _PROCESS_LIMIT,
            "stderr_truncated": len(result.stderr.encode()) > _PROCESS_LIMIT,
        },
    )
    return result


def _retain_archive(guest: Callable[..., subprocess.CompletedProcess[str]]) -> None:
    archive = "files/document-delivery-evidence.tar.gz"
    # Include every present allowlisted root; initialization failures need no suite directory.
    roots = " ".join(sorted(_ROOTS))
    packing = (
        "cd files || exit; set --; "
        f'for root in {roots}; do if [ -d "$root" ]; then set -- "$@" "$root"; fi; done; '
        '[ "$#" -gt 0 ] || exit 44; '
        'tar -czf document-delivery-evidence.tar.gz -- "$@"'
    )
    pack_error: Exception | None = None
    try:
        packed = _observed_command(
            guest,
            "document-delivery-archive-status.json",
            "shell",
            "-T",
            shlex.join(["run-as", _PACKAGE, "sh", "-c", packing]),
            timeout=30,
        )
        if packed.returncode:
            pack_error = RuntimeError("Native archive packing failed")
    except Exception as error:
        pack_error = error
    extraction = (
        f"if [ -f {archive} ]; then head -c {_ARCHIVE_LIMIT + 1} {archive} | base64; "
        "else exit 44; fi"
    )
    pulled = _observed_command(
        guest,
        "document-delivery-pull-status.json",
        "shell",
        "-T",
        shlex.join(["run-as", _PACKAGE, "sh", "-c", extraction]),
        timeout=30,
        opaque_stdout=True,
    )
    if pulled.returncode:
        raise RuntimeError("Native archive retrieval failed")
    data = decoded_archive(pulled.stdout)
    with Path("native.tar.gz").open("xb") as output:
        output.write(data)
    unpack_evidence(Path("native.tar.gz"), Path("document-delivery-native"))
    if pack_error is not None:
        raise pack_error


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
            result = _observed_command(
                guest,
                f"document-delivery-{mode}-process.json",
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
            code, decoded = instrumentation_result(safe_stdout)
            results[mode] = {
                "returncode": result.returncode,
                "instrumentation_code": code,
                "result": decoded,
            }
            if result.returncode or code:
                break
    finally:
        original_error = sys.exception()
        try:
            _retain_archive(guest)
        except Exception as error:
            try:
                _record(
                    "document-delivery-retention-error.json",
                    {
                        "exception": type(error).__name__,
                        "message": _safe_text(str(error)),
                    },
                )
            except Exception:
                if original_error is None:
                    raise
            if original_error is None:
                raise
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
