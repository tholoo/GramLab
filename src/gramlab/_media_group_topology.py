"""Media-group consistency and change-page boundaries for client projection."""

from __future__ import annotations

import json
import re
import sqlite3
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from gramlab.documents import canonical_document_id


@dataclass(frozen=True, slots=True)
class ChangePageRow:
    position: int
    event_sequence: int
    kind: str
    body: str
    request_id: str | None


class MediaGroupTopology:
    """Enforce album membership as one complete, contiguous delivery unit."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def require_message(
        self, message: Any, version: int, *, revision: int | None = None
    ) -> None:
        if isinstance(message, dict) and "media_group_id" in message and version < 6:
            raise ValueError("GRAMLAB_UNSUPPORTED: media groups require client bridge v6")
        if version >= 6:
            self._validate_message(message, revision=revision)

    def require_messages(
        self, messages: Iterable[tuple[Any, int | None]], version: int
    ) -> None:
        validated_groups: set[int] = set()
        for message, revision in messages:
            group_id = self._group_identifier(message)
            if version >= 6 and group_id is not None:
                if group_id in validated_groups:
                    continue
                validated_groups.add(group_id)
            self.require_message(message, version, revision=revision)

    def change_page(
        self, *, user_id: int, after: int, limit: int, version: int
    ) -> tuple[ChangePageRow, ...]:
        if version == 6:
            split = self._connection.execute(
                "SELECT 1 FROM media_groups g JOIN media_group_members m ON m.group_id=g.id "
                "JOIN message_revisions r ON r.chat_id=m.chat_id AND r.message_id=m.message_id "
                "JOIN client_changes c ON c.user_id=? AND c.event_sequence=r.revision "
                "GROUP BY g.id HAVING MIN(c.position)<=? AND ?<MAX(c.position) LIMIT 1",
                (user_id, after, after),
            ).fetchone()
            if split is not None:
                raise ValueError("Client cursor splits a media group")
        rows = self._connection.execute(
            "SELECT c.position, c.event_sequence, e.type, e.body, s.request_id "
            "FROM client_changes c "
            "JOIN events e ON e.sequence=c.event_sequence "
            "LEFT JOIN client_sends s ON s.user_id=c.user_id AND s.position=c.position "
            "WHERE c.user_id=? AND c.position>? ORDER BY c.position LIMIT ?",
            (user_id, after, limit),
        ).fetchall()
        if version == 6 and rows:
            self._complete_trailing_group(user_id, rows)
            self._require_complete_groups(user_id, rows)
        return tuple(
            ChangePageRow(
                position=int(position),
                event_sequence=int(event_sequence),
                kind=str(kind),
                body=str(body),
                request_id=str(request_id) if request_id is not None else None,
            )
            for position, event_sequence, kind, body, request_id in rows
        )

    def _complete_trailing_group(self, user_id: int, rows: list[Any]) -> None:
        trailing_groups = self._connection.execute(
            "SELECT DISTINCT m.group_id FROM media_group_members m "
            "JOIN message_revisions r "
            "ON r.chat_id=m.chat_id AND r.message_id=m.message_id "
            "WHERE r.revision=?",
            (rows[-1][1],),
        ).fetchall()
        if len(trailing_groups) > 1:
            raise ValueError("Invalid stored media group")
        if not trailing_groups:
            return
        rows.extend(
            self._connection.execute(
                "SELECT c.position, c.event_sequence, e.type, e.body, s.request_id "
                "FROM media_group_members m JOIN message_revisions r "
                "ON r.chat_id=m.chat_id AND r.message_id=m.message_id "
                "JOIN client_changes c ON c.event_sequence=r.revision "
                "JOIN events e ON e.sequence=c.event_sequence "
                "LEFT JOIN client_sends s "
                "ON s.user_id=c.user_id AND s.position=c.position "
                "WHERE c.user_id=? AND m.group_id=? AND c.position>? "
                "ORDER BY c.position LIMIT 9",
                (user_id, trailing_groups[0][0], rows[-1][0]),
            ).fetchall()
        )

    def _require_complete_groups(self, user_id: int, rows: list[Any]) -> None:
        topology = self._connection.execute(
            "SELECT m.group_id, c.position, r.revision "
            "FROM media_group_members m JOIN message_revisions r "
            "ON r.chat_id=m.chat_id AND r.message_id=m.message_id "
            "JOIN client_changes c ON c.event_sequence=r.revision "
            "WHERE c.user_id=? ORDER BY m.group_id, m.ordinal",
            (user_id,),
        ).fetchall()
        complete_groups: dict[int, list[int]] = {}
        revision_groups: dict[int, list[int]] = {}
        for group_id, position, event_sequence in topology:
            complete_groups.setdefault(int(group_id), []).append(int(position))
            revision_groups.setdefault(int(event_sequence), []).append(int(group_id))
        grouped_positions: dict[int, list[int]] = {}
        for position, event_sequence, _event_kind, _body, _request_id in rows:
            groups = revision_groups.get(int(event_sequence), [])
            if len(groups) > 1:
                raise ValueError("Invalid stored media group")
            if groups:
                grouped_positions.setdefault(groups[0], []).append(int(position))
        for group_id, positions in grouped_positions.items():
            complete = complete_groups[group_id]
            if (
                positions != complete
                or not 2 <= len(complete) <= 10
                or complete != list(range(complete[0], complete[0] + len(complete)))
            ):
                raise ValueError("Invalid stored media group")

    def _validate_message(self, message: Any, *, revision: int | None) -> None:
        if not isinstance(message, dict):
            raise ValueError("Invalid stored media group")
        message_id = message.get("id")
        chat_id = message.get("chat_id")
        sender_id = message.get("sender_id")
        if (
            type(message_id) is not int
            or not 0 < message_id < 2**63
            or type(chat_id) is not int
            or not 0 < chat_id < 2**63
            or type(sender_id) is not int
            or not 0 < sender_id < 2**63
        ):
            raise ValueError("Invalid stored media group")
        stored = self._stored_membership(chat_id, message_id, revision=revision)
        value = message.get("media_group_id")
        if stored is None:
            if value is not None:
                raise ValueError("Invalid stored media group")
            return
        if (
            not isinstance(value, str)
            or re.fullmatch(r"[1-9][0-9]*", value) is None
            or int(value) >= 2**63
            or int(value) != stored[0]
            or chat_id != stored[4]
            or message_id != stored[5]
        ):
            raise ValueError("Invalid stored media group")
        group_id, ordinal, kind, member_count = stored[:4]
        rows = self._connection.execute(
            "SELECT m.ordinal, m.chat_id, m.message_id, messages.body, "
            "r.revision, e.type, e.body, chats.bot_id "
            "FROM media_group_members m JOIN messages "
            "ON messages.chat_id=m.chat_id AND messages.id=m.message_id "
            "JOIN message_revisions r "
            "ON r.chat_id=m.chat_id AND r.message_id=m.message_id "
            "JOIN events e ON e.sequence=r.revision "
            "JOIN chats ON chats.id=m.chat_id "
            "WHERE m.group_id=? ORDER BY m.ordinal",
            (group_id,),
        ).fetchall()
        if len(rows) != member_count or [row[0] for row in rows] != list(range(member_count)):
            raise ValueError("Invalid stored media group")
        identifiers = [int(row[2]) for row in rows]
        if identifiers != list(range(identifiers[0], identifiers[0] + member_count)):
            raise ValueError("Invalid stored media group")
        revisions = [int(row[4]) for row in rows]
        if revisions != list(range(revisions[0], revisions[0] + member_count)):
            raise ValueError("Invalid stored media group")
        for row in rows:
            self._validate_member(
                row,
                representative_ordinal=int(ordinal),
                representative=message,
                group_value=value,
                group_chat_id=int(chat_id),
                kind=str(kind),
            )

    def _stored_membership(
        self, chat_id: int, message_id: int, *, revision: int | None
    ) -> Any:
        query = (
            "SELECT m.group_id, m.ordinal, g.kind, g.member_count, m.chat_id, m.message_id "
            "FROM media_group_members m JOIN media_groups g "
            "ON g.id=m.group_id AND g.chat_id=m.chat_id "
        )
        if revision is None:
            return self._connection.execute(
                query + "WHERE m.chat_id=? AND m.message_id=?", (chat_id, message_id)
            ).fetchone()
        rows = self._connection.execute(
            query
            + "JOIN message_revisions r "
            "ON r.chat_id=m.chat_id AND r.message_id=m.message_id WHERE r.revision=?",
            (revision,),
        ).fetchall()
        if len(rows) > 1:
            raise ValueError("Invalid stored media group")
        return rows[0] if rows else None

    def _validate_member(
        self,
        row: Any,
        *,
        representative_ordinal: int,
        representative: dict[str, Any],
        group_value: str,
        group_chat_id: int,
        kind: str,
    ) -> None:
        member_ordinal, member_chat_id, member_id, body, _, event_kind, event_body, bot_id = row
        try:
            member = json.loads(body)
            event = json.loads(event_body)
        except (TypeError, ValueError):
            raise ValueError("Invalid stored media group") from None
        if (
            not isinstance(member, dict)
            or not isinstance(event, dict)
            or event_kind != "message.created"
            or event != member
            or type(member.get("id")) is not int
            or member.get("id") != member_id
            or type(member.get("chat_id")) is not int
            or member.get("chat_id") != member_chat_id
            or member_chat_id != group_chat_id
            or member.get("media_group_id") != group_value
            or type(member.get("sender_id")) is not int
            or member.get("sender_id") != bot_id
        ):
            raise ValueError("Invalid stored media group")
        self._validate_media(member, kind)
        if member_ordinal == representative_ordinal and member != representative:
            raise ValueError("Invalid stored media group")

    def _validate_media(self, member: dict[str, Any], kind: str) -> None:
        if kind == "photo":
            photo = member.get("photo")
            if (
                not isinstance(photo, dict)
                or photo.keys() != {"asset_id"}
                or type(photo.get("asset_id")) is not int
                or "document" in member
                or self._connection.execute(
                    "SELECT 1 FROM assets a JOIN media_blobs b ON b.sha256=a.sha256 WHERE a.id=?",
                    (photo.get("asset_id"),),
                ).fetchone()
                is None
            ):
                raise ValueError("Invalid stored media group")
            return
        if kind == "document":
            document = member.get("document")
            try:
                if (
                    not isinstance(document, dict)
                    or document.keys() != {"document_id"}
                    or not isinstance(document.get("document_id"), str)
                    or "photo" in member
                ):
                    raise ValueError
                document_id = canonical_document_id(document["document_id"])
                if (
                    str(document_id) != document["document_id"]
                    or self._connection.execute(
                        "SELECT 1 FROM documents d JOIN media_blobs b ON b.sha256=d.sha256 "
                        "WHERE d.id=?",
                        (document_id,),
                    ).fetchone()
                    is None
                ):
                    raise ValueError
            except (TypeError, ValueError):
                raise ValueError("Invalid stored media group") from None
            return
        raise ValueError("Invalid stored media group")

    @staticmethod
    def _group_identifier(message: Any) -> int | None:
        if not isinstance(message, dict):
            return None
        value = message.get("media_group_id")
        if (
            not isinstance(value, str)
            or re.fullmatch(r"[1-9][0-9]*", value) is None
            or int(value) >= 2**63
        ):
            return None
        return int(value)
