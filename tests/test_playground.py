"""The public playground keeps a real consumer alive and restores its seeded baseline."""

from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, cast

import pytest

from gramlab.playground import PlaygroundControl, request


def _project(directory: Path) -> Path:
    directory.mkdir()
    (directory / "run.toml").write_text(
        """schema = 1
mode = "simulation-only"
seed = 29
now = 1700000000
timeout = 15

[scenario]
entry = "scenario.py"
files = ["scenario.py"]

[bots.target]
entry = "target.py"
files = ["target.py"]

[bots.anchor]
entry = "anchor.py"
files = ["anchor.py"]
"""
    )
    (directory / "scenario.py").write_text(
        """from gramlab import Scenario

lab = Scenario.from_environment()
owner = lab.create_user(first_name="Mina", username="mina", language_code="en")
member = lab.create_user(first_name="Arman", username="arman", language_code="en")
bots = lab.bots()
lab.open_private_chat(user_id=owner["id"], bot_id=bots["target"])
lab.create_group_chat(
    title="Already running",
    creator_id=owner["id"],
    member_ids=[member["id"]],
    bot_ids=[bots["target"]],
)
fresh = lab.create_group_chat(
    title="Add target here",
    creator_id=owner["id"],
    member_ids=[member["id"]],
    bot_ids=[bots["anchor"]],
)
lab.capture_chat(chat_id=fresh["id"], user_id=owner["id"], label="ready", contains=[])
print("Seeded the playground")
"""
    )
    (directory / "target.py").write_text(
        """import http.client
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit

endpoint = urlsplit(os.environ["GRAMLAB_BOT_API"])
token = os.environ["GRAMLAB_BOT_TOKEN"]

def call(method, parameters):
    connection = http.client.HTTPConnection("127.0.0.1", endpoint.port, timeout=2)
    try:
        connection.request(
            "POST", f"/bot{token}/{method}", json.dumps(parameters),
            {"Content-Type": "application/json"},
        )
        response = connection.getresponse()
        body = json.loads(response.read())
        if response.status != 200 or not body["ok"]:
            raise RuntimeError(body)
        return body["result"]
    finally:
        connection.close()

offset = 0
while True:
    parameters = {
        "offset": offset,
        "timeout": 1,
        "allowed_updates": ["my_chat_member", "message", "callback_query"],
    }
    for update in call("getUpdates", parameters):
        offset = update["update_id"] + 1
        if "my_chat_member" in update:
            membership = update["my_chat_member"]
            Path("joined.json").write_text(json.dumps(membership, sort_keys=True))
            subprocess.Popen([
                sys.executable,
                "-c",
                "import time; from pathlib import Path; time.sleep(1.5); "
                "Path('late.txt').write_text('stale')",
            ])
            call(
                "sendMessage",
                {
                    "chat_id": membership["chat"]["id"],
                    "text": "Target joined this group",
                },
            )
        elif "message" in update:
            message = update["message"]
            call(
                "sendRichMessage",
                {
                    "chat_id": message["chat"]["id"],
                    "rich_message": {
                        "skip_entity_detection": True,
                        "blocks": [
                            {"type": "paragraph", "text": "Ready for input"},
                            {
                                "type": "buttons",
                                "buttons": [
                                    {
                                        "text": "Continue",
                                        "style": "primary",
                                        "callback_data": "continue",
                                    }
                                ],
                            },
                        ],
                    },
                },
            )
        elif "callback_query" in update:
            callback = update["callback_query"]
            call(
                "editMessageText",
                {
                    "chat_id": callback["message"]["chat"]["id"],
                    "message_id": callback["message"]["message_id"],
                    "text": "Continued through the playground",
                },
            )
            call("answerCallbackQuery", {"callback_query_id": callback["id"]})
    time.sleep(0.01)
"""
    )
    (directory / "anchor.py").write_text(
        """import http.client
import json
import os
from urllib.parse import urlsplit

endpoint = urlsplit(os.environ["GRAMLAB_BOT_API"])
token = os.environ["GRAMLAB_BOT_TOKEN"]
while True:
    connection = http.client.HTTPConnection("127.0.0.1", endpoint.port, timeout=2)
    try:
        connection.request(
            "POST", f"/bot{token}/getUpdates", json.dumps({"timeout": 1}),
            {"Content-Type": "application/json"},
        )
        response = connection.getresponse()
        if response.status != 200 or not json.loads(response.read())["ok"]:
            raise RuntimeError("Anchor polling failed")
    finally:
        connection.close()
"""
    )
    return directory / "run.toml"


def _invoke(output: Path, operation: str, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - public CLI under the enclosing network guard
        [
            sys.executable,
            "-m",
            "gramlab",
            "playground",
            operation,
            "--output",
            str(output),
            *arguments,
        ],
        capture_output=True,
        text=True,
        timeout=30,
        env=os.environ.copy(),
    )


def _status(output: Path) -> dict[str, Any]:
    result = _invoke(output, "status")
    assert result.returncode == 0, result.stderr
    return cast(dict[str, Any], json.loads(result.stdout))


def _group(status: dict[str, Any], title: str) -> dict[str, Any]:
    return next(chat for chat in status["world"]["chats"] if chat.get("title") == title)


def _wait_for_join(output: Path) -> dict[str, Any]:
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        status = _status(output)
        group = _group(status, "Add target here")
        if status["at_baseline"] is False and status["histories"][str(group["id"])]:
            return status
        time.sleep(0.05)
    raise AssertionError("The added target bot never observed and answered the membership update")


def _wait_for_text(output: Path, chat_id: int, text: str) -> dict[str, Any]:
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        status = _status(output)
        if any(message.get("text") == text for message in status["histories"][str(chat_id)]):
            return status
        time.sleep(0.05)
    raise AssertionError(f"Playground chat never contained {text!r}")


def test_disconnected_helper_cannot_stop_a_playground_after_dispatch(tmp_path: Path) -> None:
    calls: list[str] = []

    def dispatch(operation: str, _parameters: dict[str, Any]) -> dict[str, str]:
        calls.append(operation)
        return {"state": "running"}

    with PlaygroundControl(
        tmp_path,
        run_id="00000000-0000-0000-0000-000000000000",
        dispatch=dispatch,
    ) as control:
        payload = json.dumps(
            {
                "schema": 1,
                "run_id": control.run_id,
                "capability": control.capability,
                "operation": "status",
                "parameters": {},
            }
        ).encode()
        abandoned = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        abandoned.connect(str(control.path))
        abandoned.sendall(payload)
        abandoned.shutdown(socket.SHUT_WR)
        abandoned.close()

        assert control.poll() is False
        assert calls == ["status"]

        with ThreadPoolExecutor(max_workers=1) as workers:
            healthy = workers.submit(request, tmp_path, "status")
            deadline = time.monotonic() + 2
            while not healthy.done():
                assert time.monotonic() < deadline
                control.poll()
            assert healthy.result() == {"state": "running"}
        assert calls == ["status", "status"]


def test_interrupted_playground_removes_stale_controls_and_writes_a_retryable_report(
    tmp_path: Path,
) -> None:
    manifest = _project(tmp_path / "project")
    output = tmp_path / "playground"
    start = subprocess.Popen(  # noqa: S603 - public CLI under the enclosing network guard
        [
            sys.executable,
            "-m",
            "gramlab",
            "playground",
            "start",
            str(manifest),
            "--output",
            str(output),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=os.environ.copy(),
    )
    try:
        deadline = time.monotonic() + 15
        while not (output / "playground-control.json").is_file():
            assert start.poll() is None, start.communicate()
            assert time.monotonic() < deadline, "Playground did not become ready"
            time.sleep(0.05)

        start.send_signal(signal.SIGINT)
        assert start.wait(timeout=15) == 1
        assert not (output / "playground-control.json").exists()
        assert not (output / "playground.sock").exists()
        result = json.loads((output / "result.json").read_text())
        assert result["outcome"] == "failed"
        assert result["failure"] == "supervisor_interrupted"
        assert (output / "report.html").is_file()
    finally:
        if start.poll() is None:
            start.kill()
            start.wait(timeout=10)


def test_public_playground_adds_real_bot_resets_exact_state_and_stops(tmp_path: Path) -> None:
    manifest = _project(tmp_path / "project")
    output = tmp_path / "playground"
    start = subprocess.Popen(  # noqa: S603 - public CLI under the enclosing network guard
        [
            sys.executable,
            "-m",
            "gramlab",
            "playground",
            "start",
            str(manifest),
            "--output",
            str(output),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=os.environ.copy(),
    )
    try:
        deadline = time.monotonic() + 15
        while not (output / "playground-control.json").is_file():
            if start.poll() is not None:
                stdout, stderr = start.communicate()
                raise AssertionError(f"Playground exited before readiness: {stdout}\n{stderr}")
            assert time.monotonic() < deadline, "Playground did not become ready"
            time.sleep(0.05)

        initial = _status(output)
        fresh = _group(initial, "Add target here")
        target_id = initial["bots"]["target"]
        assert initial["state"] == "running"
        assert initial["at_baseline"] is True
        assert target_id not in {member["user_id"] for member in fresh["members"]}
        assert initial["histories"][str(fresh["id"])] == []

        control_path = output / "playground-control.json"
        original_control = json.loads(control_path.read_text())
        tampered = dict(original_control)
        tampered["capability"] = "gramlab-playground_" + "a" * 43
        control_path.write_text(json.dumps(tampered))
        rejected_control = _invoke(output, "status")
        assert rejected_control.returncode == 2
        assert "identity or capability did not match" in rejected_control.stderr
        assert start.poll() is None
        control_path.write_text(json.dumps(original_control))
        assert _status(output)["at_baseline"] is True

        unauthorized = _invoke(
            output,
            "add-bot",
            "--group",
            "Add target here",
            "--bot",
            "target",
            "--actor",
            "arman",
        )
        assert unauthorized.returncode == 2
        assert "Only a group creator or administrator" in unauthorized.stderr
        unchanged = _status(output)
        assert unchanged["at_baseline"] is True
        assert target_id not in {
            member["user_id"] for member in _group(unchanged, "Add target here")["members"]
        }

        running = _group(initial, "Already running")
        sent = _invoke(
            output,
            "send",
            "--chat-id",
            str(running["id"]),
            "--actor-id",
            "4",
            "--text",
            "hello",
        )
        assert sent.returncode == 0, sent.stderr
        ready = _wait_for_text(output, running["id"], "")
        rich = ready["histories"][str(running["id"])][-1]
        assert "Ready for input" in str(rich["rich_message"])
        for _ in range(64):
            missing = _invoke(
                output,
                "tap",
                "--chat-id",
                str(running["id"]),
                "--actor-id",
                "4",
                "--label",
                "Missing",
            )
            assert missing.returncode == 2
            assert "No current rich button has that label" in missing.stderr
        tapped = _invoke(
            output,
            "tap",
            "--chat-id",
            str(running["id"]),
            "--actor-id",
            "4",
            "--label",
            "Continue",
        )
        assert tapped.returncode == 0, tapped.stderr
        _wait_for_text(output, running["id"], "Continued through the playground")

        added = _invoke(
            output,
            "add-bot",
            "--group",
            "Add target here",
            "--bot",
            "target",
            "--actor",
            "mina",
        )
        assert added.returncode == 0, added.stderr
        changed = _wait_for_join(output)
        changed_group = _group(changed, "Add target here")
        assert target_id in {member["user_id"] for member in changed_group["members"]}
        assert [item["text"] for item in changed["histories"][str(fresh["id"])]] == [
            "Target joined this group"
        ]
        assert (
            json.loads((output / "bots" / "target" / "joined.json").read_text())["new_chat_member"][
                "status"
            ]
            == "member"
        )

        reset = _invoke(output, "reset")
        assert reset.returncode == 0, reset.stderr
        restored = _status(output)
        restored_group = _group(restored, "Add target here")
        assert restored["run_id"] == initial["run_id"]
        assert restored["at_baseline"] is True
        assert target_id not in {member["user_id"] for member in restored_group["members"]}
        assert restored["histories"][str(restored_group["id"])] == []
        assert not (output / "bots" / "target" / "joined.json").exists()
        assert restored["histories"][str(running["id"])] == []
        time.sleep(1.7)
        assert not (output / "bots" / "target" / "late.txt").exists()

        repeated = _invoke(
            output,
            "add-bot",
            "--group",
            "Add target here",
            "--bot",
            "target",
            "--actor",
            "mina",
        )
        assert repeated.returncode == 0, repeated.stderr
        _wait_for_join(output)

        stopped = _invoke(output, "stop")
        assert stopped.returncode == 0, stopped.stderr
        assert start.wait(timeout=15) == 0
        result = json.loads((output / "result.json").read_text())
        assert result["outcome"] == "passed"
        assert [event["operation"] for event in result["playground"]["lifecycle"]] == [
            "send",
            "tap",
            "add_bot",
            "reset",
            "add_bot",
            "stop",
        ]
        stopped_again = _invoke(output, "stop")
        assert stopped_again.returncode == 0, stopped_again.stderr
        assert json.loads(stopped_again.stdout)["state"] == "stopped"
    finally:
        if start.poll() is None:
            start.kill()
            start.wait(timeout=10)


def test_playground_rejects_stale_control_metadata(tmp_path: Path) -> None:
    output = tmp_path / "playground"
    output.mkdir()
    control = output / "playground-control.json"
    control.write_text(
        json.dumps(
            {
                "schema": 1,
                "run_id": "00000000-0000-0000-0000-000000000000",
                "socket": "playground.sock",
                "capability": "gramlab-playground_" + "a" * 43,
            }
        )
    )

    control.chmod(0o600)
    for operation in ("status", "reset"):
        result = _invoke(output, operation)
        assert result.returncode == 2
        assert "cannot control playground" in result.stderr
    assert control.is_file()


@pytest.mark.android
def test_android_playground_refreshes_added_membership_and_visible_reset(tmp_path: Path) -> None:
    android_profile = os.environ.get("GRAMLAB_ANDROID_RUNTIME_PROFILE")
    apk = os.environ.get("GRAMLAB_ANDROID_PROBE_APK")
    if android_profile is None or apk is None or not os.access("/dev/kvm", os.R_OK | os.W_OK):
        pytest.skip("Requires the Android profile, group-capable APK and KVM")
    manifest = _project(tmp_path / "project")
    manifest.write_text(
        manifest.read_text()
        .replace('mode = "simulation-only"', 'mode = "headless-android"')
        .replace("timeout = 15", "timeout = 420")
    )
    output = tmp_path / "playground"
    start = subprocess.Popen(  # noqa: S603 - public CLI under the enclosing network guard
        [
            sys.executable,
            "-m",
            "gramlab",
            "playground",
            "start",
            str(manifest),
            "--output",
            str(output),
            "--android-profile",
            android_profile,
            "--android-apk",
            apk,
            "--bridge-version",
            "6",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=os.environ.copy(),
    )
    try:
        deadline = time.monotonic() + 300
        while not (output / "playground-control.json").is_file():
            if start.poll() is not None:
                stdout, stderr = start.communicate()
                raise AssertionError(
                    f"Android playground failed before readiness: {stdout}\n{stderr}"
                )
            assert time.monotonic() < deadline, "Android playground did not become ready"
            time.sleep(0.2)
        initial = _status(output)
        fresh = _group(initial, "Add target here")
        added = _invoke(
            output,
            "add-bot",
            "--group",
            "Add target here",
            "--bot",
            "target",
            "--actor",
            "mina",
        )
        assert added.returncode == 0, added.stderr
        _wait_for_join(output)
        captured = _invoke(
            output,
            "capture",
            "--chat-id",
            str(fresh["id"]),
            "--actor-id",
            "3",
            "--label",
            "joined",
            "--contains",
            "Target joined this group",
        )
        assert captured.returncode == 0, captured.stderr
        assert (output / "captures" / "joined.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n")

        reset = _invoke(output, "reset")
        assert reset.returncode == 0, reset.stderr
        restored = _status(output)
        assert restored["at_baseline"] is True
        captured_reset = _invoke(
            output,
            "capture",
            "--chat-id",
            str(fresh["id"]),
            "--actor-id",
            "3",
            "--label",
            "reset",
        )
        assert captured_reset.returncode == 0, captured_reset.stderr
        assert (output / "captures" / "reset.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n")

        stopped = _invoke(output, "stop")
        assert stopped.returncode == 0, stopped.stderr
        assert start.wait(timeout=30) == 0
        result = json.loads((output / "result.json").read_text())
        assert result["outcome"] == "passed"
        assert result["android"]["network"]["ipv4"] != 0
        assert result["android"]["network"]["ipv6"] != 0
        assert [capture["label"] for capture in result["captures"]] == [
            "ready",
            "joined",
            "reset",
        ]
    finally:
        if start.poll() is None:
            start.kill()
            start.wait(timeout=30)
