# Render synthetic groups in the Android client

Type: task
Status: complete
Work state: complete
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

Completed on 2026-09-13. The implementation keeps the public group ID negative while assigning a
non-colliding native channel ID above the snapshot's user IDs, projects complete users/chat/history
objects, and accepts native group callbacks and composer sends only for the selected member. The
composer's `inputPeerUserFromMessage` form is rejected unless its channel, persona and referenced
member-authored message all agree. Existing private-chat envelopes and their native path remain
covered by the original bridge acceptance test.

Red-first native runs retained the invalid-group projection, missing composer, rejected send shape,
and false Owner-role failures under `artifacts/group-android-native-05` through `-08`. Final run
`artifacts/group-android-native-11/test_group_example_renders_cal0/run` passes the real member
callback, bot edit, original composer send, bot restart, response and cold relaunch with exact
four-message history. All three original screenshots were inspected; they agree with semantics and
show no erroneous admin/Owner label. Android reports zero accounts and blocked IPv4/IPv6 egress.

Final evidence:

- `1619 passed` in the complete non-Android gate at 88.83% coverage; Ruff check/format and strict
  mypy over the changed Python surface pass.
- The focused group tests pass 78 selected non-Android cases. The final group codec, public native
  group scenario and unchanged private bridge scenario each pass against the same APK.
- Patch 0034 stages exactly three adapter/probe Java files with no fuzz or offsets, then builds
  offline successfully. APK SHA-256:
  `432168246376d98c3bd4eaebb791771401023946a5ef2c3f8f0c55291209c92f`; Android profile SHA-256:
  `fe878c649232bd571a1a64f075a79c11f5db19d30b6e3b04c9573307da83c68f`.
- Final screenshot SHA-256 values, in before/after/restarted order:
  `e7f471155bbc5e0921821ee34770362626efa53defa83159035f3ed8088f8ad9`,
  `8be1cda1e6fe420f48a6dc9fa462fa048ee442c3d4f147bc9b570b7fbf0ea056`, and
  `ecd4dedfde1a232730e34b8bb011b180c9db0193a58e2a8a3670d17fcd2f6926`.

Documentation-impact review updated the patch/build record, group contract, compatibility matrix,
scenario actor/capture references and retained-failure-trace behavior. Distribution remains out of
scope and blocked by the existing license/corresponding-source review.
