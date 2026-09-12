"""Version policy and complete semantic envelopes for the client bridge."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Protocol

from gramlab._media_group_topology import MediaGroupTopology
from gramlab._message_publication import (
    message_assets,
    message_custom_emoji,
    message_documents,
)


class ClientWorld(Protocol):
    @property
    def world_id(self) -> str: ...

    def get_user(self, user_id: int) -> dict[str, Any]: ...

    def get_chat(self, chat_id: int) -> dict[str, Any]: ...

    def history(self, chat_id: int) -> list[dict[str, Any]]: ...

    def client_visible_users(self, user_id: int) -> list[dict[str, Any]]: ...

    def asset_descriptor(self, asset_id: int) -> dict[str, Any]: ...

    def document_descriptor(self, document_id: Any) -> dict[str, Any]: ...

    def custom_emoji_descriptor(self, custom_emoji_id: int | str) -> dict[str, Any]: ...


@dataclass(frozen=True, slots=True)
class BridgeVersion:
    number: int
    media: bool
    rich_mentions: bool
    custom_emoji: bool
    documents: bool
    media_groups: bool

    @classmethod
    def for_operation(cls, value: Any, operation: str) -> BridgeVersion:
        admitted = {
            "snapshot": (1, 2, 3, 4, 5, 6),
            "changes": (2, 3, 4, 5, 6),
            "callback": (1, 3, 4, 5, 6),
            "message": (2, 4, 5, 6),
        }
        errors = {
            "snapshot": "Unsupported client snapshot version",
            "changes": "Unsupported client changes version",
            "callback": "Unsupported client callback version",
            "message": "Unsupported client message version",
        }
        if operation not in admitted:
            raise RuntimeError("Unknown client bridge operation policy")
        if type(value) is not int or value not in admitted[operation]:
            raise ValueError(errors[operation])
        return cls(
            number=value,
            media=value >= 3,
            rich_mentions=value >= 3,
            custom_emoji=value >= 4,
            documents=value >= 5,
            media_groups=value >= 6,
        )


def require_runtime_bridge_version(value: Any, *, owner: str) -> int:
    if type(value) is not int or value not in (3, 4, 5, 6):
        raise ValueError(f"{owner} bridge version must be 3, 4, 5 or 6")
    return value


def bridge_version_from_path(path: str) -> int:
    for version in (6, 5, 4, 3, 2, 1):
        if path.startswith(f"/v{version}/"):
            return version
    return 1


def error_envelope(path: str, code: str, message: str) -> dict[str, Any]:
    return {
        "schema": bridge_version_from_path(path),
        "error": {"code": code, "message": message},
    }


def message_users(message: dict[str, Any]) -> set[int]:
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


class ClientBridgeSchema:
    """Interpret bridge versions and construct semantic JSON independently of HTTP."""

    def __init__(
        self,
        connection: sqlite3.Connection,
        world: ClientWorld,
        media_groups: MediaGroupTopology,
    ) -> None:
        self._connection = connection
        self._world = world
        self._media_groups = media_groups

    def require_message(
        self,
        message: dict[str, Any],
        *,
        version: int,
        operation: str,
        revision: int | None = None,
    ) -> None:
        policy = BridgeVersion.for_operation(version, operation)
        self._require_messages(((message, revision),), policy)

    def snapshot(self, user_id: int, *, version: int) -> dict[str, Any]:
        policy = BridgeVersion.for_operation(version, "snapshot")
        with self._connection:
            self._connection.execute("BEGIN")
            user = self._world.get_user(user_id)
            if user["is_bot"]:
                raise ValueError("Client personas must be virtual users")
            world_id, now = self._connection.execute(
                "SELECT world_id, now FROM configuration"
            ).fetchone()
            cursor = self._connection.execute(
                "SELECT COALESCE(MAX(sequence), 0) FROM events"
            ).fetchone()[0]
            chats = [
                self._world.get_chat(row[0])
                for row in self._connection.execute(
                    "SELECT id FROM chats WHERE user_id=? ORDER BY id", (user_id,)
                )
            ]
            try:
                messages = [
                    message for chat in chats for message in self._world.history(chat["id"])
                ]
            except (TypeError, ValueError):
                if policy.media_groups:
                    raise ValueError("Invalid stored media group") from None
                raise
            self._require_messages(((message, None) for message in messages), policy)
            result = self._base(policy, user_id, world_id=world_id)
            result.update(
                {
                    "cursor": cursor,
                    "now": now,
                    "users": [
                        self._world.get_user(identifier)
                        for identifier in sorted({user_id, *(chat["bot_id"] for chat in chats)})
                    ],
                    "chats": chats,
                    "messages": messages,
                }
            )
            if policy.number == 2:
                result["message_position"] = self._message_position(user_id)
                result["sends"] = self._sends(user_id)
            if policy.media:
                result["users"] = self._identity_dependencies(user_id, messages)
                result["message_position"] = self._message_position(user_id)
                result["sends"] = self._sends(user_id)
                granted_assets = [
                    self._world.asset_descriptor(row[0])
                    for row in self._connection.execute(
                        "SELECT asset_id FROM asset_grants WHERE user_id=? ORDER BY asset_id",
                        (user_id,),
                    )
                ]
                result["assets"] = [
                    descriptor
                    for descriptor in granted_assets
                    if policy.custom_emoji or descriptor["mime_type"] in ("image/png", "image/jpeg")
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
                    for message in messages
                ]
            if policy.custom_emoji:
                result["custom_emoji"] = [
                    self._world.custom_emoji_descriptor(row[0])
                    for row in self._connection.execute(
                        "SELECT custom_emoji_id FROM custom_emoji_grants "
                        "WHERE user_id=? ORDER BY custom_emoji_id",
                        (user_id,),
                    )
                ]
            if policy.documents:
                result["documents"] = [
                    self._world.document_descriptor(str(row[0]))
                    for row in self._connection.execute(
                        "SELECT document_id FROM document_grants "
                        "WHERE user_id=? ORDER BY document_id",
                        (user_id,),
                    )
                ]
            return result

    def changes(self, user_id: int, *, after: int, limit: int, version: int) -> dict[str, Any]:
        policy = BridgeVersion.for_operation(version, "changes")
        if type(after) is not int or not 0 <= after < 2**63:
            raise ValueError("Invalid client message position")
        if type(limit) is not int or not 1 <= limit <= 1000:
            raise ValueError("Client change limit must be between 1 and 1000")
        with self._connection:
            self._connection.execute("BEGIN")
            if self._world.get_user(user_id)["is_bot"]:
                raise ValueError("Client personas must be virtual users")
            head = self._message_position(user_id)
            if after > head:
                raise ValueError(
                    "Client message position is ahead of this world; resnapshot required"
                )
            world_id, now = self._connection.execute(
                "SELECT world_id, now FROM configuration"
            ).fetchone()
            rows = self._media_groups.change_page(
                user_id=user_id,
                after=after,
                limit=limit,
                complete_groups=policy.media_groups,
            )
            parsed_rows = []
            for row in rows:
                try:
                    data = json.loads(row.body)
                except (TypeError, ValueError):
                    if policy.media_groups:
                        raise ValueError("Invalid stored media group") from None
                    raise
                if policy.media_groups and not isinstance(data, dict):
                    raise ValueError("Invalid stored media group")
                parsed_rows.append((row, data))
            self._require_messages(
                ((data, row.event_sequence) for row, data in parsed_rows), policy
            )
            changes = []
            asset_ids: set[int] = set()
            document_ids: set[int] = set()
            mentioned_ids: set[int] = set()
            emoji_ids: set[int] = set()
            for row, data in parsed_rows:
                change = {"position": row.position, "type": row.kind, "data": data}
                documents = message_documents(data)
                media = message_assets(data)
                mentions = message_users(data)
                emojis = message_custom_emoji(data)
                emoji_ids.update(emojis)
                asset_ids.update(media)
                document_ids.update(documents)
                mentioned_ids.update(mentions)
                if policy.media:
                    change["revision"] = self._connection.execute(
                        "SELECT event_sequence FROM client_changes WHERE user_id=? AND position=?",
                        (user_id, row.position),
                    ).fetchone()[0]
                if row.request_id is not None:
                    change["request_id"] = row.request_id
                changes.append(change)
            result = self._base(policy, user_id, world_id=world_id)
            result.update(
                {
                    "cursor": rows[-1].position if rows else after,
                    "head": head,
                    "now": now,
                    "changes": changes,
                }
            )
            if policy.media:
                identifiers = {entry["id"] for entry in self._world.client_visible_users(user_id)}
                identifiers.update(mentioned_ids)
                result["users"] = [
                    self._world.get_user(identifier) for identifier in sorted(identifiers)
                ]
                if policy.custom_emoji:
                    for identifier in emoji_ids:
                        descriptor = self._world.custom_emoji_descriptor(identifier)
                        asset_ids.update(
                            (descriptor["main_asset_id"], descriptor["thumbnail_asset_id"])
                        )
                result["assets"] = [
                    self._world.asset_descriptor(asset_id) for asset_id in sorted(asset_ids)
                ]
            if policy.custom_emoji:
                result["custom_emoji"] = [
                    self._world.custom_emoji_descriptor(identifier)
                    for identifier in sorted(emoji_ids)
                ]
            if policy.documents:
                result["documents"] = [
                    self._world.document_descriptor(str(identifier))
                    for identifier in sorted(document_ids)
                ]
            return result

    def send_envelope(self, user_id: int, sent: dict[str, Any], *, version: int) -> dict[str, Any]:
        policy = BridgeVersion.for_operation(version, "message")
        result = self._base(policy, user_id)
        result["send"] = sent
        if policy.custom_emoji:
            message = sent["message"]
            result["users"] = self._identity_dependencies(user_id, [message])
            emoji_ids = message_custom_emoji(message)
            descriptors = [
                self._world.custom_emoji_descriptor(identifier) for identifier in sorted(emoji_ids)
            ]
            result["custom_emoji"] = descriptors
            asset_ids = set(message_assets(message))
            for descriptor in descriptors:
                asset_ids.update((descriptor["main_asset_id"], descriptor["thumbnail_asset_id"]))
            result["assets"] = [
                self._world.asset_descriptor(identifier) for identifier in sorted(asset_ids)
            ]
            result["message_revision"] = self._connection.execute(
                "SELECT revision FROM message_revisions WHERE chat_id=? AND message_id=?",
                (message["chat_id"], message["id"]),
            ).fetchone()[0]
            if policy.documents:
                result["documents"] = [
                    self._world.document_descriptor(str(identifier))
                    for identifier in sorted(message_documents(message))
                ]
        return result

    def callback_envelope(
        self, user_id: int, callback: dict[str, Any], *, version: int
    ) -> dict[str, Any]:
        policy = BridgeVersion.for_operation(version, "callback")
        self._require_messages(((callback["message"], None),), policy)
        result = self._base(policy, user_id)
        result["callback"] = callback
        if policy.media:
            result.update(self._callback_dependencies(user_id, callback, policy))
        return result

    def callback_dependencies(
        self, user_id: int, callback: dict[str, Any], *, version: int
    ) -> dict[str, Any]:
        policy = BridgeVersion.for_operation(version, "callback")
        if not policy.media:
            raise ValueError("Unsupported client callback version")
        return self._callback_dependencies(user_id, callback, policy)

    def custom_emoji_envelope(
        self,
        user_id: int,
        custom_emoji: list[dict[str, Any]],
        assets: list[dict[str, Any]],
        *,
        version: int,
    ) -> dict[str, Any]:
        policy = BridgeVersion.for_operation(version, "callback")
        if not policy.custom_emoji:
            raise ValueError("GRAMLAB_UNSUPPORTED: custom emoji requires client bridge v4")
        result = self._base(policy, user_id)
        result.update({"custom_emoji": custom_emoji, "assets": assets})
        return result

    def _callback_dependencies(
        self, user_id: int, callback: dict[str, Any], policy: BridgeVersion
    ) -> dict[str, Any]:
        message = callback["message"]
        self._require_messages(((message, None),), policy)
        assets = [
            self._world.asset_descriptor(asset_id) for asset_id in sorted(message_assets(message))
        ]
        row = self._connection.execute(
            "SELECT message_revision FROM callback_revisions WHERE callback_id=?",
            (callback["id"],),
        ).fetchone()
        if row is None:
            raise ValueError("Callback message revision is unavailable")
        emoji_ids = message_custom_emoji(message)
        if policy.custom_emoji:
            for identifier in emoji_ids:
                descriptor = self._world.custom_emoji_descriptor(identifier)
                for asset_id in (
                    descriptor["main_asset_id"],
                    descriptor["thumbnail_asset_id"],
                ):
                    if asset_id not in {entry["asset_id"] for entry in assets}:
                        assets.append(self._world.asset_descriptor(asset_id))
            assets.sort(key=lambda item: item["asset_id"])
        result = {
            "users": self._identity_dependencies(user_id, [message]),
            "assets": assets,
            "message_revision": int(row[0]),
        }
        if policy.custom_emoji:
            result["custom_emoji"] = [
                self._world.custom_emoji_descriptor(identifier) for identifier in sorted(emoji_ids)
            ]
        if policy.documents:
            result["documents"] = [
                self._world.document_descriptor(str(identifier))
                for identifier in sorted(message_documents(message))
            ]
        return result

    def _require_messages(
        self,
        messages: Iterable[tuple[dict[str, Any], int | None]],
        policy: BridgeVersion,
    ) -> None:
        entries = tuple(messages)
        values = tuple(message for message, _revision in entries)
        if not policy.media_groups and any("media_group_id" in message for message in values):
            raise ValueError("GRAMLAB_UNSUPPORTED: media groups require client bridge v6")
        if policy.media_groups:
            self._media_groups.require_messages(entries)
        if not policy.documents and any(message_documents(message) for message in values):
            raise ValueError("GRAMLAB_UNSUPPORTED: documents require client bridge v5")
        if not policy.media and any(message_assets(message) for message in values):
            raise ValueError("GRAMLAB_UNSUPPORTED: media requires client bridge v3")
        if not policy.rich_mentions and any(message_users(message) for message in values):
            raise ValueError("GRAMLAB_UNSUPPORTED: rich mentions require client bridge v3")
        if not policy.custom_emoji and any(message_custom_emoji(message) for message in values):
            raise ValueError("GRAMLAB_UNSUPPORTED: custom emoji requires client bridge v4")

    def _identity_dependencies(
        self, user_id: int, messages: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        identifiers = {entry["id"] for entry in self._world.client_visible_users(user_id)}
        for message in messages:
            identifiers.update(message_users(message))
        return [self._world.get_user(identifier) for identifier in sorted(identifiers)]

    def _base(
        self, policy: BridgeVersion, user_id: int, *, world_id: str | None = None
    ) -> dict[str, Any]:
        return {
            "schema": policy.number,
            "world_id": self._world.world_id if world_id is None else world_id,
            "user_id": user_id,
        }

    def _message_position(self, user_id: int) -> int:
        return int(
            self._connection.execute(
                "SELECT COALESCE(MAX(position), 0) FROM client_changes WHERE user_id=?",
                (user_id,),
            ).fetchone()[0]
        )

    def _sends(self, user_id: int) -> list[dict[str, Any]]:
        return [
            json.loads(row[0])
            for row in self._connection.execute(
                "SELECT body FROM client_sends WHERE user_id=? ORDER BY position", (user_id,)
            )
        ]
