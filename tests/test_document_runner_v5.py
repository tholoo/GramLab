"""Public runner version selection for ordinary document scenarios."""

import threading
import time
from pathlib import Path

import pytest

from gramlab._android import Android
from gramlab._interactions import Interactions
from gramlab.documents import DocumentUpload
from gramlab.runner import run
from gramlab.runtime import RuntimeProfile
from gramlab.world import World


def profile() -> RuntimeProfile:
    return RuntimeProfile(bubblewrap="", python="", store_paths=())


def test_runner_and_android_admit_explicit_v5_before_reading_run_inputs(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        run(
            tmp_path / "missing.toml",
            tmp_path / "output",
            profile=profile(),
            bridge_version=5,
        )
    assert Android(
        profile(), deadline=time.monotonic() + 5, secrets=[], bridge_version=5
    )._bridge_version == 5


def test_simulated_document_callback_uses_latest_world_contract(tmp_path: Path) -> None:
    directory = tmp_path / "world"
    keyboard = {
        "inline_keyboard": [[{"text": "Reuse / استفاده دوباره", "callback_data": "document:reuse"}]]
    }
    with World.create(directory, seed=107, now=1_700_000_000) as world:
        user = world.create_user(first_name="Sara")
        bot = world.create_user(first_name="Files", is_bot=True)
        chat = world.open_private_chat(user_id=user["id"], bot_id=bot["id"])
        message = world.send_document(
            chat_id=chat["id"],
            sender_id=bot["id"],
            document={"media": "attach://document"},
            uploads={"document": DocumentUpload(b"ordinary document", "report.pdf")},
            caption="فایل Report",
            reply_markup=keyboard,
        )

    interaction = Interactions(directory, lock=threading.Lock()).tap_inline_button(
        chat_id=chat["id"], message_id=message["id"], row=0, column=0
    )
    callback = interaction["callback"]
    assert callback["message"] == message
    assert callback["data"] == "document:reuse"
    with World.open(directory) as world:
        assert world.callback_dependencies(user["id"], callback, version=5)["documents"] == [
            world.granted_document(user["id"], "1")[0]
        ]
