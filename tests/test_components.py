"""Real components share one offline network without sharing private files or processes."""

import errno
import fcntl
import json
import os
import shutil
import subprocess
from dataclasses import asdict
from pathlib import Path

import pytest

from gramlab.runtime import RuntimeProfile, Sandbox


def test_component_reaches_run_service_without_supervisor_files_or_privileges(
    tmp_path: Path,
) -> None:
    profile = RuntimeProfile.load(Path(os.environ["GRAMLAB_RUNTIME_PROFILE"]))
    shutil.copytree(
        "src/gramlab", tmp_path / "gramlab", ignore=shutil.ignore_patterns("__pycache__")
    )
    (tmp_path / "profile.json").write_text(json.dumps(asdict(profile)))
    (tmp_path / "world-secret").write_text("supervisor-only synthetic data")
    bot = tmp_path / "bot"
    bot.mkdir()
    (bot / "escape").symlink_to("/work/world-secret")
    (bot / "client.py").write_text(
        """
import json, os, pathlib, socket, sys
with socket.create_connection(('127.0.0.1', int(sys.argv[1])), timeout=2) as connection:
    connection.sendall(b'component')
    reply = connection.recv(64).decode()
readable = []
for name in ['/work/world-secret', '/work/escape', '/proc/1/root/work/world-secret']:
    try:
        pathlib.Path(name).read_text()
    except OSError:
        continue
    readable.append(name)
inherited = []
for fd in pathlib.Path('/proc/self/fd').iterdir():
    try:
        if 'world-secret' in os.readlink(fd):
            inherited.append(fd.name)
    except FileNotFoundError:
        pass
try:
    os.unshare(os.CLONE_NEWUSER)
except OSError as error:
    namespace_error = error.errno
else:
    namespace_error = None
with socket.socket() as connection:
    try:
        connection.connect(('192.0.2.1', 443))
    except OSError as error:
        external_error = error.errno
    else:
        external_error = None
lines = pathlib.Path('/proc/self/status').read_text().splitlines()
status = dict(line.split(':', 1) for line in lines)
pathlib.Path('state.txt').write_text('private bot state')
print(json.dumps({'reply': reply, 'readable': readable, 'inherited': inherited,
    'secret': os.environ.get('SUPERVISOR_SECRET'), 'setting': os.environ.get('BOT_SETTING'),
    'supervisor_marker': os.environ.get('GRAMLAB_SUPERVISOR_NETNS'),
    'network': os.readlink('/proc/self/ns/net'), 'pid_namespace': os.readlink('/proc/self/ns/pid'),
    'namespace_error': namespace_error, 'external_error': external_error,
    'capabilities': int(status['CapEff'], 16), 'new_privileges': int(status['NoNewPrivs'])}))
"""
    )
    (tmp_path / "supervisor.py").write_text(
        """
import json, os, pathlib, socketserver, threading
from gramlab.runtime import RuntimeProfile, Sandbox
profile = RuntimeProfile(**json.loads(pathlib.Path('profile.json').read_text()))
os.environ['SUPERVISOR_SECRET'] = 'synthetic parent capability'
class Service(socketserver.BaseRequestHandler):
    def handle(self):
        if self.request.recv(32) == b'component':
            self.request.sendall(b'hello component')
with socketserver.TCPServer(('127.0.0.1', 0), Service) as service:
    worker = threading.Thread(target=service.serve_forever)
    worker.start()
    try:
        with open('world-secret') as secret:
            os.set_inheritable(secret.fileno(), True)
            with Sandbox(profile).component(
                [profile.python, '/work/client.py', str(service.server_address[1])],
                data=pathlib.Path('bot'), environment={'BOT_SETTING': 'explicit'}
            ) as process:
                stdout, stderr = process.communicate(timeout=5)
                assert process.returncode == 0, stderr
        print(json.dumps({'component': json.loads(stdout),
            'network': os.readlink('/proc/self/ns/net'),
            'pid_namespace': os.readlink('/proc/self/ns/pid')}))
    finally:
        service.shutdown()
        worker.join(timeout=5)
"""
    )
    result = Sandbox(profile).supervise([profile.python, "/work/supervisor.py"], data=tmp_path)
    assert result.returncode == 0, result.stderr
    observed = json.loads(result.stdout)
    assert observed["network"] != os.readlink("/proc/self/ns/net")
    component = observed.pop("component")
    assert component.pop("network") == observed["network"]
    assert component.pop("pid_namespace") != observed["pid_namespace"]
    assert component.pop("namespace_error") in (errno.ENOSPC, errno.EPERM)
    assert component == {
        "reply": "hello component",
        "readable": [],
        "inherited": [],
        "secret": None,
        "setting": "explicit",
        "supervisor_marker": None,
        "external_error": errno.ENETUNREACH,
        "capabilities": 0,
        "new_privileges": 1,
    }
    assert (bot / "state.txt").read_text() == "private bot state"
    assert (tmp_path / "world-secret").read_text() == "supervisor-only synthetic data"


@pytest.mark.parametrize("finish", ["exit", "exception", "kill", "supervisor_kill", "timeout"])
def test_component_descendants_are_gone_after_interruption(tmp_path: Path, finish: str) -> None:
    profile = RuntimeProfile.load(Path(os.environ["GRAMLAB_RUNTIME_PROFILE"]))
    shutil.copytree(
        "src/gramlab", tmp_path / "gramlab", ignore=shutil.ignore_patterns("__pycache__")
    )
    (tmp_path / "profile.json").write_text(json.dumps(asdict(profile)))
    bot = tmp_path / "bot"
    bot.mkdir()
    (bot / "child.py").write_text(
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
print('ready', flush=True)
if sys.argv[1] != 'exit':
    while True:
        signal.pause()
"""
    )
    (tmp_path / "supervisor.py").write_text(
        """
import fcntl, json, os, pathlib, signal, sys
from gramlab.runtime import RuntimeProfile, Sandbox
profile = RuntimeProfile(**json.loads(pathlib.Path('profile.json').read_text()))
try:
    with Sandbox(profile).component(
        [profile.python, '/work/child.py', sys.argv[1]], data=pathlib.Path('bot')
    ) as process:
        assert process.stdout.readline() == 'ready\\n'
        if sys.argv[1] == 'exception':
            raise ValueError('controlled interruption')
        if sys.argv[1] == 'supervisor_kill':
            os.kill(os.getpid(), signal.SIGKILL)
        if sys.argv[1] == 'timeout':
            while True:
                signal.pause()
        if sys.argv[1] == 'kill':
            process.kill()
        process.wait(timeout=5)
except ValueError:
    assert sys.argv[1] == 'exception'
with open('bot/descendant.lock') as stream:
    fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
print('component-cleaned')
"""
    )
    command = [profile.python, "/work/supervisor.py", finish]
    if finish == "timeout":
        with pytest.raises(subprocess.TimeoutExpired):
            Sandbox(profile).supervise(command, data=tmp_path, timeout=3)
    else:
        result = Sandbox(profile).supervise(command, data=tmp_path, timeout=10)
        if finish == "supervisor_kill":
            assert result.returncode != 0
        else:
            assert result.returncode == 0, result.stderr
            assert result.stdout == "component-cleaned\n"
    assert (bot / "descendant.started").read_text() == "ready"
    with (bot / "descendant.lock").open() as stream:
        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)


def test_component_cannot_start_outside_a_run_supervisor(tmp_path: Path) -> None:
    profile = RuntimeProfile.load(Path(os.environ["GRAMLAB_RUNTIME_PROFILE"]))
    with pytest.raises(RuntimeError, match="trusted isolated run supervisor"):
        with Sandbox(profile).component(
            [profile.python, "-c", "open('started', 'w').close()"], data=tmp_path
        ) as process:
            process.communicate(timeout=3)
    assert not (tmp_path / "started").exists()


def test_live_components_share_the_run_network_but_not_each_others_state(tmp_path: Path) -> None:
    profile = RuntimeProfile.load(Path(os.environ["GRAMLAB_RUNTIME_PROFILE"]))
    shutil.copytree(
        "src/gramlab", tmp_path / "gramlab", ignore=shutil.ignore_patterns("__pycache__")
    )
    (tmp_path / "profile.json").write_text(json.dumps(asdict(profile)))
    for name in ("first", "second"):
        data = tmp_path / name
        data.mkdir()
        (data / "identity").write_text(name)
        (data / "child.py").write_text(
            """
import json, os, pathlib, sys
own = pathlib.Path('identity').read_text()
visible = [str(path) for path in [pathlib.Path('/work/first'), pathlib.Path('/work/second')]
           if path.exists()]
print(json.dumps({'identity': own, 'visible': visible,
    'net': os.readlink('/proc/self/ns/net'), 'pid': os.readlink('/proc/self/ns/pid')}), flush=True)
assert sys.stdin.readline() == 'continue\\n'
pathlib.Path('state').write_text(own + '-updated')
"""
        )
    (tmp_path / "supervisor.py").write_text(
        """
import json, pathlib
from contextlib import ExitStack
from gramlab.runtime import RuntimeProfile, Sandbox
profile = RuntimeProfile(**json.loads(pathlib.Path('profile.json').read_text()))
with ExitStack() as contexts:
    processes = [contexts.enter_context(Sandbox(profile).component(
        [profile.python, '/work/child.py'], data=pathlib.Path(name)
    )) for name in ('first', 'second')]
    records = [json.loads(process.stdout.readline()) for process in processes]
    assert all(process.poll() is None for process in processes)
    for process in processes:
        stdout, stderr = process.communicate(input='continue\\n', timeout=5)
        assert process.returncode == 0, stderr
        assert stdout == ''
print(json.dumps(records))
"""
    )
    result = Sandbox(profile).supervise([profile.python, "/work/supervisor.py"], data=tmp_path)
    assert result.returncode == 0, result.stderr
    first, second = json.loads(result.stdout)
    assert first.pop("net") == second.pop("net")
    assert first.pop("pid") != second.pop("pid")
    assert first == {"identity": "first", "visible": []}
    assert second == {"identity": "second", "visible": []}
    for name in ("first", "second"):
        assert (tmp_path / name / "state").read_text() == name + "-updated"
