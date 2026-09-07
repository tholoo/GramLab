"""Independent literal v4 metadata and original serialized custom emoji observations."""

import copy
import json
import os
import shutil
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pytest
from test_android_quoted_code import assert_isolation

from gramlab.runtime import RuntimeProfile, Sandbox

pytestmark = pytest.mark.android

INVALID = "GRAMLAB_BRIDGE_INVALID_DATA"
CUSTOM = "GRAMLAB_BRIDGE_INVALID_CUSTOM_EMOJI"
RICH = "GRAMLAB_BRIDGE_INVALID_RICH_MESSAGE"
MAX_ID = "9223372036854775807"
USERS = [
    {"id": 1, "is_bot": False, "first_name": "Sara", "language_code": "fa"},
    {"id": 2, "is_bot": True, "first_name": "Echo", "username": "gramlab_echo_bot"},
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
        "first_name": "Echo",
        "self": False,
        "bot": True,
        "username": "gramlab_echo_bot",
        "language_code": None,
        "phone": None,
    },
]
# Metadata-only codec fixtures: no byte download or decoder success is claimed here.
ASSETS = [
    {
        "asset_id": 1,
        "mime_type": "image/webp",
        "file_size": 123,
        "sha256": "a" * 64,
        "width": 100,
        "height": 100,
    },
    {
        "asset_id": 2,
        "mime_type": "image/webp",
        "file_size": 45,
        "sha256": "b" * 64,
        "width": 32,
        "height": 32,
    },
    {
        "asset_id": 3,
        "mime_type": "video/webm",
        "file_size": 234,
        "sha256": "c" * 64,
        "width": 100,
        "height": 100,
    },
]
CATALOG = [
    {
        "custom_emoji_id": "1",
        "fallback": "🙂",
        "free": True,
        "needs_repainting": False,
        "main_asset_id": 1,
        "thumbnail_asset_id": 2,
        "duration_ms": 0,
    },
    {
        "custom_emoji_id": "1109",
        "fallback": "✨",
        "free": False,
        "needs_repainting": True,
        "main_asset_id": 3,
        "thumbnail_asset_id": 2,
        "duration_ms": 1250,
    },
    {
        "custom_emoji_id": MAX_ID,
        "fallback": "بیشینه",
        "free": True,
        "needs_repainting": True,
        "main_asset_id": 1,
        "thumbnail_asset_id": 1,
        "duration_ms": 0,
    },
]


def snapshot() -> dict[str, Any]:
    return copy.deepcopy(
        {
            "schema": 4,
            "world_id": "custom-emoji-codec-world",
            "user_id": 1,
            "cursor": 20,
            "now": 1700000000,
            "users": USERS,
            "chats": [{"id": 1, "type": "private", "user_id": 1, "bot_id": 2}],
            "messages": [
                {
                    "id": 1,
                    "chat_id": 1,
                    "sender_id": 2,
                    "date": 1700000000,
                    "text": "Transport baseline",
                }
            ],
            "message_position": 1,
            "sends": [],
            "assets": ASSETS,
            "custom_emoji": CATALOG,
            "message_revisions": [{"chat_id": 1, "message_id": 1, "revision": 1}],
        }
    )


def native_output() -> dict[str, Any]:
    return copy.deepcopy(
        {
            "persona": 1,
            "cursor": 20,
            "now": 1700000000,
            "users": NATIVE_USERS,
            "dialogs": [{"peer_id": 2, "top_message": 1}],
            "messages": [
                {
                    "id": 1,
                    "sender_id": 2,
                    "recipient_id": 1,
                    "out": False,
                    "date": 1700000000,
                    "text": "Transport baseline",
                }
            ],
            "dialog_message_count": 1,
            "history_users": [{"peer_id": 2, "user_ids": [1, 2]}],
        }
    )


def native_documents() -> list[dict[str, Any]]:
    # Fully authored TL carrier fields, including legacy thumbnail location preservation.
    static: dict[str, Any] = {
        "id": "1",
        "dc_id": -1,
        "access_hash": 0,
        "file_reference_bytes": 0,
        "date": 0,
        "mime_type": "image/webp",
        "size": 123,
        "flags": 1,
        "thumbs": [
            {
                "kind": "TL_photoSize_layer127",
                "type": "m",
                "width": 32,
                "height": 32,
                "size": 45,
                "volume_id": 2,
                "local_id": 2,
                "location_dc_id": 0,
                "image_dc_id": -1,
                "key": "2_2",
                "filename": "2_2.jpg",
            }
        ],
        "video_thumbs": 0,
        "attributes": [
            {
                "kind": "TL_documentAttributeCustomEmoji",
                "flags": 1,
                "alt": "🙂",
                "free": True,
                "text_color": False,
                "stickerset": "TL_inputStickerSetEmpty",
            },
            {"kind": "TL_documentAttributeImageSize", "width": 100, "height": 100},
            {"kind": "TL_documentAttributeFilename", "file_name": "emoji.webp"},
        ],
        "key": "-1_1",
        "filename": "-1_1.webp",
    }
    video = copy.deepcopy(static)
    video.update(
        id="1109", mime_type="video/webm", size=234, key="-1_1109", filename="-1_1109.webm"
    )
    video["attributes"] = [
        {
            "kind": "TL_documentAttributeCustomEmoji",
            "flags": 2,
            "alt": "✨",
            "free": False,
            "text_color": True,
            "stickerset": "TL_inputStickerSetEmpty",
        },
        {
            "kind": "TL_documentAttributeVideo",
            "flags": 8,
            "width": 100,
            "height": 100,
            "duration": 1.25,
            "nosound": True,
            "round_message": False,
            "supports_streaming": False,
        },
        {"kind": "TL_documentAttributeFilename", "file_name": "emoji.webm"},
    ]
    maximum = copy.deepcopy(static)
    maximum.update(
        id="9223372036854775807",
        key="-1_9223372036854775807",
        filename="-1_9223372036854775807.webp",
    )
    maximum["attributes"][0].update(flags=3, alt="بیشینه", text_color=True)
    maximum["thumbs"][0].update(
        width=100, height=100, size=123, volume_id=1, key="1_2", filename="1_2.jpg"
    )
    return [static, video, maximum]


def cases() -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    authored: list[dict[str, Any]] = []
    expected: dict[str, dict[str, Any]] = {}

    def add(name: str, body: dict[str, Any], oracle: dict[str, Any], **options: Any) -> None:
        authored.append({"name": name, "snapshot": copy.deepcopy(body), **copy.deepcopy(options)})
        expected[name] = copy.deepcopy(oracle)

    def reject(name: str, body: dict[str, Any], error: str = INVALID, **options: Any) -> None:
        add(name, body, {"error": error}, **options)

    baseline = snapshot()
    add("retained-metadata-no-document-lookup", baseline, native_output())
    documents: dict[str, Any] = {
        "schema": 4,
        "world_id": "custom-emoji-codec-world",
        "user_id": 1,
        "custom_emoji": CATALOG,
        "assets": ASSETS,
    }
    lookup: dict[str, Any] = {
        "mode": "custom-emoji-documents",
        "documents": documents,
        "requested_ids": [MAX_ID, "1109", "1", "1"],
        "expected_ids": ["1", "1109", MAX_ID],
    }
    add(
        "static-video-max-id-roundtrip-and-collision",
        baseline,
        native_output() | {"documents": native_documents()},
        **lookup,
    )
    rich: dict[str, Any] = {
        "blocks": [
            {
                "type": "paragraph",
                "text": [
                    {
                        "type": "custom_emoji",
                        "custom_emoji_id": "1",
                        "alternative_text": "different",
                    },
                    " / فارسی ",
                    {
                        "type": "bold",
                        "text": {
                            "type": "custom_emoji",
                            "custom_emoji_id": MAX_ID,
                            "alternative_text": "",
                        },
                    },
                    {"type": "custom_emoji", "custom_emoji_id": "1109", "alternative_text": "👩‍💻"},
                ],
            },
            {
                "type": "buttons",
                "buttons": [
                    {
                        "text": [
                            "بزن ",
                            [
                                {
                                    "type": "custom_emoji",
                                    "custom_emoji_id": "1",
                                    "alternative_text": "",
                                }
                            ],
                        ],
                        "callback_data": "emoji-click",
                    }
                ],
            },
        ],
        "is_rtl": True,
    }
    rich_body = snapshot()
    rich_body["messages"][0].update(text="", rich_message=rich)
    rich_output = native_output()
    rich_output["messages"][0].update(text="", rich_message=rich)
    add("recursive-rich-empty-alternative-and-button-label", rich_body, rich_output)
    ordinary = snapshot()
    ordinary["messages"][0].update(
        text="A🙂✨",
        entities=[
            {"type": "bold", "offset": 1, "length": 2},
            {"type": "custom_emoji", "offset": 1, "length": 2, "custom_emoji_id": MAX_ID},
            {"type": "custom_emoji", "offset": 3, "length": 1, "custom_emoji_id": "1109"},
        ],
    )
    native_ordinary = native_output()
    native_ordinary["messages"][0].update(
        text="A🙂✨",
        entities=[
            {
                "kind": "TL_messageEntityCustomEmoji",
                "offset": 1,
                "length": 2,
                "custom_emoji_id": "9223372036854775807",
            },
            {"kind": "TL_messageEntityBold", "offset": 1, "length": 2},
            {
                "kind": "TL_messageEntityCustomEmoji",
                "offset": 3,
                "length": 1,
                "custom_emoji_id": "1109",
            },
        ],
    )
    add("ordinary-utf16-id-order", ordinary, native_ordinary)
    caption = snapshot()
    caption["assets"].append(
        {
            "asset_id": 4,
            "mime_type": "image/jpeg",
            "file_size": 99,
            "sha256": "d" * 64,
            "width": 120,
            "height": 80,
        }
    )
    caption["messages"][0].update(
        text="",
        photo={"asset_id": 4},
        caption="A🙂✨",
        caption_entities=ordinary["messages"][0]["entities"],
    )
    native_caption = copy.deepcopy(native_ordinary)
    native_caption["messages"][0]["native_photo"] = {
        "asset_id": 4,
        "dc_id": 0,
        "access_hash": 0,
        "file_reference_bytes": 0,
        "size_type": "x",
        "volume_id": 4,
        "local_id": 1,
        "width": 120,
        "height": 80,
        "file_size": 99,
    }
    add("photo-caption-emoji-preserves-separate-location", caption, native_caption)
    bad_caption = copy.deepcopy(caption)
    bad_caption["custom_emoji"] = []
    reject("caption-missing-response-local-documents", bad_caption, CUSTOM)
    duplicate = copy.deepcopy(ordinary)
    duplicate["messages"][0]["entities"].append(
        copy.deepcopy(ordinary["messages"][0]["entities"][1])
    )
    add("identical-entity-duplicate-collapse", duplicate, native_ordinary)
    incoming = copy.deepcopy(ordinary)
    incoming["messages"][0]["sender_id"] = 1
    incoming_output = copy.deepcopy(native_ordinary)
    incoming_output["messages"][0].update(sender_id=1, recipient_id=2, out=True)
    add("scenario-incoming-ordinary-entity", incoming, incoming_output)
    legacy = snapshot()
    legacy.update(schema=3, assets=[])
    legacy.pop("custom_emoji")
    add("v3-baseline-preserved", legacy, native_output(), bridge_version=3)
    for kind, original in (("rich", rich_body), ("ordinary", ordinary)):
        body = copy.deepcopy(original)
        body.update(schema=3, assets=[])
        body.pop("custom_emoji")
        reject(
            f"v3-{kind}-emoji-rejected", body, "GRAMLAB_BRIDGE_EMOJI_REQUIRES_V4", bridge_version=3
        )
    for field in CATALOG[0]:
        body = snapshot()
        body["custom_emoji"][0].pop(field)
        reject(f"descriptor-missing-{field}", body, CUSTOM)
    for field in ASSETS[0]:
        body = snapshot()
        body["assets"][0].pop(field)
        reject(f"asset-missing-{field}", body, CUSTOM)
    bad_descriptors: list[tuple[str, str, Any]] = [
        ("id-number", "custom_emoji_id", 1),
        ("id-zero", "custom_emoji_id", "0"),
        ("id-negative", "custom_emoji_id", "-1"),
        ("id-leading-zero", "custom_emoji_id", "01"),
        ("id-plus", "custom_emoji_id", "+1"),
        ("id-overflow", "custom_emoji_id", "9223372036854775808"),
        ("id-space", "custom_emoji_id", " 1"),
        ("id-float", "custom_emoji_id", 1.0),
        ("id-bool", "custom_emoji_id", True),
        ("fallback-empty", "fallback", ""),
        ("fallback-long", "fallback", "🙂" * 33),
        ("fallback-null", "fallback", None),
        ("fallback-surrogate", "fallback", "\ud800"),
        ("free-string", "free", "true"),
        ("repaint-number", "needs_repainting", 1),
        ("main-missing", "main_asset_id", 99),
        ("thumb-missing", "thumbnail_asset_id", 99),
        ("thumb-video", "thumbnail_asset_id", 3),
        ("static-duration", "duration_ms", 1),
    ]
    for name, field, value in bad_descriptors:
        body = snapshot()
        body["custom_emoji"][0][field] = value
        reject(name, body, CUSTOM)
    for name, value in (("video-zero", 0), ("video-long", 3001), ("video-negative", -1)):
        body = snapshot()
        body["custom_emoji"][1]["duration_ms"] = value
        reject(name, body, INVALID if value < 0 else CUSTOM)
    for name, field, value in (
        ("duration-bool", "duration_ms", True),
        ("main-bool", "main_asset_id", True),
        ("thumb-string", "thumbnail_asset_id", "2"),
    ):
        body = snapshot()
        body["custom_emoji"][0][field] = value
        reject(name, body)
    for name, field in (("descriptor-extra", "custom_emoji"), ("asset-extra", "assets")):
        body = snapshot()
        body[field][0]["extra"] = 1
        reject(name, body)
    for name, field in (("catalog-duplicate", "custom_emoji"), ("assets-duplicate", "assets")):
        body = snapshot()
        body[field].insert(1, copy.deepcopy(body[field][0]))
        reject(name, body, CUSTOM)
    for name, field in (("catalog-unsorted", "custom_emoji"), ("assets-unsorted", "assets")):
        body = snapshot()
        body[field].reverse()
        reject(name, body, CUSTOM)
    for name, index, field, value in (
        ("main-not-square", 0, "width", 99),
        ("main-large", 0, "file_size", 524289),
        ("thumb-large", 1, "file_size", 131073),
        ("video-large", 2, "file_size", 262145),
        ("video-mime", 2, "mime_type", "video/mp4"),
        ("digest-case", 0, "sha256", "A" * 64),
        ("thumb-zero", 1, "height", 0),
    ):
        body = snapshot()
        body["assets"][index][field] = value
        reject(name, body, CUSTOM)
    thin = snapshot()
    thin["assets"][1].update(width=1, height=100)
    thin_documents = copy.deepcopy(documents)
    thin_documents["assets"] = thin["assets"]
    thin_native = native_documents()
    for doc in thin_native[:2]:
        doc["thumbs"][0].update(width=1, height=100)
    add(
        "thumbnail-independent-dimension-boundary",
        thin,
        native_output() | {"documents": thin_native},
        **(lookup | {"documents": thin_documents}),
    )
    for field in ("assets", "custom_emoji"):
        body = snapshot()
        body.pop(field)
        reject(f"snapshot-missing-{field}", body)
    missing_rich = copy.deepcopy(rich_body)
    missing_rich["custom_emoji"] = []
    reject("rich-missing-catalog", missing_rich, CUSTOM)
    for field, value in (
        ("custom_emoji_id", "99"),
        ("custom_emoji_id", 1),
        ("alternative_text", None),
        ("extra", True),
    ):
        body = copy.deepcopy(rich_body)
        body["messages"][0]["rich_message"]["blocks"][0]["text"][0][field] = value
        reject(
            f"rich-invalid-{field}-{value}", body, CUSTOM if field == "custom_emoji_id" else RICH
        )
    missing_alt = copy.deepcopy(rich_body)
    missing_alt["messages"][0]["rich_message"]["blocks"][0]["text"][0].pop("alternative_text")
    reject("rich-missing-alternative", missing_alt, RICH)
    bad_button = copy.deepcopy(rich_body)
    bad_button["messages"][0]["rich_message"]["blocks"][1]["buttons"][0]["text"] = {
        "type": "bold",
        "text": "x",
    }
    reject("button-does-not-admit-arbitrary-rich-node", bad_button, RICH)
    for name, offset, length in (
        ("split-start", 2, 1),
        ("split-end", 1, 1),
        ("past-end", 3, 2),
        ("empty", 1, 0),
    ):
        body = copy.deepcopy(ordinary)
        body["messages"][0]["entities"][1].update(offset=offset, length=length)
        reject(f"entity-{name}", body)
    for name, entity in (
        ("conflicting", {"type": "custom_emoji", "offset": 1, "length": 2, "custom_emoji_id": "1"}),
        ("contained", {"type": "custom_emoji", "offset": 0, "length": 4, "custom_emoji_id": "1"}),
        ("code", {"type": "code", "offset": 1, "length": 2}),
        ("contains-quote", {"type": "blockquote", "offset": 3, "length": 1}),
    ):
        body = copy.deepcopy(ordinary)
        if name == "contains-quote":
            body["messages"][0]["entities"] = [
                {"type": "custom_emoji", "offset": 0, "length": 4, "custom_emoji_id": "1"}
            ]
        body["messages"][0]["entities"].append(entity)
        reject(f"entity-overlap-{name}", body)
    # A failed reconnect cannot poison the previous response's immutable metadata.
    for name, field, value in (
        ("descriptor", "fallback", "changed"),
        ("asset", "sha256", "d" * 64),
    ):
        bad = snapshot()
        bad["custom_emoji" if name == "descriptor" else "assets"][0][field] = value
        add(
            f"reconnect-{name}-conflict-recovery",
            baseline,
            native_output() | {"rejected_reconnect": CUSTOM},
            mode="reconnect-recovery",
            snapshots=[baseline, bad, baseline],
        )
    # Exact lookup response sets; unknown and mixed requests have the same bounded failure.
    for name, ids in (("unknown", ["99"]), ("mixed", ["1", "99"])):
        reject(
            f"documents-{name}",
            baseline,
            "GRAMLAB_BRIDGE_HTTP_404",
            **(
                lookup
                | {
                    "requested_ids": ids,
                    "expected_ids": ids,
                    "document_status": 404,
                    "documents": {"schema": 4, "error": "document_unavailable"},
                }
            ),
        )
    for field, value in (("schema", 3), ("world_id", "other-world"), ("user_id", 2)):
        reject(
            f"documents-wrong-{field}",
            baseline,
            **(lookup | {"documents": documents | {field: value}}),
        )
    for field in ("assets", "custom_emoji"):
        bad = copy.deepcopy(documents)
        bad.pop(field)
        reject(f"documents-missing-{field}", baseline, **(lookup | {"documents": bad}))
    for name, field in (("omitted-document", "custom_emoji"), ("omitted-asset", "assets")):
        bad = copy.deepcopy(documents)
        bad[field].pop()
        reject(
            f"documents-{name}",
            baseline,
            INVALID if field == "custom_emoji" else CUSTOM,
            **(lookup | {"documents": bad}),
        )
    extra_asset = copy.deepcopy(documents)
    extra_asset["assets"].append(ASSETS[0] | {"asset_id": 4})
    reject("documents-excess-asset", baseline, **(lookup | {"documents": extra_asset}))
    reject(
        "documents-empty-request", baseline, **(lookup | {"requested_ids": [], "expected_ids": []})
    )
    reject(
        "documents-over-limit-request",
        baseline,
        **(lookup | {"requested_ids": ["1"] * 201, "expected_ids": ["1"]}),
    )
    # Fresh v4 live envelopes must carry their own dependencies even when the snapshot knew IDs.
    event_message = copy.deepcopy(ordinary["messages"][0])
    changes = {
        "schema": 4,
        "world_id": "custom-emoji-codec-world",
        "user_id": 1,
        "cursor": 1,
        "head": 1,
        "now": 1700000001,
        "users": USERS,
        "assets": ASSETS,
        "custom_emoji": CATALOG[1:],
        "changes": [
            {"position": 1, "type": "message.created", "revision": 1, "data": event_message}
        ],
    }
    event_output = native_output() | {
        "changes": {
            "cursor": 1,
            "head": 1,
            "now": 1700000001,
            "envelopes": [
                {
                    "seq": 1,
                    "date": 1700000001,
                    "users": NATIVE_USERS,
                    "updates": [
                        {
                            "kind": "TL_updateNewMessage",
                            "pts": 1,
                            "pts_count": 1,
                            "message": native_ordinary["messages"][0],
                        }
                    ],
                }
            ],
        }
    }
    add("v4-live-created", baseline, event_output, mode="changes", changes=changes)
    reject(
        "v4-live-excess-document-dependency",
        baseline,
        CUSTOM,
        mode="changes",
        changes=changes | {"custom_emoji": CATALOG},
    )
    reject(
        "v4-live-missing-response-local-documents",
        baseline,
        CUSTOM,
        mode="changes",
        changes=changes | {"custom_emoji": []},
    )
    callback = {
        "schema": 4,
        "world_id": "custom-emoji-codec-world",
        "user_id": 1,
        "users": USERS,
        "assets": ASSETS,
        "custom_emoji": CATALOG,
        "message_revision": 1,
        "callback": {
            "id": "emoji-callback",
            "user_id": 1,
            "chat_id": 1,
            "message": rich_body["messages"][0],
            "data": "mention-codec",
            "chat_instance": "local-chat",
            "answer": {"text": "Observed", "show_alert": False, "cache_time": 0},
        },
    }
    add(
        "v4-frozen-callback-rich-dependencies",
        baseline,
        native_output() | {"callback": {"text": "Observed", "show_alert": False, "cache_time": 0}},
        mode="callback",
        callback=callback,
    )
    reject(
        "v4-callback-missing-response-local-documents",
        baseline,
        CUSTOM,
        mode="callback",
        callback=callback | {"custom_emoji": []},
    )
    return authored, expected


def test_native_codec_projects_and_rejects_custom_emoji(tmp_path: Path) -> None:
    manifest = os.environ.get("GRAMLAB_ANDROID_RUNTIME_PROFILE")
    apk = os.environ.get("GRAMLAB_ANDROID_PROBE_APK")
    if manifest is None or apk is None or not os.access("/dev/kvm", os.R_OK | os.W_OK):
        pytest.skip("Requires the Android profile, reviewed custom emoji APK and accessible KVM")
    profile = RuntimeProfile.load(Path(manifest))
    toolchain = json.loads(Path("clients/android/toolchain.json").read_text())
    image_package = (
        f"system-images;android-{toolchain['sdk']['platform']};"
        f"{toolchain['runtime']['imageType']};{toolchain['runtime']['abi']}"
    )
    authored, expected = cases()
    (tmp_path / "custom-emoji-codec-cases.json").write_text(json.dumps(authored))
    shutil.copy2(apk, tmp_path / "client.apk")
    shutil.copytree(
        "src/gramlab", tmp_path / "gramlab", ignore=shutil.ignore_patterns("__pycache__")
    )
    (tmp_path / "emulator-profile.json").write_text(json.dumps(asdict(profile)))
    for name in ("emulator_process.py", "android_guest.py", "android_custom_emoji_codec.py"):
        shutil.copy2(Path("tests/probes") / name, tmp_path / name)
    result = Sandbox(profile).supervise(
        [
            profile.python,
            "/work/android_custom_emoji_codec.py",
            profile.executables["emulator"],
            profile.executables["adb"],
            profile.executables["avdmanager"],
            image_package,
        ],
        data=tmp_path,
        kvm=True,
        timeout=900,
    )
    (tmp_path / "custom-emoji-codec-result.json").write_text(result.stdout)
    (tmp_path / "custom-emoji-codec-stderr.log").write_text(result.stderr)
    assert result.returncode == 0, result.stderr
    full = json.loads(result.stdout)
    assert_isolation(full)
    observed = full["extra_probe"]["cases"]
    assert set(observed) == set(expected)
    for name, oracle in expected.items():
        assert observed[name] == {"returncode": 2 if "error" in oracle else 0, "result": oracle}, (
            name
        )
