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

from gramlab.entities import formatting_entities

# Names are the subscription vocabulary, not a claim that each type can be generated.
# See docs/development/update-delivery-references.md for the pinned 10.3 contract.
_UPDATE_TYPES = frozenset(
    "message edited_message channel_post edited_channel_post inline_query chosen_inline_result "
    "callback_query custom_event custom_query shipping_query pre_checkout_query poll poll_answer "
    "my_chat_member chat_member chat_join_request chat_boost removed_chat_boost message_reaction "
    "message_reaction_count business_connection business_message edited_business_message "
    "deleted_business_messages purchased_paid_media managed_bot guest_message subscription "
    "stopped_message_generation".split()
)
_DEFAULT_EXCLUDED = frozenset({"chat_member", "message_reaction", "message_reaction_count"})


def update_selection(value: Any) -> list[str] | None:
    """Normalize a parsed subscription array; malformed values leave the setting alone."""
    if not isinstance(value, list) or any(not isinstance(name, str) for name in value):
        return None
    return sorted({name.lower() for name in value} & _UPDATE_TYPES)


_CALLBACK_TABLE = """
    CREATE TABLE callbacks (
        id TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id),
        bot_id INTEGER NOT NULL REFERENCES bots(id),
        request_id TEXT NOT NULL, request_body TEXT NOT NULL,
        body TEXT NOT NULL, answer TEXT,
        UNIQUE(user_id, request_id)
    )
"""

_CLIENT_CHANGES_TABLE = """
    CREATE TABLE client_changes (
        user_id INTEGER NOT NULL REFERENCES users(id), position INTEGER NOT NULL,
        event_sequence INTEGER NOT NULL UNIQUE REFERENCES events(sequence),
        PRIMARY KEY(user_id, position)
    )
"""
_CLIENT_SENDS_TABLE = """
    CREATE TABLE client_sends (
        user_id INTEGER NOT NULL REFERENCES users(id),
        chat_id INTEGER NOT NULL REFERENCES chats(id), request_id TEXT NOT NULL,
        request_body TEXT NOT NULL, body TEXT NOT NULL, position INTEGER NOT NULL,
        PRIMARY KEY(user_id, chat_id, request_id),
        FOREIGN KEY(user_id, position) REFERENCES client_changes(user_id, position)
    )
"""


def _inline_keyboard(markup: dict[str, Any] | None) -> dict[str, Any] | None:
    if markup is None:
        return None
    if not isinstance(markup, dict) or markup.keys() != {"inline_keyboard"}:
        raise ValueError("GRAMLAB_UNSUPPORTED: only inline callback keyboards are implemented")
    if not isinstance(markup["inline_keyboard"], list):
        raise ValueError("Inline keyboard must contain an array of rows")
    rows = []
    for row in markup["inline_keyboard"]:
        if not isinstance(row, list):
            raise ValueError("Inline keyboard rows must be arrays")
        buttons = []
        for button in row:
            if not isinstance(button, dict) or button.keys() != {"text", "callback_data"}:
                raise ValueError("GRAMLAB_UNSUPPORTED: button requires text and callback_data")
            text, data = button["text"], button["callback_data"]
            if not isinstance(text, str) or not text:
                raise ValueError("Button text must be a nonempty string")
            text.encode("utf-8", errors="strict")
            if not isinstance(data, str) or not 1 <= len(data.encode("utf-8")) <= 64:
                raise ValueError("Callback data must contain 1 to 64 UTF-8 bytes")
            buttons.append({"text": text, "callback_data": data})
        if buttons:
            rows.append(buttons)
    return {"inline_keyboard": rows} if rows else None


class World:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection
        connection.execute("PRAGMA foreign_keys=ON")

    @classmethod
    def create(cls, directory: Path, *, seed: int, now: int) -> Self:
        directory.mkdir(mode=0o700)
        connection = sqlite3.connect(directory / "world.sqlite3")
        try:
            connection.executescript(f"""
                PRAGMA journal_mode=WAL;
                CREATE TABLE configuration (
                    seed INTEGER NOT NULL, now INTEGER NOT NULL, world_id TEXT NOT NULL
                );
                CREATE TABLE users (id INTEGER PRIMARY KEY, body TEXT NOT NULL);
                CREATE TABLE bots (
                    id INTEGER PRIMARY KEY REFERENCES users(id), next_update INTEGER NOT NULL,
                    allowed_updates TEXT NOT NULL DEFAULT '[]'
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
                {_CALLBACK_TABLE};
                {_CLIENT_CHANGES_TABLE};
                {_CLIENT_SENDS_TABLE};
                PRAGMA user_version=5;
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
            if connection.execute("PRAGMA user_version").fetchone()[0] == 2:
                with connection:
                    connection.execute("BEGIN IMMEDIATE")
                    if connection.execute("PRAGMA user_version").fetchone()[0] == 2:
                        connection.execute(_CALLBACK_TABLE)
                        connection.execute("PRAGMA user_version=3")
            if connection.execute("PRAGMA user_version").fetchone()[0] == 3:
                with connection:
                    connection.execute("BEGIN IMMEDIATE")
                    if connection.execute("PRAGMA user_version").fetchone()[0] == 3:
                        connection.execute(
                            "ALTER TABLE bots ADD COLUMN allowed_updates TEXT NOT NULL DEFAULT '[]'"
                        )
                        connection.execute("PRAGMA user_version=4")
            if connection.execute("PRAGMA user_version").fetchone()[0] == 4:
                with connection:
                    connection.execute("BEGIN IMMEDIATE")
                    if connection.execute("PRAGMA user_version").fetchone()[0] == 4:
                        connection.execute(_CLIENT_CHANGES_TABLE)
                        connection.execute(_CLIENT_SENDS_TABLE)
                        connection.execute(
                            "INSERT INTO client_changes(user_id, position, event_sequence) "
                            "SELECT chats.user_id, ROW_NUMBER() OVER "
                            "(PARTITION BY chats.user_id ORDER BY events.sequence), "
                            "events.sequence FROM events JOIN chats "
                            "ON chats.id=json_extract(events.body, '$.chat_id') "
                            "WHERE events.type IN ('message.created', 'message.edited')"
                        )
                        connection.execute("PRAGMA user_version=5")
            if connection.execute("PRAGMA user_version").fetchone()[0] != 5:
                raise ValueError("Unsupported world schema")
        except BaseException:
            connection.close()
            raise
        return cls(connection)

    def __enter__(self) -> Self:
        return self

    @property
    def world_id(self) -> str:
        return str(self._connection.execute("SELECT world_id FROM configuration").fetchone()[0])

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
                self._connection.execute(
                    "INSERT INTO bots(id, next_update) VALUES (?, 1)", (body["id"],)
                )
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
        event = self._connection.execute(
            "INSERT INTO events(type, body) VALUES (?, ?)", (kind, json.dumps(data))
        )
        if kind in ("message.created", "message.edited"):
            user_id = self.get_chat(data["chat_id"])["user_id"]
            self._connection.execute(
                "INSERT INTO client_changes VALUES (?, ?, ?)",
                (user_id, self._message_position(user_id) + 1, event.lastrowid),
            )

    def _message_position(self, user_id: int) -> int:
        return int(
            self._connection.execute(
                "SELECT COALESCE(MAX(position), 0) FROM client_changes WHERE user_id=?", (user_id,)
            ).fetchone()[0]
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
        if type(chat_id) is not int or not 0 < chat_id < 2**63:
            raise ValueError("Invalid chat ID")
        row = self._connection.execute(
            "SELECT user_id, bot_id FROM chats WHERE id=?", (chat_id,)
        ).fetchone()
        if row is None:
            raise ValueError("Unknown chat")
        return {"id": chat_id, "type": "private", "user_id": row[0], "bot_id": row[1]}

    def send_message(
        self,
        *,
        chat_id: int,
        sender_id: int,
        text: str,
        reply_markup: dict[str, Any] | None = None,
        entities: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        if not isinstance(text, str) or not 1 <= len(text) <= 4096:
            raise ValueError("Text must contain 1 to 4096 characters")
        text.encode("utf-8", errors="strict")
        formatting = formatting_entities(text, entities)
        keyboard = _inline_keyboard(reply_markup)
        with self._connection:
            self._connection.execute("BEGIN IMMEDIATE")
            if reply_markup is not None and sender_id != self.get_chat(chat_id)["bot_id"]:
                raise ValueError("Only bots can attach inline keyboards")
            return self._insert_message(
                chat_id=chat_id,
                sender_id=sender_id,
                text=text,
                keyboard=keyboard,
                formatting=formatting,
            )

    def _insert_message(
        self,
        *,
        chat_id: int,
        sender_id: int,
        text: str,
        keyboard: dict[str, Any] | None,
        formatting: list[dict[str, Any]] | None,
    ) -> dict[str, Any]:
        """Insert validated content inside the caller's existing writer transaction."""
        chat = self.get_chat(chat_id)
        self.get_user(sender_id)
        if sender_id not in (chat["user_id"], chat["bot_id"]):
            raise ValueError("Sender is not a participant in this chat")
        message_id = self._connection.execute(
            "SELECT COALESCE(MAX(id), 0)+1 FROM messages WHERE chat_id=?", (chat_id,)
        ).fetchone()[0]
        now = self._connection.execute("SELECT now FROM configuration").fetchone()[0]
        message: dict[str, Any] = {
            "id": message_id,
            "chat_id": chat_id,
            "sender_id": sender_id,
            "date": now,
            "text": text,
        }
        if keyboard is not None:
            message["reply_markup"] = keyboard
        if formatting is not None:
            message["entities"] = formatting
        self._connection.execute(
            "INSERT INTO messages VALUES (?, ?, ?)", (chat_id, message_id, json.dumps(message))
        )
        self._emit("message.created", message)
        if sender_id == chat["user_id"]:
            self._enqueue_update(chat["bot_id"], "message", message)
        return message

    def send_client_message(
        self,
        *,
        user_id: int,
        chat_id: int,
        request_id: str,
        text: str,
        entities: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        if (
            not isinstance(request_id, str)
            or re.fullmatch(r"[A-Za-z0-9_-]{1,128}", request_id) is None
        ):
            raise ValueError("Client request_id must be 1 to 128 ASCII identifier characters")
        if not isinstance(text, str) or not 1 <= len(text) <= 4096:
            raise ValueError("Text must contain 1 to 4096 characters")
        text.encode("utf-8", errors="strict")
        formatting = formatting_entities(text, entities)
        command = json.dumps({"text": text, "entities": formatting}, sort_keys=True)
        with self._connection:
            self._connection.execute("BEGIN IMMEDIATE")
            if self.get_user(user_id)["is_bot"] or self.get_chat(chat_id)["user_id"] != user_id:
                raise ValueError("Client send is not available to this persona")
            previous = self._connection.execute(
                "SELECT request_body, body FROM client_sends "
                "WHERE user_id=? AND chat_id=? AND request_id=?",
                (user_id, chat_id, request_id),
            ).fetchone()
            if previous is not None:
                if previous[0] != command:
                    raise ValueError("Request ID already identifies another client send")
                return dict(json.loads(previous[1]))
            message = self._insert_message(
                chat_id=chat_id, sender_id=user_id, text=text, keyboard=None, formatting=formatting
            )
            position = self._message_position(user_id)
            result = {"request_id": request_id, "position": position, "message": message}
            self._connection.execute(
                "INSERT INTO client_sends VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, chat_id, request_id, command, json.dumps(result), position),
            )
            return result

    def history(self, chat_id: int) -> list[dict[str, Any]]:
        self.get_chat(chat_id)
        return [
            json.loads(row[0])
            for row in self._connection.execute(
                "SELECT body FROM messages WHERE chat_id=? ORDER BY id", (chat_id,)
            )
        ]

    def get_message(self, chat_id: int, message_id: int) -> dict[str, Any]:
        self.get_chat(chat_id)
        if type(message_id) is not int or not 0 < message_id < 2**63:
            raise ValueError("Invalid message ID")
        row = self._connection.execute(
            "SELECT body FROM messages WHERE chat_id=? AND id=?", (chat_id, message_id)
        ).fetchone()
        if row is None:
            raise ValueError("Unknown message")
        return dict(json.loads(row[0]))

    def edit_message(
        self,
        *,
        chat_id: int,
        message_id: int,
        bot_id: int,
        text: str,
        reply_markup: dict[str, Any] | None = None,
        entities: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        if not isinstance(text, str) or not 1 <= len(text) <= 4096:
            raise ValueError("Text must contain 1 to 4096 characters")
        text.encode("utf-8", errors="strict")
        formatting = formatting_entities(text, entities)
        keyboard = _inline_keyboard(reply_markup)
        with self._connection:
            self._connection.execute("BEGIN IMMEDIATE")
            chat = self.get_chat(chat_id)
            if bot_id != chat["bot_id"]:
                raise ValueError("Private chat is not available to this bot")
            message = self.get_message(chat_id, message_id)
            if message["sender_id"] != bot_id:
                raise ValueError("Only the sending bot can edit this message")
            if (
                message["text"] == text
                and message.get("reply_markup") == keyboard
                and message.get("entities") == formatting
            ):
                raise ValueError("MESSAGE_NOT_MODIFIED")
            message["text"] = text
            message["edit_date"] = self._connection.execute(
                "SELECT now FROM configuration"
            ).fetchone()[0]
            message.pop("reply_markup", None)
            message.pop("entities", None)
            if formatting is not None:
                message["entities"] = formatting
            if keyboard is not None:
                message["reply_markup"] = keyboard
            self._connection.execute(
                "UPDATE messages SET body=? WHERE chat_id=? AND id=?",
                (json.dumps(message), chat_id, message_id),
            )
            self._emit("message.edited", message)
        return message

    def create_callback(
        self,
        *,
        user_id: int,
        chat_id: int,
        message_id: int,
        data: str,
        request_id: str,
    ) -> dict[str, Any]:
        if (
            not isinstance(request_id, str)
            or re.fullmatch(r"[A-Za-z0-9_-]{1,128}", request_id) is None
        ):
            raise ValueError("Callback request_id must be 1 to 128 ASCII identifier characters")
        if not isinstance(data, str) or not 1 <= len(data.encode("utf-8")) <= 64:
            raise ValueError("Callback data must contain 1 to 64 UTF-8 bytes")
        with self._connection:
            self._connection.execute("BEGIN IMMEDIATE")
            self.get_user(user_id)
            chat = self.get_chat(chat_id)
            if chat["user_id"] != user_id:
                raise ValueError("Callback chat is not available to this persona")
            message = self.get_message(chat_id, message_id)
            if message["sender_id"] != chat["bot_id"]:
                raise ValueError("Callbacks require a message sent by the chat bot")
            command = json.dumps(
                {"chat_id": chat_id, "message_id": message_id, "data": data}, sort_keys=True
            )
            previous = self._connection.execute(
                "SELECT id, request_body FROM callbacks WHERE user_id=? AND request_id=?",
                (user_id, request_id),
            ).fetchone()
            if previous is not None:
                if previous[1] != command:
                    raise ValueError("Request ID already identifies another callback")
                return self.get_callback(user_id=user_id, callback_id=previous[0])
            world_id = self._connection.execute("SELECT world_id FROM configuration").fetchone()[0]
            callback = {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "chat_id": chat_id,
                "message": message,
                "data": data,
                "chat_instance": hashlib.sha256(f"{world_id}:{chat_id}".encode()).hexdigest(),
            }
            self._connection.execute(
                "INSERT INTO callbacks VALUES (?, ?, ?, ?, ?, ?, NULL)",
                (
                    callback["id"],
                    user_id,
                    chat["bot_id"],
                    request_id,
                    command,
                    json.dumps(callback),
                ),
            )
            self._enqueue_update(chat["bot_id"], "callback_query", callback)
            self._emit("callback.created", callback)
            return callback | {"answer": None}

    def get_callback(self, *, user_id: int, callback_id: str) -> dict[str, Any]:
        self.get_user(user_id)
        if not isinstance(callback_id, str) or not 1 <= len(callback_id) <= 128:
            raise ValueError("Invalid callback query ID")
        row = self._connection.execute(
            "SELECT body, answer FROM callbacks WHERE id=? AND user_id=?", (callback_id, user_id)
        ).fetchone()
        if row is None:
            raise ValueError("Callback query is not available to this persona")
        return dict(json.loads(row[0])) | {
            "answer": json.loads(row[1]) if row[1] is not None else None
        }

    def answer_callback(
        self,
        *,
        bot_id: int,
        callback_id: str,
        text: str = "",
        show_alert: bool = False,
        cache_time: int = 0,
    ) -> None:
        if not isinstance(text, str) or len(text) > 200:
            raise ValueError("Callback answer text must contain 0 to 200 characters")
        text.encode("utf-8", errors="strict")
        if type(show_alert) is not bool:
            raise ValueError("show_alert must be a Boolean")
        if type(cache_time) is not int or cache_time != 0:
            raise ValueError("GRAMLAB_UNSUPPORTED: callback answer caching")
        if not isinstance(callback_id, str) or not 1 <= len(callback_id) <= 128:
            raise ValueError("Invalid callback query ID")
        with self._connection:
            self._connection.execute("BEGIN IMMEDIATE")
            self.get_user(bot_id)
            row = self._connection.execute(
                "SELECT user_id, answer FROM callbacks WHERE id=? AND bot_id=?",
                (callback_id, bot_id),
            ).fetchone()
            if row is None:
                raise ValueError("Callback query is not available to this bot")
            if row[1] is not None:
                raise ValueError("GRAMLAB_UNSUPPORTED: callback query already answered")
            answer = {"text": text, "show_alert": show_alert, "cache_time": 0}
            self._connection.execute(
                "UPDATE callbacks SET answer=? WHERE id=?", (json.dumps(answer), callback_id)
            )
            self._emit(
                "callback.answered", {"id": callback_id, "user_id": row[0], "answer": answer}
            )

    def _enqueue_update(self, bot_id: int, kind: str, body: dict[str, Any]) -> None:
        # Called inside the same writer transaction as the authoritative event. A filter
        # change and a writer therefore agree on whether this new event gets an update ID.
        selection = json.loads(
            self._connection.execute(
                "SELECT allowed_updates FROM bots WHERE id=?", (bot_id,)
            ).fetchone()[0]
        )
        if (selection and kind not in selection) or (not selection and kind in _DEFAULT_EXCLUDED):
            return
        update_id = self._connection.execute(
            "UPDATE bots SET next_update=next_update+1 WHERE id=? RETURNING next_update-1",
            (bot_id,),
        ).fetchone()[0]
        self._connection.execute(
            "INSERT INTO updates VALUES (?, ?, ?)",
            (bot_id, update_id, json.dumps({"update_id": update_id, kind: body})),
        )

    def poll_updates(
        self,
        bot_id: int,
        *,
        offset: int = 0,
        limit: int = 100,
        allowed_updates: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        if type(offset) is not int or not -(2**63) <= offset < 2**63:
            raise ValueError("Update offset must be a signed 64-bit integer")
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("Update limit must be between 1 and 100")
        if not self.get_user(bot_id)["is_bot"]:
            raise ValueError("Only bots have update queues")
        selection = update_selection(allowed_updates)
        with self._connection:
            self._connection.execute("BEGIN IMMEDIATE")
            if selection is not None:
                self._connection.execute(
                    "UPDATE bots SET allowed_updates=? WHERE id=?", (json.dumps(selection), bot_id)
                )
            if offset < 0:
                row = self._connection.execute(
                    "SELECT id FROM updates WHERE bot_id=? ORDER BY id DESC LIMIT 1 OFFSET ?",
                    (bot_id, -offset - 1),
                ).fetchone()
                offset = row[0] if row else 0
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

    def client_snapshot(self, user_id: int, *, version: int = 1) -> dict[str, Any]:
        if type(version) is not int or version not in (1, 2):
            raise ValueError("Unsupported client snapshot version")
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
            result = {
                "schema": version,
                "world_id": world_id,
                "user_id": user_id,
                "cursor": cursor,
                "now": now,
                "users": [self.get_user(identifier) for identifier in sorted(visible_users)],
                "chats": chats,
                "messages": [message for chat in chats for message in self.history(chat["id"])],
            }
            if version == 2:
                result["message_position"] = self._message_position(user_id)
                result["sends"] = [
                    json.loads(row[0])
                    for row in self._connection.execute(
                        "SELECT body FROM client_sends WHERE user_id=? ORDER BY position",
                        (user_id,),
                    )
                ]
            return result

    def client_changes(self, user_id: int, *, after: int, limit: int = 100) -> dict[str, Any]:
        if type(after) is not int or not 0 <= after < 2**63:
            raise ValueError("Invalid client message position")
        if type(limit) is not int or not 1 <= limit <= 1000:
            raise ValueError("Client change limit must be between 1 and 1000")
        with self._connection:
            self._connection.execute("BEGIN")
            if self.get_user(user_id)["is_bot"]:
                raise ValueError("Client personas must be virtual users")
            head = self._message_position(user_id)
            if after > head:
                raise ValueError(
                    "Client message position is ahead of this world; resnapshot required"
                )
            world_id, now = self._connection.execute(
                "SELECT world_id, now FROM configuration"
            ).fetchone()
            rows = self._connection.execute(
                "SELECT c.position, e.type, e.body, s.request_id FROM client_changes c "
                "JOIN events e ON e.sequence=c.event_sequence "
                "LEFT JOIN client_sends s ON s.user_id=c.user_id AND s.position=c.position "
                "WHERE c.user_id=? AND c.position>? ORDER BY c.position LIMIT ?",
                (user_id, after, limit),
            ).fetchall()
            changes = []
            for position, kind, body, request_id in rows:
                change = {"position": position, "type": kind, "data": json.loads(body)}
                if request_id is not None:
                    change["request_id"] = request_id
                changes.append(change)
            return {
                "schema": 2,
                "world_id": world_id,
                "user_id": user_id,
                "cursor": rows[-1][0] if rows else after,
                "head": head,
                "now": now,
                "changes": changes,
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
                if kind in ("message.created", "message.edited"):
                    visible = data["chat_id"] in chats
                elif kind == "chat.created":
                    visible = data["user_id"] == user_id
                elif kind == "user.created":
                    visible = data["id"] in visible_users
                elif kind == "clock.advanced":
                    visible = True
                elif kind in ("callback.created", "callback.answered"):
                    visible = data["user_id"] == user_id
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
