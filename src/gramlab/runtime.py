"""Linux process containment for the approved offline prototype.

Profiles are trusted, Nix-generated provisioning inputs. Commands run with only their
immutable dependency closure and an explicitly selected writable data directory.
This is an internal foundation, not the public scenario or world API.
"""

from __future__ import annotations

import errno
import json
import os
import select
import signal
import subprocess
import time
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import BinaryIO


@dataclass(frozen=True)
class RuntimeProfile:
    """Provisioned executables and their immutable runtime dependencies."""

    bubblewrap: str
    python: str
    store_paths: tuple[str, ...]
    executables: Mapping[str, str] = field(default_factory=dict)
    environment: tuple[tuple[str, str], ...] = ()

    @classmethod
    def load(cls, path: Path) -> RuntimeProfile:
        manifest = json.loads(path.read_text())
        if manifest["schema"] != 1:
            raise ValueError("Unsupported runtime profile schema")
        return cls(
            bubblewrap=manifest["bubblewrap"],
            python=manifest["python"],
            store_paths=tuple(Path(manifest["storePaths"]).read_text().splitlines()),
            executables=manifest.get("executables", {}),
            environment=tuple(manifest.get("environment", {}).items()),
        )


class Sandbox:
    """Run a process in a fresh, loopback-only Linux namespace."""

    def __init__(self, profile: RuntimeProfile) -> None:
        self.profile = profile

    def run(
        self, command: list[str], *, data: Path, timeout: float = 30, kvm: bool = False
    ) -> subprocess.CompletedProcess[str]:
        arguments = [
            self.profile.bubblewrap,
            "--unshare-user",
            "--unshare-pid",
            "--unshare-net",
            "--unshare-ipc",
            "--unshare-uts",
            "--unshare-cgroup",
            "--disable-userns",
            "--die-with-parent",
            "--new-session",
            "--cap-drop",
            "ALL",
            "--hostname",
            "gramlab",
            "--clearenv",
            "--setenv",
            "LANG",
            "C.UTF-8",
            "--proc",
            "/proc",
            "--dev",
            "/dev",
            "--tmpfs",
            "/tmp",  # noqa: S108 — private tmpfs, no host /tmp
            "--tmpfs",
            "/run",
        ]
        for path in self.profile.store_paths:
            arguments.extend(("--ro-bind", path, path))
        for name, value in self.profile.environment:
            arguments.extend(("--setenv", name, value))
        if kvm:
            arguments.extend(("--dev-bind", "/dev/kvm", "/dev/kvm"))
        with _data_directory(data) as data_fd:
            arguments.extend(("--bind-fd", str(data_fd), "/work", "--chdir", "/work"))
            return _run_supervised(arguments, command, data_fd, timeout)


@contextmanager
def _data_directory(path: Path) -> Iterator[int]:
    # Walk directory handles without following symlinks. Keep the final handle alive
    # through mount setup so a concurrent rename cannot redirect the bind mount.
    directory = os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        for part in path.absolute().parts[1:]:
            try:
                child = os.open(
                    part,
                    os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                    dir_fd=directory,
                )
            except OSError as error:
                if error.errno in (errno.ELOOP, errno.ENOTDIR):
                    raise ValueError(
                        "Data path must contain directories without symlinks"
                    ) from error
                raise
            os.close(directory)
            directory = child
        yield directory
    finally:
        os.close(directory)


@contextmanager
def _pipe() -> Iterator[tuple[BinaryIO, BinaryIO]]:
    reader, writer = os.pipe2(os.O_CLOEXEC)
    with os.fdopen(reader, "rb", buffering=0) as incoming:
        with os.fdopen(writer, "wb", buffering=0) as outgoing:
            yield incoming, outgoing


def _run_supervised(
    arguments: list[str], command: list[str], data_fd: int, timeout: float
) -> subprocess.CompletedProcess[str]:
    deadline = time.monotonic() + timeout
    # Pin the namespace's init with a pidfd before allowing the workload to start.
    # Waiting only for bwrap (or for stdout EOF) races with descendant teardown.
    with _pipe() as (info_reader, info_writer), _pipe() as (gate_reader, gate_writer):
        arguments.extend(
            ("--info-fd", str(info_writer.fileno()), "--block-fd", str(gate_reader.fileno()))
        )
        with subprocess.Popen(  # noqa: S603 — trusted profile, argv execution without a shell
            [*arguments, "--", *command],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            close_fds=True,
            pass_fds=(data_fd, info_writer.fileno(), gate_reader.fileno()),
            start_new_session=True,
        ) as process:
            init_fd = None
            try:
                info_writer.close()
                gate_reader.close()
                info = bytearray()
                while True:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0 or not select.select([info_reader], [], [], remaining)[0]:
                        raise subprocess.TimeoutExpired(command, timeout)
                    chunk = info_reader.read(65536)
                    if not chunk:
                        break
                    info.extend(chunk)
                if info:
                    pid = json.loads(info)["child-pid"]
                    try:
                        init_fd = os.pidfd_open(pid)
                    except ProcessLookupError:
                        pass  # Setup failed; no workload passed the gate.
                    else:
                        try:
                            gate_writer.write(b"1")
                        except BrokenPipeError:
                            pass  # Mount setup failed after reporting its process ID.
                stdout, stderr = process.communicate(timeout=max(0, deadline - time.monotonic()))
                return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)
            finally:
                # Kill the namespace init, including descendants that changed sessions.
                # pidfds cannot accidentally signal a subsequently reused numeric PID.
                try:
                    if init_fd is not None:
                        try:
                            try:
                                signal.pidfd_send_signal(init_fd, signal.SIGKILL)
                            except ProcessLookupError:
                                pass
                            if not select.select([init_fd], [], [], 10)[0]:
                                raise RuntimeError("Runtime namespace did not finish cleanup")
                        finally:
                            os.close(init_fd)
                finally:
                    # Before the startup gate opens, setup children still share the
                    # launcher's process group and may not have installed PDEATHSIG.
                    if process.returncode is None:
                        try:
                            os.killpg(process.pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                    process.communicate()
