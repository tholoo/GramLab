"""Real bot kill/restart and callback HTTP exchange, wholly inside the process boundary."""

import http.client
import json
import os
import selectors
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from gramlab.bot_api import BotAPIServer
from gramlab.client_bridge import ClientBridge
from gramlab.world import World


def run(
    interact: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
    observe: Callable[[], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    directory = Path("world")
    with World.create(directory, seed=11, now=1700000000) as world:
        world.create_user(first_name="Sara", language_code="fa")
        world.create_user(first_name="Echo", username="gramlab_echo_bot", is_bot=True)
        world.open_private_chat(user_id=1, bot_id=2)
        token, capability = world.issue_bot_token(2), world.issue_client_token(1)
        world_id = world.world_id
        world.send_message(chat_id=1, sender_id=1, text="سلام hello")
    with BotAPIServer(directory) as server, ClientBridge(directory) as bridge:
        environment = {**os.environ, "GRAMLAB_BOT_API": server.base_url, "GRAMLAB_BOT_TOKEN": token}
        records = []

        def client(path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
            endpoint = urlsplit(bridge.base_url)
            connection = http.client.HTTPConnection("127.0.0.1", endpoint.port, timeout=5)
            try:
                connection.request(
                    "POST" if body is not None else "GET",
                    path,
                    json.dumps(body) if body is not None else None,
                    {"Authorization": "Bearer " + capability, "Content-Type": "application/json"},
                )
                response = connection.getresponse()
                result = json.loads(response.read())
                if response.status != 200:
                    raise RuntimeError("Client callback operation failed")
                return dict(result)
            finally:
                connection.close()

        with subprocess.Popen(
            [sys.executable, "callback_bot.py"],
            env=environment | {"GRAMLAB_BOT_PAUSE_ON_CALLBACK": "1"},
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        ) as bot:
            output = bot.stdout
            assert output is not None
            buffer = ""
            try:

                def wait_event(name: str) -> None:
                    nonlocal buffer
                    deadline = time.monotonic() + 15
                    while time.monotonic() < deadline:
                        if "\n" not in buffer:
                            with selectors.DefaultSelector() as selector:
                                selector.register(output, selectors.EVENT_READ)
                                if not selector.select(max(0, deadline - time.monotonic())):
                                    break
                            chunk = os.read(output.fileno(), 65536)
                            if not chunk:
                                break
                            buffer += chunk.decode("utf-8")
                            continue
                        line, buffer = buffer.split("\n", 1)
                        record = json.loads(line)
                        records.append(record)
                        if record.get("event") == name:
                            return
                    raise RuntimeError(f"Real bot did not reach {name}")

                wait_event("prompt_ready")
                with World.open(directory) as world:
                    world.advance_time(5)
                if interact is None:
                    before = client(
                        "/v1/callbacks",
                        {"request_id": "tap-1", "chat_id": 1, "message_id": 2, "data": "confirm"},
                    )
                else:
                    before = interact(
                        {
                            "endpoint": bridge.base_url,
                            "capability": capability,
                            "world_id": world_id,
                            "user_id": 1,
                        }
                    )
                wait_event("callback_received")
                bot.kill()
                tail, error = bot.communicate(timeout=5)
                killed = bot.returncode
                records.extend(json.loads(line) for line in (buffer + tail).splitlines())
                if error:
                    raise RuntimeError("Interrupted bot wrote unexpected stderr")
            finally:
                if bot.poll() is None:
                    bot.kill()
                    bot.wait(timeout=5)
        recovered = subprocess.run(
            [sys.executable, "callback_bot.py"],
            env=environment,
            capture_output=True,
            text=True,
            timeout=15,
        )
        if recovered.returncode != 0:
            raise RuntimeError("Restarted bot did not complete its callback")
        after = client("/v1/callbacks/" + before["callback"]["id"])
        with World.open(directory) as world:
            result = {
                "before": before,
                "after": after,
                "killed": killed,
                "history": world.history(1),
                "pending": world.poll_updates(2),
                "bot_before": records,
                "bot_after": [json.loads(line) for line in recovered.stdout.splitlines()],
            }
        if observe is not None:
            result["client"] = observe()
        serialized = json.dumps(result)
        if token in serialized or capability in serialized or token in recovered.stderr:
            raise RuntimeError("Callback evidence contains a capability")
        return result


if __name__ == "__main__":
    print(json.dumps(run()))
