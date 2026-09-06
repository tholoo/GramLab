"""Trusted inline-button selection shared by virtual and actual client scenarios."""

from __future__ import annotations

import threading
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

from gramlab.world import World


class Interactions:
    def __init__(
        self,
        directory: Path,
        *,
        lock: threading.Lock,
        tap: Callable[..., dict[str, Any]] | None = None,
    ) -> None:
        self.directory = directory
        self._lock = lock
        self.tap = tap
        self.records: list[dict[str, Any]] = []
        self.failed = False

    def tap_inline_button(
        self, *, chat_id: int, message_id: int, row: int, column: int
    ) -> dict[str, Any]:
        if any(
            type(value) is not int or not 0 <= value < 2**63
            for value in (chat_id, message_id, row, column)
        ):
            raise ValueError("Inline target requires nonnegative integer identifiers and indices")
        with self._lock:
            if len(self.records) >= 64:
                raise ValueError("At most 64 inline interactions are supported per run")
            with World.open(self.directory) as world:
                chat = world.get_chat(chat_id)
                message = world.get_message(chat_id, message_id)
                keyboard = message.get("reply_markup", {}).get("inline_keyboard", [])
                if (
                    message["sender_id"] != chat["bot_id"]
                    or row >= len(keyboard)
                    or column >= len(keyboard[row])
                ):
                    raise ValueError("Inline target is absent from the bot message")
                button = keyboard[row][column]
                record: dict[str, Any] = {
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "row": row,
                    "column": column,
                    "native": False,
                }
                if self.tap is None:
                    record["callback"] = world.create_callback(
                        user_id=chat["user_id"],
                        chat_id=chat_id,
                        message_id=message_id,
                        data=button["callback_data"],
                        request_id=uuid.uuid4().hex,
                    )
                else:
                    try:
                        observed = self.tap(chat, message, row, column)
                        record.update(observed)
                        record["native"] = True
                    except Exception as error:
                        self.failed = True
                        record["failure"] = type(error).__name__
                        self.records.append(record)
                        raise RuntimeError("Android inline input failed") from None
            self.records.append(record)
            return record
