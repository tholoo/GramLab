"""Static boundaries for the GPL synthetic-group adapter patch."""

import re
from pathlib import Path


def test_group_patch_is_bounded_and_preserves_original_ui_sources() -> None:
    path = Path("clients/android/patches/0034-synthetic-group-chats.patch")
    patch = path.read_text()
    affected = re.findall(r"^diff --git a/(\S+) b/\1$", patch, re.MULTILINE)

    assert affected == [
        "TMessagesProj/src/main/java/org/telegram/gramlab/GramLabBridge.java",
        "TMessagesProj/src/main/java/org/telegram/gramlab/GramLabRuntime.java",
        "TMessagesProj_GramLab/src/main/java/org/telegram/gramlab/BridgeProbe.java",
    ]
    assert all("/org/telegram/ui/" not in name and "/res/" not in name for name in affected)
    for contract in (
        "channel.default_banned_rights = new TLRPC.TL_chatBannedRights();",
        "long channelId = maximumUserId - chat;",
        "TLRPC.TL_inputPeerUserFromMessage",
        "personaSendAs(state, dialogId, query.send_as)",
        "MessagesController.getInstance(0).putChats(current.dialogs.chats, false);",
        'trace("send_shape"',
        '"rejected_group_send_as"',
    ):
        assert contract in patch

    series = Path("clients/android/patches/series").read_text().splitlines()
    assert series[-2:] == [path.name, "0035-group-rich-button-input.patch"]
    assert series.count(path.name) == 1


def test_group_rich_input_patch_only_accepts_signed_chat_identity_at_the_probe_boundary() -> None:
    path = Path("clients/android/patches/0035-group-rich-button-input.patch")
    patch = path.read_text()
    affected = re.findall(r"^diff --git a/(\S+) b/\1$", patch, re.MULTILINE)

    assert affected == [
        "TMessagesProj/src/main/java/org/telegram/gramlab/GramLabButtonObserver.java"
    ]
    assert all("/org/telegram/ui/" not in name and "/res/" not in name for name in affected)
    assert patch.count('GramLabBridge.chatIdentifier(activation, "chat_id")') == 2
    assert 'GramLabBridge.chatIdentifier(candidate, "chat_id")' in patch
    assert 'positive(activation, "chat_id")' in patch
    assert '-                || positive(candidate, "chat_id")' in patch
    assert '+                || positive(candidate, "chat_id")' not in patch

    series = Path("clients/android/patches/series").read_text().splitlines()
    assert series[-1] == path.name
    assert series.count(path.name) == 1
