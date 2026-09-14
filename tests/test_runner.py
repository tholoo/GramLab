"""Consumer runs are invoked through the actual public command in network containment."""

import json
import os
import re
import socket
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

import pytest


def project(directory: Path, scenario: str | None = None) -> Path:
    directory.mkdir()
    (directory / "run.toml").write_text("""schema = 1
seed = 7
now = 1700000000
timeout = 10
[scenario]
entry = "scenario.py"
files = ["scenario.py"]
[bots.echo]
entry = "bot.py"
files = ["bot.py"]
""")
    (directory / "scenario.py").write_text(
        scenario
        or """import time
from pathlib import Path
from gramlab.scenario import Scenario
lab = Scenario.from_environment()
user = lab.create_user(first_name="Sara", language_code="fa")
chat = lab.open_private_chat(user_id=user["id"], bot_id=lab.bots()["echo"])
lab.send_message(chat_id=chat["id"], sender_id=user["id"], text="سلام hello")
deadline = time.monotonic() + 5
while len(lab.history(chat["id"])) != 2:
    assert time.monotonic() < deadline, "Bot reply missing"
    time.sleep(0.01)
assert lab.history(chat["id"])[1]["text"] == "Echo: سلام hello"
assert not Path("/work/world/world.sqlite3").exists()
assert not Path("/proc/1/root/work/world/world.sqlite3").exists()
assert not Path("/work/bots/echo/bot.py").exists()
assert not Path("ambient-secret.txt").exists()
print("Scenario verified")
"""
    )
    (directory / "bot.py").write_bytes(Path("tests/fixtures/echo_bot.py").read_bytes())
    (directory / "ambient-secret.txt").write_text("ambient-private-value")
    return directory / "run.toml"


def invoke(manifest: Path, output: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 — actual CLI argv, no shell or consumer import
        [
            sys.executable,
            "-m",
            "gramlab",
            "run",
            str(manifest),
            "--output",
            str(output),
            *arguments,
        ],
        capture_output=True,
        text=True,
        timeout=30,
        env=os.environ.copy(),
    )


def runtime_profile_with_dependency(
    tmp_path: Path, *, name: str = "consumer", forbidden: Path | None = None
) -> Path:
    dependency = tmp_path / f"{name}-runtime"
    dependency.mkdir()
    (dependency / "consumer_dependency.py").write_text(f'PREFIX = "Echo: "\nMARKER = {name!r}\n')
    source = json.loads(Path(os.environ["GRAMLAB_RUNTIME_PROFILE"]).read_text())
    store_paths = tmp_path / f"{name}-store-paths"
    store_paths.write_text(Path(source["storePaths"]).read_text() + dependency.as_posix() + "\n")
    source["storePaths"] = store_paths.as_posix()
    source["environment"] = {
        "CONSUMER_DEPENDENCY_ROOT": dependency.as_posix(),
        "EXPECTED_MARKER": name,
        **({"FORBIDDEN_ROOT": forbidden.as_posix()} if forbidden is not None else {}),
    }
    profile = tmp_path / f"{name}-profile.json"
    profile.write_text(json.dumps(source))
    return profile


def test_public_run_command_executes_private_scenario_and_real_bot(tmp_path: Path):
    manifest = project(tmp_path / "project")
    output = tmp_path / "run"
    result = invoke(manifest, output)
    assert result.returncode == 0, result.stderr
    recorded = json.loads((output / "result.json").read_text())
    assert recorded["outcome"] == "passed"
    assert recorded["mode"] == "simulation-only"
    assert recorded["world"]["seed"] == 7
    assert recorded["histories"] == {
        "1": [
            {"id": 1, "chat_id": 1, "sender_id": 2, "date": 1700000000, "text": "سلام hello"},
            {"id": 2, "chat_id": 1, "sender_id": 1, "date": 1700000000, "text": "Echo: سلام hello"},
        ]
    }
    report = (output / "report.html").read_text()
    assert "Scenario verified" in report
    assert "ambient-private-value" not in report
    assert "gramlab-control_" not in report
    assert ":gramlab_" not in report
    assert "Scenario verified" in recorded["processes"]["scenario"]["stdout"]
    assert not (output / "scenario" / "ambient-secret.txt").exists()


def test_android_theme_is_validated_and_recorded_before_guest_start(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from gramlab.runner import run
    from gramlab.runtime import RuntimeProfile

    manifest = project(tmp_path / "project")
    manifest.write_text('mode = "headless-android"\n' + manifest.read_text())
    apk = tmp_path / "client.apk"
    apk.write_bytes(b"PK\x03\x04approved")
    profile = RuntimeProfile.load(Path(os.environ["GRAMLAB_RUNTIME_PROFILE"]))
    android_profile = replace(
        profile,
        executables={
            **profile.executables,
            "adb": "adb",
            "emulator": "emulator",
            "avdmanager": "avdmanager",
        },
    )

    def supervise(_self, _command, *, data: Path, **_kwargs):
        (data / "observation.json").write_text(
            json.dumps({"failure": None, "processes": {}, "captures": [], "android": {}})
        )
        return subprocess.CompletedProcess([], 0)

    monkeypatch.setattr("gramlab.runner.Sandbox.supervise", supervise)
    output = tmp_path / "dark-run"

    outcome = run(
        manifest,
        output,
        profile=profile,
        android_profile=android_profile,
        android_apk=apk,
        android_theme="dark",
    )

    assert outcome == "incomplete"
    recorded = json.loads((output / "result.json").read_text())
    assert recorded["configuration"]["android"]["theme"] == "dark"

    with pytest.raises(ValueError, match="Android theme must be light or dark"):
        run(
            manifest,
            tmp_path / "invalid-run",
            profile=profile,
            android_profile=android_profile,
            android_apk=apk,
            android_theme="sepia",
        )
    assert not (tmp_path / "invalid-run").exists()


def test_interactive_android_selects_one_explicit_display_socket(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from gramlab.runner import run
    from gramlab.runtime import RuntimeProfile

    manifest = project(tmp_path / "project")
    manifest.write_text('mode = "interactive-android"\n' + manifest.read_text())
    apk = tmp_path / "client.apk"
    apk.write_bytes(b"PK\x03\x04approved")
    profile = RuntimeProfile.load(Path(os.environ["GRAMLAB_RUNTIME_PROFILE"]))
    android_profile = replace(
        profile,
        executables={
            **profile.executables,
            "adb": "adb",
            "emulator": "emulator",
            "avdmanager": "avdmanager",
            "scrcpy": "scrcpy",
        },
    )
    display = tmp_path / "X7"
    with socket.socket(socket.AF_UNIX) as listener:
        listener.bind(display.as_posix())
        observed: dict[str, object] = {}

        def supervise(_self, _command, *, data: Path, **kwargs):
            observed.update(kwargs)
            (data / "observation.json").write_text(
                json.dumps({"failure": None, "processes": {}, "captures": [], "android": {}})
            )
            return subprocess.CompletedProcess([], 0)

        monkeypatch.setattr("gramlab.runner.Sandbox.supervise", supervise)
        outcome = run(
            manifest,
            tmp_path / "interactive-run",
            profile=profile,
            android_profile=android_profile,
            android_apk=apk,
            display_socket=display,
        )

    assert outcome == "incomplete"
    assert observed["display_socket"] == display
    assert observed["kvm"] is True
    recorded = json.loads((tmp_path / "interactive-run" / "result.json").read_text())
    assert recorded["mode"] == "interactive-android"
    assert recorded["configuration"]["android"]["display"] == "X7"


def test_interactive_android_rejects_a_profile_without_the_screen_viewer(
    tmp_path: Path,
) -> None:
    from gramlab.runner import run
    from gramlab.runtime import RuntimeProfile

    manifest = project(tmp_path / "project")
    manifest.write_text('mode = "interactive-android"\n' + manifest.read_text())
    apk = tmp_path / "client.apk"
    apk.write_bytes(b"PK\x03\x04approved")
    profile = RuntimeProfile.load(Path(os.environ["GRAMLAB_RUNTIME_PROFILE"]))
    android_profile = replace(
        profile,
        executables={
            **profile.executables,
            "adb": "adb",
            "emulator": "emulator",
            "avdmanager": "avdmanager",
        },
    )
    display = tmp_path / "X7"
    with socket.socket(socket.AF_UNIX) as listener:
        listener.bind(display.as_posix())
        with pytest.raises(ValueError, match="scrcpy"):
            run(
                manifest,
                tmp_path / "interactive-run",
                profile=profile,
                android_profile=android_profile,
                android_apk=apk,
                display_socket=display,
            )
    assert not (tmp_path / "interactive-run").exists()


def test_public_playground_cli_forwards_the_selected_display_socket(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from gramlab import __main__ as cli
    from gramlab.runtime import RuntimeProfile

    profile = RuntimeProfile.load(Path(os.environ["GRAMLAB_RUNTIME_PROFILE"]))
    manifest = tmp_path / "run.toml"
    manifest.write_text('mode = "interactive-android"\n')
    display = tmp_path / "X0"
    display.touch()
    recorded: dict[str, object] = {}

    def fake_run(manifest_path, output_path, **kwargs):
        recorded.update({"manifest": manifest_path, "output": output_path, **kwargs})
        return "passed"

    monkeypatch.setattr(cli.RuntimeProfile, "load", lambda _path: profile)
    monkeypatch.setattr(cli, "run", fake_run)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "gramlab",
            "playground",
            "start",
            str(manifest),
            "--output",
            str(tmp_path / "output"),
            "--profile",
            str(tmp_path / "profile.json"),
            "--display-socket",
            str(display),
        ],
    )

    assert cli.main() == 0
    assert recorded["display_socket"] == display


def test_bot_can_use_its_own_trusted_runtime_profile(tmp_path: Path):
    manifest = project(tmp_path / "project")
    bot = manifest.parent / "bot.py"
    bot.write_text(
        "import os, sys\n"
        'sys.path.insert(0, os.environ["CONSUMER_DEPENDENCY_ROOT"])\n'
        "from consumer_dependency import PREFIX\n"
        + bot.read_text().replace('"Echo: " + message["text"]', 'PREFIX + message["text"]')
    )
    profile = runtime_profile_with_dependency(tmp_path)
    output = tmp_path / "run"

    result = invoke(manifest, output, "--bot-profile", f"echo={profile}")

    assert result.returncode == 0, result.stderr
    recorded = json.loads((output / "result.json").read_text())
    assert recorded["outcome"] == "passed"
    assert set(recorded["bot_runtime_profiles"]) == {"echo"}
    fingerprint = recorded["bot_runtime_profiles"]["echo"]
    assert re.fullmatch(r"[0-9a-f]{64}", fingerprint)
    assert fingerprint in (output / "report.html").read_text()
    assert recorded["histories"]["1"][1]["text"] == "Echo: سلام hello"


def test_python_runner_keeps_per_bot_runtime_profiles_isolated(tmp_path: Path):
    from gramlab.runner import run
    from gramlab.runtime import RuntimeProfile

    project_root = tmp_path / "project"
    manifest = project(
        project_root,
        """import time
from gramlab import Scenario
lab = Scenario.from_environment()
deadline = time.monotonic() + 5
for name in ("first", "second"):
    while lab.bot_status(name)["state"] == "running":
        if time.monotonic() >= deadline:
            raise AssertionError("Bot did not finish its profile check")
        time.sleep(0.01)
    status = lab.bot_status(name)
    if status["state"] != "exited" or status["exit_code"] != 0:
        raise AssertionError(f"Bot profile check failed: {status}")
print("Both bot runtime profiles remained isolated")
""",
    )
    manifest.write_text(
        manifest.read_text().replace(
            "[bots.echo]\n",
            '[bots.first]\nentry = "bot.py"\nfiles = ["bot.py"]\n[bots.second]\n',
        )
    )
    first_root = tmp_path / "first-runtime"
    second_root = tmp_path / "second-runtime"
    first_path = runtime_profile_with_dependency(tmp_path, name="first", forbidden=second_root)
    second_path = runtime_profile_with_dependency(tmp_path, name="second", forbidden=first_root)
    (project_root / "bot.py").write_text(
        """import os, sys
from pathlib import Path
sys.path.insert(0, os.environ["CONSUMER_DEPENDENCY_ROOT"])
from consumer_dependency import MARKER
if MARKER != os.environ["EXPECTED_MARKER"]:
    raise RuntimeError("Wrong profile dependency")
if Path(os.environ["FORBIDDEN_ROOT"]).exists():
    raise RuntimeError("Another bot's profile dependency is visible")
print(f"Profile {MARKER} verified")
"""
    )
    default_profile = RuntimeProfile.load(Path(os.environ["GRAMLAB_RUNTIME_PROFILE"]))
    output = tmp_path / "run"

    outcome = run(
        manifest,
        output,
        profile=default_profile,
        bot_profiles={
            "first": RuntimeProfile.load(first_path),
            "second": RuntimeProfile.load(second_path),
        },
    )

    assert outcome == "passed"
    recorded = json.loads((output / "result.json").read_text())
    assert set(recorded["bot_runtime_profiles"]) == {"first", "second"}
    assert "Profile first verified" in recorded["processes"]["bot:first"]["stdout"]
    assert "Profile second verified" in recorded["processes"]["bot:second"]["stdout"]


@pytest.mark.parametrize("reason", ["unknown", "duplicate"])
def test_invalid_bot_runtime_profile_bindings_fail_before_output(tmp_path: Path, reason: str):
    manifest = project(tmp_path / "project")
    output = tmp_path / "run"
    arguments: tuple[str, ...]
    if reason == "unknown":
        profile = runtime_profile_with_dependency(tmp_path)
        arguments = ("--bot-profile", f"absent={profile}")
        expected = "undeclared aliases: absent"
    else:
        arguments = (
            "--bot-profile",
            "echo=/missing/first.json",
            "--bot-profile",
            "echo=/missing/second.json",
        )
        expected = "repeated for echo"

    result = invoke(manifest, output, *arguments)

    assert result.returncode == 2
    assert expected in result.stderr
    assert "Traceback" not in result.stderr
    assert not output.exists()


def test_nested_entry_can_import_sdk_and_explicit_data(tmp_path: Path):
    manifest = project(tmp_path / "project")
    (manifest.parent / "nested").mkdir()
    (manifest.parent / "scenario.py").rename(manifest.parent / "nested" / "scenario.py")
    with (manifest.parent / "nested" / "scenario.py").open("a") as stream:
        stream.write('assert Path("input.txt").read_text() == "selected data"\n')
    (manifest.parent / "input.txt").write_text("selected data")
    manifest.write_text(
        manifest.read_text().replace(
            'entry = "scenario.py"\nfiles = ["scenario.py"]',
            'entry = "nested/scenario.py"\nfiles = ["nested/scenario.py", "input.txt"]',
        )
    )
    result = invoke(manifest, tmp_path / "run")
    assert result.returncode == 0, (tmp_path / "run" / "result.json").read_text()


@pytest.mark.parametrize("bad_path", ["", ".", "../outside.py", "/etc/passwd", "a/../bot.py"])
def test_invalid_input_paths_fail_before_creating_output(tmp_path: Path, bad_path: str):
    manifest = project(tmp_path / "project")
    manifest.write_text(
        manifest.read_text().replace(
            '["scenario.py"]', '["scenario.py", ' + json.dumps(bad_path) + "]"
        )
    )
    output = tmp_path / "run"
    result = invoke(manifest, output)
    assert result.returncode == 2
    assert "Traceback" not in result.stderr
    assert not output.exists()


@pytest.mark.parametrize("kind", ["file", "parent", "fifo"])
def test_nonregular_or_symlink_inputs_are_rejected(tmp_path: Path, kind: str):
    manifest = project(tmp_path / "project")
    script = manifest.parent / "scenario.py"
    if kind == "file":
        script.unlink()
        script.symlink_to(manifest.parent / "bot.py")
    elif kind == "parent":
        (tmp_path / "link").symlink_to(manifest.parent, target_is_directory=True)
        manifest = tmp_path / "link" / "run.toml"
    else:
        script.unlink()
        os.mkfifo(script)
    output = tmp_path / "run"
    result = invoke(manifest, output)
    assert result.returncode == 2
    assert not output.exists()


@pytest.mark.parametrize(
    "reason", ["existing_output", "output_symlink", "unsupported_mode", "unknown_field"]
)
def test_invalid_runs_cannot_overwrite_or_silently_change_mode(tmp_path: Path, reason: str):
    manifest = project(tmp_path / "project")
    output = tmp_path / "run"
    if reason == "existing_output":
        output.mkdir()
        (output / "sentinel").write_text("keep")
    elif reason == "output_symlink":
        output.symlink_to(manifest.parent, target_is_directory=True)
    elif reason == "unsupported_mode":
        manifest.write_text('mode = "interactive-android"\n' + manifest.read_text())
    else:
        manifest.write_text("unexpected = true\n" + manifest.read_text())
    result = invoke(manifest, output)
    assert result.returncode == 2
    assert not (output / "result.json").exists()
    if reason == "existing_output":
        assert (output / "sentinel").read_text() == "keep"
    if reason == "output_symlink":
        assert output.is_symlink()


def test_ambiguous_redacted_input_labels_are_rejected_before_output(tmp_path: Path):
    manifest = project(tmp_path / "project")
    names = ["gramlab-control_" + letter * 43 for letter in ("a", "b")]
    for name in names:
        (manifest.parent / name).write_text("selected data")
    manifest.write_text(
        manifest.read_text().replace('["scenario.py"]', json.dumps(["scenario.py", *names]))
    )
    output = tmp_path / "run"
    result = invoke(manifest, output)
    assert result.returncode == 2
    assert "Traceback" not in result.stderr
    assert not output.exists()


def test_failure_report_preserves_state_and_redacts_process_credentials(tmp_path: Path):
    scenario = """import os
from gramlab.scenario import Scenario
lab = Scenario.from_environment()
lab.create_user(first_name="Before failure")
print(os.environ["GRAMLAB_CONTROL_CAPABILITY"])
raise RuntimeError("Intentional scenario failure")
"""
    manifest = project(tmp_path / "project", scenario)
    (manifest.parent / "bot.py").write_text("""import os, time
print(os.environ["GRAMLAB_BOT_TOKEN"], flush=True)
time.sleep(30)
""")
    output = tmp_path / "run"
    result = invoke(manifest, output)
    assert result.returncode == 1
    recorded = json.loads((output / "result.json").read_text())
    assert recorded["failure"] == "process_failed"
    assert recorded["world"]["users"][1]["first_name"] == "Before failure"
    assert "Intentional scenario failure" in recorded["processes"]["scenario"]["stderr"]
    for artifact in ("report.html", "result.json", "observation.json"):
        text = (output / artifact).read_text()
        assert "gramlab-control_" not in text
        assert ":gramlab_" not in text


def test_bot_failure_fails_run_and_stops_scenario(tmp_path: Path):
    manifest = project(tmp_path / "project", "import time\ntime.sleep(30)\n")
    (manifest.parent / "bot.py").write_text('raise RuntimeError("Bot failed")\n')
    output = tmp_path / "run"
    result = invoke(manifest, output)
    assert result.returncode == 1
    recorded = json.loads((output / "result.json").read_text())
    assert recorded["failure"] == "process_failed"
    assert "Bot failed" in recorded["processes"]["bot:echo"]["stderr"]
    assert recorded["processes"]["scenario"]["stopped_by_runner"]


def test_timeout_stops_detached_descendants_and_retains_report(tmp_path: Path):
    manifest = project(
        tmp_path / "project",
        """import json, os, time
from pathlib import Path
if os.fork() == 0:
    os.setsid()
    Path("ready.tmp").write_text(json.dumps({"pid": os.getpid(), "sid": os.getsid(0)}))
    Path("ready.tmp").replace("ready.json")
    while True:
        with Path("heartbeat").open("a") as stream:
            stream.write("alive\\n")
        time.sleep(0.01)
time.sleep(30)
""",
    )
    # This case needs a running detached child before testing timeout cleanup.
    # An unrelated bot and a one-second whole-run budget could expire before the scenario starts.
    manifest.write_text(
        manifest.read_text().split("[bots.echo]", 1)[0].replace("timeout = 10", "timeout = 5")
    )
    output = tmp_path / "run"
    heartbeat = output / "scenario" / "heartbeat"
    ready = output / "scenario" / "ready.json"
    with subprocess.Popen(  # noqa: S603 — actual public CLI, no shell or consumer import
        [sys.executable, "-m", "gramlab", "run", str(manifest), "--output", str(output)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=os.environ.copy(),
    ) as process:
        try:
            deadline = time.monotonic() + 15
            while not ready.exists() or not heartbeat.exists():
                assert process.poll() is None, "CLI exited before descendant readiness"
                assert time.monotonic() < deadline, "Detached descendant did not become ready"
                time.sleep(0.01)
            identity = json.loads(ready.read_text())
            assert set(identity) == {"pid", "sid"}
            assert type(identity["pid"]) is int and identity["pid"] == identity["sid"] > 0
            initial = heartbeat.read_bytes()
            while heartbeat.read_bytes() == initial:
                assert process.poll() is None, "CLI exited before descendant liveness was observed"
                assert time.monotonic() < deadline, "Detached descendant heartbeat did not grow"
                time.sleep(0.01)
            assert process.poll() is None
            stdout, stderr = process.communicate(timeout=30)
            assert process.returncode == 1, (stdout, stderr)
        finally:
            if process.poll() is None:
                # Allow the bounded public run to perform its own namespace cleanup even when a
                # readiness assertion fails; kill the CLI only if it also violates that bound.
                try:
                    process.communicate(timeout=30)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.communicate(timeout=10)
    recorded = json.loads((output / "result.json").read_text())
    assert recorded["failure"] == "timeout"
    assert set(recorded["processes"]) == {"scenario"}
    assert recorded["processes"]["scenario"]["stopped_by_runner"] is True
    before = heartbeat.read_bytes()
    assert before
    time.sleep(0.1)  # Observe after CLI completion; a leaked descendant would keep writing.
    assert heartbeat.read_bytes() == before
    assert (output / "report.html").is_file()


def test_output_flood_is_bounded_and_reported(tmp_path: Path):
    manifest = project(tmp_path / "project", 'while True:\n    print("x" * 65536)\n')
    output = tmp_path / "run"
    result = invoke(manifest, output)
    assert result.returncode == 1
    recorded = json.loads((output / "result.json").read_text())
    assert recorded["failure"] == "output_limit"
    assert len(recorded["processes"]["scenario"]["stdout"].encode()) == 1024 * 1024
    assert (output / "report.html").is_file()


def test_simultaneous_runs_keep_worlds_and_outputs_independent(tmp_path: Path):
    manifests = [project(tmp_path / f"project-{index}") for index in range(2)]
    outputs = [tmp_path / f"run-{index}" for index in range(2)]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(invoke, manifests, outputs))
    assert [result.returncode for result in results] == [0, 0]
    evidence = [json.loads((output / "result.json").read_text()) for output in outputs]
    assert evidence[0]["world"] == evidence[1]["world"]
    assert evidence[0]["histories"] == evidence[1]["histories"]
    assert evidence[0]["run_id"] != evidence[1]["run_id"]


def test_large_evidence_still_produces_a_bounded_report(tmp_path: Path):
    manifest = project(
        tmp_path / "project",
        """from gramlab.scenario import Scenario
lab = Scenario.from_environment()
for index in range(180):
    lab.create_user(first_name="<>&" * 10000)
print("Large world verified")
""",
    )
    output = tmp_path / "run"
    result = invoke(manifest, output)
    assert result.returncode == 0, result.stderr
    recorded = json.loads((output / "result.json").read_text())
    assert len(recorded["world"]["users"]) == 181
    assert recorded["world"]["users"][-1]["first_name"] == "<>&" * 10000
    report = (output / "report.html").read_text()
    assert "result.json" in report
    assert "truncated" in report
    assert len(report.encode()) < 16 * 1024 * 1024


@pytest.mark.parametrize(
    "field",
    [
        "schema = true",
        "seed = -1",
        "now = 9223372036854775808",
        "timeout = nan",
        "timeout = 0",
        "timeout = 86401",
        "scenario = 1",
        "bots = []",
    ],
)
def test_invalid_manifest_values_are_reported_before_execution(tmp_path: Path, field: str):
    manifest = project(tmp_path / "project")
    key = field.split(" = ")[0]
    lines = manifest.read_text().splitlines()
    if key in ("scenario", "bots"):
        # Replace a whole table without introducing a TOML parse error.
        lines = [*lines[:4], field]
        if key == "bots":
            lines += ["[scenario]", 'entry = "scenario.py"', 'files = ["scenario.py"]']
    else:
        lines = [field if line.startswith(key + " = ") else line for line in lines]
    manifest.write_text("\n".join(lines))
    output = tmp_path / "run"
    result = invoke(manifest, output)
    assert result.returncode == 2
    assert "Traceback" not in result.stderr
    assert not output.exists()


def test_missing_runtime_produces_incomplete_report(tmp_path: Path, monkeypatch):
    profile = json.loads(Path(os.environ["GRAMLAB_RUNTIME_PROFILE"]).read_text())
    profile["bubblewrap"] = "/missing-gramlab-runtime/bwrap"
    profile_path = tmp_path / "profile.json"
    profile_path.write_text(json.dumps(profile))
    monkeypatch.setenv("GRAMLAB_RUNTIME_PROFILE", str(profile_path))
    manifest = project(tmp_path / "project")
    output = tmp_path / "run"
    result = invoke(manifest, output)
    assert result.returncode == 1
    recorded = json.loads((output / "result.json").read_text())
    assert recorded["outcome"] == "incomplete"
    assert recorded["failure"] == "supervisor_startup_failed"
    assert recorded["processes"] == {}
    assert (output / "report.html").is_file()


def test_consumer_environment_does_not_inherit_host_configuration(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("GRAMLAB_TEST_AMBIENT", "host-only-value")
    monkeypatch.setenv("HTTP_PROXY", "http://invalid.example:1")
    monkeypatch.setenv("HTTPS_PROXY", "http://invalid.example:1")
    manifest = project(
        tmp_path / "project",
        """import os
from gramlab.scenario import Scenario
if any(key in os.environ for key in ("GRAMLAB_TEST_AMBIENT", "HTTP_PROXY", "HTTPS_PROXY")):
    raise RuntimeError("Ambient configuration leaked")
if Scenario.from_environment().bots() != {"echo": 1}:
    raise AssertionError("Unexpected bot identities")
print("Clean scenario environment verified")
""",
    )
    (manifest.parent / "bot.py").write_text("""import os
if any(key in os.environ for key in (
    "GRAMLAB_TEST_AMBIENT", "HTTP_PROXY", "HTTPS_PROXY", "GRAMLAB_CONTROL_CAPABILITY",
)):
    raise RuntimeError("Ambient or scenario configuration leaked to bot")
""")
    output = tmp_path / "run"
    result = invoke(manifest, output)
    assert result.returncode == 0, (output / "result.json").read_text()
    assert "host-only-value" not in (output / "report.html").read_text()
