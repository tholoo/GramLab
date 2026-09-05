"""Observe real processes at the approved isolation boundary."""

import errno
import fcntl
import json
import os
import select
import socket
import subprocess
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

import pytest

from gramlab.runtime import RuntimeProfile, Sandbox


def test_child_can_exchange_local_tcp_without_host_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HTTP_PROXY", "http://parent-proxy.invalid:9999")
    profile = RuntimeProfile.load(Path(os.environ["GRAMLAB_RUNTIME_PROFILE"]))
    result = Sandbox(profile).run(
        [
            profile.python,
            "-c",
            """
import json, os, socket
with socket.socket() as server:
    server.bind(('127.0.0.1', 0))
    server.listen()
    with socket.create_connection(server.getsockname(), timeout=2) as sender:
        receiver, _ = server.accept()
        with receiver:
            sender.sendall(b'hello world')
            payload = receiver.recv(32).decode()
print(json.dumps({'payload': payload, 'proxy': os.environ.get('HTTP_PROXY'),
                  'cwd': os.getcwd(), 'hostname': socket.gethostname()}))
""",
        ],
        data=tmp_path,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {
        "payload": "hello world",
        "proxy": None,
        "cwd": "/work",
        "hostname": "gramlab",
    }


def test_child_cannot_reach_parent_or_external_ipv4_ipv6(tmp_path: Path) -> None:
    profile = RuntimeProfile.load(Path(os.environ["GRAMLAB_RUNTIME_PROFILE"]))
    with socket.socket() as parent_server:
        parent_server.bind(("127.0.0.1", 0))
        parent_server.listen()
        parent_server.settimeout(0.1)
        result = Sandbox(profile).run(
            [
                profile.python,
                "-c",
                """
import json, os, socket, sys
results = {}
for label, family, kind, address in [
    ('parent', socket.AF_INET, socket.SOCK_STREAM, ('127.0.0.1', int(sys.argv[1]))),
    ('ipv4', socket.AF_INET, socket.SOCK_STREAM, ('192.0.2.1', 443)),
    ('ipv6', socket.AF_INET6, socket.SOCK_STREAM, ('2001:db8::1', 443)),
    ('dns', socket.AF_INET, socket.SOCK_DGRAM, ('192.0.2.53', 53)),
]:
    with socket.socket(family, kind) as client:
        client.settimeout(1)
        try:
            client.connect(address)
        except OSError as error:
            results[label] = error.errno
        else:
            results[label] = 'CONNECTED'
print(json.dumps({'errors': results, 'net': os.readlink('/proc/self/ns/net'),
                  'interfaces': socket.if_nameindex()}))
""",
                str(parent_server.getsockname()[1]),
            ],
            data=tmp_path,
        )
        assert result.returncode == 0, result.stderr
        observed = json.loads(result.stdout)
        assert observed["errors"] == {
            "parent": errno.ECONNREFUSED,
            "ipv4": errno.ENETUNREACH,
            "ipv6": errno.ENETUNREACH,
            "dns": errno.ENETUNREACH,
        }
        assert observed["net"] != os.readlink("/proc/self/ns/net")
        assert observed["interfaces"] == [[1, "lo"]]
        with pytest.raises(TimeoutError):
            parent_server.accept()


def test_child_cannot_read_parent_files_or_inherit_open_descriptors(tmp_path: Path) -> None:
    profile = RuntimeProfile.load(Path(os.environ["GRAMLAB_RUNTIME_PROFILE"]))
    secret = tmp_path / "parent-only"
    secret.write_text("synthetic parent sentinel")
    data = tmp_path / "run"
    data.mkdir()
    # A pre-existing symlink cannot reveal anything outside the mounted run directory.
    (data / "escape").symlink_to(secret)
    with secret.open() as stream:
        os.set_inheritable(stream.fileno(), True)
        result = Sandbox(profile).run(
            [
                profile.python,
                "-c",
                """
import json, os, pathlib, sys
readable = []
for name in [sys.argv[1], '/work/escape', '/proc/1/root' + sys.argv[1]]:
    try:
        pathlib.Path(name).read_text()
    except OSError:
        continue
    readable.append(name)
leaked_fds = []
for fd in pathlib.Path('/proc/self/fd').iterdir():
    try:
        if os.readlink(fd) == sys.argv[1]:
            leaked_fds.append(fd.name)
    except FileNotFoundError:
        continue
pathlib.Path('result.txt').write_text('owned artifact')
print(json.dumps({'readable': readable, 'leaked_fds': leaked_fds,
                  'home': pathlib.Path('/home').exists(),
                  'run': list(pathlib.Path('/run').iterdir())}))
""",
                str(secret),
            ],
            data=data,
        )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"readable": [], "leaked_fds": [], "home": False, "run": []}
    assert (data / "result.txt").read_text() == "owned artifact"
    assert secret.read_text() == "synthetic parent sentinel"


@pytest.mark.parametrize("finish", ["exit", "timeout"])
def test_detached_descendants_die_with_the_run(tmp_path: Path, finish: str) -> None:
    profile = RuntimeProfile.load(Path(os.environ["GRAMLAB_RUNTIME_PROFILE"]))
    command = [
        profile.python,
        "-c",
        """
import fcntl, os, pathlib, signal, sys
reader, writer = os.pipe()
if os.fork() == 0:
    os.close(reader)
    os.setsid()
    with open('descendant.lock', 'w') as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        pathlib.Path('descendant.started').write_text('ready')
        os.write(writer, b'1')
        os.close(writer)
        while True:
            signal.pause()
os.close(writer)
assert os.read(reader, 1) == b'1'
os.close(reader)
if sys.argv[1] == 'timeout':
    while True:
        signal.pause()
""",
        finish,
    ]
    if finish == "timeout":
        with pytest.raises(subprocess.TimeoutExpired):
            Sandbox(profile).run(command, data=tmp_path, timeout=2)
    else:
        result = Sandbox(profile).run(command, data=tmp_path, timeout=2)
        assert result.returncode == 0, result.stderr
    assert (tmp_path / "descendant.started").read_text() == "ready"
    # The detached child holds this lock for its entire lifetime, including across setsid.
    with (tmp_path / "descendant.lock").open() as stream:
        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)


def test_symlinked_data_directory_is_rejected_before_startup(tmp_path: Path) -> None:
    profile = RuntimeProfile.load(Path(os.environ["GRAMLAB_RUNTIME_PROFILE"]))
    unrelated = tmp_path / "unrelated"
    unrelated.mkdir()
    alias = tmp_path / "alias"
    alias.symlink_to(unrelated, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        Sandbox(profile).run([profile.python, "-c", "open('started', 'w').close()"], data=alias)
    assert list(unrelated.iterdir()) == []


def test_missing_runtime_dependency_prevents_workload_startup(tmp_path: Path) -> None:
    profile = RuntimeProfile.load(Path(os.environ["GRAMLAB_RUNTIME_PROFILE"]))
    broken_profile = replace(profile, store_paths=(*profile.store_paths, str(tmp_path / "missing")))
    result = Sandbox(broken_profile).run(
        [profile.python, "-c", "open('started', 'w').close()"], data=tmp_path
    )
    assert result.returncode != 0
    assert "No such file or directory" in result.stderr
    assert not (tmp_path / "started").exists()


def test_immutable_dependencies_and_privileges_cannot_be_changed(tmp_path: Path) -> None:
    profile = RuntimeProfile.load(Path(os.environ["GRAMLAB_RUNTIME_PROFILE"]))
    result = Sandbox(profile).run(
        [
            profile.python,
            "-c",
            """
import json, os, pathlib, sys
lines = pathlib.Path('/proc/self/status').read_text().splitlines()
status = dict(line.split(':', 1) for line in lines)
try:
    descriptor = os.open(sys.executable, os.O_WRONLY)
except OSError as error:
    write_error = error.errno
else:
    os.close(descriptor)
    write_error = 'WRITABLE'
try:
    os.unshare(os.CLONE_NEWUSER)
except OSError as error:
    namespace_error = error.errno
else:
    namespace_error = 'CREATED'
print(json.dumps({'write_error': write_error, 'namespace_error': namespace_error,
                  'caps': int(status['CapEff'], 16), 'new_privs': int(status['NoNewPrivs']),
                  'mounts': [line.split()[5].split(',') for line in
                             pathlib.Path('/proc/self/mountinfo').read_text().splitlines()
                             if line.split()[4].startswith('/nix/store/')]}))
""",
        ],
        data=tmp_path,
    )
    assert result.returncode == 0, result.stderr
    observed = json.loads(result.stdout)
    # The VFS may reject permissions before checking the read-only mount flag.
    assert observed["write_error"] in (errno.EROFS, errno.EACCES)
    assert observed["mounts"]
    assert all("ro" in options for options in observed["mounts"])
    assert observed["namespace_error"] in (errno.ENOSPC, errno.EPERM)
    assert observed["caps"] == 0
    assert observed["new_privs"] == 1


def test_concurrent_runs_can_use_the_same_port_without_sharing_data(tmp_path: Path) -> None:
    profile = RuntimeProfile.load(Path(os.environ["GRAMLAB_RUNTIME_PROFILE"]))
    with ThreadPoolExecutor(max_workers=2) as workers:
        runs = []
        descriptors = []
        try:
            for name in ("first", "second"):
                data = tmp_path / name
                data.mkdir()
                (data / "identity").write_text(name)
                for channel in ("ready", "release"):
                    os.mkfifo(data / channel)
                    descriptors.append(os.open(data / channel, os.O_RDWR | os.O_CLOEXEC))
                runs.append(
                    workers.submit(
                        Sandbox(profile).run,
                        [
                            profile.python,
                            "-c",
                            """
import json, os, pathlib, socket
with socket.socket() as server:
    server.bind(('127.0.0.1', 16837))
    server.listen()
    with open('ready', 'wb', buffering=0) as ready:
        ready.write(b'1')
    with open('release', 'rb', buffering=0) as release:
        assert release.read(1) == b'1'
    print(json.dumps({'identity': pathlib.Path('identity').read_text(),
                      'net': os.readlink('/proc/self/ns/net')}))
""",
                        ],
                        data=data,
                        timeout=5,
                    )
                )
            for ready in descriptors[::2]:
                assert select.select([ready], [], [], 3)[0], "Run did not reach the barrier"
                assert os.read(ready, 1) == b"1"
            for release in descriptors[1::2]:
                os.write(release, b"1")
            results = [run.result() for run in runs]
        finally:
            for descriptor in descriptors:
                os.close(descriptor)
    assert all(result.returncode == 0 for result in results), results
    observed = [json.loads(result.stdout) for result in results]
    assert [item["identity"] for item in observed] == ["first", "second"]
    assert observed[0]["net"] != observed[1]["net"]
