"""Trusted inline-button selection shared by virtual and actual client scenarios."""

from __future__ import annotations

import threading
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

from gramlab._composer import composer_text
from gramlab.world import World


class Interactions:
    def __init__(
        self,
        directory: Path,
        *,
        lock: threading.Lock,
        tap: Callable[..., dict[str, Any]] | None = None,
        compose: Callable[..., dict[str, Any]] | None = None,
        start_chat: Callable[..., dict[str, Any]] | None = None,
    ) -> None:
        self.directory = directory
        self._lock = lock
        self.tap = tap
        self.compose = compose
        self.start_chat = start_chat
        if (compose is None) != (start_chat is None):
            raise ValueError("Native composer and start-chat handlers must be configured together")
        self.records: list[dict[str, Any]] = []
        self.failed = False
        self._quota_lock = threading.Lock()
        self._rich_reserved = 0
        self.virtual_persona: int | None = None
        self.virtual_client_nonce = uuid.uuid4().hex

    def select_virtual_persona(self, user_id: int) -> str:
        """Select the simulated client under the shared input lock."""
        if self.virtual_persona != user_id:
            self.virtual_persona = user_id
            self.virtual_client_nonce = uuid.uuid4().hex
        return self.virtual_client_nonce

    def _check_capacity(self) -> None:
        with self._quota_lock:
            if len(self.records) + self._rich_reserved >= 64:
                raise ValueError("At most 64 interactions are supported per run")

    def reserve_rich_targets(self, count: int, allocate: Callable[[], None]) -> None:
        """Reserve input slots only after a complete target allocation is durable."""
        with self._quota_lock:
            if (
                type(count) is not int
                or count < 0
                or len(self.records) + self._rich_reserved + count > 64
            ):
                raise ValueError("At most 64 interactions are supported per run")
            allocate()
            self._rich_reserved += count

    def check_rich_capacity(self, count: int) -> None:
        """Reject a known capacity failure before opening a native observation."""
        with self._quota_lock:
            if (
                type(count) is not int
                or count < 0
                or len(self.records) + self._rich_reserved + count > 64
            ):
                raise ValueError("At most 64 interactions are supported per run")

    def claim_rich_target(self, receipt: dict[str, Any]) -> None:
        """Transfer one reservation to its single retained receipt, without freeing capacity."""
        with self._quota_lock:
            if self._rich_reserved <= 0:
                raise RuntimeError("Rich target has no reserved interaction slot")
            self._rich_reserved -= 1
            self.records.append(receipt)

    def type_message(self, *, chat_id: int, text: str) -> dict[str, Any]:
        return self._composer_action(chat_id, text, composer_text(text), start=False)

    def start_bot_chat(self, *, chat_id: int) -> dict[str, Any]:
        return self._composer_action(chat_id, "/start", {"text": "/start"}, start=True)

    def _composer_action(
        self, chat_id: int, text: str, message: dict[str, Any], *, start: bool
    ) -> dict[str, Any]:
        if type(chat_id) is not int or not 0 < chat_id < 2**63:
            raise ValueError("Composer requires a positive integer chat identifier")
        with self._lock:
            self._check_capacity()
            with World.open(self.directory) as world:
                chat = world.get_chat(chat_id)
                history = world.history(chat_id)
                if start and history:
                    raise ValueError("Start Bot requires a new empty conversation")
                if not start and not history:
                    raise ValueError("Start the new bot conversation before typing")
                record: dict[str, Any] = {
                    "operation": "start_bot_chat" if start else "type_message",
                    "chat_id": chat_id,
                    "text": text,
                    "native": self.compose is not None,
                }
                if self.compose is None:
                    self.select_virtual_persona(chat["user_id"])
                    record["sends"] = [
                        world.send_client_message(
                            user_id=chat["user_id"],
                            chat_id=chat_id,
                            request_id=uuid.uuid4().hex,
                            **message,
                        )
                    ]
                else:
                    try:
                        if start:
                            if self.start_chat is None:
                                raise RuntimeError("Native Start Bot handler is unavailable")
                            record.update(self.start_chat(chat))
                        else:
                            record.update(self.compose(chat, text, message))
                    except Exception as error:
                        self.failed = True
                        record["failure"] = type(error).__name__
                        self.records.append(record)
                        raise RuntimeError("Android composer input failed") from None
            self.records.append(record)
            return record

    def tap_inline_button(
        self, *, chat_id: int, message_id: int, row: int, column: int
    ) -> dict[str, Any]:
        if any(
            type(value) is not int or not 0 <= value < 2**63
            for value in (chat_id, message_id, row, column)
        ):
            raise ValueError("Inline target requires nonnegative integer identifiers and indices")
        with self._lock:
            self._check_capacity()
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
                    self.select_virtual_persona(chat["user_id"])
                    record["callback"] = world.create_callback(
                        user_id=chat["user_id"],
                        chat_id=chat_id,
                        message_id=message_id,
                        data=button["callback_data"],
                        request_id=uuid.uuid4().hex,
                        version=4,
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
