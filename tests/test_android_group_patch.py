"""Static boundaries for the GPL synthetic-group adapter patch."""

import re
from pathlib import Path


def test_group_patch_is_last_bounded_and_preserves_original_ui_sources() -> None:
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
    assert series[-4:] == [
        "0031-rich-auto-detection.patch",
        "0032-atomic-media-groups.patch",
        "0033-rich-navigation-buttons.patch",
        path.name,
    ]
    assert series.count(path.name) == 1
