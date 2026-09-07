# Native rich-message projection

Patch `0011-rich-message-projection.patch` adds a strict `GramLabRichMessage` decoder inside the
separately licensed Android adapter. It consumes the shared world's official-shaped
`message.rich_message` and creates the pinned client's original `TL_iv.RichMessage`. This is
structured content; it does not flatten blocks into ordinary message text. Snapshot history,
live message/edit events and difference recovery all use `GramLabBridge.message`.
Patch `0012-rich-list-projection.patch` extends the decoder and native observation with recursive
ordered/unordered lists, canonical labels and bot-owned checkbox state.

The projection is based on Telegram Android revision
`62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c`:
[`TL_iv`](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/tgnet/tl/TL_iv.java),
[`TLRPC`](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/tgnet/TLRPC.java)
and the original
[`RichMessageLayout`](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/messenger/RichMessageLayout.java).
These source and renderer files are unchanged by this patch. The independent Python world does
not import native types. The patch retains the [client license boundary](licensing.md).

## Exact mapping

| Semantic content | Native object and fields |
| --- | --- |
| Rich message `blocks`, `is_rtl` | `RichMessage.blocks`, `rtl`; message `flags2` bit 13 |
| String / array | `textPlain` / recursively populated `textConcat` |
| Bold, italic, underline, strikethrough | `textBold`, `textItalic`, `textUnderline`, `textStrike` |
| Spoiler, subscript, superscript, marked, code | `textSpoiler`, `textSubscript`, `textSuperscript`, `textMarked`, `textFixed` |
| Paragraph / footer | `pageBlockParagraph` / `pageBlockFooter` |
| Heading with size 1–6 | `pageBlockHeading1` through `pageBlockHeading6` |
| Preformatted `text`, optional `language` | `pageBlockPreformatted.text`, `language` |
| Divider | `pageBlockDivider` |
| Blockquote `blocks`, optional `credit` | `pageBlockBlockquoteBlocks.blocks`, `caption` |
| Expandable blockquote `text`, optional `credit` | `pageBlockBlockquote.text`, `caption`, `collapsed=true` |
| Pullquote `text`, optional `credit` | `pageBlockPullquote.text`, `caption` |
| Details `summary`, `blocks`, `is_open` | `pageBlockDetails.title`, `blocks`, `open` |
| Table `cells`, optional `caption`, border/stripe/compact flags | `pageBlockTable.rows`, `title`, `bordered`, `striped`, `compact` |
| Cell text, header, spans and horizontal/vertical alignment | `pageTableCell` with text/span presence bits and alignment flags |
| Unordered list and recursive item blocks | `pageBlockList`, `TL_pageListItemBlocks` |
| Ordered list and recursive item blocks | `pageBlockOrderedList`, `TL_pageListOrderedItemBlocks`; item label/type/value presence flags |
| Item checkbox and checked state | Original item `checkbox` and `checked` flags |

Absent optional text uses native `textEmpty`; required empty text remains `textPlain("")`.
The core omits plain empty optional credit/caption/cell text, matching pinned server output;
formatting wrappers or concatenations containing empty text retain their structure. Table
cell alignment defaults to center for headers and left otherwise; vertical alignment defaults to
middle. Span presence bits survive serialization. No media objects are fabricated. Rich-only
messages must originate from the bot, have the world's empty ordinary `text`, and omit ordinary
`entities`. Existing plain-message handling is retained.

Unknown fields or types, wrong scalar types, invalid headings/alignment/spans, empty block lists
(except list-item blocks),
empty table rows and empty RichText arrays fail explicitly. The shared implementation profile
bounds nesting to 32, traversed JSON values including object keys to 10,000, aggregate UTF-8 string
bytes to 65,536, and each explicit span to 100. Table expanded cell area (sum of colspan × rowspan, with
missing spans treated as one) cannot exceed 10,000; no later row may be wider than the first. Unpaired UTF-16 surrogates and control characters
other than newline/tab are rejected. These are local resource/support limits, not production
Telegram acceptance claims. HTML/Markdown parsing, automatic entity detection, links, media,
buttons, custom emoji and draft parts remain outside this projection slice.

## Verification and integration

The current twelve-patch queue applies to a fresh pinned export, preserving all 6,666 original
UI/resource files. The list integration changes two Java inputs; its incremental offline APK
build completes in 2 minutes 31 seconds. Actual native serialization preserves the complete list
catalog, and 42 malformed list/budget cases reject explicitly. Empty item block vectors survive
the codec although the original renderer skips those items.

Focused original captures show nested checkboxes, wrapped Persian/English text, all five ordered
label styles, RTL edits and cold restart. A normal tap on a bot-owned checkbox opens the original
message menu without changing world history/events or checkbox state. A real bot subsequently
flips both states; the live view and cold restart retain its complete edit. Ordered labels can
overlap checkboxes in the pinned renderer; this observed quirk is preserved. The reusable
[list scene](../../examples/rich_lists/README.md) uses nested unordered checkboxes so its ordered
labels remain visible. Public list inline input has focused callback/edit and offscreen
metadata-only ambiguity-rejection evidence. The list-inclusive combined Android gate passes all 38 cases without skips in 2,362.99 seconds.
The subsequent world-side string-cleaning correction passes a separate focused native case in
65.98 seconds with no APK change. It compares complete serialized messages, verifies live RTL
editing and cold restart, and retains successful launch status, zero accounts and guest isolation.
All three original PNGs were inspected: cleaned heading/paragraph/pre/table content appears, and
the RTL edit survives restart. This is focused acceptance after the preceding 38-case gate, not a
rerun of that full gate. A prior concurrent startup timeout remains an unresolved scheduling issue,
recorded in the handoff.

The following eleven-patch evidence is the earlier pre-list checkpoint.
The full eleven-patch queue applies to a fresh export of the pinned source. The three changed
Java inputs compile against the pinned Android 36 SDK and the preceding verified client classes.
The integrated offline APK builds successfully. The real-bot native test passes in 72 seconds:
original screenshots show a bilingual heading, formatted paragraph, bordered table and nested
quotation, followed by a live RTL edit and cold restart. Visual inspection confirms all three
captures. Actual native serialization also preserves the complete ten-block catalog, and both
malformed table fixtures fail with `GRAMLAB_BRIDGE_INVALID_RICH_MESSAGE`. Catalog serialization
is not evidence that every catalog block has been visually reviewed. The combined Android
regression gate now passes all 29 tests with no skips in 1,630.71 seconds. Existing formatting,
callbacks, composer input and controlled recovery boundaries retain passing evidence.

`BridgeProbe` observes `rich_message` only after actual native message serialization and
`TLdeserialize`. Its recursive observer reads native classes, flags, text, rows and nested blocks;
it never returns the input JSON. The observation uses the canonical official-shaped object:
false flags, absent/plain empty optional text, empty preformatted language and spans of one are omitted;
cell `align` and `valign` are always present. Ordinary-message observations are unchanged.

The original [comprehensive fixture](../../clients/android/fixtures/rich-message.json) covers all
ten block types, six heading sizes, nine recursive wrappers, Persian/English text, a ZWNJ, an
emoji sequence, RTL, nested quotation/details, absent optional text and required empty text, all
alignment directions and cell span flags. It is synthetic GramLab-authored data under the root
MIT license. Stage this canonical object as a bot rich message in a contained world and compare
its complete structure with `messages[*].rich_message` in `BridgeProbe` output. Add malformed
counterparts at the bridge boundary and retain the existing plain-message codec assertions.

Use the [parallel workflow](parallel-work.md) build/guest locks and
[offline guard](offline-safety.md). A focused `javac` check can reuse read-only compiled client
classes while writing output to the worker's ignored directory; full builds and guests need
separate writable state. Do not rebuild the entire application independently in every worker.

## Pinned table constraint

`RichMessageLayout.RichTableBlock` derives the table column count from the first row. The pinned
[`TableLayout`](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/ui/Components/TableLayout.java)
uses spans for axis allocations and rejects a column count below the largest child index.
A wider later row can therefore throw during original rendering. The shared local profile rejects
that shape and bounds expanded area before mutation/projection. This does not claim Telegram
rejects the same inputs, and does not replace the original layout. Broader table semantics remain
a recorded compatibility gap. The independent
[negative fixtures](../../clients/android/fixtures/rich-message-invalid-tables.json) capture these
two specific boundaries for the coordinator's native codec checks.

## Reproduce the integrated scenario

After preparing the approved APK and Android environment, set `GRAMLAB_ANDROID_PROBE_APK` to
its locally discovered path and run the focused test through the shared guest lock:

```sh
tools/worktree lock android-gate tools/dev android --offline --command \
  unshare --user --map-root-user --net bash -eu -c \
  'ip link set lo up; .venv/bin/pytest tests/test_android_rich_messages.py --basetemp=artifacts/rich-native'
```

The test retains `initial.png`, `edited.png`, `restarted.png`, UI hierarchies, native codec JSON,
redacted traces, `rich-result.json` and a self-contained `report.html` beneath its test directory.
The baseline profile is the pinned client on AOSP API 36, 320 × 640 at 160 dpi, with software GPU
and synthetic identities. This does not establish the [effects-enabled profile](android-effects-profile.md).

One measured run spent 4.34 seconds installing, 4.04 and 3.45 seconds on cold app launches,
3.20–5.06 seconds per capture, and 1.51–2.14 seconds per codec observation. These are individual
observations, not latency percentiles. Sharing one dedicated guest across the related phases
avoids repeated guest startup while preserving separate world and malformed-input fixtures.
The initial full core gate passes 269 tests at 82.06% coverage. The subsequent
[public rich capture implementation](scenario-rich-messages.md) passes its simulation checks and
272-test core gate; its separate Android consumer integration also passes in 65 seconds with
matching semantic evidence and three visually inspected original captures. Subsequent rich inline
targeting has focused evidence recorded in the [input contract](scenario-input.md).
The first generated rich report mislabeled seconds as milliseconds; the
report adapter now converts those measurements, and the separately corrected retained report
passes browser inspection at desktop/mobile widths with all three images loaded, no overflow
and no external resources.
