# Upstream research and maintenance

The scaffold includes no upstream client code. These source observations were reviewed on
2026-09-05 against moving upstream pages; they are leads, not the pinned build manifest or proof
that the Android adapter works.

| Finding | Primary source | Consequence |
| --- | --- | --- |
| Official Android app source and native build requirements | [README](https://github.com/DrKLO/Telegram/blob/master/README.md) | Establish a reproducible build profile before UI claims |
| Java request serialization reaches native transport; incoming updates reach controllers | [ConnectionsManager](https://github.com/DrKLO/Telegram/blob/master/TMessagesProj/src/main/java/org/telegram/tgnet/ConnectionsManager.java) | Investigate a narrowly patched local boundary and initialization paths |
| Existing native request handshake trusts Telegram keys | [Handshake](https://github.com/DrKLO/Telegram/blob/master/TMessagesProj/jni/tgnet/Handshake.cpp) | Endpoint redirection is not an offline server implementation |
| Rich-message layout exists in source | [RichMessageLayout](https://github.com/DrKLO/Telegram/blob/master/TMessagesProj/src/main/java/org/telegram/messenger/RichMessageLayout.java) | Inspect block/RTL/media behavior and separately verify Bot API exposure |
| Message cells expose accessibility structures | [ChatMessageCell](https://github.com/DrKLO/Telegram/blob/master/TMessagesProj/src/main/java/org/telegram/ui/Cells/ChatMessageCell.java) | Test semantic button access before relying on pixel coordinates |
| Upstream Android instrumentation tests exist | [test build](https://github.com/DrKLO/Telegram/blob/master/TMessagesProj_AppTests/build.gradle) | Reuse conventions where appropriate; not proof of an offline chat mode |

## Acquisition and upgrades

1. Resolve a specific upstream commit/tag, license inventory, submodules and required toolchain.
2. Record source URLs, commit hashes, schema layer/Bot API version and local asset provenance in
   a committed manifest. Never put credentials or unverified version guesses in it.
3. Preserve the upstream checkout unchanged and maintain a reviewable patch queue, or propose an
   equivalent isolation strategy to the user. Do not commit giant source copies by default.
4. Prove an offline build/run, including initialization, media and background paths. Dummy upstream
   release/Firebase files are not a GramLab production-signing or account-provisioning strategy.
5. For upgrades, compare schema, server contracts, UI, assets and patch applicability. Run the
   agreed compatibility and isolation gates before moving the pin; retain prior evidence.

The Android build has native dependencies. Do not assume a pure JVM preview reproduces the actual
app's media/text behavior. Preserve runtime/font/display profiles with screenshot evidence.

## Host setup

At scaffold preparation, `adb` was available in the inspected execution environment, but emulator,
SDK manager, Java/Gradle commands and `/dev/kvm` were not visible in the checked paths. This is not
a complete host inventory or proof acceleration is unavailable outside that environment.
No SDK, emulator, Waydroid or system service was installed/enabled. Check the host afresh and ask
before host-level changes. Prefer a pinned emulator profile for reproducibility; assess Waydroid
as an alternative, not an assumed prerequisite.
