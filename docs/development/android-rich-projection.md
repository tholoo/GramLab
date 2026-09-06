# Native rich-message projection

Patch `0011-rich-message-projection.patch` adds a strict `GramLabRichMessage` decoder inside the
separately licensed Android adapter. It consumes the shared world's official-shaped
`message.rich_message` and creates the pinned client's original `TL_iv.RichMessage`. This is
structured content; it does not flatten blocks into ordinary message text. Snapshot history,
live message/edit events and difference recovery all use `GramLabBridge.message`.

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

Absent optional text uses native `textEmpty`; required empty text remains `textPlain("")`.
The core omits plain empty optional credit/caption/cell text, matching pinned server output;
formatting wrappers or concatenations containing empty text retain their structure. Table
cell alignment defaults to center for headers and left otherwise; vertical alignment defaults to
middle. Span presence bits survive serialization. No media objects are fabricated. Rich-only
messages must originate from the bot, have the world's empty ordinary `text`, and omit ordinary
`entities`. Existing plain-message handling is retained.

Unknown fields or types, wrong scalar types, invalid headings/alignment/spans, empty block lists,
empty table rows and empty RichText arrays fail explicitly. The shared implementation profile
bounds nesting to 32, traversed JSON values including object keys to 10,000, aggregate UTF-8 string
bytes to 65,536, and each explicit span to 100. Table expanded cell area (sum of colspan × rowspan, with
missing spans treated as one) cannot exceed 10,000; no later row may be wider than the first. Unpaired UTF-16 surrogates and control characters
other than newline/tab are rejected. These are local resource/support limits, not production
Telegram acceptance claims. HTML/Markdown parsing, automatic entity detection, links, media,
lists, buttons, custom emoji and draft parts remain outside this projection slice.

## Verification and integration

The full eleven-patch queue applies to a fresh export of the pinned source. The three changed
Java inputs compile against the pinned Android 36 SDK and the preceding verified client classes.
These checks establish patch applicability and Java type correctness, not runtime fidelity.
The coordinator owns APK build, actual guest codec execution, rendered screenshots, live edits
and restart verification before marking the task integrated.

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
