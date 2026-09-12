"""Public scenario for photo then live-document groups through bridge v6."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from gramlab.scenario import Scenario

TRIGGER = "documents / اسناد"


def wait_for_history(lab: Scenario, chat_id: int, count: int) -> list[dict[str, Any]]:
    """Poll owned local state to a deadline without timing the consumer with fixed sleeps."""
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        history = lab.history(chat_id)
        if len(history) == count:
            return history
        if len(history) > count:
            raise RuntimeError("Album scenario observed an unexpected extra message")
    raise RuntimeError("Album scenario history deadline expired")


def main() -> None:
    lab = Scenario.from_environment()
    lab.register_custom_emoji(
        request_id="album-caption",
        custom_emoji_id="1109",
        main=Path("emoji-static.webp").read_bytes(),
        thumbnail=Path("emoji-thumbnail.webp").read_bytes(),
        fallback="👩‍💻",
    )
    user = lab.create_user(first_name="Sara", language_code="fa")
    bot = lab.bots()["albums"]
    chat = lab.open_private_chat(user_id=user["id"], bot_id=bot)
    start = lab.start_bot_chat(chat_id=chat["id"])
    initial = wait_for_history(lab, chat["id"], 3)
    photo_group = initial[1:]
    if (
        [item.get("media_group_id") for item in photo_group] != ["1", "1"]
        or [item["id"] for item in photo_group] != [2, 3]
        or [item.get("caption") for item in photo_group] != ["Album 👩‍💻", None]
    ):
        raise RuntimeError("Photo group lost its original topology")
    first_capture = lab.capture_chat(
        chat_id=chat["id"], label="album-photos", contains=["Album 👩‍💻"]
    )
    composer = lab.type_message(chat_id=chat["id"], text=TRIGGER)
    final = wait_for_history(lab, chat["id"], 6)
    document_group = final[4:]
    if (
        [item.get("media_group_id") for item in document_group] != ["2", "2"]
        or [item["id"] for item in document_group] != [5, 6]
        or [item.get("caption") for item in document_group] != ["First / نخست", "Second / دوم"]
        or [item["document"]["document_id"] for item in document_group] != ["1", "2"]
    ):
        raise RuntimeError("Document group lost its original topology")
    second_capture = lab.capture_chat(
        chat_id=chat["id"],
        label="album-documents",
        contains=["First / نخست", "Second / دوم"],
    )
    print(
        json.dumps(
            {
                "start": start,
                "photo_group": photo_group,
                "photo_capture": first_capture,
                "composer": composer,
                "document_group": document_group,
                "document_capture": second_capture,
                "history": final,
                "events": lab.events(),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
