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
import socket
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
    posix_shell: str | None = None

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
            posix_shell=manifest.get("posixShell"),
        )


class Sandbox:
    """Run a process in a fresh, loopback-only Linux namespace."""

    def __init__(self, profile: RuntimeProfile) -> None:
        self.profile = profile

    def run(
        self, command: list[str], *, data: Path, timeout: float = 30, kvm: bool = False
    ) -> subprocess.CompletedProcess[str]:
        arguments = self._arguments(kvm=kvm)
        with _data_directory(data) as data_fd:
            arguments.extend(("--bind-fd", str(data_fd), "/work", "--chdir", "/work"))
            return _run_supervised(arguments, command, data_fd, timeout)

    def supervise(
        self, command: list[str], *, data: Path, timeout: float = 30, kvm: bool = False
    ) -> subprocess.CompletedProcess[str]:
        """Run trusted orchestration which may create restricted components on its network.

        Scenario/bot code belongs in component(), never directly in this supervisor.
        Only the supervisor can create further user namespaces; components cannot.
        """
        arguments = self._arguments(kvm=kvm, supervisor=True)
        bootstrap = [
            self.profile.python,
            "-c",
            "import os, sys; "
            "os.environ['GRAMLAB_SUPERVISOR_NETNS'] = os.readlink('/proc/self/ns/net'); "
            "os.execv(sys.argv[1], sys.argv[1:])",
            *command,
        ]
        with _data_directory(data) as data_fd:
            arguments.extend(("--bind-fd", str(data_fd), "/work", "--chdir", "/work"))
            return _run_supervised(arguments, bootstrap, data_fd, timeout)

    @contextmanager
    def component(
        self,
        command: list[str],
        *,
        data: Path,
        environment: Mapping[str, str] | None = None,
        startup_timeout: float = 10,
    ) -> Iterator[subprocess.Popen[str]]:
        """Open a private component inside trusted orchestration's offline network.

        The enclosing supervisor bounds total lifetime. Callers bound their interactive I/O;
        leaving this context kills and waits for the component's entire PID namespace.
        Only explicit environment values and this component's /work directory are supplied.
        """
        if os.environ.get("GRAMLAB_SUPERVISOR_NETNS") != os.readlink("/proc/self/ns/net") or [
            name for _, name in socket.if_nameindex()
        ] != ["lo"]:
            raise RuntimeError("Components require a trusted isolated run supervisor")
        if environment and "GRAMLAB_SUPERVISOR_NETNS" in environment:
            raise ValueError("The supervisor namespace marker is reserved")
        arguments = self._arguments(shared_network=True)
        for name, value in (environment or {}).items():
            arguments.extend(("--setenv", name, value))
        with _data_directory(data) as data_fd:
            arguments.extend(("--bind-fd", str(data_fd), "/work", "--chdir", "/work"))
            with _open_supervised(
                arguments, command, data_fd, startup_timeout, interactive=True
            ) as process:
                yield process

    def _arguments(
        self, *, kvm: bool = False, supervisor: bool = False, shared_network: bool = False
    ) -> list[str]:
        arguments = [
            self.profile.bubblewrap,
            "--unshare-user",
            "--unshare-pid",
            "--unshare-ipc",
            "--unshare-uts",
            "--unshare-cgroup",
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
        if not shared_network:
            arguments.append("--unshare-net")
        if not supervisor:
            arguments.append("--disable-userns")
        else:
            # Mapping parent UID 0 into another user namespace requires CAP_SETFCAP.
            # Use a fixed non-root namespace identity instead of retaining capabilities.
            arguments.extend(("--uid", "65534", "--gid", "65534"))
        for path in self.profile.store_paths:
            arguments.extend(("--ro-bind", path, path))
        if self.profile.posix_shell is not None:
            # SDK Ninja invokes /bin/sh directly. Resolve it only to the trusted closure.
            arguments.extend(("--symlink", self.profile.posix_shell, "/bin/sh"))
        for name, value in self.profile.environment:
            arguments.extend(("--setenv", name, value))
        if kvm:
            arguments.extend(("--dev-bind", "/dev/kvm", "/dev/kvm"))
        return arguments


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
    with _open_supervised(arguments, command, data_fd, timeout) as process:
        stdout, stderr = process.communicate(timeout=max(0, deadline - time.monotonic()))
        return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)


@contextmanager
def _open_supervised(
    arguments: list[str],
    command: list[str],
    data_fd: int,
    timeout: float,
    *,
    interactive: bool = False,
) -> Iterator[subprocess.Popen[str]]:
    deadline = time.monotonic() + timeout
    # Pin the namespace's init with a pidfd before allowing the workload to start.
    # Waiting only for bwrap (or for stdout EOF) races with descendant teardown.
    with _pipe() as (info_reader, info_writer), _pipe() as (gate_reader, gate_writer):
        arguments.extend(
            ("--info-fd", str(info_writer.fileno()), "--block-fd", str(gate_reader.fileno()))
        )
        with subprocess.Popen(  # noqa: S603 — trusted profile, argv execution without a shell
            [*arguments, "--", *command],
            stdin=subprocess.PIPE if interactive else subprocess.DEVNULL,
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
                yield process
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
