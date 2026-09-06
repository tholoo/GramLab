"""Trusted semantic capture validation shared by simulation and actual rendering."""

from __future__ import annotations

import re
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

from gramlab.reports import _Redactor
from gramlab.world import World


class Captures:
    def __init__(
        self,
        directory: Path,
        *,
        render: Callable[[dict[str, Any], str, list[str]], dict[str, Any]] | None = None,
    ) -> None:
        self.directory = directory
        self.render = render
        self.records: list[dict[str, Any]] = []
        self.failed = False
        self._lock = threading.Lock()

    def capture_chat(self, *, chat_id: int, label: str, contains: list[str]) -> dict[str, Any]:
        if (
            type(chat_id) is not int
            or not isinstance(label, str)
            or re.fullmatch(r"[a-z][a-z0-9_-]{0,63}", label) is None
            or _Redactor(()).text(label) != label
            or not isinstance(contains, list)
            or not 1 <= len(contains) <= 32
            or any(not isinstance(text, str) or not 1 <= len(text) <= 4096 for text in contains)
        ):
            raise ValueError("Capture requires a chat, safe label and 1 to 32 expected texts")
        with self._lock:
            if len(self.records) >= 8 or any(record["label"] == label for record in self.records):
                raise ValueError("Capture labels must be unique and at most eight are supported")
            with World.open(self.directory) as world:
                chats = [chat for chat in world.snapshot()["chats"] if chat["id"] == chat_id]
                if not chats:
                    raise ValueError("Capture chat does not exist")
                history = world.history(chat_id)
            if any(not any(text in message["text"] for message in history) for text in contains):
                raise ValueError("Expected capture text is absent from the authoritative chat")
            record: dict[str, Any] = {
                "chat_id": chat_id,
                "label": label,
                "history": history,
                "rendered": False,
            }
            if self.render is not None:
                try:
                    record["android"] = self.render(chats[0], label, contains)
                    record["rendered"] = True
                except Exception as error:
                    self.failed = True
                    record["failure"] = type(error).__name__
                    self.records.append(record)
                    raise RuntimeError("Android capture failed") from None
            self.records.append(record)
            return record
