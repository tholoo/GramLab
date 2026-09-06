"""Observe the pinned original composer's text transformations in a dedicated guest."""

import json
import subprocess
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from android_guest import main

from gramlab.client_bridge import ClientBridge
from gramlab.world import World

PACKAGE = "org.gramlab.android"


def probe(adb: Callable[..., subprocess.CompletedProcess[str]]) -> dict[str, Any]:
    capability = ""

    def retain(name: str, value: str) -> str:
        if capability and capability in value:
            raise RuntimeError("Composer text evidence contained a capability")
        Path(name).write_text(value)
        return value

    def command(*arguments: str, **kwargs: Any) -> str:
        result = adb(*arguments, **kwargs)
        if result.returncode:
            retain("failed-command.txt", result.stdout + result.stderr)
            retain("failed-logcat.txt", adb("logcat", "-d", "-t", "1000").stdout)
            raise RuntimeError(f"Guest command failed: {arguments[0]}")
        return result.stdout

    def capture(name: str) -> None:
        command("shell", "uiautomator", "dump", "/data/local/tmp/composer-text.xml")
        retain(name + ".xml", command("shell", "cat", "/data/local/tmp/composer-text.xml"))
        command("shell", "screencap", "-p", "/data/local/tmp/composer-text.png")
        command("pull", "/data/local/tmp/composer-text.png", "/work/" + name + ".png")

    with World.create(Path("world"), seed=19, now=1700000000) as world:
        world.create_user(first_name="Sara", language_code="fa")
        world.create_user(first_name="Composer text", is_bot=True)
        world.open_private_chat(user_id=1, bot_id=2)
        world.send_message(chat_id=1, sender_id=2, text="Composer text contract")
        capability = world.issue_client_token(1)
        identity = world.world_id
    command("install", "--no-streaming", "/work/client.apk", timeout=60)
    command("push", "/work/client.apk", "/data/local/tmp/composer-client.apk", timeout=30)
    command("shell", "chmod", "0444", "/data/local/tmp/composer-client.apk")
    observed = []
    cases = json.loads(Path("composer-text.json").read_text())
    with ClientBridge(Path("world")) as bridge:
        command(
            "shell",
            "-T",
            "run-as",
            PACKAGE,
            "sh",
            "-c",
            "'mkdir -p files/gramlab && cat > files/gramlab/config.json'",
            input=json.dumps(
                {
                    "endpoint": bridge.base_url.replace("127.0.0.1", "10.0.2.2"),
                    "capability": capability,
                    "world_id": identity,
                    "user_id": 1,
                }
            ),
        )
        retain(
            "launch.log",
            command(
                "shell",
                "am",
                "start",
                "-W",
                "-n",
                PACKAGE + "/org.telegram.ui.LaunchActivity",
                "-a",
                "com.tmessages.openchat",
                "--el",
                "userId",
                "2",
                timeout=40,
            ),
        )
        capture("before-text")
        for index, case in enumerate(cases):
            entered = json.loads(
                command(
                    "shell",
                    "-T",
                    "CLASSPATH=/data/local/tmp/composer-client.apk",
                    "/system/bin/app_process",
                    "/system/bin",
                    "org.telegram.gramlab.GramLabInput",
                    input=json.dumps(
                        {
                            "operation": "compose_and_send",
                            "package": PACKAGE,
                            "expected_text": "",
                            "text": case["input"],
                            "send_description": "Send",
                        }
                    ),
                    timeout=20,
                )
            )
            deadline = time.monotonic() + 15
            while True:
                with World.open(Path("world")) as world:
                    sends = world.client_snapshot(1, version=2)["sends"]
                if len(sends) > index:
                    break
                if time.monotonic() >= deadline:
                    capture("failed-text")
                    retain(
                        "failed-trace.jsonl",
                        command("shell", "run-as", PACKAGE, "cat", "files/gramlab/trace.jsonl"),
                    )
                    raise RuntimeError("Composer case did not commit: " + case["name"])
                time.sleep(0.05)
            observed.append({"name": case["name"], "input": entered, "send": sends[index]})
            retain("text-observations.json", json.dumps(observed, ensure_ascii=False))
        capture("after-text")
        command("shell", "am", "force-stop", PACKAGE)
    with World.open(Path("world")) as world:
        return {"cases": observed, "history": world.history(1), "updates": world.poll_updates(2)}


if __name__ == "__main__":
    main(probe)
