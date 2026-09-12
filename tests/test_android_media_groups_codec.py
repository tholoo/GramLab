"""Independent bridge-v6 album topology and original Android codec oracles."""

from __future__ import annotations

import copy
import http.client
import json
import os
import shutil
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pytest
from test_android_quoted_code import assert_isolation

from gramlab.runtime import RuntimeProfile, Sandbox

sys.path.insert(0, str(Path("tests/probes").resolve()))
from android_media_groups_codec import probe

INVALID = "GRAMLAB_BRIDGE_INVALID_DATA"
INVALID_MEDIA = "GRAMLAB_BRIDGE_INVALID_CUSTOM_EMOJI"
MAX_ID = "9223372036854775807"
WORLD = "media-groups-codec-world"
USERS = [
    {"id": 1, "is_bot": False, "first_name": "Sara", "language_code": "fa"},
    {"id": 2, "is_bot": True, "first_name": "Albums", "username": "albums_bot"},
]
NATIVE_USERS = [
    {
        "id": 1,
        "first_name": "Sara",
        "self": True,
        "bot": False,
        "username": None,
        "language_code": "fa",
        "phone": None,
    },
    {
        "id": 2,
        "first_name": "Albums",
        "self": False,
        "bot": True,
        "username": "albums_bot",
        "language_code": None,
        "phone": None,
    },
]
PHOTO = {
    "asset_id": 1,
    "mime_type": "image/png",
    "file_size": 100,
    "sha256": "a" * 64,
    "width": 16,
    "height": 16,
}
EXTRA_PHOTO = PHOTO | {"asset_id": 2, "sha256": "b" * 64}
EMOJI_ASSETS = [
    {
        "asset_id": 2,
        "mime_type": "image/webp",
        "file_size": 123,
        "sha256": "b" * 64,
        "width": 100,
        "height": 100,
    },
    {
        "asset_id": 3,
        "mime_type": "image/webp",
        "file_size": 45,
        "sha256": "c" * 64,
        "width": 32,
        "height": 32,
    },
]
EMOJI = {
    "custom_emoji_id": "7",
    "fallback": "🙂",
    "free": True,
    "needs_repainting": False,
    "main_asset_id": 2,
    "thumbnail_asset_id": 3,
    "duration_ms": 0,
}
DOCUMENTS = [
    {
        "document_id": "1",
        "file_name": "اول.txt",
        "mime_type": "text/plain",
        "file_size": 11,
        "sha256": "d" * 64,
    },
    {
        "document_id": "2",
        "file_name": "second.bin",
        "mime_type": "application/octet-stream",
        "file_size": 12,
        "sha256": "e" * 64,
    },
]


def photo(message_id: int, group_id: Any | None = None, *, chat: int = 1) -> dict[str, Any]:
    result: dict[str, Any] = {
        "id": message_id,
        "chat_id": chat,
        "sender_id": 2 if chat == 1 else 3,
        "date": 1700000000,
        "text": "",
        "photo": {"asset_id": 1},
    }
    if group_id is not None:
        result["media_group_id"] = group_id
    return result


def document(message_id: int, document_id: str, group_id: Any) -> dict[str, Any]:
    return {
        "id": message_id,
        "chat_id": 1,
        "sender_id": 2,
        "date": 1700000000,
        "text": "",
        "document": {"document_id": document_id},
        "media_group_id": group_id,
    }


def text(message_id: int, value: str = "standalone") -> dict[str, Any]:
    return {
        "id": message_id,
        "chat_id": 1,
        "sender_id": 2,
        "date": 1700000000,
        "text": value,
    }


def snapshot(
    messages: list[dict[str, Any]],
    *,
    version: int = 6,
    assets: list[dict[str, Any]] | None = None,
    documents: list[dict[str, Any]] | None = None,
    custom_emoji: list[dict[str, Any]] | None = None,
    users: list[dict[str, Any]] | None = None,
    chats: list[dict[str, Any]] | None = None,
    message_position: int | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "schema": version,
        "world_id": WORLD,
        "user_id": 1,
        "cursor": 20,
        "now": 1700000000,
        "users": copy.deepcopy(USERS if users is None else users),
        "chats": copy.deepcopy(
            [{"id": 1, "type": "private", "user_id": 1, "bot_id": 2}] if chats is None else chats
        ),
        "messages": copy.deepcopy(messages),
        "message_position": len(messages) if message_position is None else message_position,
        "sends": [],
        "assets": copy.deepcopy([] if assets is None else assets),
        "message_revisions": [
            {"chat_id": item["chat_id"], "message_id": item["id"], "revision": index + 1}
            for index, item in enumerate(messages)
        ],
        "custom_emoji": copy.deepcopy([] if custom_emoji is None else custom_emoji),
        "documents": copy.deepcopy([] if documents is None else documents),
    }
    if version < 5:
        body.pop("documents")
    if version < 4:
        body.pop("custom_emoji")
    return body


def changes(
    messages: list[dict[str, Any]],
    *,
    version: int = 6,
    kinds: list[str] | None = None,
    assets: list[dict[str, Any]] | None = None,
    documents: list[dict[str, Any]] | None = None,
    custom_emoji: list[dict[str, Any]] | None = None,
    after: int = 0,
) -> dict[str, Any]:
    event_kinds = ["message.created"] * len(messages) if kinds is None else kinds
    rows = [
        {
            "position": after + index + 1,
            "type": event_kinds[index],
            "data": copy.deepcopy(message),
            "revision": after + index + 1,
        }
        for index, message in enumerate(messages)
    ]
    return {
        "schema": version,
        "world_id": WORLD,
        "user_id": 1,
        "cursor": after + len(rows),
        "head": after + len(rows),
        "now": 1700000001,
        "changes": rows,
        "users": copy.deepcopy(USERS),
        "assets": copy.deepcopy([] if assets is None else assets),
        "custom_emoji": copy.deepcopy([] if custom_emoji is None else custom_emoji),
        "documents": copy.deepcopy([] if documents is None else documents),
    }


def native_photo(message_id: int, group_id: str) -> dict[str, Any]:
    return {
        "id": message_id,
        "sender_id": 2,
        "recipient_id": 1,
        "out": False,
        "date": 1700000000,
        "text": "",
        "media_group_id": group_id,
        "grouped_flag": True,
        "native_photo": {
            "asset_id": 1,
            "dc_id": 0,
            "access_hash": 0,
            "file_reference_bytes": 0,
            "size_type": "x",
            "volume_id": 1,
            "local_id": 1,
            "width": 16,
            "height": 16,
            "file_size": 100,
        },
    }


def cases() -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    authored: list[dict[str, Any]] = []
    expected: dict[str, dict[str, Any]] = {}

    def add(name: str, case: dict[str, Any], **oracle: Any) -> None:
        authored.append({"name": name, **copy.deepcopy(case)})
        expected[name] = copy.deepcopy(oracle)

    def reject(name: str, body: dict[str, Any], *, error: str = INVALID, **options: Any) -> None:
        add(name, {"snapshots": [body], **options}, error=error, returncode=2)

    basic = snapshot([photo(1, MAX_ID), photo(2, MAX_ID)], assets=[PHOTO])
    add(
        "snapshot-canonical-max-id-and-flag17",
        {"snapshots": [basic]},
        returncode=0,
        messages=[native_photo(2, MAX_ID), native_photo(1, MAX_ID)],
        paths=["/v6/snapshot"],
    )
    retained = snapshot([photo(1, "1"), photo(2, "1")], assets=[PHOTO, EXTRA_PHOTO])
    add(
        "snapshot-retained-superset-dependencies",
        {"snapshots": [retained]},
        returncode=0,
        messages=[native_photo(2, "1"), native_photo(1, "1")],
    )
    documents = snapshot([document(1, "1", "2"), document(2, "2", "2")], documents=DOCUMENTS)
    add("snapshot-document-group", {"snapshots": [documents]}, returncode=0, group_ids=["2", "2"])
    emoji_group = [photo(1, "3"), photo(2, "3")]
    emoji_group[0]["caption"] = "🙂"
    emoji_group[0]["caption_entities"] = [
        {"type": "custom_emoji", "offset": 0, "length": 2, "custom_emoji_id": "7"}
    ]
    add(
        "snapshot-caption-custom-emoji-scope",
        {
            "snapshots": [
                snapshot(
                    emoji_group,
                    assets=[PHOTO, *EMOJI_ASSETS],
                    custom_emoji=[EMOJI],
                )
            ]
        },
        returncode=0,
        group_ids=["3", "3"],
    )

    live_messages = [text(1, "before"), photo(2, "4"), photo(3, "4"), text(4, "after")]
    live = changes(live_messages, assets=[PHOTO])
    add(
        "changes-one-atomic-group-application",
        {
            "snapshots": [snapshot([], message_position=0)],
            "mode": "changes",
            "get": {"/v6/changes?after=0&limit=100": {"body": live}},
        },
        returncode=0,
        application_counts=[1, 2, 1],
        application_sequences=[1, 3, 4],
        paths=["/v6/snapshot", "/v6/changes?after=0&limit=100"],
    )
    add(
        "difference-complete-group-topology",
        {
            "snapshots": [snapshot([], message_position=0)],
            "mode": "difference",
            "get": {"/v6/changes?after=0&limit=100": {"body": live}},
        },
        returncode=0,
        difference_group_ids=[None, "4", "4", None],
    )

    ten_members = [photo(index, "10") for index in range(1, 11)]
    add(
        "snapshot-valid-ten-member-group",
        {"snapshots": [snapshot(ten_members, assets=[PHOTO])]},
        returncode=0,
        group_ids=["10"] * 10,
    )
    consecutive_groups = [
        photo(1, "11"),
        photo(2, "11"),
        photo(3, "12"),
        photo(4, "12"),
    ]
    add(
        "changes-two-consecutive-complete-groups",
        {
            "snapshots": [snapshot([], message_position=0)],
            "mode": "changes",
            "get": {
                "/v6/changes?after=0&limit=100": {
                    "body": changes(consecutive_groups, assets=[PHOTO])
                }
            },
        },
        returncode=0,
        application_counts=[2, 2],
        application_sequences=[2, 4],
    )

    limit_one_group = [photo(1, "13"), photo(2, "13")]
    add(
        "changes-limit-one-expands-complete-group",
        {
            "snapshots": [snapshot([], message_position=0)],
            "mode": "changes-limit-1",
            "get": {
                "/v6/changes?after=0&limit=1": {"body": changes(limit_one_group, assets=[PHOTO])}
            },
        },
        returncode=0,
        final_atomic_count=2,
        final_sequence=2,
        paths=["/v6/snapshot", "/v6/changes?after=0&limit=1"],
    )

    maximum_expansion = [text(index, f"standalone-{index}") for index in range(1, 1000)]
    maximum_expansion += [photo(index, "14") for index in range(1000, 1010)]
    add(
        "changes-limit-one-thousand-expands-to-one-thousand-nine",
        {
            "snapshots": [snapshot([], message_position=0)],
            "mode": "changes-limit-1000",
            "get": {
                "/v6/changes?after=0&limit=1000": {
                    "body": changes(maximum_expansion, assets=[PHOTO])
                }
            },
        },
        returncode=0,
        final_atomic_count=10,
        final_sequence=1009,
        paths=["/v6/snapshot", "/v6/changes?after=0&limit=1000"],
    )

    expanded_messages = [text(index, f"standalone-{index}") for index in range(1, 100)]
    expanded_messages += [photo(100, "5"), photo(101, "5"), photo(102, "5")]
    add(
        "changes-limit-plus-group-remainder",
        {
            "snapshots": [snapshot([], message_position=0)],
            "mode": "changes",
            "get": {
                "/v6/changes?after=0&limit=100": {
                    "body": changes(expanded_messages, assets=[PHOTO])
                }
            },
        },
        returncode=0,
        final_atomic_count=3,
        final_sequence=102,
    )

    send_message = text(1, "album codec send") | {"sender_id": 1}
    add(
        "v6-messages-route",
        {
            "snapshots": [snapshot([], message_position=0)],
            "mode": "send",
            "post": {
                "/v6/messages": {
                    "body": {
                        "schema": 6,
                        "world_id": WORLD,
                        "user_id": 1,
                        "send": {"request_id": "42", "position": 1, "message": send_message},
                        "users": USERS,
                        "assets": [],
                        "custom_emoji": [],
                        "documents": [],
                        "message_revision": 1,
                    }
                }
            },
            "expected_request": {
                "/v6/messages": {
                    "keys": ["request_id", "chat_id", "text", "entities"],
                    "values": {
                        "request_id": "42",
                        "chat_id": 1,
                        "text": "album codec send",
                        "entities": [],
                    },
                }
            },
        },
        returncode=0,
        send={"id": 1, "pts": 1, "pts_count": 1, "date": 1700000000},
        paths=["/v6/snapshot", "/v6/messages"],
    )

    add(
        "v5-valid-snapshot-path",
        {"bridge_version": 5, "snapshots": [snapshot([text(1)], version=5)]},
        returncode=0,
        paths=["/v5/snapshot"],
    )
    add(
        "v5-valid-changes-path",
        {
            "bridge_version": 5,
            "snapshots": [snapshot([], version=5, message_position=0)],
            "mode": "changes",
            "get": {"/v5/changes?after=0&limit=100": {"body": changes([text(1)], version=5)}},
        },
        returncode=0,
        application_counts=[1],
        application_sequences=[1],
        paths=["/v5/snapshot", "/v5/changes?after=0&limit=100"],
    )
    add(
        "v5-valid-messages-path",
        {
            "bridge_version": 5,
            "snapshots": [snapshot([], version=5, message_position=0)],
            "mode": "send",
            "post": {
                "/v5/messages": {
                    "body": {
                        "schema": 5,
                        "world_id": WORLD,
                        "user_id": 1,
                        "send": {"request_id": "42", "position": 1, "message": send_message},
                        "users": USERS,
                        "assets": [],
                        "custom_emoji": [],
                        "documents": [],
                        "message_revision": 1,
                    }
                }
            },
            "expected_request": {
                "/v5/messages": {
                    "keys": ["request_id", "chat_id", "text", "entities"],
                    "values": {
                        "request_id": "42",
                        "chat_id": 1,
                        "text": "album codec send",
                        "entities": [],
                    },
                }
            },
        },
        returncode=0,
        send={"id": 1, "pts": 1, "pts_count": 1, "date": 1700000000},
        paths=["/v5/snapshot", "/v5/messages"],
    )

    callback_message = photo(1, "6")
    add(
        "v6-callback-route-carries-grouped-member",
        {
            "snapshots": [snapshot([photo(1), photo(2)], assets=[PHOTO])],
            "mode": "callback",
            "post": {
                "/v6/callbacks": {
                    "body": {
                        "schema": 6,
                        "world_id": WORLD,
                        "user_id": 1,
                        "callback": {
                            "id": "callback-1",
                            "user_id": 1,
                            "chat_id": 1,
                            "message": callback_message,
                            "data": "mention-codec",
                            "chat_instance": "1",
                            "answer": {"text": "ok", "show_alert": False, "cache_time": 0},
                        },
                        "users": USERS,
                        "assets": [PHOTO],
                        "message_revision": 1,
                        "custom_emoji": [],
                        "documents": [],
                    }
                }
            },
            "expected_request": {
                "/v6/callbacks": {
                    "keys": ["request_id", "chat_id", "message_id", "data"],
                    "values": {"chat_id": 1, "message_id": 1, "data": "mention-codec"},
                    "generated_request_id": True,
                }
            },
        },
        returncode=0,
        callback={"text": "ok", "show_alert": False, "cache_time": 0},
        paths=["/v6/snapshot", "/v6/callbacks"],
    )
    add(
        "v6-custom-emoji-document-route",
        {
            "snapshots": [snapshot([], message_position=0)],
            "mode": "custom-emoji-documents",
            "requested": ["7"],
            "post": {
                "/v6/custom-emoji-documents": {
                    "body": {
                        "schema": 6,
                        "world_id": WORLD,
                        "user_id": 1,
                        "custom_emoji": [EMOJI],
                        "assets": EMOJI_ASSETS,
                    }
                }
            },
            "expected_request": {
                "/v6/custom-emoji-documents": {
                    "keys": ["custom_emoji_ids"],
                    "values": {"custom_emoji_ids": ["7"]},
                }
            },
        },
        returncode=0,
        document_count=1,
        paths=["/v6/snapshot", "/v6/custom-emoji-documents"],
    )

    recovery_snapshot = snapshot([photo(1, "7"), photo(2, "7")], assets=[PHOTO])
    recovery_snapshot["message_position"] = 2
    empty_after_recovery = changes([], after=2)
    add(
        "split-cursor-exact-409-resnapshot-and-resume",
        {
            "snapshots": [recovery_snapshot, recovery_snapshot],
            "mode": "media-group-resnapshot",
            "get": {
                "/v6/changes?after=1&limit=100": {
                    "status": 409,
                    "body": {
                        "schema": 6,
                        "error": {
                            "code": "resnapshot_required",
                            "message": "Client cursor splits a media group",
                        },
                    },
                },
                "/v6/changes?after=2&limit=100": {"body": empty_after_recovery},
            },
        },
        returncode=0,
        recovery={
            "error": "GRAMLAB_BRIDGE_RESNAPSHOT_REQUIRED",
            "snapshot_position": 2,
            "resumed_cursor": 2,
            "resumed_changes": 0,
        },
        paths=[
            "/v6/snapshot",
            "/v6/changes?after=1&limit=100",
            "/v6/snapshot",
            "/v6/changes?after=2&limit=100",
        ],
    )

    legacy = snapshot([photo(1, "1"), photo(2, "1")], version=5, assets=[PHOTO])
    reject("v5-rejects-group-field", legacy, bridge_version=5)
    for name, identifier in [
        ("numeric", 1),
        ("zero", "0"),
        ("leading-zero", "01"),
        ("negative", "-1"),
        ("overflow", "9223372036854775808"),
        ("twenty-digits", "10000000000000000000"),
        ("null", None),
    ]:
        members = [photo(1, identifier), photo(2, identifier)]
        if name == "null":
            for member in members:
                member["media_group_id"] = None
        reject(
            f"group-id-{name}",
            snapshot(members, assets=[PHOTO]),
        )
    reject("group-singleton", snapshot([photo(1, "8")], assets=[PHOTO]))
    reject(
        "group-eleven-members",
        snapshot([photo(index, "8") for index in range(1, 12)], assets=[PHOTO]),
    )
    reject(
        "group-mixed-media-kind",
        snapshot([photo(1, "8"), document(2, "1", "8")], assets=[PHOTO], documents=[DOCUMENTS[0]]),
    )
    reject("group-message-id-gap", snapshot([photo(1, "8"), photo(3, "8")], assets=[PHOTO]))
    reject("group-duplicate-message-id", snapshot([photo(1, "8"), photo(1, "8")], assets=[PHOTO]))
    reject("group-reordered-message-id", snapshot([photo(2, "8"), photo(1, "8")], assets=[PHOTO]))

    for name, revisions in (
        ("gapped", [1, 3]),
        ("duplicate", [1, 1]),
        ("reordered", [2, 1]),
    ):
        revision_snapshot = snapshot([photo(1, "15"), photo(2, "15")], assets=[PHOTO])
        for record, revision in zip(revision_snapshot["message_revisions"], revisions, strict=True):
            record["revision"] = revision
        reject(f"snapshot-group-revision-{name}", revision_snapshot)
    reject(
        "group-disjoint-reuse",
        snapshot(
            [photo(1, "8"), photo(2, "8"), text(3), photo(4, "8"), photo(5, "8")], assets=[PHOTO]
        ),
    )
    reject(
        "group-interleaved-identities",
        snapshot([photo(1, "8"), photo(2, "9"), photo(3, "8"), photo(4, "9")], assets=[PHOTO]),
    )
    cross_users = [*USERS, {"id": 3, "is_bot": True, "first_name": "Other"}]
    cross_chats = [
        {"id": 1, "type": "private", "user_id": 1, "bot_id": 2},
        {"id": 2, "type": "private", "user_id": 1, "bot_id": 3},
    ]
    reject(
        "group-cross-chat",
        snapshot(
            [photo(1, "8"), photo(2, "8", chat=2)],
            assets=[PHOTO],
            users=cross_users,
            chats=cross_chats,
        ),
    )
    edited = [photo(1, "8"), photo(2, "8")]
    edited[0]["edit_date"] = 1700000001
    reject("grouped-snapshot-edit", snapshot(edited, assets=[PHOTO]))
    nonmedia = text(1)
    nonmedia["media_group_id"] = "8"
    reject("grouped-nonmedia", snapshot([nonmedia, photo(2, "8")], assets=[PHOTO]))
    wrong_sender = [photo(1, "8"), photo(2, "8")]
    wrong_sender[0]["sender_id"] = 1
    reject("grouped-persona-sender", snapshot(wrong_sender, assets=[PHOTO]))
    extra = [photo(1, "8"), photo(2, "8")]
    extra[0]["group_ordinal"] = 0
    reject("unknown-group-field", snapshot(extra, assets=[PHOTO]))

    reject(
        "changes-incomplete-group",
        snapshot([], message_position=0),
        mode="changes",
        get={"/v6/changes?after=0&limit=100": {"body": changes([photo(1, "9")], assets=[PHOTO])}},
    )
    reject(
        "changes-grouped-edit",
        snapshot([], message_position=0),
        mode="changes",
        get={
            "/v6/changes?after=0&limit=100": {
                "body": changes(
                    [photo(1, "9"), photo(2, "9")], kinds=["message.edited"] * 2, assets=[PHOTO]
                )
            }
        },
    )
    reject(
        "changes-response-local-extra-dependency",
        snapshot([], message_position=0),
        error=INVALID_MEDIA,
        mode="changes",
        get={
            "/v6/changes?after=0&limit=100": {
                "body": changes([photo(1, "9"), photo(2, "9")], assets=[PHOTO, EXTRA_PHOTO])
            }
        },
    )
    duplicate_response_message = [photo(1, "16"), photo(2, "16"), text(2)]
    reject(
        "changes-duplicate-grouped-and-standalone-message-id",
        snapshot([], message_position=0),
        mode="changes",
        get={
            "/v6/changes?after=0&limit=100": {
                "body": changes(duplicate_response_message, assets=[PHOTO])
            }
        },
    )
    reject(
        "difference-duplicate-grouped-and-standalone-message-id",
        snapshot([], message_position=0),
        mode="difference",
        get={
            "/v6/changes?after=0&limit=100": {
                "body": changes(duplicate_response_message, assets=[PHOTO])
            }
        },
    )
    too_many_standalone = [text(index, f"m{index}") for index in range(1, 102)]
    reject(
        "changes-over-limit-without-group-expansion",
        snapshot([], message_position=0),
        mode="changes",
        get={"/v6/changes?after=0&limit=100": {"body": changes(too_many_standalone)}},
    )
    return authored, expected


def test_patch_and_fixture_freeze_bridge_v6_album_invariants() -> None:
    patch = Path("clients/android/patches/0032-atomic-media-groups.patch").read_text()
    assert patch.count("diff --git ") == 5
    for path in (
        "GramLabBridge.java",
        "GramLabMedia.java",
        "GramLabRuntime.java",
        "FileLoader.java",
        "BridgeProbe.java",
    ):
        assert path in patch
    for required in (
        "message.grouped_id = mediaGroupId;",
        "message.flags |= 1 << 17;",
        "validateCompleteGroups(snapshotTopology);",
        "validateCompleteGroups(changeTopology);",
        'responseMessages.add(record.chatId + ":" + record.messageId)',
        "groupMember(record, version, revisionValue, null)",
        "records.length() <= (version == 6 ? limit + 9 : limit)",
        "application.envelope(current, batch.now)",
        "eventCursor = application.finalPosition;",
        "catch (GramLabBridge.ResnapshotRequired split)",
        "reconcileSnapshotOnUi(recovered);",
        "eventCursor = recovered.messagePosition;",
        '"/v" + version + "/documents/"',
        '"/v" + version + "/messages"',
    ):
        assert required in patch
    assert patch.index(
        "processUpdates(\n+                                        application.envelope"
    ) < patch.index("eventCursor = application.finalPosition;")
    assert (
        patch.index("reconcileSnapshotOnUi(recovered);")
        < patch.index("snapshot = recovered;")
        < patch.index("eventCursor = recovered.messagePosition;")
    )
    series = Path("clients/android/patches/series").read_text().splitlines()
    assert series[-2:] == ["0031-rich-auto-detection.patch", "0032-atomic-media-groups.patch"]
    assert series.count("0032-atomic-media-groups.patch") == 1
    java = Path("tests/fixtures/android_media_groups/MediaGroupsCodecProbe.java").read_text()
    assert java.startswith("// SPDX-License-Identifier: GPL-2.0-or-later\n")
    assert 'Class.forName("org.telegram.gramlab.BridgeProbe")' in java
    assert "TLRPC" not in java
    assert "retained normal30" not in java


def test_independent_case_inventory_covers_contract_boundaries() -> None:
    authored, expected = cases()
    names = [case["name"] for case in authored]
    assert len(names) == len(set(names)) == 48
    assert set(names) == set(expected)
    assert all(case["snapshots"] for case in authored)
    assert {
        "snapshot-canonical-max-id-and-flag17",
        "snapshot-document-group",
        "snapshot-caption-custom-emoji-scope",
        "changes-one-atomic-group-application",
        "difference-complete-group-topology",
        "snapshot-valid-ten-member-group",
        "changes-two-consecutive-complete-groups",
        "changes-limit-one-expands-complete-group",
        "changes-limit-one-thousand-expands-to-one-thousand-nine",
        "changes-limit-plus-group-remainder",
        "v5-valid-snapshot-path",
        "v5-valid-changes-path",
        "v5-valid-messages-path",
        "v6-messages-route",
        "v6-callback-route-carries-grouped-member",
        "v6-custom-emoji-document-route",
        "split-cursor-exact-409-resnapshot-and-resume",
        "v5-rejects-group-field",
        "group-eleven-members",
        "group-cross-chat",
        "group-disjoint-reuse",
        "group-reordered-message-id",
        "snapshot-group-revision-gapped",
        "snapshot-group-revision-duplicate",
        "snapshot-group-revision-reordered",
        "changes-response-local-extra-dependency",
        "changes-duplicate-grouped-and-standalone-message-id",
        "difference-duplicate-grouped-and-standalone-message-id",
    } <= set(names)
    explicit_null = next(case for case in authored if case["name"] == "group-id-null")
    assert [message["media_group_id"] for message in explicit_null["snapshots"][0]["messages"]] == [
        None,
        None,
    ]


def test_probe_collects_process_results_and_bounded_request_journal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    authored = [{"name": "unsupported", "snapshots": [snapshot([])]}]
    Path("media-groups-codec-cases.json").write_text(json.dumps(authored))
    result_body = {"error": INVALID}

    def guest(*arguments: str, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        if "/system/bin/app_process" in arguments:
            return subprocess.CompletedProcess(arguments, 2, json.dumps(result_body), "")
        return subprocess.CompletedProcess(arguments, 0, "", "")

    observed = probe(guest)
    assert observed["cases"] == {
        "unsupported": {"returncode": 2, "result": result_body, "requests": []}
    }
    retained = json.loads(Path("unsupported-codec-process.json").read_text())
    assert retained["returncode"] == 2
    assert retained["requests"] == []
    assert retained["unconsumed_snapshots"] == 1


def test_probe_fixture_serves_legacy_v5_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    expected = snapshot([text(1)], version=5)
    Path("media-groups-codec-cases.json").write_text(
        json.dumps([{"name": "v5-snapshot", "bridge_version": 5, "snapshots": [expected]}])
    )
    configuration: dict[str, Any] = {}

    def guest(*arguments: str, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        nonlocal configuration
        if kwargs.get("input") is not None:
            configuration = json.loads(kwargs["input"])
        if "/system/bin/app_process" not in arguments:
            return subprocess.CompletedProcess(arguments, 0, "", "")
        endpoint = configuration["endpoint"].removeprefix("http://")
        _guest_host, raw_port = endpoint.rsplit(":", 1)
        connection = http.client.HTTPConnection("127.0.0.1", int(raw_port), timeout=5)
        try:
            connection.request(
                "GET",
                "/v5/snapshot",
                headers={"Authorization": "Bearer " + configuration["capability"]},
            )
            response = connection.getresponse()
            body = response.read()
        finally:
            connection.close()
        assert response.status == 200
        return subprocess.CompletedProcess(arguments, 0, body.decode(), "")

    observed = probe(guest)
    assert observed["cases"] == {
        "v5-snapshot": {
            "returncode": 0,
            "result": expected,
            "requests": [{"method": "GET", "path": "/v5/snapshot"}],
        }
    }


def _run_android_codec(
    tmp_path: Path, client_apk: str, probe_apk: str, authored: list[dict[str, Any]]
) -> dict[str, Any]:
    manifest = os.environ.get("GRAMLAB_ANDROID_RUNTIME_PROFILE")
    if manifest is None or not os.access("/dev/kvm", os.R_OK | os.W_OK):
        pytest.skip("Requires the Android profile and accessible KVM")
    profile = RuntimeProfile.load(Path(manifest))
    shutil.copy2(client_apk, tmp_path / "client.apk")
    shutil.copy2(probe_apk, tmp_path / "media-groups-probe.apk")
    (tmp_path / "media-groups-codec-cases.json").write_text(
        json.dumps(authored, ensure_ascii=False)
    )
    shutil.copytree(
        "src/gramlab", tmp_path / "gramlab", ignore=shutil.ignore_patterns("__pycache__")
    )
    (tmp_path / "emulator-profile.json").write_text(json.dumps(asdict(profile)))
    for name in ("emulator_process.py", "android_guest.py", "android_media_groups_codec.py"):
        shutil.copy2(Path("tests/probes") / name, tmp_path / name)
    toolchain = json.loads(Path("clients/android/toolchain.json").read_text())
    image = (
        f"system-images;android-{toolchain['sdk']['platform']};"
        f"{toolchain['runtime']['imageType']};{toolchain['runtime']['abi']}"
    )
    result = Sandbox(profile).supervise(
        [
            profile.python,
            "/work/android_media_groups_codec.py",
            profile.executables["emulator"],
            profile.executables["adb"],
            profile.executables["avdmanager"],
            image,
        ],
        data=tmp_path,
        kvm=True,
        timeout=600,
    )
    (tmp_path / "media-groups-codec-result.json").write_text(result.stdout)
    assert result.returncode == 0, result.stderr
    full = json.loads(result.stdout)
    assert_isolation(full)
    observed = full["extra_probe"]
    assert isinstance(observed, dict)
    return observed


@pytest.mark.android
def test_actual_pre_album_apk_rejects_bridge_v6(tmp_path: Path) -> None:
    client_apk = os.environ.get("GRAMLAB_ANDROID_PRE_ALBUM_APK")
    probe_apk = os.environ.get("GRAMLAB_ANDROID_MEDIA_GROUPS_CODEC_PROBE_APK")
    if client_apk is None or probe_apk is None:
        pytest.skip("Requires the reviewed pre-album APK and media-group probe APK")
    authored = [{"name": "normal30-unsupported-v6", "snapshots": [snapshot([])]}]
    observed = _run_android_codec(tmp_path, client_apk, probe_apk, authored)
    assert observed == {
        "cases": {
            "normal30-unsupported-v6": {
                "returncode": 2,
                "result": {"error": INVALID},
                "requests": [],
            }
        }
    }


@pytest.mark.android
def test_actual_album_codec_uses_complete_original_group_carriers(tmp_path: Path) -> None:
    client_apk = os.environ.get("GRAMLAB_ANDROID_PROBE_APK")
    probe_apk = os.environ.get("GRAMLAB_ANDROID_MEDIA_GROUPS_CODEC_PROBE_APK")
    if client_apk is None or probe_apk is None:
        pytest.skip("Requires the reviewed album-era client and media-group probe APKs")
    authored, expected = cases()
    observed = _run_android_codec(tmp_path, client_apk, probe_apk, authored)
    actual = observed["cases"]
    assert set(actual) == set(expected)
    for name, oracle in expected.items():
        result = actual[name]
        assert result["returncode"] == oracle["returncode"], (name, result)
        if "error" in oracle:
            assert result["result"] == {"error": oracle["error"]}, (name, result)
            continue
        body = result["result"]
        if "messages" in oracle:
            assert body["messages"] == oracle["messages"], name
        if "group_ids" in oracle:
            assert [message["media_group_id"] for message in body["messages"]] == oracle[
                "group_ids"
            ]
        if "application_counts" in oracle:
            envelopes = body["changes"]["envelopes"]
            assert [len(envelope["updates"]) for envelope in envelopes] == oracle[
                "application_counts"
            ]
            assert [envelope["seq"] for envelope in envelopes] == oracle["application_sequences"]
        if "difference_group_ids" in oracle:
            updates = body["difference"]["updates"]
            assert [update["message"].get("media_group_id") for update in updates] == oracle[
                "difference_group_ids"
            ]
        if "final_atomic_count" in oracle:
            final = body["changes"]["envelopes"][-1]
            assert (final["atomic_count"], final["seq"]) == (
                oracle["final_atomic_count"],
                oracle["final_sequence"],
            )
        if "send" in oracle:
            assert body["send"] == oracle["send"]
        if "callback" in oracle:
            assert body["callback"] == oracle["callback"]
        if "document_count" in oracle:
            assert len(body["documents"]) == oracle["document_count"]
        if "recovery" in oracle:
            assert body["media_group_resnapshot"] == oracle["recovery"]
        if "paths" in oracle:
            assert [entry["path"] for entry in result["requests"]] == oracle["paths"]
