# Render synthetic groups in the Android client

Type: task
Status: active
Work state: claimed
Blocked by: 07-group-conversations.md

Project the existing generic synthetic-group model through the authenticated client bridge and the
pinned Telegram Android adapter. Preserve upstream group rendering and input behavior; do not
approximate a group with a private chat or add consumer-specific policy to GramLab.

## Acceptance

- A bridge snapshot for a selected group member carries the group identity, title, memberships,
  visible users, and history without changing existing private-chat envelopes.
- The pinned Android adapter creates the correct native group peer/dialog objects and opens the
  negative group chat ID for the selected synthetic member.
- A real contained bot can send and edit a group message; the original Android UI shows the group
  title and message, and a distinct member's native callback reaches the originating bot.
- Restarting the bot and relaunching the client preserves the same group identity and visible
  history without replaying an uncertain tap.
- An unrelated persona, unrelated bot, malformed group envelope, and unsupported bridge version
  fail explicitly at public boundaries.
- The Android run remains account-free and offline, retains inspected original screenshots plus
  semantic/callback/lifecycle evidence, and records the immutable APK/profile identifiers.
- Focused red/green tests, strict typing, patch staging/build checks, the applicable non-Android
  gate, and the serialized native acceptance case pass before native group support is claimed.

## Public seams

The tests use the versioned client HTTP bridge, the staged GPL Android adapter, and the public
Android runner/capture/input interfaces. World database rows, Java private helpers, and direct UI
injection are not acceptance seams.

## Comments

Claimed on 2026-09-13 after the generic simulation-only group capability reached `main`. The user
approved the GPL Android patch, local APK build, and isolated emulator run. Runtime network,
identity, licensing, and upstream-source boundaries remain unchanged.
