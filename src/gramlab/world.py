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
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
from types import TracebackType
from typing import Any, Self

from gramlab.documents import DocumentUpload, _storage_fields, canonical_document_id
from gramlab.entities import canonical_custom_emoji_id, formatting_entities
from gramlab.media import ImageAsset, validate_image
from gramlab.rich_messages import rich_message as validate_rich_message

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


_MEDIA_BLOBS_TABLE = "CREATE TABLE media_blobs (sha256 TEXT PRIMARY KEY, body BLOB NOT NULL)"
_ASSETS_TABLE = (
    "CREATE TABLE assets (id INTEGER PRIMARY KEY, "
    "sha256 TEXT NOT NULL UNIQUE REFERENCES media_blobs(sha256), mime_type TEXT NOT NULL, "
    "extension TEXT NOT NULL, width INTEGER NOT NULL, height INTEGER NOT NULL)"
)
_DOCUMENTS_TABLE = (
    "CREATE TABLE documents (id INTEGER PRIMARY KEY, "
    "sha256 TEXT NOT NULL REFERENCES media_blobs(sha256), file_name TEXT NOT NULL, "
    "mime_type TEXT NOT NULL, file_unique_id TEXT NOT NULL UNIQUE, "
    "UNIQUE(sha256, file_name, mime_type))"
)
_BOT_DOCUMENT_FILES_TABLE = (
    "CREATE TABLE bot_document_files (bot_id INTEGER NOT NULL REFERENCES bots(id), "
    "file_id TEXT NOT NULL UNIQUE, document_id INTEGER NOT NULL REFERENCES documents(id), "
    "PRIMARY KEY(bot_id, document_id))"
)
_DOCUMENT_GRANTS_TABLE = (
    "CREATE TABLE document_grants (user_id INTEGER NOT NULL REFERENCES users(id), "
    "document_id INTEGER NOT NULL REFERENCES documents(id), PRIMARY KEY(user_id, document_id))"
)


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
            connection.execute("PRAGMA journal_mode=WAL")
            with connection:
                connection.executescript(
                    f"""
                BEGIN IMMEDIATE;
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
                {_MEDIA_BLOBS_TABLE};
                {_ASSETS_TABLE};
                CREATE TABLE bot_files (
                    bot_id INTEGER NOT NULL REFERENCES bots(id), file_id TEXT NOT NULL UNIQUE,
                    asset_id INTEGER NOT NULL REFERENCES assets(id), PRIMARY KEY(bot_id, asset_id)
                );
                CREATE TABLE asset_grants (
                    user_id INTEGER NOT NULL REFERENCES users(id), asset_id INTEGER NOT NULL
                    REFERENCES assets(id), PRIMARY KEY(user_id, asset_id)
                );
                CREATE TABLE message_revisions (
                    chat_id INTEGER NOT NULL, message_id INTEGER NOT NULL,
                    revision INTEGER NOT NULL,
                    PRIMARY KEY(chat_id, message_id), FOREIGN KEY(chat_id, message_id)
                    REFERENCES messages(chat_id, id)
                );
                CREATE TABLE callback_revisions (
                    callback_id TEXT PRIMARY KEY REFERENCES callbacks(id),
                    message_revision INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS custom_emoji (
                    id INTEGER PRIMARY KEY, fallback TEXT NOT NULL, free INTEGER NOT NULL,
                    needs_repainting INTEGER NOT NULL, main_asset_id INTEGER NOT NULL
                    REFERENCES assets(id),
                    thumbnail_asset_id INTEGER NOT NULL REFERENCES assets(id),
                    duration_ms INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS custom_emoji_registrations (
                    request_id TEXT PRIMARY KEY, request_body TEXT NOT NULL,
                    custom_emoji_id INTEGER NOT NULL REFERENCES custom_emoji(id)
                );
                CREATE TABLE IF NOT EXISTS custom_emoji_counter (
                    singleton INTEGER PRIMARY KEY CHECK(singleton=1), next_id INTEGER NOT NULL
                );
                INSERT INTO custom_emoji_counter VALUES (1, 1);
                CREATE TABLE IF NOT EXISTS custom_emoji_grants (
                    user_id INTEGER NOT NULL REFERENCES users(id), custom_emoji_id INTEGER NOT NULL
                    REFERENCES custom_emoji(id), PRIMARY KEY(user_id, custom_emoji_id)
                );
                {_DOCUMENTS_TABLE};
                {_BOT_DOCUMENT_FILES_TABLE};
                {_DOCUMENT_GRANTS_TABLE};
                PRAGMA user_version=9;
            """  # noqa: S608
                )
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
            if connection.execute("PRAGMA user_version").fetchone()[0] == 5:
                with connection:
                    connection.execute("BEGIN IMMEDIATE")
                    if connection.execute("PRAGMA user_version").fetchone()[0] == 5:
                        statements = (
                            "CREATE TABLE assets (id INTEGER PRIMARY KEY, sha256 TEXT NOT NULL "
                            "UNIQUE, mime_type TEXT NOT NULL, extension TEXT NOT NULL, "
                            "width INTEGER NOT NULL, height INTEGER NOT NULL, body BLOB NOT NULL)",
                            "CREATE TABLE bot_files (bot_id INTEGER NOT NULL REFERENCES bots(id), "
                            "file_id TEXT NOT NULL UNIQUE, asset_id INTEGER NOT NULL "
                            "REFERENCES assets(id), PRIMARY KEY(bot_id, asset_id))",
                            "CREATE TABLE asset_grants (user_id INTEGER NOT NULL "
                            "REFERENCES users(id), "
                            "asset_id INTEGER NOT NULL REFERENCES assets(id), "
                            "PRIMARY KEY(user_id, asset_id))",
                            "CREATE TABLE message_revisions (chat_id INTEGER NOT NULL, "
                            "message_id INTEGER NOT NULL, revision INTEGER NOT NULL, "
                            "PRIMARY KEY(chat_id, message_id), FOREIGN KEY(chat_id, message_id) "
                            "REFERENCES messages(chat_id, id))",
                            "INSERT INTO message_revisions SELECT json_extract(body, '$.chat_id'), "
                            "json_extract(body, '$.id'), MAX(sequence) FROM events WHERE type IN "
                            "('message.created', 'message.edited') GROUP BY "
                            "json_extract(body, '$.chat_id'), json_extract(body, '$.id')",
                            "CREATE TABLE callback_revisions (callback_id TEXT PRIMARY KEY "
                            "REFERENCES callbacks(id), message_revision INTEGER NOT NULL)",
                            "INSERT INTO callback_revisions SELECT c.id, (SELECT MAX(e.sequence) "
                            "FROM events e WHERE e.type IN ('message.created','message.edited') "
                            "AND json_extract(e.body,'$.chat_id')="
                            "json_extract(c.body,'$.message.chat_id') AND "
                            "json_extract(e.body,'$.id')=json_extract(c.body,'$.message.id') AND "
                            "e.sequence < (SELECT MIN(ce.sequence) FROM events ce WHERE "
                            "ce.type='callback.created' AND json_extract(ce.body,'$.id')=c.id)) "
                            "FROM callbacks c",
                        )
                        for statement in statements:
                            connection.execute(statement)
                        connection.execute("PRAGMA user_version=6")
            if connection.execute("PRAGMA user_version").fetchone()[0] == 6:
                with connection:
                    connection.execute("BEGIN IMMEDIATE")
                    if connection.execute("PRAGMA user_version").fetchone()[0] == 6:
                        connection.execute(
                            "CREATE TABLE IF NOT EXISTS custom_emoji (id INTEGER PRIMARY KEY, fallback TEXT NOT NULL, free INTEGER NOT NULL, needs_repainting INTEGER NOT NULL, main_asset_id INTEGER NOT NULL REFERENCES assets(id), thumbnail_asset_id INTEGER NOT NULL REFERENCES assets(id), duration_ms INTEGER NOT NULL)"  # noqa: E501
                        )
                        connection.execute(
                            "CREATE TABLE IF NOT EXISTS custom_emoji_registrations (request_id TEXT PRIMARY KEY, request_body TEXT NOT NULL, custom_emoji_id INTEGER NOT NULL REFERENCES custom_emoji(id))"  # noqa: E501
                        )
                        connection.execute(
                            "CREATE TABLE IF NOT EXISTS custom_emoji_counter (singleton INTEGER PRIMARY KEY CHECK(singleton=1), next_id INTEGER NOT NULL)"  # noqa: E501
                        )
                        connection.execute("INSERT INTO custom_emoji_counter VALUES (1, 1)")
                        connection.execute(
                            "CREATE TABLE IF NOT EXISTS custom_emoji_grants (user_id INTEGER NOT NULL REFERENCES users(id), custom_emoji_id INTEGER NOT NULL REFERENCES custom_emoji(id), PRIMARY KEY(user_id, custom_emoji_id))"  # noqa: E501
                        )
                        connection.execute("PRAGMA user_version=7")
            if connection.execute("PRAGMA user_version").fetchone()[0] == 7:
                # Table replacement must not delete grants or rewrite their FK targets.
                # This fresh connection has no caller transaction; restore enforcement in cls.
                connection.execute("PRAGMA foreign_keys=OFF")
                with connection:
                    connection.execute("BEGIN IMMEDIATE")
                    if connection.execute("PRAGMA user_version").fetchone()[0] == 7:
                        connection.execute(_MEDIA_BLOBS_TABLE)
                        connection.execute(
                            "INSERT INTO media_blobs SELECT sha256, body FROM assets"
                        )
                        connection.execute(_ASSETS_TABLE.replace("assets (", "assets_next ("))
                        connection.execute(
                            "INSERT INTO assets_next SELECT id, sha256, mime_type, extension, "
                            "width, height FROM assets"
                        )
                        connection.execute("DROP TABLE assets")
                        connection.execute("ALTER TABLE assets_next RENAME TO assets")
                        if connection.execute("PRAGMA foreign_key_check").fetchall():
                            raise ValueError("World media migration violates foreign keys")
                        connection.execute("PRAGMA user_version=8")
            if connection.execute("PRAGMA user_version").fetchone()[0] == 8:
                with connection:
                    connection.execute("BEGIN IMMEDIATE")
                    if connection.execute("PRAGMA user_version").fetchone()[0] == 8:
                        connection.execute(_DOCUMENTS_TABLE)
                        connection.execute(_BOT_DOCUMENT_FILES_TABLE)
                        connection.execute(_DOCUMENT_GRANTS_TABLE)
                        if connection.execute("PRAGMA foreign_key_check").fetchall():
                            raise ValueError("World document migration violates foreign keys")
                        connection.execute("PRAGMA user_version=9")
            if connection.execute("PRAGMA user_version").fetchone()[0] != 9:
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

    def client_visible_users(self, user_id: int) -> list[dict[str, Any]]:
        identifiers = {user_id}
        identifiers.update(
            row[0]
            for row in self._connection.execute(
                "SELECT bot_id FROM chats WHERE user_id=?", (user_id,)
            )
        )
        return [self.get_user(identifier) for identifier in sorted(identifiers)]

    def _resolve_mention(self, bot_id: int, value: Any) -> dict[str, Any]:
        if not isinstance(value, dict) or "id" not in value:
            raise ValueError("Rich text mention user must contain an ID")
        user_id = value["id"]
        if type(user_id) is not int or not 1 <= user_id < 2**63:
            raise ValueError("Rich text mention user ID must be a positive signed 64-bit integer")
        self.get_user(user_id)
        if user_id != bot_id:
            known = self._connection.execute(
                "SELECT 1 FROM chats WHERE user_id=? AND bot_id=?", (user_id, bot_id)
            ).fetchone()
            if known is None:
                raise ValueError("Rich text mention user is unavailable to this bot")
        return {"user_id": user_id}

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

    def _emit(self, kind: str, data: dict[str, Any]) -> int:
        event = self._connection.execute(
            "INSERT INTO events(type, body) VALUES (?, ?)", (kind, json.dumps(data))
        )
        if kind in ("message.created", "message.edited"):
            user_id = self.get_chat(data["chat_id"])["user_id"]
            self._connection.execute(
                "INSERT INTO client_changes VALUES (?, ?, ?)",
                (user_id, self._message_position(user_id) + 1, event.lastrowid),
            )
        if event.lastrowid is None:
            raise RuntimeError("SQLite did not allocate an event sequence")
        return event.lastrowid

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

    def register_custom_emoji(
        self,
        *,
        request_id: str,
        main: bytes,
        thumbnail: bytes,
        fallback: str,
        custom_emoji_id: int | str | None = None,
        free: bool = True,
        needs_repainting: bool = False,
    ) -> dict[str, Any]:
        if (
            not isinstance(request_id, str)
            or re.fullmatch(r"[A-Za-z0-9_-]{1,128}", request_id) is None
        ):
            raise ValueError("Custom emoji request_id must be 1 to 128 ASCII identifier characters")
        if (
            not isinstance(fallback, str)
            or not fallback
            or sum(2 if ord(c) > 0xFFFF else 1 for c in fallback) > 64
        ):
            raise ValueError("Custom emoji fallback must contain 1 to 64 UTF-16 units")
        fallback.encode("utf-8", errors="strict")
        if type(free) is not bool or type(needs_repainting) is not bool:
            raise ValueError("Custom emoji flags must be booleans")
        chosen = None if custom_emoji_id is None else canonical_custom_emoji_id(custom_emoji_id)
        from gramlab._emoji_media import validate_custom_emoji

        media = validate_custom_emoji(main, thumbnail)
        request = json.dumps(
            {
                "main": media.main.sha256,
                "thumbnail": media.thumbnail.sha256,
                "fallback": fallback,
                "custom_emoji_id": chosen,
                "free": free,
                "needs_repainting": needs_repainting,
                "duration_ms": media.duration_ms,
            },
            sort_keys=True,
        )
        with self._connection:
            self._connection.execute("BEGIN IMMEDIATE")
            previous = self._connection.execute(
                "SELECT request_body, custom_emoji_id FROM custom_emoji_registrations WHERE request_id=?",  # noqa: E501
                (request_id,),
            ).fetchone()
            if previous is not None:
                if previous[0] != request:
                    raise ValueError(
                        "Request ID already identifies another custom emoji registration"
                    )
                return self.custom_emoji_descriptor(previous[1])
            main_id = self._store_asset(media.main)
            thumbnail_id = self._store_asset(media.thumbnail)
            if chosen is None:
                candidate = self._connection.execute(
                    "SELECT next_id FROM custom_emoji_counter WHERE singleton=1"
                ).fetchone()[0]
                while self._connection.execute(
                    "SELECT 1 FROM custom_emoji WHERE id=?", (candidate,)
                ).fetchone():
                    candidate += 1
                    if candidate >= 2**63:
                        raise ValueError("Custom emoji identifier space is exhausted")
                identifier = candidate
                self._connection.execute(
                    "UPDATE custom_emoji_counter SET next_id=? WHERE singleton=1", (candidate + 1,)
                )
            else:
                identifier = int(chosen)
            existing = self._connection.execute(
                "SELECT fallback, free, needs_repainting, main_asset_id, thumbnail_asset_id, duration_ms FROM custom_emoji WHERE id=?",  # noqa: E501
                (identifier,),
            ).fetchone()
            values = (
                fallback,
                int(free),
                int(needs_repainting),
                main_id,
                thumbnail_id,
                media.duration_ms,
            )
            if existing is not None and tuple(existing) != values:
                raise ValueError("Custom emoji ID already identifies another registration")
            if existing is None:
                self._connection.execute(
                    "INSERT INTO custom_emoji VALUES (?, ?, ?, ?, ?, ?, ?)", (identifier, *values)
                )
            self._connection.execute(
                "INSERT INTO custom_emoji_registrations VALUES (?, ?, ?)",
                (request_id, request, identifier),
            )
            return self.custom_emoji_descriptor(identifier)

    def custom_emoji_descriptor(self, custom_emoji_id: int | str) -> dict[str, Any]:
        identifier = int(canonical_custom_emoji_id(custom_emoji_id))
        row = self._connection.execute(
            "SELECT fallback, free, needs_repainting, main_asset_id, thumbnail_asset_id, duration_ms FROM custom_emoji WHERE id=?",  # noqa: E501
            (identifier,),
        ).fetchone()
        if row is None:
            raise ValueError("Custom emoji is unavailable")
        return {
            "custom_emoji_id": str(identifier),
            "fallback": row[0],
            "free": bool(row[1]),
            "needs_repainting": bool(row[2]),
            "main_asset_id": row[3],
            "thumbnail_asset_id": row[4],
            "duration_ms": row[5],
        }

    def _message_custom_emoji(self, message: dict[str, Any]) -> set[int]:
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

    def _grant_custom_emoji(self, user_id: int, message: dict[str, Any]) -> None:
        for identifier in self._message_custom_emoji(message):
            row = self._connection.execute(
                "SELECT main_asset_id, thumbnail_asset_id FROM custom_emoji WHERE id=?",
                (identifier,),
            ).fetchone()
            if row is None:
                raise ValueError("Custom emoji is unavailable")
            self._connection.execute(
                "INSERT OR IGNORE INTO custom_emoji_grants VALUES (?, ?)", (user_id, identifier)
            )
            for asset_id in row:
                self._connection.execute(
                    "INSERT OR IGNORE INTO asset_grants VALUES (?, ?)", (user_id, asset_id)
                )

    def custom_emoji_stickers(
        self, bot_id: int, custom_emoji_ids: list[Any]
    ) -> list[dict[str, Any]]:
        if not isinstance(custom_emoji_ids, list) or len(custom_emoji_ids) > 200:
            raise ValueError("custom_emoji_ids must contain 0 to 200 identifiers")
        if any(not isinstance(value, str) for value in custom_emoji_ids):
            raise ValueError("custom_emoji_ids must contain decimal strings")
        identifiers = sorted({int(canonical_custom_emoji_id(value)) for value in custom_emoji_ids})
        if not self.get_user(bot_id)["is_bot"]:
            raise ValueError("Only bots can obtain sticker file identities")
        result = []
        with self._connection:
            self._connection.execute("BEGIN IMMEDIATE")
            for identifier in identifiers:
                try:
                    descriptor = self.custom_emoji_descriptor(identifier)
                except ValueError:
                    continue
                main = self.asset_descriptor(descriptor["main_asset_id"])
                self._file_identity(bot_id, descriptor["main_asset_id"])
                self._file_identity(bot_id, descriptor["thumbnail_asset_id"])
                thumb = self.photo_size(bot_id, descriptor["thumbnail_asset_id"])
                sticker = {
                    "file_id": self._file_identity(bot_id, descriptor["main_asset_id"]),
                    "file_unique_id": main["sha256"],
                    "file_size": main["file_size"],
                    "type": "custom_emoji",
                    "width": main["width"],
                    "height": main["height"],
                    "is_animated": False,
                    "is_video": main["mime_type"] == "video/webm",
                    "custom_emoji_id": str(identifier),
                    "emoji": descriptor["fallback"],
                    "thumbnail": thumb,
                }
                if descriptor["needs_repainting"]:
                    sticker["needs_repainting"] = True
                result.append(sticker)
        return result

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

    def send_rich_message(
        self,
        *,
        chat_id: int,
        sender_id: int,
        rich_message: dict[str, Any],
        reply_markup: dict[str, Any] | None = None,
        uploads: Mapping[str, bytes] | None = None,
    ) -> dict[str, Any]:
        keyboard = _inline_keyboard(reply_markup)
        with self._connection:
            self._connection.execute("BEGIN IMMEDIATE")
            if sender_id != self.get_chat(chat_id)["bot_id"]:
                raise ValueError("Only bots can send rich messages")
            used: set[str] = set()

            def resolve(value: Any) -> dict[str, Any]:
                if isinstance(value, dict) and isinstance(value.get("media"), str):
                    media = value["media"]
                    if media.startswith("attach://"):
                        name = media.removeprefix("attach://")
                        if name in used:
                            raise ValueError("Photo attachment is referenced more than once")
                        used.add(name)
                return self._resolve_photo(sender_id, value, uploads)

            content = validate_rich_message(
                rich_message, resolve, lambda value: self._resolve_mention(sender_id, value)
            )
            if set(uploads or {}) != used:
                raise ValueError("Uploaded photo attachment is unused")
            return self._insert_message(
                chat_id=chat_id,
                sender_id=sender_id,
                text="",
                keyboard=keyboard,
                formatting=None,
                rich_message=content,
            )

    def _insert_message(
        self,
        *,
        chat_id: int,
        sender_id: int,
        text: str,
        keyboard: dict[str, Any] | None,
        formatting: list[dict[str, Any]] | None,
        rich_message: dict[str, Any] | None = None,
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
        if rich_message is not None:
            message["rich_message"] = rich_message
        if keyboard is not None:
            message["reply_markup"] = keyboard
        if formatting is not None:
            message["entities"] = formatting
        self._grant_custom_emoji(chat["user_id"], message)
        self._connection.execute(
            "INSERT INTO messages VALUES (?, ?, ?)", (chat_id, message_id, json.dumps(message))
        )
        revision = self._emit("message.created", message)
        self._connection.execute(
            "INSERT INTO message_revisions VALUES (?, ?, ?)", (chat_id, message_id, revision)
        )
        for asset_id in self._message_assets(message):
            self._connection.execute(
                "INSERT OR IGNORE INTO asset_grants VALUES (?, ?)", (chat["user_id"], asset_id)
            )
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
        version: int = 2,
    ) -> dict[str, Any]:
        if type(version) is not int or version not in (2, 4, 5):
            raise ValueError("Unsupported client message version")
        if (
            not isinstance(request_id, str)
            or re.fullmatch(r"[A-Za-z0-9_-]{1,128}", request_id) is None
        ):
            raise ValueError("Client request_id must be 1 to 128 ASCII identifier characters")
        if not isinstance(text, str) or not 1 <= len(text) <= 4096:
            raise ValueError("Text must contain 1 to 4096 characters")
        text.encode("utf-8", errors="strict")
        formatting = formatting_entities(text, entities)
        probe = {"entities": formatting}
        if version < 4 and self._message_custom_emoji(probe):
            raise ValueError("GRAMLAB_UNSUPPORTED: custom emoji requires client bridge v4")
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

    def _rich_button_record(self, *, user_id: int, chat_id: int, message_id: int) -> dict[str, Any]:
        if type(user_id) is not int or not 0 < user_id < 2**63:
            raise ValueError("access_denied")
        chat = self.get_chat(chat_id)
        if chat["user_id"] != user_id:
            raise ValueError("access_denied")
        message = self.get_message(chat_id, message_id)
        if message["sender_id"] != chat["bot_id"]:
            raise ValueError("target_unavailable")
        revision = self._connection.execute(
            "SELECT revision FROM message_revisions WHERE chat_id=? AND message_id=?",
            (chat_id, message_id),
        ).fetchone()
        if revision is None:
            raise RuntimeError("Bot message has no journal revision")
        return {"chat": chat, "message": message, "revision": revision[0]}

    def rich_button_snapshot(
        self, *, user_id: int, chat_id: int, message_id: int
    ) -> dict[str, Any]:
        """Read authorized canonical content and its actual journal revision atomically."""
        with self._connection:
            self._connection.execute("BEGIN")
            result = self._rich_button_record(
                user_id=user_id, chat_id=chat_id, message_id=message_id
            )
            if "rich_message" not in result["message"]:
                raise ValueError("target_unavailable")
            return result

    @contextmanager
    def rich_button_transaction(
        self,
        *,
        user_id: int,
        chat_id: int,
        message_id: int,
        revision: int,
        path: list[str | int],
        button: dict[str, Any],
    ) -> Iterator[dict[str, Any]]:
        """Keep target validation and a trusted client effect in one World transaction."""
        if (
            type(revision) is not int
            or not 0 < revision < 2**63
            or not isinstance(path, list)
            or not path
            or any(type(part) not in (str, int) for part in path)
        ):
            raise ValueError("target_unavailable")
        with self._connection:
            self._connection.execute("BEGIN IMMEDIATE")
            result = self._rich_button_record(
                user_id=user_id, chat_id=chat_id, message_id=message_id
            )
            if result["revision"] != revision:
                raise ValueError("message_revision_changed")
            # The independently implemented canonical traversal is shared with observation.
            from gramlab._rich_buttons import occurrences

            content = result["message"].get("rich_message")
            if content is None or not any(
                item["path"] == path and item["button"] == button for item in occurrences(content)
            ):
                raise ValueError("target_unavailable")
            yield result

    def edit_message(
        self,
        *,
        chat_id: int,
        message_id: int,
        bot_id: int,
        text: str | None = None,
        reply_markup: dict[str, Any] | None = None,
        entities: list[dict[str, Any]] | None = None,
        rich_message: dict[str, Any] | None = None,
        uploads: Mapping[str, bytes] | None = None,
    ) -> dict[str, Any]:
        content = None
        if rich_message is not None:
            if text is not None or entities is not None:
                raise ValueError("GRAMLAB_UNSUPPORTED: combined text and rich content")
            text = ""
            formatting = None
        else:
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
            if "photo" in message:
                raise ValueError("GRAMLAB_UNSUPPORTED: editing ordinary photo messages")
            if "document" in message:
                raise ValueError("GRAMLAB_UNSUPPORTED: editing ordinary document messages")
            if rich_message is not None:
                used: set[str] = set()

                def resolve(value: Any) -> dict[str, Any]:
                    if isinstance(value, dict) and isinstance(value.get("media"), str):
                        media = value["media"]
                        if media.startswith("attach://"):
                            name = media.removeprefix("attach://")
                            if name in used:
                                raise ValueError("Photo attachment is referenced more than once")
                            used.add(name)
                    return self._resolve_photo(bot_id, value, uploads)

                content = validate_rich_message(
                    rich_message, resolve, lambda value: self._resolve_mention(bot_id, value)
                )
                if set(uploads or {}) != used:
                    raise ValueError("Uploaded photo attachment is unused")
            elif uploads:
                raise ValueError("Uploaded photo attachment is unused")
            if message["sender_id"] != bot_id:
                raise ValueError("Only the sending bot can edit this message")
            if (
                message["text"] == text
                and message.get("reply_markup") == keyboard
                and message.get("entities") == formatting
                and message.get("rich_message") == content
            ):
                raise ValueError("MESSAGE_NOT_MODIFIED")
            message["text"] = text
            message["edit_date"] = self._connection.execute(
                "SELECT now FROM configuration"
            ).fetchone()[0]
            message.pop("reply_markup", None)
            message.pop("entities", None)
            message.pop("rich_message", None)
            if content is not None:
                message["rich_message"] = content
            if formatting is not None:
                message["entities"] = formatting
            if keyboard is not None:
                message["reply_markup"] = keyboard
            self._grant_custom_emoji(chat["user_id"], message)
            self._connection.execute(
                "UPDATE messages SET body=? WHERE chat_id=? AND id=?",
                (json.dumps(message), chat_id, message_id),
            )
            revision = self._emit("message.edited", message)
            self._connection.execute(
                "INSERT OR REPLACE INTO message_revisions VALUES (?, ?, ?)",
                (chat_id, message_id, revision),
            )
            for asset_id in self._message_assets(message):
                self._connection.execute(
                    "INSERT OR IGNORE INTO asset_grants VALUES (?, ?)",
                    (chat["user_id"], asset_id),
                )
        return message

    def _message_assets(self, message: dict[str, Any]) -> set[int]:
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

    def _message_documents(self, message: dict[str, Any]) -> set[int]:
        if "document" not in message:
            return set()
        document = message["document"]
        if not isinstance(document, dict) or document.keys() != {"document_id"}:
            raise ValueError("Invalid stored document reference")
        return {canonical_document_id(document["document_id"])}

    def _require_document_version(self, message: dict[str, Any], version: int) -> None:
        if version < 5 and self._message_documents(message):
            raise ValueError("GRAMLAB_UNSUPPORTED: documents require client bridge v5")

    def _message_users(self, message: dict[str, Any]) -> set[int]:
        users: set[int] = set()
        pending: list[Any] = [message.get("rich_message")]
        while pending:
            value = pending.pop()
            if isinstance(value, dict):
                if value.get("type") == "text_mention" and "user_id" in value:
                    users.add(int(value["user_id"]))
                pending.extend(value.values())
            elif isinstance(value, list):
                pending.extend(value)
        return users

    def _identity_dependencies(
        self, user_id: int, messages: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        identifiers = {entry["id"] for entry in self.client_visible_users(user_id)}
        for message in messages:
            identifiers.update(self._message_users(message))
        return [self.get_user(identifier) for identifier in sorted(identifiers)]

    def _store_asset(self, image: ImageAsset) -> int:
        row = self._connection.execute(
            "SELECT id FROM assets WHERE sha256=?", (image.sha256,)
        ).fetchone()
        if row is not None:
            return int(row[0])
        asset_id = int(
            self._connection.execute("SELECT COALESCE(MAX(id), 0)+1 FROM assets").fetchone()[0]
        )
        self._connection.execute(
            "INSERT INTO media_blobs VALUES (?, ?) ON CONFLICT(sha256) DO NOTHING",
            (image.sha256, image.data),
        )
        self._connection.execute(
            "INSERT INTO assets VALUES (?, ?, ?, ?, ?, ?)",
            (
                asset_id,
                image.sha256,
                image.mime_type,
                image.extension,
                image.width,
                image.height,
            ),
        )
        return asset_id

    def _file_identity(self, bot_id: int, asset_id: int) -> str:
        row = self._connection.execute(
            "SELECT file_id FROM bot_files WHERE bot_id=? AND asset_id=?", (bot_id, asset_id)
        ).fetchone()
        if row is None:
            file_id = "gramlab_" + secrets.token_urlsafe(24)
            self._connection.execute(
                "INSERT INTO bot_files VALUES (?, ?, ?)", (bot_id, file_id, asset_id)
            )
            return file_id
        return str(row[0])

    def _resolve_photo(
        self, bot_id: int, value: Any, uploads: Mapping[str, bytes] | None
    ) -> dict[str, Any]:
        if (
            not isinstance(value, dict)
            or value.keys() != {"type", "media"}
            or value["type"] != "photo"
        ):
            raise ValueError("Photo input requires type and media")
        media = value["media"]
        if not isinstance(media, str):
            raise ValueError("Photo media must be a string")
        if media.startswith("attach://"):
            name = media.removeprefix("attach://")
            if not name or uploads is None or name not in uploads:
                raise ValueError("Photo attachment is unavailable")
            asset_id = self._store_asset(validate_image(uploads[name]))
        else:
            row = self._connection.execute(
                "SELECT f.asset_id, a.mime_type FROM bot_files f JOIN assets a ON a.id=f.asset_id "
                "WHERE f.bot_id=? AND f.file_id=?",
                (bot_id, media),
            ).fetchone()
            if row is None or row[1] not in ("image/png", "image/jpeg"):
                raise ValueError("Photo file identifier is unavailable")
            asset_id = int(row[0])
        self._file_identity(bot_id, asset_id)
        return {"asset_id": asset_id}

    def send_photo(
        self,
        *,
        chat_id: int,
        sender_id: int,
        photo: Any,
        uploads: Mapping[str, bytes] | None = None,
        caption: str | None = None,
        caption_entities: list[dict[str, Any]] | None = None,
        reply_markup: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if caption is not None:
            if not isinstance(caption, str) or len(caption) > 1024:
                raise ValueError("Caption must contain 0 to 1024 characters")
            caption.encode("utf-8", errors="strict")
        formatting = formatting_entities(caption or "", caption_entities)
        keyboard = _inline_keyboard(reply_markup)
        with self._connection:
            self._connection.execute("BEGIN IMMEDIATE")
            chat = self.get_chat(chat_id)
            if sender_id != chat["bot_id"]:
                raise ValueError("Only chat bots can send photos")
            media = photo.get("media") if isinstance(photo, dict) else None
            expected = (
                {media.removeprefix("attach://")}
                if isinstance(media, str) and media.startswith("attach://")
                else set()
            )
            if set(uploads or {}) != expected:
                raise ValueError("Photo uploads must exactly match the attachment")
            resolved = self._resolve_photo(sender_id, photo, uploads)
            message = self._insert_message(
                chat_id=chat_id, sender_id=sender_id, text="", keyboard=keyboard, formatting=None
            )
            message["photo"] = resolved
            if caption is not None:
                message["caption"] = caption
            if formatting:
                message["caption_entities"] = formatting
            self._grant_custom_emoji(chat["user_id"], message)
            self._connection.execute(
                "UPDATE messages SET body=? WHERE chat_id=? AND id=?",
                (json.dumps(message), chat_id, message["id"]),
            )
            revision = self._connection.execute(
                "SELECT revision FROM message_revisions WHERE chat_id=? AND message_id=?",
                (chat_id, message["id"]),
            ).fetchone()[0]
            self._connection.execute(
                "UPDATE events SET body=? WHERE sequence=?", (json.dumps(message), revision)
            )
            self._connection.execute(
                "INSERT OR IGNORE INTO asset_grants VALUES (?, ?)",
                (chat["user_id"], resolved["asset_id"]),
            )
            return message

    def _store_document(self, upload: DocumentUpload) -> int:
        sha256, file_name, mime_type, file_unique_id = _storage_fields(upload)
        row = self._connection.execute(
            "SELECT id FROM documents WHERE sha256=? AND file_name=? AND mime_type=?",
            (sha256, file_name, mime_type),
        ).fetchone()
        if row is not None:
            return int(row[0])
        document_id = int(
            self._connection.execute("SELECT COALESCE(MAX(id), 0)+1 FROM documents").fetchone()[0]
        )
        if document_id >= 2**63:
            raise ValueError("Document identifier space is exhausted")
        self._connection.execute(
            "INSERT INTO media_blobs VALUES (?, ?) ON CONFLICT(sha256) DO NOTHING",
            (sha256, upload.data),
        )
        self._connection.execute(
            "INSERT INTO documents VALUES (?, ?, ?, ?, ?)",
            (
                document_id,
                sha256,
                file_name,
                mime_type,
                file_unique_id,
            ),
        )
        return document_id

    def _document_file_identity(self, bot_id: int, document_id: int) -> str:
        row = self._connection.execute(
            "SELECT file_id FROM bot_document_files WHERE bot_id=? AND document_id=?",
            (bot_id, document_id),
        ).fetchone()
        if row is not None:
            return str(row[0])
        file_id = "gramlab_document_" + secrets.token_urlsafe(24)
        self._connection.execute(
            "INSERT INTO bot_document_files VALUES (?, ?, ?)", (bot_id, file_id, document_id)
        )
        return file_id

    def _resolve_document(
        self,
        bot_id: int,
        value: Any,
        uploads: Mapping[str, DocumentUpload] | None,
    ) -> dict[str, str]:
        if not isinstance(value, dict) or value.keys() != {"media"}:
            raise ValueError("Document input requires exactly media")
        media = value["media"]
        if not isinstance(media, str):
            raise ValueError("Document media must be a string")
        if media.startswith("attach://"):
            name = media.removeprefix("attach://")
            if not name or uploads is None or name not in uploads:
                raise ValueError("Document attachment is unavailable")
            upload = uploads[name]
            if type(upload) is not DocumentUpload:
                raise TypeError("Document attachment must be a DocumentUpload")
            document_id = self._store_document(upload)
        else:
            row = self._connection.execute(
                "SELECT document_id FROM bot_document_files WHERE bot_id=? AND file_id=?",
                (bot_id, media),
            ).fetchone()
            if row is None:
                raise ValueError("Document file identifier is unavailable")
            document_id = int(row[0])
        self._document_file_identity(bot_id, document_id)
        return {"document_id": str(document_id)}

    def send_document(
        self,
        *,
        chat_id: int,
        sender_id: int,
        document: Any,
        uploads: Mapping[str, DocumentUpload] | None = None,
        caption: str | None = None,
        caption_entities: list[dict[str, Any]] | None = None,
        reply_markup: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if caption is not None:
            if not isinstance(caption, str) or len(caption) > 1024:
                raise ValueError("Caption must contain 0 to 1024 characters")
            caption.encode("utf-8", errors="strict")
        formatting = formatting_entities(caption or "", caption_entities)
        keyboard = _inline_keyboard(reply_markup)
        if uploads is not None and not isinstance(uploads, Mapping):
            raise TypeError("Document uploads must be a mapping")
        media = document.get("media") if isinstance(document, dict) else None
        expected = (
            {media.removeprefix("attach://")}
            if isinstance(media, str) and media.startswith("attach://")
            else set()
        )
        if set(uploads or {}) != expected:
            raise ValueError("Document uploads must exactly match the attachment")
        with self._connection:
            self._connection.execute("BEGIN IMMEDIATE")
            chat = self.get_chat(chat_id)
            if sender_id != chat["bot_id"]:
                raise ValueError("Only chat bots can send documents")
            resolved = self._resolve_document(sender_id, document, uploads)
            message = self._insert_message(
                chat_id=chat_id, sender_id=sender_id, text="", keyboard=keyboard, formatting=None
            )
            message["document"] = resolved
            if caption is not None:
                message["caption"] = caption
            if formatting:
                message["caption_entities"] = formatting
            self._grant_custom_emoji(chat["user_id"], message)
            self._connection.execute(
                "UPDATE messages SET body=? WHERE chat_id=? AND id=?",
                (json.dumps(message), chat_id, message["id"]),
            )
            revision = self._connection.execute(
                "SELECT revision FROM message_revisions WHERE chat_id=? AND message_id=?",
                (chat_id, message["id"]),
            ).fetchone()[0]
            self._connection.execute(
                "UPDATE events SET body=? WHERE sequence=?", (json.dumps(message), revision)
            )
            self._connection.execute(
                "INSERT OR IGNORE INTO document_grants VALUES (?, ?)",
                (chat["user_id"], canonical_document_id(resolved["document_id"])),
            )
            return message

    def document_descriptor(self, document_id: Any) -> dict[str, Any]:
        identifier = canonical_document_id(document_id)
        row = self._connection.execute(
            "SELECT d.file_name, d.mime_type, length(b.body), d.sha256 "
            "FROM documents d JOIN media_blobs b ON b.sha256=d.sha256 WHERE d.id=?",
            (identifier,),
        ).fetchone()
        if row is None:
            raise ValueError("Document is unavailable")
        return {
            "document_id": str(identifier),
            "file_name": row[0],
            "mime_type": row[1],
            "file_size": row[2],
            "sha256": row[3],
        }

    def document_file(self, bot_id: int, document_id: Any) -> dict[str, Any]:
        identifier = canonical_document_id(document_id)
        descriptor = self.document_descriptor(str(identifier))
        row = self._connection.execute(
            "SELECT file_id, file_unique_id FROM bot_document_files f "
            "JOIN documents d ON d.id=f.document_id WHERE f.bot_id=? AND f.document_id=?",
            (bot_id, identifier),
        ).fetchone()
        if row is None:
            raise ValueError("Document file identifier is unavailable")
        result = {
            "file_id": row[0],
            "file_unique_id": row[1],
            "file_size": descriptor["file_size"],
        }
        if descriptor["file_name"]:
            result["file_name"] = descriptor["file_name"]
        if descriptor["mime_type"]:
            result["mime_type"] = descriptor["mime_type"]
        return result

    def granted_document(self, user_id: int, document_id: Any) -> tuple[dict[str, Any], bytes]:
        identifier = canonical_document_id(document_id)
        row = self._connection.execute(
            "SELECT b.body FROM document_grants g JOIN documents d ON d.id=g.document_id "
            "JOIN media_blobs b ON b.sha256=d.sha256 WHERE g.user_id=? AND g.document_id=?",
            (user_id, identifier),
        ).fetchone()
        if row is None:
            raise ValueError("Document is unavailable")
        return self.document_descriptor(str(identifier)), bytes(row[0])

    def asset_descriptor(self, asset_id: int) -> dict[str, Any]:
        row = self._connection.execute(
            "SELECT a.mime_type, length(b.body), a.sha256, a.width, a.height "
            "FROM assets a JOIN media_blobs b ON b.sha256=a.sha256 WHERE a.id=?",
            (asset_id,),
        ).fetchone()
        if row is None:
            raise ValueError("Asset is unavailable")
        return {
            "asset_id": asset_id,
            "mime_type": row[0],
            "file_size": row[1],
            "sha256": row[2],
            "width": row[3],
            "height": row[4],
        }

    def photo_size(self, bot_id: int, asset_id: int) -> dict[str, Any]:
        descriptor = self.asset_descriptor(asset_id)
        row = self._connection.execute(
            "SELECT file_id FROM bot_files WHERE bot_id=? AND asset_id=?", (bot_id, asset_id)
        ).fetchone()
        if row is None:
            raise ValueError("Photo file identifier is unavailable")
        file_id = str(row[0])
        return {
            "file_id": file_id,
            "file_unique_id": descriptor["sha256"],
            "width": descriptor["width"],
            "height": descriptor["height"],
            "file_size": descriptor["file_size"],
        }

    def bot_file(self, bot_id: int, file_id: str) -> tuple[dict[str, Any], bytes]:
        row = self._connection.execute(
            "SELECT a.id, a.sha256, a.extension, a.mime_type, b.body FROM bot_files f "
            "JOIN assets a ON a.id=f.asset_id JOIN media_blobs b ON b.sha256=a.sha256 "
            "WHERE f.bot_id=? AND f.file_id=?",
            (bot_id, file_id),
        ).fetchone()
        if row is not None:
            info = {
                "file_id": file_id,
                "file_unique_id": row[1],
                "file_size": len(row[4]),
                "file_path": f"{'stickers' if row[3] in ('image/webp', 'video/webm') else 'photos'}/{file_id}.{row[2]}",  # noqa: E501
                "mime_type": row[3],
            }
            return info, bytes(row[4])
        document = self._connection.execute(
            "SELECT d.file_unique_id, d.file_name, d.mime_type, b.body "
            "FROM bot_document_files f JOIN documents d ON d.id=f.document_id "
            "JOIN media_blobs b ON b.sha256=d.sha256 WHERE f.bot_id=? AND f.file_id=?",
            (bot_id, file_id),
        ).fetchone()
        if document is None:
            raise ValueError("File is unavailable")
        info = {
            "file_id": file_id,
            "file_unique_id": document[0],
            "file_size": len(document[3]),
            "file_path": f"documents/{file_id}",
            "mime_type": document[2],
        }
        if document[1]:
            info["file_name"] = document[1]
        return info, bytes(document[3])

    def granted_asset(self, user_id: int, asset_id: int) -> tuple[dict[str, Any], bytes]:
        row = self._connection.execute(
            "SELECT b.body FROM asset_grants g JOIN assets a ON a.id=g.asset_id "
            "JOIN media_blobs b ON b.sha256=a.sha256 WHERE g.user_id=? AND g.asset_id=?",
            (user_id, asset_id),
        ).fetchone()
        if row is None:
            raise ValueError("Asset is unavailable")
        return self.asset_descriptor(asset_id), bytes(row[0])

    def granted_custom_emoji(
        self, user_id: int, custom_emoji_ids: list[Any]
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        if not isinstance(custom_emoji_ids, list) or not 1 <= len(custom_emoji_ids) <= 200:
            raise ValueError("custom_emoji_ids must contain 1 to 200 identifiers")
        if any(not isinstance(value, str) for value in custom_emoji_ids):
            raise ValueError("custom_emoji_ids must contain decimal strings")
        identifiers = sorted({int(canonical_custom_emoji_id(value)) for value in custom_emoji_ids})
        descriptors = []
        assets: set[int] = set()
        for identifier in identifiers:
            if (
                self._connection.execute(
                    "SELECT 1 FROM custom_emoji_grants WHERE user_id=? AND custom_emoji_id=?",
                    (user_id, identifier),
                ).fetchone()
                is None
            ):
                raise LookupError("Document is unavailable")
            descriptor = self.custom_emoji_descriptor(identifier)
            descriptors.append(descriptor)
            assets.update((descriptor["main_asset_id"], descriptor["thumbnail_asset_id"]))
        return descriptors, [self.asset_descriptor(asset_id) for asset_id in sorted(assets)]

    def create_callback(
        self,
        *,
        user_id: int,
        chat_id: int,
        message_id: int,
        data: str,
        request_id: str,
        version: int = 1,
    ) -> dict[str, Any]:
        with self._connection:
            self._connection.execute("BEGIN IMMEDIATE")
            return self._create_callback_locked(
                user_id=user_id,
                chat_id=chat_id,
                message_id=message_id,
                data=data,
                request_id=request_id,
                version=version,
            )

    def _create_callback_locked(
        self,
        *,
        user_id: int,
        chat_id: int,
        message_id: int,
        data: str,
        request_id: str,
        version: int = 1,
    ) -> dict[str, Any]:
        if not self._connection.in_transaction:
            raise RuntimeError("Callback effect requires an active World transaction")
        if type(version) is not int or version not in (1, 3, 4, 5):
            raise ValueError("Unsupported client callback version")
        if (
            not isinstance(request_id, str)
            or re.fullmatch(r"[A-Za-z0-9_-]{1,128}", request_id) is None
        ):
            raise ValueError("Callback request_id must be 1 to 128 ASCII identifier characters")
        if not isinstance(data, str) or not 1 <= len(data.encode("utf-8")) <= 64:
            raise ValueError("Callback data must contain 1 to 64 UTF-8 bytes")
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
            stored = self.get_callback(user_id=user_id, callback_id=previous[0])
            self._require_document_version(stored["message"], version)
            if version < 3 and self._message_assets(stored["message"]):
                raise ValueError("GRAMLAB_UNSUPPORTED: media requires client bridge v3")
            if version < 3 and self._message_users(stored["message"]):
                raise ValueError("GRAMLAB_UNSUPPORTED: rich mentions require client bridge v3")
            if version < 4 and self._message_custom_emoji(stored["message"]):
                raise ValueError("GRAMLAB_UNSUPPORTED: custom emoji requires client bridge v4")
            return stored
        self._require_document_version(message, version)
        if version < 3 and self._message_assets(message):
            raise ValueError("GRAMLAB_UNSUPPORTED: media requires client bridge v3")
        if version < 3 and self._message_users(message):
            raise ValueError("GRAMLAB_UNSUPPORTED: rich mentions require client bridge v3")
        if version < 4 and self._message_custom_emoji(message):
            raise ValueError("GRAMLAB_UNSUPPORTED: custom emoji requires client bridge v4")
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
        revision = self._connection.execute(
            "SELECT revision FROM message_revisions WHERE chat_id=? AND message_id=?",
            (chat_id, message_id),
        ).fetchone()[0]
        self._connection.execute(
            "INSERT INTO callback_revisions VALUES (?, ?)", (callback["id"], revision)
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

    def discard_pending_updates(self, bot_id: int) -> int:
        """Remove queued deliveries for one bot without resetting its update sequence."""
        if not self.get_user(bot_id)["is_bot"]:
            raise ValueError("Only bots have update queues")
        with self._connection:
            self._connection.execute("BEGIN IMMEDIATE")
            cursor = self._connection.execute("DELETE FROM updates WHERE bot_id=?", (bot_id,))
            return cursor.rowcount

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
        if type(version) is not int or version not in (1, 2, 3, 4, 5):
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
            if version < 5 and any(
                self._message_documents(message) for message in result["messages"]
            ):
                raise ValueError("GRAMLAB_UNSUPPORTED: documents require client bridge v5")
            if version < 3 and any(self._message_assets(message) for message in result["messages"]):
                raise ValueError("GRAMLAB_UNSUPPORTED: media requires client bridge v3")
            if version < 3 and any(self._message_users(message) for message in result["messages"]):
                raise ValueError("GRAMLAB_UNSUPPORTED: rich mentions require client bridge v3")
            if version < 4 and any(
                self._message_custom_emoji(message) for message in result["messages"]
            ):
                raise ValueError("GRAMLAB_UNSUPPORTED: custom emoji requires client bridge v4")
            if version == 2:
                result["message_position"] = self._message_position(user_id)
                result["sends"] = [
                    json.loads(row[0])
                    for row in self._connection.execute(
                        "SELECT body FROM client_sends WHERE user_id=? ORDER BY position",
                        (user_id,),
                    )
                ]
            if version >= 3:
                result["users"] = self._identity_dependencies(user_id, result["messages"])
                result["message_position"] = self._message_position(user_id)
                result["sends"] = [
                    json.loads(row[0])
                    for row in self._connection.execute(
                        "SELECT body FROM client_sends WHERE user_id=? ORDER BY position",
                        (user_id,),
                    )
                ]
                granted_assets = [
                    self.asset_descriptor(row[0])
                    for row in self._connection.execute(
                        "SELECT asset_id FROM asset_grants WHERE user_id=? ORDER BY asset_id",
                        (user_id,),
                    )
                ]
                result["assets"] = [
                    descriptor
                    for descriptor in granted_assets
                    if version >= 4 or descriptor["mime_type"] in ("image/png", "image/jpeg")
                ]
                result["message_revisions"] = [
                    {
                        "chat_id": message["chat_id"],
                        "message_id": message["id"],
                        "revision": self._connection.execute(
                            "SELECT revision FROM message_revisions "
                            "WHERE chat_id=? AND message_id=?",
                            (message["chat_id"], message["id"]),
                        ).fetchone()[0],
                    }
                    for message in result["messages"]
                ]
            if version >= 4:
                result["custom_emoji"] = [
                    self.custom_emoji_descriptor(row[0])
                    for row in self._connection.execute(
                        "SELECT custom_emoji_id FROM custom_emoji_grants WHERE user_id=? ORDER BY custom_emoji_id",  # noqa: E501
                        (user_id,),
                    )
                ]
            if version == 5:
                result["documents"] = [
                    self.document_descriptor(str(row[0]))
                    for row in self._connection.execute(
                        "SELECT document_id FROM document_grants "
                        "WHERE user_id=? ORDER BY document_id",
                        (user_id,),
                    )
                ]
            return result

    def client_changes(
        self, user_id: int, *, after: int, limit: int = 100, version: int = 2
    ) -> dict[str, Any]:
        if type(version) is not int or version not in (2, 3, 4, 5):
            raise ValueError("Unsupported client changes version")
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
            asset_ids: set[int] = set()
            document_ids: set[int] = set()
            mentioned_ids: set[int] = set()
            emoji_ids: set[int] = set()
            for position, kind, body, request_id in rows:
                change = {"position": position, "type": kind, "data": json.loads(body)}
                documents = self._message_documents(change["data"])
                if version < 5 and documents:
                    raise ValueError("GRAMLAB_UNSUPPORTED: documents require client bridge v5")
                media = self._message_assets(change["data"])
                if version < 3 and media:
                    raise ValueError("GRAMLAB_UNSUPPORTED: media requires client bridge v3")
                mentions = self._message_users(change["data"])
                if version < 3 and mentions:
                    raise ValueError("GRAMLAB_UNSUPPORTED: rich mentions require client bridge v3")
                emojis = self._message_custom_emoji(change["data"])
                if version < 4 and emojis:
                    raise ValueError("GRAMLAB_UNSUPPORTED: custom emoji requires client bridge v4")
                emoji_ids.update(emojis)
                asset_ids.update(media)
                document_ids.update(documents)
                mentioned_ids.update(mentions)
                if version >= 3:
                    change["revision"] = self._connection.execute(
                        "SELECT event_sequence FROM client_changes WHERE user_id=? AND position=?",
                        (user_id, position),
                    ).fetchone()[0]
                if request_id is not None:
                    change["request_id"] = request_id
                changes.append(change)
            result = {
                "schema": version,
                "world_id": world_id,
                "user_id": user_id,
                "cursor": rows[-1][0] if rows else after,
                "head": head,
                "now": now,
                "changes": changes,
            }
            if version >= 3:
                identifiers = {entry["id"] for entry in self.client_visible_users(user_id)}
                identifiers.update(mentioned_ids)
                result["users"] = [self.get_user(identifier) for identifier in sorted(identifiers)]
                if version >= 4:
                    for identifier in emoji_ids:
                        descriptor = self.custom_emoji_descriptor(identifier)
                        asset_ids.update(
                            (descriptor["main_asset_id"], descriptor["thumbnail_asset_id"])
                        )
                result["assets"] = [
                    self.asset_descriptor(asset_id) for asset_id in sorted(asset_ids)
                ]
            if version >= 4:
                result["custom_emoji"] = [
                    self.custom_emoji_descriptor(identifier) for identifier in sorted(emoji_ids)
                ]
            if version == 5:
                result["documents"] = [
                    self.document_descriptor(str(identifier)) for identifier in sorted(document_ids)
                ]
            return result

    def callback_dependencies(
        self, user_id: int, callback: dict[str, Any], *, version: int = 3
    ) -> dict[str, Any]:
        if self._connection.in_transaction:
            return self._callback_dependencies(user_id, callback, version=version)
        self._connection.execute("BEGIN")
        try:
            return self._callback_dependencies(user_id, callback, version=version)
        finally:
            self._connection.rollback()

    def _callback_dependencies(
        self, user_id: int, callback: dict[str, Any], *, version: int = 3
    ) -> dict[str, Any]:
        if type(version) is not int or version not in (3, 4, 5):
            raise ValueError("Unsupported client callback version")
        message = callback["message"]
        self._require_document_version(message, version)
        assets = [
            self.asset_descriptor(asset_id) for asset_id in sorted(self._message_assets(message))
        ]
        row = self._connection.execute(
            "SELECT message_revision FROM callback_revisions WHERE callback_id=?",
            (callback["id"],),
        ).fetchone()
        if row is None:
            raise ValueError("Callback message revision is unavailable")
        emoji_ids = self._message_custom_emoji(message)
        if version < 4 and emoji_ids:
            raise ValueError("GRAMLAB_UNSUPPORTED: custom emoji requires client bridge v4")
        if version >= 4:
            for identifier in emoji_ids:
                descriptor = self.custom_emoji_descriptor(identifier)
                for asset_id in (descriptor["main_asset_id"], descriptor["thumbnail_asset_id"]):
                    if asset_id not in {entry["asset_id"] for entry in assets}:
                        assets.append(self.asset_descriptor(asset_id))
            assets.sort(key=lambda item: item["asset_id"])
        result = {
            "users": self._identity_dependencies(user_id, [message]),
            "assets": assets,
            "message_revision": int(row[0]),
        }
        if version >= 4:
            result["custom_emoji"] = [
                self.custom_emoji_descriptor(identifier) for identifier in sorted(emoji_ids)
            ]
        if version == 5:
            result["documents"] = [
                self.document_descriptor(str(identifier))
                for identifier in sorted(self._message_documents(message))
            ]
        return result

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
                    if visible and self._message_documents(data):
                        raise ValueError("GRAMLAB_UNSUPPORTED: documents require client bridge v5")
                    if visible and self._message_assets(data):
                        raise ValueError("GRAMLAB_UNSUPPORTED: media requires client bridge v3")
                    if visible and self._message_users(data):
                        raise ValueError(
                            "GRAMLAB_UNSUPPORTED: rich mentions require client bridge v3"
                        )
                    if visible and self._message_custom_emoji(data):
                        raise ValueError(
                            "GRAMLAB_UNSUPPORTED: custom emoji requires client bridge v4"
                        )
                elif kind == "chat.created":
                    visible = data["user_id"] == user_id
                elif kind == "user.created":
                    visible = data["id"] in visible_users
                elif kind == "clock.advanced":
                    visible = True
                elif kind in ("callback.created", "callback.answered"):
                    visible = data["user_id"] == user_id
                    if visible and self._message_documents(data.get("message", {})):
                        raise ValueError("GRAMLAB_UNSUPPORTED: documents require client bridge v5")
                    if visible and self._message_custom_emoji(data.get("message", {})):
                        raise ValueError(
                            "GRAMLAB_UNSUPPORTED: custom emoji requires client bridge v4"
                        )
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
