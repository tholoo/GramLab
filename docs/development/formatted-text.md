# Explicit formatting in the actual Android chat

The local Bot API accepts nine explicit non-link formatting types in ordinary private text
messages: `bold`, `italic`, `underline`, `strikethrough`, `spoiler`, `code`, `pre`, `blockquote`
and `expandable_blockquote`. A real bot can change only the formatting while keeping the text
unchanged. The actual Telegram Android message cell renders that edit and retains it after a
cold restart. This extends the [callback/edit adapter](android-callbacks.md); the separate
RichMessage block API, media and custom-emoji documents remain planned.

## Contract and sources

The independent Python implementation follows the official
[MessageEntity contract](https://core.telegram.org/bots/api#messageentity) and
[formatting nesting rules](https://core.telegram.org/bots/api#formatting-options), consulted on
2026-09-06. Offsets and lengths use UTF-16 code units. Valid ranges must fit the message and must
not split a surrogate pair. Ranges may be disjoint or wholly nested; code/pre cannot overlap
other formatting, and quotes cannot nest even with intervening emphasis. `pre` accepts an
optional language string. Unknown types/fields and invalid ranges fail before state changes.

`World.send_message` and `World.edit_message` accept `entities`; `sendMessage`, `editMessageText`
and delivered `getUpdates` messages expose the same semantic records. Persistence, authenticated
client snapshots and ordered events retain them. Entity lists are sorted by offset, descending
length and type, with exact duplicates removed and empty lists omitted. A canonical duplicate
edit fails with `MESSAGE_NOT_MODIFIED`. Omitting entities from a text edit removes prior formatting.
The existing JSON message storage needs no schema migration.

Python owns the semantic format without importing client schemas. The sixth
[GPL patch](../../clients/android/patches/README.md) maps it to pinned Java TL classes, preserving
pre language and the expandable quote's collapsed flag. Snapshot/history and live edits use the
same conversion. Java also validates fields, ranges and nesting before handing data to the
existing controller. This patch changes only `GramLabBridge` and its serializer probe; it does
not change message cells, fonts, resources or native code.

## Evidence and limits

The [original fixture](../../tests/fixtures/formatting.json) contains Persian/English text, a
leading supplementary-plane emoji and all nine types, with independently authored UTF-16 ranges.
It introduces no downloaded source or assets. A separate
[stdlib bot](../../tests/fixtures/formatted_bot.py) receives one virtual-user message over actual
HTTP, replies with plain text, then edits only the formatting and acknowledges delivery. The
[shared scenario](../../tests/probes/formatted_round_trip.py) runs in simulation-only and Android
modes with the same exact expected HTTP results, history and empty pending queue.

The Android test captures plain, formatted and restarted screens, waits for the live event to
apply, verifies both messages, checks cold launches and confirms zero Android accounts. Manual
inspection shows emphasis, underline, strike, spoiler masking, a language-labeled highlighted
code block and quote bars. The four-line expandable quote preserves its TL flag; an expansion
gesture and long-quote truncation are not established by this fixture. A separate guest test
round-trips all nine types through the real pinned TL serializer and asserts their exact ranges,
language and collapsed state. UI XML alone is not used as proof of visual formatting.

The profile remains Telegram Android 12.10.1 at
`62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c`, TL layer 229, AOSP API 36 default x86_64 revision 2,
Emulator 37.1.11 and `swangle` software graphics, with the display/font/locale settings in the
[callback profile](android-callbacks.md#profile-and-boundary). Bot and emulator retain separate
component files/processes within the independently isolated run network. No external conformance
service, real account or Telegram DC is used. Guest clocks, animation and spoiler noise are not
deterministic world state or an approved pixel-golden baseline.

Behavioral regressions first showed `sendMessage`/`editMessageText` rejecting entities and the
five-patch Android APK rejecting the extended schema. Additional failing cases exposed missing
formatting types and a nested quote accepted through an intervening bold span. Each corresponding
public-boundary test passes after the change. Unicode property tests use independent UTF-16
encoding over Persian, emoji, combining marks and joiners; invalid requests leave history, events
and message ID allocation unchanged.

The full core gate passes 65 tests at 91.56% statement coverage; all twelve Android tests pass,
including guest networking, native rejection, startup identity checks and callback recovery.
Python lint/format and strict typing, Nix/direnv/workflow, local links and public-tree privacy
checks pass. The final formatting and callback restart screenshots were inspected.
Fresh six-patch preparation
matches the built Java inputs and strict dependency metadata, preserving all 6,666 checked
upstream UI/resource files byte-for-byte. The contained cached-dependency build passes strict
offline verification. APK v1/v2 signatures verify; the restricted manifest and x86_64 native
libraries were inspected. Artifact hashes, screenshots, logs and process details remain ignored.

Parse modes, link/mention/date-time entities, automatic entity recognition, custom emoji,
captions/media, rich-message blocks and broader cache recovery remain unsupported. This is local
model and renderer evidence, not a complete Telegram conformance claim. Runtime quotas,
per-component control-port restrictions and remaining media/WebView network surfaces are still
tracked separately.

## Reproduction

Use the [contained build procedure](android-build.md) with the complete patch queue and set
`GRAMLAB_ANDROID_PROBE_APK` to the resulting local APK. Use fresh artifact directories:

```sh
nix develop --command unshare --user --map-root-user --net bash -eu -c '
  ip link set lo up
  test ! -e artifacts/formatting-core
  .venv/bin/pytest tests/test_entities.py --basetemp=artifacts/formatting-core
'
nix develop .#android --command unshare --user --map-root-user --net bash -eu -c '
  ip link set lo up
  test ! -e artifacts/formatting-android
  .venv/bin/pytest tests/test_android_entities.py --basetemp=artifacts/formatting-android
'
```

The renderer test retains `plain.png`, `formatted.png`, `restarted.png`, UI XML and guarded
diagnostics in its ignored test directory. Run the full Android gate with `-m android` and the
separate core/coverage and static gates from [CONTRIBUTING.md](../../CONTRIBUTING.md). Keep all
host observations and generated artifacts out of the public tree.
