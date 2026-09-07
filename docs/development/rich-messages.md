# Structured rich messages

The independent world and local Bot API support a bounded block-based subset of Bot API 10.3.
`sendRichMessage` accepts `chat_id`, `rich_message` and the existing callback-only `reply_markup`.
`editMessageText` accepts `rich_message` instead of `text`/`entities`, plus the existing chat,
message and keyboard fields. Requests can use JSON or JSON-serialized objects in form fields.
Normal execution remains subject to [offline containment](offline-safety.md).

```json
{
  "chat_id": 1,
  "rich_message": {
    "skip_entity_detection": true,
    "is_rtl": true,
    "blocks": [
      {"type": "heading", "size": 2, "text": "نتیجه / Result"},
      {"type": "paragraph", "text": ["Hello ", {"type": "bold", "text": "دنیا"}]}
    ]
  }
}
```

Automatic entity detection is unimplemented: `skip_entity_detection` must explicitly be `true`.
Omission or `false` returns `GRAMLAB_UNSUPPORTED` before mutation. It is an input control, so the
stored and returned `rich_message` contains only `blocks` and optional true `is_rtl`. Ordinary
API `text` and `entities` are absent from rich-only responses. Internally the world retains
`text: ""` for existing consumers; it is never a flattened rendition of the blocks.

## Supported content

RichText values are UTF-8 strings, non-empty arrays of RichText, or objects with exactly `type`
and nested `text`, or the link and inline button shapes below. Supported wrappers are `bold`, `italic`, `underline`, `strikethrough`,
`spoiler`, `subscript`, `superscript`, `marked` and `code`. Arrays and nested wrappers retain
structure and multilingual content.

Structured links have `type` equal to `url`, `email_address` or `phone_number`, recursive `text`,
and a required string metadata field with the same name as the type. Metadata uses the existing
cleaner; empty and non-address strings are preserved. Captures match visible labels and exclude
destinations. [Core, real-bot, capture and focused original Android checks pass](rich-links-contract.md);
combined native acceptance remains in progress. This support does not enable navigation or automatic detection.

| Block type | Required fields besides `type` | Optional fields |
| --- | --- | --- |
| `paragraph`, `footer` | `text` | — |
| `heading` | `text`, integer `size` 1–6 | — |
| `pre` | `text` | string `language` |
| `divider` | — | — |
| `blockquote` | `blocks` | RichText `credit` |
| `expandable_blockquote`, `pullquote` | `text` | RichText `credit` |
| `table` | `cells` (array of rows of cells) | RichText `caption`; boolean `is_bordered`, `is_striped`, `is_compact` |
| `details` | RichText `summary`, `blocks` | boolean `is_open` |
| `list` | non-empty `items` array | — |
| `buttons` | array of 1–8 buttons | `align`: left, center or right |

Rich buttons use the [callback/copy/disabled contract](rich-buttons-contract.md). An inline
RichText button has `type: "button"` and a `button` object; row and inline buttons share plain
string/recursive-array labels, optional normalized style, and exactly one direct action field.
Labels and copied text are cleaned; callback bytes are preserved. Captures read labels and exclude
action metadata. Core/API and public simulation capture checks pass. The rebuilt normal APK passes focused native
codec and real-bot rendering/live RTL edit/cold-restart checks; the full Android gate is running. Public `tap_inline_button` still selects reply-markup cells.

List items require `blocks`, including an empty array, and accept optional boolean `has_checkbox`
and `is_checked`, signed 32-bit integer `value`, and label `type`. An absent or empty type means
unordered; nonempty types are `a`, `A`, `i`, `I` and `1`. Every item in one list must agree on
ordered versus unordered behavior. Ordered items may mix the five styles and arbitrary values.
Output adds a required `label`; ordered output also retains type/value, defaulting omitted input
value to zero. Positive alphabetic labels use spreadsheet letters; Roman values 1–3999 use
numerals; other values use decimal fallback. Unordered values normalize away. False checkbox
flags omit, and checked state without a checkbox normalizes away. Output labels must be removed
before resubmitting a message as input. See the [pinned list contract](rich-list-references.md).

Cells accept optional RichText `text` (absent means invisible), boolean `is_header`, integer
`colspan`/`rowspan`, `align` (`left`, `center`, `right`) and `valign` (`top`, `middle`, `bottom`).
Output includes both alignments; input defaults are center for headers and left otherwise, with
middle vertical alignment. Spans 0 and 1 normalize to omitted unit spans; larger spans persist.
False flags, empty preformatted languages and plain empty optional cell text/quote credit/table
caption are omitted. Empty required text and nested wrappers or arrays retain their values.

The local implementation bounds both input and canonical output to depth 32 (root depth 0),
10,000 JSON values including object keys, and 65,536 aggregate UTF-8 bytes of keys and strings.
Individual spans are capped at 100, and the sum of cell colspan × rowspan is capped at 10,000.
Later rows cannot be wider than the first row when summing normalized column spans. These are
explicit GramLab limits for the supported native table profile, not asserted Telegram
production limits. Blocks, table rows and RichText arrays must be non-empty, except list-item
block arrays, which may be empty. C0 controls other
than newline and tab are rejected as unsupported normalization; invalid UTF-8 is rejected.
Admitted plain RichText leaves and preformatted language undergo the pinned
[string cleaning](rich-text-cleaning.md), including tab-to-space, selected Unicode removals,
direction-marker normalization and per-leaf UTF-8 truncation. Optional plain-empty fields omit
after cleaning; required text and nested wrappers/arrays preserve their structure.
Unknown fields, unsupported wrappers/blocks and ambiguous text plus rich content fail explicitly.
HTML/Markdown parsing, automatic entities, ordinary link entities, navigation actions, media, custom emoji, streaming,
and the remaining rich inventory are still open. No network asset is fetched.

## State and evidence

The world validates complete content before starting a writer transaction. Only the chat's bot
can send rich messages or edit its own messages. Rich-to-rich, text-to-rich and rich-to-text edits
use the same durable message, journal and client-position path as ordinary messages. An unchanged
canonical edit fails without allocating an event. Existing SQLite message bodies carry the new
field without a schema migration. Snapshot, difference events and database reopening retain the
complete content; input and returned objects cannot mutate stored state after the operation.

The integrated list World/HTTP suite passes all 82 focused cases, including the Unicode property
test. Public captures find nested list fragments while preserving canonical history and rejecting
metadata or cross-fragment text targets. Focused native evidence covers the list codec, original
checkbox input without user mutation, bot edits, cold restart, nested inline targeting and
offscreen metadata-only ambiguity rejection. The list-inclusive combined Android gate passes all 38 cases without skips in 2,362.99 seconds.
The pre-normalization full core gate passes 326 tests at 80.52% coverage in 46 seconds; the
installed-wheel list scenario also passes complete semantic verification. The subsequent cleaning
correction passes 91 World/HTTP cases, the real-bot regression and the full 336-test core gate
at 80.67% coverage in 48.58 seconds. Its focused native case passes in 65.98 seconds, including
complete serialization, live RTL editing and cold restart; all three original captures were
inspected. That case uses the same APK and is separate from the preceding 38-case gate. The rebuilt
installed wheel passes the list scenario and direct World normalization verification. See the
[reusable list example](../../examples/rich_lists/README.md).

The dedicated tests exercise actual HTTP sends/edits through both request encodings, full responses,
atomic malformed/unsupported rejection, wrong bot/message ownership, normalization, plain/rich
transitions, world isolation and Unicode persistence. Run the focused checks inside the development
shell with the outer network guard:

```sh
unshare --user --map-root-user --net bash -eu -c \
  'ip link set lo up; .venv/bin/pytest tests/test_rich_messages.py tests/test_rich_bot_api.py'
```

At the earlier pre-list checkpoint, the real-bot scenario and [native projection checks](android-rich-projection.md)
pass, including original send/edit/restart captures. The full core gate passes 269 tests at
82.06% coverage. The combined Android regression gate passes all 29 tests without skips. Broader rich-content
rendering remains separate required evidence. The [public scenario example](scenario-rich-messages.md)
also passes in both modes with complete equivalent semantic outcomes and original captures.

## Contract provenance

The public [Bot API 10.3 specification](https://core.telegram.org/bots/api#inputrichmessage)
defines the input control fields; [RichMessage](https://core.telegram.org/bots/api#richmessage),
[RichText](https://core.telegram.org/bots/api#richtext) and
[input blocks](https://core.telegram.org/bots/api#inputrichblock) define the JSON vocabulary.
Reviewed on 2026-09-06, with independently authored implementation and synthetic test content.

The pinned official [server parser and serializer](https://github.com/tdlib/telegram-bot-api/blob/2efabc722e9493b9cac450233198d09e5cea0573/telegram-bot-api/Client.cpp)
(`get_input_rich_message`, `get_input_page_block`, `get_page_block_table_cell`, `JsonRichText`,
`JsonRichTableCell`, `JsonRichMessage`) establish detection defaults, table alignment defaults and
conditional output fields. The pinned [TDLib block validation](https://github.com/tdlib/td/blob/bc9c263e2bfee06aaab41e82db51a103376030bc/td/telegram/WebPageBlock.cpp)
establishes heading bounds and non-negative spans normalized to at least one;
[rich-message construction](https://github.com/tdlib/td/blob/bc9c263e2bfee06aaab41e82db51a103376030bc/td/telegram/RichMessage.cpp)
passes the detection setting into the outgoing representation. No upstream implementation was
copied into the independent core. Source inspection is not live Telegram conformance evidence.
The simulator deliberately rejects unsupported extra fields instead of reproducing the official
parser's field precedence or silently ignoring them.
