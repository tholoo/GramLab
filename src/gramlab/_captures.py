"""Trusted semantic capture validation shared by simulation and actual rendering."""

from __future__ import annotations

import re
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

from gramlab.reports import _Redactor
from gramlab.world import World


def _rich_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "".join(_rich_text(child) for child in value)
    if value["type"] == "custom_emoji":
        return cast(str, value["alternative_text"])
    if value["type"] == "button":
        return _rich_text(value["button"]["text"])
    return _rich_text(value["text"])


def _rich_fragments(rich_message: dict[str, Any]) -> list[str]:
    fragments: list[str] = []
    pending = list(reversed(rich_message["blocks"]))
    while pending:
        block = pending.pop()
        for name in ("text", "summary", "caption", "credit"):
            if name in block:
                if name == "caption" and block["type"] == "photo":
                    caption = block[name]
                    fragments.extend(
                        _rich_text(caption[field])
                        for field in ("text", "credit")
                        if field in caption
                    )
                else:
                    fragments.append(_rich_text(block[name]))
        if "blocks" in block:
            pending.extend(reversed(block["blocks"]))
        if "items" in block:
            for item in reversed(block["items"]):
                pending.extend(reversed(item["blocks"]))
        if "cells" in block:
            for row in block["cells"]:
                for cell in row:
                    if "text" in cell:
                        fragments.append(_rich_text(cell["text"]))
        if block["type"] == "buttons":
            fragments.extend(_rich_text(button["text"]) for button in block["buttons"])
    return fragments


def _message_fragments(message: dict[str, Any]) -> list[str]:
    fragments = [message["text"]]
    if "caption" in message:
        fragments.append(message["caption"])
    if "rich_message" in message:
        fragments.extend(_rich_fragments(message["rich_message"]))
    return fragments


class Captures:
    def __init__(
        self,
        directory: Path,
        *,
        lock: threading.Lock | None = None,
        render: Callable[[dict[str, Any], str, list[str]], dict[str, Any]] | None = None,
    ) -> None:
        self.directory = directory
        self.render = render
        self.records: list[dict[str, Any]] = []
        self.failed = False
        self._lock = lock if lock is not None else threading.Lock()

    def capture_chat(self, *, chat_id: int, label: str, contains: list[str]) -> dict[str, Any]:
        if (
            type(chat_id) is not int
            or not isinstance(label, str)
            or re.fullmatch(r"[a-z][a-z0-9_-]{0,63}", label) is None
            or _Redactor(()).text(label) != label
            or not isinstance(contains, list)
            or not 0 <= len(contains) <= 32
            or any(not isinstance(text, str) or not 1 <= len(text) <= 4096 for text in contains)
        ):
            raise ValueError("Capture requires a chat, safe label and up to 32 expected texts")
        with self._lock:
            if len(self.records) >= 8 or any(record["label"] == label for record in self.records):
                raise ValueError("Capture labels must be unique and at most eight are supported")
            with World.open(self.directory) as world:
                chats = [chat for chat in world.snapshot()["chats"] if chat["id"] == chat_id]
                if not chats:
                    raise ValueError("Capture chat does not exist")
                history = world.history(chat_id)
            if not contains and history:
                raise ValueError("An empty expected-text list requires an empty chat")
            fragments = [
                fragment for message in history for fragment in _message_fragments(message)
            ]
            if any(not any(text in fragment for fragment in fragments) for text in contains):
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
