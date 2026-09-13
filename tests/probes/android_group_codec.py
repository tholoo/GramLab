"""Project one synthetic supergroup through the actual Android bridge codec."""

import json
import subprocess
from collections.abc import Callable
from pathlib import Path

from android_guest import main

from gramlab.client_bridge import ClientBridge
from gramlab.world import World


def probe(adb: Callable[..., subprocess.CompletedProcess[str]]) -> dict[str, object]:
    directory = Path("world")
    with World.create(directory, seed=41, now=1_700_000_000) as world:
        owner = world.create_user(first_name="Mina", username="mina")
        member = world.create_user(first_name="Arman", username="arman")
        bot = world.create_user(first_name="Helper", username="helper_bot", is_bot=True)
        group = world.create_group_chat(
            title="Study group",
            creator_id=owner["id"],
            member_ids=[member["id"]],
            bot_ids=[bot["id"]],
        )
        world.send_message(chat_id=group["id"], sender_id=member["id"], text="/game")
        world.send_message(
            chat_id=group["id"],
            sender_id=bot["id"],
            text="Ready for the group",
            reply_markup={"inline_keyboard": [[{"text": "Continue", "callback_data": "continue"}]]},
        )
        capability = world.issue_client_token(member["id"])
        world_id = world.world_id

    with ClientBridge(directory) as server:
        configuration = {
            "endpoint": server.base_url.replace("127.0.0.1", "10.0.2.2"),
            "capability": capability,
            "world_id": world_id,
            "user_id": member["id"],
            "bridge_version": 6,
        }
        Path("client-config.json").write_text(json.dumps(configuration))
        for command in (
            ("push", "/work/client.apk", "/data/local/tmp/gramlab-group-client.apk"),
            ("push", "/work/client-config.json", "/data/local/tmp/gramlab-group-config.json"),
            ("shell", "chmod", "0444", "/data/local/tmp/gramlab-group-client.apk"),
            ("shell", "chmod", "0400", "/data/local/tmp/gramlab-group-config.json"),
        ):
            if adb(*command, timeout=30).returncode:
                raise RuntimeError("Group codec preparation failed")
        result = adb(
            "shell",
            "CLASSPATH=/data/local/tmp/gramlab-group-client.apk",
            "/system/bin/app_process",
            "/system/bin",
            "org.telegram.gramlab.BridgeProbe",
            "/data/local/tmp/gramlab-group-config.json",
            "group",
            timeout=30,
        )
        retained = result.stdout + result.stderr
        if capability in retained:
            raise RuntimeError("Group codec output contained a capability")
        return {
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }


if __name__ == "__main__":
    main(probe)
