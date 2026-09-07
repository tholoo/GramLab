"""Independent full native oracles for mention identity, envelopes and rejection."""

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

WIDE_ID = 9007199254740993
MAX_ID = 9223372036854775807
INVALID = "GRAMLAB_BRIDGE_INVALID_DATA"
INVALID_RICH = "GRAMLAB_BRIDGE_INVALID_RICH_MESSAGE"
LEGACY = "GRAMLAB_UNSUPPORTED: rich mentions require client bridge v3"
BASE_USERS = [
    {"id": 1, "is_bot": False, "first_name": "Sara", "language_code": "fa"},
    {"id": 2, "is_bot": True, "first_name": "Echo", "username": "gramlab_echo_bot"},
]
EXTRA_USERS = [
    {
        "id": WIDE_ID,
        "is_bot": False,
        "first_name": "آرمان",
        "username": "arman",
        "language_code": "fa",
    },
    {"id": MAX_ID, "is_bot": False, "first_name": "Maximum"},
]
# Literal native observations; no production rich mapper or User projection supplies these.
NATIVE_BASE = [
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
NATIVE_EXTRA = [
    {
        "id": 9007199254740993,
        "first_name": "آرمان",
        "self": False,
        "bot": False,
        "username": "arman",
        "language_code": "fa",
        "phone": None,
    },
    {
        "id": 9223372036854775807,
        "first_name": "Maximum",
        "self": False,
        "bot": False,
        "username": None,
        "language_code": None,
        "phone": None,
    },
]


def snapshot(rich: dict[str, Any] | None = None, *, extras: bool = False) -> dict[str, Any]:
    message: dict[str, Any] = {
        "id": 1,
        "chat_id": 1,
        "sender_id": 2,
        "date": 1700000000,
        "text": "" if rich is not None else "Transport baseline",
    }
    if rich is not None:
        message["rich_message"] = rich
    return copy.deepcopy(
        {
            "schema": 3,
            "world_id": "mentions-codec-world",
            "user_id": 1,
            "cursor": 20,
            "now": 1700000000,
            "users": BASE_USERS + (EXTRA_USERS if extras else []),
            "chats": [{"id": 1, "type": "private", "user_id": 1, "bot_id": 2}],
            "messages": [message],
            "message_position": 1,
            "sends": [],
            "assets": [],
            "message_revisions": [{"chat_id": 1, "message_id": 1, "revision": 1}],
        }
    )


def native_message(rich: dict[str, Any] | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "id": 1,
        "sender_id": 2,
        "recipient_id": 1,
        "out": False,
        "date": 1700000000,
        "text": "" if rich is not None else "Transport baseline",
    }
    if rich is not None:
        result["rich_message"] = copy.deepcopy(rich)
    return result


def native_output(rich: dict[str, Any] | None = None, *, extras: bool = False) -> dict[str, Any]:
    return copy.deepcopy(
        {
            "persona": 1,
            "cursor": 20,
            "now": 1700000000,
            "users": NATIVE_BASE + (NATIVE_EXTRA if extras else []),
            "dialogs": [{"peer_id": 2, "top_message": 1}],
            "messages": [native_message(rich)],
            "dialog_message_count": 1,
            "history_users": [
                {"peer_id": 2, "user_ids": [1, 2, WIDE_ID, MAX_ID] if extras else [1, 2]}
            ],
        }
    )


def mention(value: Any = WIDE_ID, text: Any = "آرمان / Arman") -> dict[str, Any]:
    return {"type": "text_mention", "text": text, "user_id": value}


def paragraph(text: Any) -> dict[str, Any]:
    return {"blocks": [{"type": "paragraph", "text": text}]}


def cases() -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    authored: list[dict[str, Any]] = []
    expected: dict[str, dict[str, Any]] = {}

    def add(name: str, body: dict[str, Any], oracle: dict[str, Any], **options: Any) -> None:
        authored.append({"name": name, "snapshot": copy.deepcopy(body), **copy.deepcopy(options)})
        expected[name] = copy.deepcopy(oracle)

    def reject(name: str, body: dict[str, Any], error: str = INVALID, **options: Any) -> None:
        add(name, body, {"error": error}, **options)

    baseline = snapshot()
    add("baseline-v3", baseline, native_output())
    input_rich = paragraph(
        [
            mention(2, "Echo"),
            " / ",
            mention(1, "سارا"),
            " / ",
            mention(WIDE_ID, ["آرمان ", {"type": "bold", "text": "Arman 👩‍💻"}]),
            " / ",
            mention(MAX_ID, ""),
            " / ",
            {"type": "italic", "text": mention(WIDE_ID, {"type": "underline", "text": "دوباره"})},
            " / ",
            mention(WIDE_ID, mention(1, "nested")),
        ]
    )
    input_rich["is_rtl"] = True
    expected_rich = {
        "blocks": [
            {
                "type": "paragraph",
                "text": [
                    {"type": "text_mention", "text": "Echo", "user_id": 2},
                    " / ",
                    {"type": "text_mention", "text": "سارا", "user_id": 1},
                    " / ",
                    {
                        "type": "text_mention",
                        "text": ["آرمان ", {"type": "bold", "text": "Arman 👩‍💻"}],
                        "user_id": 9007199254740993,
                    },
                    " / ",
                    {"type": "text_mention", "text": "", "user_id": 9223372036854775807},
                    " / ",
                    {
                        "type": "italic",
                        "text": {
                            "type": "text_mention",
                            "text": {"type": "underline", "text": "دوباره"},
                            "user_id": 9007199254740993,
                        },
                    },
                    " / ",
                    {
                        "type": "text_mention",
                        "text": {"type": "text_mention", "text": "nested", "user_id": 1},
                        "user_id": 9007199254740993,
                    },
                ],
            }
        ],
        "is_rtl": True,
    }
    full = snapshot(input_rich, extras=True)
    add(
        "recursive-repeated-self-recipient-third-party-64-bit",
        full,
        native_output(expected_rich, extras=True),
    )
    simple = snapshot(paragraph([mention(), mention(MAX_ID, "")]), extras=True)
    simple_native = {
        "blocks": [
            {
                "type": "paragraph",
                "text": [
                    {"type": "text_mention", "text": "آرمان / Arman", "user_id": 9007199254740993},
                    {"type": "text_mention", "text": "", "user_id": 9223372036854775807},
                ],
            }
        ]
    }
    add("third-party", simple, native_output(simple_native, extras=True))
    nested = {
        "blocks": [
            {
                "type": "details",
                "summary": mention(1, "Sara"),
                "is_open": True,
                "blocks": [
                    {
                        "type": "blockquote",
                        "blocks": [
                            {
                                "type": "paragraph",
                                "text": {
                                    "type": "url",
                                    "url": "https://example.invalid/",
                                    "text": mention(2, "Echo"),
                                },
                            }
                        ],
                        "credit": mention(1, ""),
                    }
                ],
            }
        ],
    }
    nested_native = {
        "blocks": [
            {
                "type": "details",
                "summary": {"type": "text_mention", "text": "Sara", "user_id": 1},
                "is_open": True,
                "blocks": [
                    {
                        "type": "blockquote",
                        "blocks": [
                            {
                                "type": "paragraph",
                                "text": {
                                    "type": "url",
                                    "url": "https://example.invalid/",
                                    "text": {"type": "text_mention", "text": "Echo", "user_id": 2},
                                },
                            }
                        ],
                        "credit": {"type": "text_mention", "text": "", "user_id": 1},
                    }
                ],
            }
        ]
    }
    add("nested-blocks-link-and-empty-credit", snapshot(nested), native_output(nested_native))

    for name, value in [
        ("zero", 0),
        ("negative", -1),
        ("boolean", True),
        ("float", 1.0),
        ("string", "1"),
        ("null", None),
        ("overflow", 2**63),
        ("huge", 2**100),
    ]:
        reject(f"mention-id-{name}", snapshot(paragraph(mention(value)), extras=True))
        changed = copy.deepcopy(simple)
        changed["users"][2]["id"] = value
        reject(f"dependency-id-{name}", changed)
    for field in ("user_id", "text"):
        node = mention()
        node.pop(field)
        reject(
            f"mention-missing-{field}",
            snapshot(paragraph(node), extras=True),
            INVALID if field == "user_id" else INVALID_RICH,
        )
    for name, node in [
        ("public-user-shape", {"type": "text_mention", "text": "spoof", "user": {"id": WIDE_ID}}),
        ("mixed-user-shape", mention() | {"user": {"id": WIDE_ID}}),
        ("unknown-field", mention() | {"extra": True}),
        ("empty-array-label", mention(text=[])),
        ("null-label", mention(text=None)),
        ("numeric-label", mention(text=1)),
    ]:
        reject(f"mention-{name}", snapshot(paragraph(node), extras=True), INVALID_RICH)
    reject("missing-mention-dependency", snapshot(paragraph(mention())), INVALID_RICH)
    reject("unknown-nested-mention", snapshot(paragraph(mention(1, mention(3)))), INVALID_RICH)
    for field in ("id", "first_name", "is_bot"):
        changed = copy.deepcopy(simple)
        changed["users"][2].pop(field)
        reject(f"dependency-missing-{field}", changed)
    for field, value in [
        ("first_name", 12),
        ("first_name", "  "),
        ("is_bot", 1),
        ("username", None),
        ("username", False),
        ("language_code", 7),
        ("unknown", "x"),
    ]:
        changed = copy.deepcopy(simple)
        changed["users"][2][field] = value
        reject(f"dependency-invalid-{field}-{str(value).strip() or 'empty'}", changed)
    for name, users in [
        ("duplicate", BASE_USERS + EXTRA_USERS + [EXTRA_USERS[0]]),
        (
            "conflicting-duplicate",
            [*BASE_USERS, EXTRA_USERS[0], EXTRA_USERS[0] | {"first_name": "spoof"}],
        ),
        ("unsorted", BASE_USERS + list(reversed(EXTRA_USERS))),
        ("missing-persona", [BASE_USERS[1], *EXTRA_USERS]),
        ("missing-bot", [BASE_USERS[0], *EXTRA_USERS]),
    ]:
        changed = copy.deepcopy(simple)
        changed["users"] = copy.deepcopy(users)
        reject(f"dependency-{name}", changed)

    legacy = copy.deepcopy(baseline)
    legacy["schema"] = 2
    legacy.pop("assets")
    legacy.pop("message_revisions")
    add("legacy-v2-baseline", legacy, native_output(), bridge_version=2)
    legacy_mention = copy.deepcopy(legacy)
    legacy_mention["messages"][0].update(text="", rich_message=paragraph(mention(1)))
    reject("legacy-v2-mention", legacy_mention, LEGACY, bridge_version=2)

    add(
        "reconnect-new-identity",
        baseline,
        native_output(simple_native, extras=True),
        mode="reconnect",
        snapshots=[baseline, simple],
    )
    add(
        "reconnect-removed-identity-not-republished",
        simple,
        native_output(),
        mode="reconnect",
        snapshots=[simple, baseline],
    )
    for field, value in [
        ("first_name", "Changed"),
        ("is_bot", True),
        ("username", "changed"),
        ("language_code", "en"),
    ]:
        changed = copy.deepcopy(simple)
        changed["users"][2][field] = value
        reject(
            f"reconnect-conflicting-{field}", simple, mode="reconnect", snapshots=[simple, changed]
        )
    removed_conflict = copy.deepcopy(simple)
    removed_conflict["users"][2]["first_name"] = "Changed after removal"
    reject(
        "removed-user-still-has-known-profile",
        simple,
        mode="reconnect-twice",
        snapshots=[simple, baseline, removed_conflict],
    )
    for mode in ("wrong-world", "wrong-persona"):
        reject(f"reconnect-{mode}-binding", simple, mode=mode)
    for field in ("username", "language_code"):
        changed = copy.deepcopy(simple)
        changed["users"][2].pop(field)
        reject(
            f"reconnect-missing-cached-{field}",
            simple,
            mode="reconnect",
            snapshots=[simple, changed],
        )
    changed = copy.deepcopy(simple)
    changed["users"][3]["username"] = ""
    reject("reconnect-absent-versus-empty", simple, mode="reconnect", snapshots=[simple, changed])
    missing_current = copy.deepcopy(simple)
    missing_current["users"] = copy.deepcopy(BASE_USERS)
    reject(
        "cached-user-cannot-replace-response-dependency",
        simple,
        INVALID_RICH,
        mode="reconnect",
        snapshots=[simple, missing_current],
    )
    poisoned = copy.deepcopy(simple)
    poisoned["users"][2]["first_name"] = "Rejected profile"
    poisoned["messages"][0]["rich_message"] = paragraph(mention(3))
    recovery = native_output(simple_native, extras=True) | {"rejected_reconnect": INVALID_RICH}
    add(
        "invalid-response-does-not-publish-identities",
        baseline,
        recovery,
        mode="reconnect-recovery",
        snapshots=[baseline, poisoned, simple],
    )

    changes: dict[str, Any] = {
        "schema": 3,
        "world_id": "mentions-codec-world",
        "user_id": 1,
        "cursor": 1,
        "head": 2,
        "now": 1700000001,
        "users": BASE_USERS + EXTRA_USERS,
        "assets": [],
        "changes": [
            {"position": 1, "type": "message.created", "revision": 1, "data": simple["messages"][0]}
        ],
    }
    native_update = {
        "kind": "TL_updateNewMessage",
        "pts": 1,
        "pts_count": 1,
        "message": native_message(simple_native),
    }
    change_oracle = {
        "cursor": 1,
        "head": 2,
        "now": 1700000001,
        "envelopes": [
            {
                "seq": 1,
                "date": 1700000001,
                "users": NATIVE_BASE + NATIVE_EXTRA,
                "updates": [native_update],
            }
        ],
    }
    add(
        "changes-first-disclosure-truncated",
        baseline,
        native_output() | {"changes": change_oracle},
        mode="changes",
        changes=changes,
    )
    add(
        "difference-first-disclosure-slice",
        baseline,
        native_output()
        | {
            "difference": {
                "kind": "TL_updates_differenceSlice",
                "users": NATIVE_BASE + NATIVE_EXTRA,
                "updates": [native_update],
                "pts": 1,
                "seq": 1,
                "date": 1700000001,
            }
        },
        mode="difference",
        changes=changes,
    )
    edited = copy.deepcopy(changes)
    edited["head"] = 1
    edited["changes"][0]["type"] = "message.edited"
    edited["changes"][0]["data"]["edit_date"] = 1700000001
    add(
        "difference-edit-complete",
        baseline,
        native_output()
        | {
            "difference": {
                "kind": "TL_updates_difference",
                "users": NATIVE_BASE + NATIVE_EXTRA,
                "updates": [native_update | {"kind": "TL_updateEditMessage"}],
                "pts": 1,
                "seq": 1,
                "date": 1700000001,
            }
        },
        mode="difference",
        changes=edited,
    )
    for name, field, value, error in [
        ("missing", "users", BASE_USERS, INVALID_RICH),
        ("duplicate", "users", BASE_USERS + EXTRA_USERS + [EXTRA_USERS[0]], INVALID),
        ("wrong-world", "world_id", "another-world", INVALID),
        ("wrong-persona", "user_id", 3, INVALID),
    ]:
        reject(
            f"changes-{name}-dependency",
            baseline,
            error,
            mode="changes",
            changes=changes | {field: value},
        )
    conflict_changes = copy.deepcopy(changes)
    conflict_changes["users"][2]["username"] = "spoof"
    reject("changes-conflicting-known-user", simple, mode="changes", changes=conflict_changes)
    # A callback carries the frozen mentioned body, even when current snapshot has removed it.
    callback: dict[str, Any] = {
        "schema": 3,
        "world_id": "mentions-codec-world",
        "user_id": 1,
        "users": BASE_USERS + EXTRA_USERS,
        "assets": [],
        "message_revision": 1,
        "callback": {
            "id": "callback1",
            "user_id": 1,
            "chat_id": 1,
            "message": simple["messages"][0],
            "data": "mention-codec",
            "chat_instance": "1",
            "answer": {"text": "Observed / دیده شد", "show_alert": True, "cache_time": 0},
        },
    }
    add(
        "callback-frozen-third-party-disclosure",
        baseline,
        native_output()
        | {"callback": {"text": "Observed / دیده شد", "show_alert": True, "cache_time": 0}},
        mode="callback",
        callback=callback,
    )
    reject(
        "callback-missing-dependency",
        baseline,
        INVALID_RICH,
        mode="callback",
        callback=callback | {"users": BASE_USERS},
    )
    conflict_callback = copy.deepcopy(callback)
    conflict_callback["users"][2]["language_code"] = "en"
    reject("callback-conflicting-known-user", simple, mode="callback", callback=conflict_callback)
    missing_answer = copy.deepcopy(callback)
    missing_answer["callback"].pop("answer")
    reject("callback-missing-answer", baseline, mode="callback", callback=missing_answer)
    legacy_changes = copy.deepcopy(changes)
    legacy_changes["schema"] = 2
    legacy_changes.pop("users")
    legacy_changes.pop("assets")
    legacy_changes["changes"][0].pop("revision")
    reject(
        "legacy-v2-changes-mention",
        legacy,
        LEGACY,
        mode="changes",
        bridge_version=2,
        changes=legacy_changes,
    )
    legacy_callback = copy.deepcopy(callback)
    legacy_callback["schema"] = 1
    for field in ("users", "assets", "message_revision"):
        legacy_callback.pop(field)
    reject(
        "legacy-v1-callback-mention",
        legacy,
        LEGACY,
        mode="callback",
        bridge_version=2,
        callback=legacy_callback,
    )
    return authored, expected


def test_native_codec_projects_mentions_and_validates_identity_envelopes(tmp_path: Path) -> None:
    manifest = os.environ.get("GRAMLAB_ANDROID_RUNTIME_PROFILE")
    apk = os.environ.get("GRAMLAB_ANDROID_PROBE_APK")
    if manifest is None or apk is None or not os.access("/dev/kvm", os.R_OK | os.W_OK):
        pytest.skip("Requires the Android profile, reviewed mention APK and accessible KVM")
    profile = RuntimeProfile.load(Path(manifest))
    toolchain = json.loads(Path("clients/android/toolchain.json").read_text())
    image_package = (
        f"system-images;android-{toolchain['sdk']['platform']};"
        f"{toolchain['runtime']['imageType']};{toolchain['runtime']['abi']}"
    )
    authored, expected = cases()
    (tmp_path / "mentions-codec-cases.json").write_text(json.dumps(authored))
    shutil.copy2(apk, tmp_path / "client.apk")
    shutil.copytree(
        "src/gramlab", tmp_path / "gramlab", ignore=shutil.ignore_patterns("__pycache__")
    )
    (tmp_path / "emulator-profile.json").write_text(json.dumps(asdict(profile)))
    for name in ("emulator_process.py", "android_guest.py", "android_rich_mentions_codec.py"):
        shutil.copy2(Path("tests/probes") / name, tmp_path / name)
    result = Sandbox(profile).supervise(
        [
            profile.python,
            "/work/android_rich_mentions_codec.py",
            profile.executables["emulator"],
            profile.executables["adb"],
            profile.executables["avdmanager"],
            image_package,
        ],
        data=tmp_path,
        kvm=True,
        timeout=600,
    )
    (tmp_path / "mentions-codec-result.json").write_text(result.stdout)
    (tmp_path / "mentions-codec-stderr.log").write_text(result.stderr)
    assert result.returncode == 0, result.stderr
    full = json.loads(result.stdout)
    assert_isolation(full)
    observed = full["extra_probe"]["cases"]
    assert set(observed) == set(expected)
    for name, oracle in expected.items():
        assert observed[name] == {"returncode": 2 if "error" in oracle else 0, "result": oracle}, (
            name
        )
