"""Atomic publication of final messages inside an existing World transaction."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from gramlab.documents import canonical_document_id
from gramlab.entities import canonical_custom_emoji_id


@dataclass(frozen=True, slots=True)
class MediaGroupPosition:
    group_id: int
    ordinal: int


@dataclass(frozen=True, slots=True)
class MessageDraft:
    chat_id: int
    sender_id: int
    content: Mapping[str, Any]
    media_group: MediaGroupPosition | None = None


def message_assets(message: Mapping[str, Any]) -> set[int]:
    assets: set[int] = set()
    if "photo" in message:
        assets.add(int(message["photo"]["asset_id"]))
    pending: list[Any] = [message.get("rich_message")]
    while pending:
        value = pending.pop()
        if isinstance(value, dict):
            if value.get("type") == "photo" and "asset_id" in value:
                assets.add(int(value["asset_id"]))
            pending.extend(value.values())
        elif isinstance(value, list):
            pending.extend(value)
    return assets


def message_documents(message: Mapping[str, Any]) -> set[int]:
    if "document" not in message:
        return set()
    document = message["document"]
    if not isinstance(document, dict) or document.keys() != {"document_id"}:
        raise ValueError("Invalid stored document reference")
    return {canonical_document_id(document["document_id"])}


def message_custom_emoji(message: Mapping[str, Any]) -> set[int]:
    result: set[int] = set()
    pending: list[Any] = [
        message.get("entities"),
        message.get("caption_entities"),
        message.get("rich_message"),
    ]
    while pending:
        value = pending.pop()
        if isinstance(value, dict):
            if value.get("type") == "custom_emoji" and "custom_emoji_id" in value:
                result.add(int(canonical_custom_emoji_id(value["custom_emoji_id"])))
            pending.extend(value.values())
        elif isinstance(value, list):
            pending.extend(value)
    return result


class MessagePublication:
    """Persist final message values, their evidence and recipient access atomically."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def publish(self, *, draft: MessageDraft) -> dict[str, Any]:
        self._require_transaction()
        chat = self._chat(draft.chat_id)
        self._require_user(draft.sender_id)
        if draft.sender_id not in (chat["user_id"], chat["bot_id"]):
            raise ValueError("Sender is not a participant in this chat")
        protected = {"id", "chat_id", "sender_id", "date"}
        if draft.content.keys() & protected:
            raise RuntimeError("Message content contains publication-owned fields")
        message_id = int(
            self._connection.execute(
                "SELECT COALESCE(MAX(id), 0)+1 FROM messages WHERE chat_id=?", (draft.chat_id,)
            ).fetchone()[0]
        )
        now = int(self._connection.execute("SELECT now FROM configuration").fetchone()[0])
        message: dict[str, Any] = {
            "id": message_id,
            "chat_id": draft.chat_id,
            "sender_id": draft.sender_id,
            "date": now,
            **dict(draft.content),
        }
        if draft.media_group is not None:
            message["media_group_id"] = str(draft.media_group.group_id)
        self._grant_message(chat["user_id"], message)
        self._connection.execute(
            "INSERT INTO messages VALUES (?, ?, ?)",
            (draft.chat_id, message_id, json.dumps(message)),
        )
        revision = self._emit_message("message.created", chat["user_id"], message)
        self._connection.execute(
            "INSERT INTO message_revisions VALUES (?, ?, ?)",
            (draft.chat_id, message_id, revision),
        )
        if draft.media_group is not None:
            self._connection.execute(
                "INSERT INTO media_group_members VALUES (?, ?, ?, ?)",
                (
                    draft.media_group.group_id,
                    draft.media_group.ordinal,
                    draft.chat_id,
                    message_id,
                ),
            )
        if draft.sender_id == chat["user_id"]:
            self._enqueue_message(chat["bot_id"], message)
        return message

    def replace(self, *, message: dict[str, Any]) -> dict[str, Any]:
        self._require_transaction()
        chat = self._chat(message["chat_id"])
        self._grant_message(chat["user_id"], message)
        self._connection.execute(
            "UPDATE messages SET body=? WHERE chat_id=? AND id=?",
            (json.dumps(message), message["chat_id"], message["id"]),
        )
        revision = self._emit_message("message.edited", chat["user_id"], message)
        self._connection.execute(
            "INSERT OR REPLACE INTO message_revisions VALUES (?, ?, ?)",
            (message["chat_id"], message["id"], revision),
        )
        return message

    def _require_transaction(self) -> None:
        if not self._connection.in_transaction:
            raise RuntimeError("Message publication requires an active World transaction")

    def _chat(self, chat_id: Any) -> dict[str, int]:
        if type(chat_id) is not int or not 0 < chat_id < 2**63:
            raise ValueError("Invalid chat ID")
        row = self._connection.execute(
            "SELECT user_id, bot_id FROM chats WHERE id=?", (chat_id,)
        ).fetchone()
        if row is None:
            raise ValueError("Unknown chat")
        return {"user_id": int(row[0]), "bot_id": int(row[1])}

    def _require_user(self, user_id: Any) -> None:
        if type(user_id) is not int or user_id <= 0:
            raise ValueError("Invalid virtual user ID")
        exists = self._connection.execute(
            "SELECT 1 FROM users WHERE id=?", (user_id,)
        ).fetchone()
        if exists is None:
            raise ValueError("Unknown virtual user")

    def _emit_message(self, kind: str, user_id: int, message: dict[str, Any]) -> int:
        event = self._connection.execute(
            "INSERT INTO events(type, body) VALUES (?, ?)", (kind, json.dumps(message))
        )
        if event.lastrowid is None:
            raise RuntimeError("SQLite did not allocate an event sequence")
        position = int(
            self._connection.execute(
                "SELECT COALESCE(MAX(position), 0) FROM client_changes WHERE user_id=?",
                (user_id,),
            ).fetchone()[0]
        )
        self._connection.execute(
            "INSERT INTO client_changes VALUES (?, ?, ?)",
            (user_id, position + 1, event.lastrowid),
        )
        return int(event.lastrowid)

    def _grant_message(self, user_id: int, message: dict[str, Any]) -> None:
        for identifier in message_custom_emoji(message):
            row = self._connection.execute(
                "SELECT main_asset_id, thumbnail_asset_id FROM custom_emoji WHERE id=?",
                (identifier,),
            ).fetchone()
            if row is None:
                raise ValueError("Custom emoji is unavailable")
            self._connection.execute(
                "INSERT OR IGNORE INTO custom_emoji_grants VALUES (?, ?)",
                (user_id, identifier),
            )
            for asset_id in row:
                self._connection.execute(
                    "INSERT OR IGNORE INTO asset_grants VALUES (?, ?)", (user_id, asset_id)
                )
        for asset_id in message_assets(message):
            self._connection.execute(
                "INSERT OR IGNORE INTO asset_grants VALUES (?, ?)", (user_id, asset_id)
            )
        for document_id in message_documents(message):
            self._connection.execute(
                "INSERT OR IGNORE INTO document_grants VALUES (?, ?)", (user_id, document_id)
            )

    def _enqueue_message(self, bot_id: int, message: dict[str, Any]) -> None:
        selection = json.loads(
            self._connection.execute(
                "SELECT allowed_updates FROM bots WHERE id=?", (bot_id,)
            ).fetchone()[0]
        )
        if selection and "message" not in selection:
            return
        update_id = self._connection.execute(
            "UPDATE bots SET next_update=next_update+1 WHERE id=? RETURNING next_update-1",
            (bot_id,),
        ).fetchone()[0]
        self._connection.execute(
            "INSERT INTO updates VALUES (?, ?, ?)",
            (bot_id, update_id, json.dumps({"update_id": update_id, "message": message})),
        )
