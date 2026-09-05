"""Authoritative synthetic state for the foundation prototype, independently implemented.

This is the internal world boundary; the public scenario SDK follows the Android proof.
Directories are dedicated supervisor-owned data, never personal client state.
"""

from __future__ import annotations

import hashlib
import json
import re
import secrets
import sqlite3
import uuid
from pathlib import Path
from types import TracebackType
from typing import Any, Self


class World:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection
        connection.execute("PRAGMA foreign_keys=ON")

    @classmethod
    def create(cls, directory: Path, *, seed: int, now: int) -> Self:
        directory.mkdir(mode=0o700)
        connection = sqlite3.connect(directory / "world.sqlite3")
        try:
            connection.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE configuration (
                    seed INTEGER NOT NULL, now INTEGER NOT NULL, world_id TEXT NOT NULL
                );
                CREATE TABLE users (id INTEGER PRIMARY KEY, body TEXT NOT NULL);
                CREATE TABLE bots (
                    id INTEGER PRIMARY KEY REFERENCES users(id), next_update INTEGER NOT NULL
                );
                CREATE TABLE bot_tokens (
                    digest TEXT PRIMARY KEY, bot_id INTEGER NOT NULL REFERENCES bots(id)
                );
                CREATE TABLE client_tokens (
                    digest TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id)
                );
                CREATE TABLE chats (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    bot_id INTEGER NOT NULL REFERENCES users(id),
                    UNIQUE(user_id, bot_id)
                );
                CREATE TABLE messages (
                    chat_id INTEGER NOT NULL REFERENCES chats(id),
                    id INTEGER NOT NULL, body TEXT NOT NULL, PRIMARY KEY(chat_id, id)
                );
                CREATE TABLE updates (
                    bot_id INTEGER NOT NULL REFERENCES bots(id),
                    id INTEGER NOT NULL, body TEXT NOT NULL, PRIMARY KEY(bot_id, id)
                );
                CREATE TABLE events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT NOT NULL, body TEXT NOT NULL
                );
                PRAGMA user_version=2;
            """)
            with connection:
                connection.execute(
                    "INSERT INTO configuration VALUES (?, ?, ?)", (seed, now, str(uuid.uuid4()))
                )
        except BaseException:
            connection.close()
            raise
        return cls(connection)

    @classmethod
    def open(cls, directory: Path) -> Self:
        uri = (directory / "world.sqlite3").absolute().as_uri() + "?mode=rw"
        connection = sqlite3.connect(uri, uri=True)
        try:
            if connection.execute("PRAGMA user_version").fetchone()[0] == 1:
                with connection:
                    connection.execute("BEGIN IMMEDIATE")
                    # Another opener may have finished migration while this one waited.
                    if connection.execute("PRAGMA user_version").fetchone()[0] == 1:
                        connection.execute("ALTER TABLE configuration ADD COLUMN world_id TEXT")
                        connection.execute(
                            "UPDATE configuration SET world_id=?", (str(uuid.uuid4()),)
                        )
                        connection.execute(
                            "CREATE TABLE client_tokens (digest TEXT PRIMARY KEY, "
                            "user_id INTEGER NOT NULL REFERENCES users(id))"
                        )
                        connection.execute("PRAGMA user_version=2")
            if connection.execute("PRAGMA user_version").fetchone()[0] != 2:
                raise ValueError("Unsupported world schema")
        except BaseException:
            connection.close()
            raise
        return cls(connection)

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self._connection.close()

    def create_user(
        self,
        *,
        first_name: str,
        is_bot: bool = False,
        username: str | None = None,
        language_code: str | None = None,
    ) -> dict[str, Any]:
        if not first_name.strip():
            raise ValueError("Virtual user first_name must not be empty")
        body: dict[str, Any] = {"is_bot": is_bot, "first_name": first_name}
        if username is not None:
            body["username"] = username
        if language_code is not None:
            body["language_code"] = language_code
        with self._connection:
            cursor = self._connection.execute(
                "INSERT INTO users(body) VALUES (?)", (json.dumps(body),)
            )
            body["id"] = cursor.lastrowid
            if is_bot:
                self._connection.execute("INSERT INTO bots VALUES (?, 1)", (body["id"],))
            self._emit("user.created", body)
        return body

    def open_private_chat(self, *, user_id: int, bot_id: int) -> dict[str, Any]:
        user = self.get_user(user_id)
        bot = self.get_user(bot_id)
        if user["is_bot"] or not bot["is_bot"]:
            raise ValueError("Private bot chats require a virtual user and a bot")
        with self._connection:
            inserted = self._connection.execute(
                "INSERT OR IGNORE INTO chats(user_id, bot_id) VALUES (?, ?)", (user_id, bot_id)
            )
            row = self._connection.execute(
                "SELECT id FROM chats WHERE user_id=? AND bot_id=?", (user_id, bot_id)
            ).fetchone()
            chat = {"id": row[0], "type": "private", "user_id": user_id, "bot_id": bot_id}
            if inserted.rowcount:
                self._emit("chat.created", chat)
        return chat

    def get_user(self, user_id: int) -> dict[str, Any]:
        if type(user_id) is not int or user_id <= 0:
            raise ValueError("Invalid virtual user ID")
        row = self._connection.execute("SELECT body FROM users WHERE id=?", (user_id,)).fetchone()
        if row is None:
            raise ValueError("Unknown virtual user")
        return {"id": user_id, **json.loads(row[0])}

    def issue_bot_token(self, bot_id: int) -> str:
        if not self.get_user(bot_id)["is_bot"]:
            raise ValueError("Only virtual bots can receive Bot API tokens")
        token = f"{bot_id}:gramlab_{secrets.token_urlsafe(32)}"
        with self._connection:
            self._connection.execute(
                "INSERT INTO bot_tokens VALUES (?, ?)",
                (hashlib.sha256(token.encode()).hexdigest(), bot_id),
            )
        return token

    def authenticate_bot(self, token: str) -> int | None:
        # Only locally issued capabilities are accepted; never import real Bot API credentials.
        if re.fullmatch(r"[1-9][0-9]*:gramlab_[A-Za-z0-9_-]{43}", token) is None:
            return None
        row = self._connection.execute(
            "SELECT bot_id FROM bot_tokens WHERE digest=?",
            (hashlib.sha256(token.encode()).hexdigest(),),
        ).fetchone()
        return int(row[0]) if row else None

    def private_chat_for_bot(self, bot_id: int, user_id: int) -> dict[str, Any]:
        if type(user_id) is not int or user_id <= 0:
            raise ValueError("Invalid private chat ID")
        row = self._connection.execute(
            "SELECT id FROM chats WHERE bot_id=? AND user_id=?", (bot_id, user_id)
        ).fetchone()
        if row is None:
            raise ValueError("Private chat is not available to this bot")
        return self.get_chat(row[0])

    def issue_client_token(self, user_id: int) -> str:
        if self.get_user(user_id)["is_bot"]:
            raise ValueError("Client personas must be virtual users")
        token = f"gramlab-client_{secrets.token_urlsafe(32)}"
        with self._connection:
            self._connection.execute(
                "INSERT INTO client_tokens VALUES (?, ?)",
                (hashlib.sha256(token.encode()).hexdigest(), user_id),
            )
        return token

    def authenticate_client(self, token: str) -> int | None:
        if re.fullmatch(r"gramlab-client_[A-Za-z0-9_-]{43}", token) is None:
            return None
        row = self._connection.execute(
            "SELECT user_id FROM client_tokens WHERE digest=?",
            (hashlib.sha256(token.encode()).hexdigest(),),
        ).fetchone()
        return int(row[0]) if row else None

    def advance_time(self, seconds: int) -> int:
        if type(seconds) is not int or not 0 <= seconds <= 2**63 - 1:
            raise ValueError("World time advances by a nonnegative integer number of seconds")
        with self._connection:
            row = self._connection.execute(
                "UPDATE configuration SET now=now+? WHERE now<=? RETURNING now",
                (seconds, 2**63 - 1 - seconds),
            ).fetchone()
            if row is None:
                raise ValueError("World time exceeds its supported range")
            if seconds:
                self._emit("clock.advanced", {"now": row[0]})
        return int(row[0])

    def _emit(self, kind: str, data: dict[str, Any]) -> None:
        self._connection.execute(
            "INSERT INTO events(type, body) VALUES (?, ?)", (kind, json.dumps(data))
        )

    def events(self, *, after: int = 0) -> list[dict[str, Any]]:
        return [
            {"sequence": row[0], "type": row[1], "data": json.loads(row[2])}
            for row in self._connection.execute(
                "SELECT sequence, type, body FROM events WHERE sequence>? ORDER BY sequence",
                (after,),
            )
        ]

    def get_chat(self, chat_id: int) -> dict[str, Any]:
        if type(chat_id) is not int or chat_id <= 0:
            raise ValueError("Invalid chat ID")
        row = self._connection.execute(
            "SELECT user_id, bot_id FROM chats WHERE id=?", (chat_id,)
        ).fetchone()
        if row is None:
            raise ValueError("Unknown chat")
        return {"id": chat_id, "type": "private", "user_id": row[0], "bot_id": row[1]}

    def send_message(self, *, chat_id: int, sender_id: int, text: str) -> dict[str, Any]:
        if not isinstance(text, str) or not 1 <= len(text) <= 4096:
            raise ValueError("Text must contain 1 to 4096 characters")
        text.encode("utf-8", errors="strict")
        with self._connection:
            self._connection.execute("BEGIN IMMEDIATE")
            chat = self.get_chat(chat_id)
            self.get_user(sender_id)
            if sender_id not in (chat["user_id"], chat["bot_id"]):
                raise ValueError("Sender is not a participant in this chat")
            message_id = self._connection.execute(
                "SELECT COALESCE(MAX(id), 0)+1 FROM messages WHERE chat_id=?", (chat_id,)
            ).fetchone()[0]
            now = self._connection.execute("SELECT now FROM configuration").fetchone()[0]
            message = {
                "id": message_id,
                "chat_id": chat_id,
                "sender_id": sender_id,
                "date": now,
                "text": text,
            }
            self._connection.execute(
                "INSERT INTO messages VALUES (?, ?, ?)", (chat_id, message_id, json.dumps(message))
            )
            self._emit("message.created", message)
            if sender_id == chat["user_id"]:
                update_id = self._connection.execute(
                    "UPDATE bots SET next_update=next_update+1 WHERE id=? RETURNING next_update-1",
                    (chat["bot_id"],),
                ).fetchone()[0]
                update = {"update_id": update_id, "message": message}
                self._connection.execute(
                    "INSERT INTO updates VALUES (?, ?, ?)",
                    (chat["bot_id"], update_id, json.dumps(update)),
                )
        return message

    def history(self, chat_id: int) -> list[dict[str, Any]]:
        self.get_chat(chat_id)
        return [
            json.loads(row[0])
            for row in self._connection.execute(
                "SELECT body FROM messages WHERE chat_id=? ORDER BY id", (chat_id,)
            )
        ]

    def poll_updates(
        self, bot_id: int, *, offset: int = 0, limit: int = 100
    ) -> list[dict[str, Any]]:
        if type(offset) is not int or not 0 <= offset < 2**63:
            raise ValueError("This prototype requires a nonnegative signed 64-bit update offset")
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("Update limit must be between 1 and 100")
        if not self.get_user(bot_id)["is_bot"]:
            raise ValueError("Only bots have update queues")
        with self._connection:
            self._connection.execute("BEGIN IMMEDIATE")
            self._connection.execute(
                "DELETE FROM updates WHERE bot_id=? AND id<?", (bot_id, offset)
            )
            return [
                json.loads(row[0])
                for row in self._connection.execute(
                    "SELECT body FROM updates WHERE bot_id=? ORDER BY id LIMIT ?", (bot_id, limit)
                )
            ]

    def snapshot(self) -> dict[str, Any]:
        seed, now = self._connection.execute("SELECT seed, now FROM configuration").fetchone()
        return {
            "schema": 1,
            "seed": seed,
            "now": now,
            "users": [
                {"id": row[0], **json.loads(row[1])}
                for row in self._connection.execute("SELECT id, body FROM users ORDER BY id")
            ],
            "chats": [
                {"id": row[0], "type": "private", "user_id": row[1], "bot_id": row[2]}
                for row in self._connection.execute(
                    "SELECT id, user_id, bot_id FROM chats ORDER BY id"
                )
            ],
        }

    def client_snapshot(self, user_id: int) -> dict[str, Any]:
        with self._connection:
            # Pin one SQLite read snapshot before reading either data or its journal cursor.
            self._connection.execute("BEGIN")
            user = self.get_user(user_id)
            if user["is_bot"]:
                raise ValueError("Client personas must be virtual users")
            world_id, now = self._connection.execute(
                "SELECT world_id, now FROM configuration"
            ).fetchone()
            cursor = self._connection.execute(
                "SELECT COALESCE(MAX(sequence), 0) FROM events"
            ).fetchone()[0]
            chats = [
                self.get_chat(row[0])
                for row in self._connection.execute(
                    "SELECT id FROM chats WHERE user_id=? ORDER BY id", (user_id,)
                )
            ]
            visible_users = {user_id, *(chat["bot_id"] for chat in chats)}
            return {
                "schema": 1,
                "world_id": world_id,
                "user_id": user_id,
                "cursor": cursor,
                "now": now,
                "users": [self.get_user(identifier) for identifier in sorted(visible_users)],
                "chats": chats,
                "messages": [message for chat in chats for message in self.history(chat["id"])],
            }

    def client_events(self, user_id: int, *, after: int, limit: int = 100) -> dict[str, Any]:
        if type(after) is not int or not 0 <= after < 2**63:
            raise ValueError("Invalid client cursor")
        if type(limit) is not int or not 1 <= limit <= 1000:
            raise ValueError("Client event limit must be between 1 and 1000")
        with self._connection:
            self._connection.execute("BEGIN")
            if self.get_user(user_id)["is_bot"]:
                raise ValueError("Client personas must be virtual users")
            world_id = self._connection.execute("SELECT world_id FROM configuration").fetchone()[0]
            head = self._connection.execute(
                "SELECT COALESCE(MAX(sequence), 0) FROM events"
            ).fetchone()[0]
            if after > head:
                raise ValueError("Client cursor is ahead of this world; resnapshot required")
            chats = dict(
                self._connection.execute(
                    "SELECT id, bot_id FROM chats WHERE user_id=?", (user_id,)
                ).fetchall()
            )
            visible_users = {user_id, *chats.values()}
            rows = self._connection.execute(
                "SELECT sequence, type, body FROM events WHERE sequence>? "
                "ORDER BY sequence LIMIT ?",
                (after, limit),
            ).fetchall()
            events = []
            for sequence, kind, body in rows:
                data = json.loads(body)
                if kind == "message.created":
                    visible = data["chat_id"] in chats
                elif kind == "chat.created":
                    visible = data["user_id"] == user_id
                elif kind == "user.created":
                    visible = data["id"] in visible_users
                elif kind == "clock.advanced":
                    visible = True
                else:
                    raise ValueError("Unsupported client event type")
                if visible:
                    events.append({"sequence": sequence, "type": kind, "data": data})
            return {
                "schema": 1,
                "world_id": world_id,
                "user_id": user_id,
                "cursor": rows[-1][0] if rows else after,
                "head": head,
                "events": events,
            }
