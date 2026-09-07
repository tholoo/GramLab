# Ordinary HTML formatting source contract

Research checkpoint against Bot API server
`2efabc722e9493b9cac450233198d09e5cea0573` and TDLib
`bc9c263e2bfee06aaab41e82db51a103376030bc`. This is source research, not
implementation or live-service acceptance: no server, bot, account or Telegram DC was used.
Parser examples below are independently derived from the pinned code and are not claimed as
complete `sendMessage` responses.

## Request path and precedence

Ordinary `sendMessage` and `editMessageText` share `get_input_message_text`; both read `text`,
`parse_mode` and `entities` through that path
([server source](https://github.com/tdlib/telegram-bot-api/blob/2efabc722e9493b9cac450233198d09e5cea0573/telegram-bot-api/Client.cpp#L11317-L11330),
[send entry point](https://github.com/tdlib/telegram-bot-api/blob/2efabc722e9493b9cac450233198d09e5cea0573/telegram-bot-api/Client.cpp#L13105-L13111),
[edit entry point](https://github.com/tdlib/telegram-bot-api/blob/2efabc722e9493b9cac450233198d09e5cea0573/telegram-bot-api/Client.cpp#L13711-L13718)).
The server rejects more than 32 KiB of raw UTF-8 bytes before parsing, lowercases `parse_mode`,
and recognizes `markdown`, `markdownv2`, `html` and `none`. A nonempty text with a recognized
mode other than `none` is parsed immediately; the function returns the parser result without
reading `entities`. Thus explicit entities are ignored, rather than merged, when nonempty HTML
parse mode is active. Empty text bypasses parsing but is rejected by the input-message layer
([selection](https://github.com/tdlib/telegram-bot-api/blob/2efabc722e9493b9cac450233198d09e5cea0573/telegram-bot-api/Client.cpp#L11241-L11280),
[empty check](https://github.com/tdlib/telegram-bot-api/blob/2efabc722e9493b9cac450233198d09e5cea0573/telegram-bot-api/Client.cpp#L11322-L11330)).

The server calls TDLib's synchronous `parseTextEntities`. That operation first requires valid
UTF-8, caps input at 65,536 Unicode code points, dispatches to `parse_html`, and wraps parser
errors as `Can't parse entities: ...`
([TDLib dispatcher](https://github.com/tdlib/td/blob/bc9c263e2bfee06aaab41e82db51a103376030bc/td/telegram/SynchronousRequests.cpp#L149-L185)).
The server's earlier 32 KiB check is the effective parser-input bound on this route.

## Pinned HTML parser

Tag names are case-insensitive. The pinned parser accepts:

| HTML forms | Generated Bot API entity |
| --- | --- |
| `b`, `strong` | `bold` |
| `i`, `em` | `italic` |
| `u`, `ins` | `underline` |
| `s`, `strike`, `del` | `strikethrough` |
| `tg-spoiler`, `span class="tg-spoiler"` | `spoiler` |
| `code` | `code` |
| `pre`, or `pre` containing a same-range `code class="language-X"` | `pre`, optionally with `language: X` |
| `blockquote`, `blockquote expandable` | `blockquote`, `expandable_blockquote` |
| `a href="..."` | `text_link` or `text_mention` for a recognized user link |
| `tg-emoji emoji-id="..."` | `custom_emoji` |
| `tg-time unix="..." format="..."` | `date_time` when `unix` is positive |

The accepted tag list, attribute scanner and projections are all in the pinned
[HTML parser](https://github.com/tdlib/td/blob/bc9c263e2bfee06aaab41e82db51a103376030bc/td/telegram/MessageEntity.cpp#L3289-L3576).
The Bot API serializer maps TDLib's `PreCode` back to `type: "pre"` plus `language`, and exposes
the link, mention, custom-emoji and date-time fields
([serializer](https://github.com/tdlib/telegram-bot-api/blob/2efabc722e9493b9cac450233198d09e5cea0573/telegram-bot-api/Client.cpp#L561-L617)).
The moving official [formatting documentation](https://core.telegram.org/bots/api#formatting-options)
documents the public syntax; it is a useful current reference but is not the immutable pin.

Attribute names are case-sensitive in this parser. Unquoted attribute values are lowercased;
quoted values retain case. Unknown attributes are scanned and ignored. Relevant values are
recognized only for lowercase `href`, `class`, `emoji-id`, `expandable`, `unix`, and `format`.
`span` is rejected unless its recognized class value is exactly `tg-spoiler`. A bare
`blockquote expandable` is accepted. A missing/invalid custom emoji ID is rejected; a nonpositive
`tg-time` timestamp produces no entity. Link targets are checked later and can disappear or fail
validation, so source inspection alone does not establish acceptance of an arbitrary URL/user.

Text content decodes decimal or lowercase-`x` hexadecimal numeric references, plus the four
named references `&lt;`, `&gt;`, `&amp;`, and `&quot;`. Their semicolon is optional. Numeric zero,
values greater than or equal to `0x10ffff`, overlong references, unknown names, uppercase-`X`,
and unsupported named references remain literal. This means `&#x10ffff;` is literal too, despite
being the highest Unicode scalar value. Decoded unmatched UTF-16 surrogate code units cause an
invalid-Unicode error. Literal `<` starts a tag and must therefore be escaped when it is text
([decoder](https://github.com/tdlib/td/blob/bc9c263e2bfee06aaab41e82db51a103376030bc/td/telegram/MessageEntity.cpp#L3240-L3287),
[UTF-8 recheck](https://github.com/tdlib/td/blob/bc9c263e2bfee06aaab41e82db51a103376030bc/td/telegram/MessageEntity.cpp#L3567-L3576)).

The parser uses a strict stack: unknown start tags, unclosed starts, unexpected ends, mismatched
ends, and an unclosed entity at end of input are errors. Empty tags produce no entity. Supported
tags may be syntactically nested, including combinations later disallowed as message entities.
Offsets and lengths are generated in UTF-16 code units as decoded text is written; markup bytes
do not count. Entities are then sorted by TDLib's entity ordering.

## Independently derived parser fixtures

These exact pairs exercise deterministic `parseTextEntities` output before send-time cleanup:

```text
HTML: A&amp;<b>😀é</b>Z
text: A&😀éZ
entities: [{"type":"bold","offset":2,"length":3}]

HTML: <strong>A<i>B</i>C</strong>
text: ABC
entities: [
  {"type":"bold","offset":0,"length":3},
  {"type":"italic","offset":1,"length":1}
]

HTML: <pre><code class="language-python">x&lt;y</code></pre>
text: x<y
entities: [{"type":"pre","offset":0,"length":3,"language":"python"}]

HTML: <blockquote expandable>Q😀</blockquote>
text: Q😀
entities: [{"type":"expandable_blockquote","offset":0,"length":3}]
```

Useful parser rejection fixtures are `<unknown>x</unknown>`, `<b>x</i>`, `<b>x`, `</b>`,
`<span class="other">x</span>`, `<tg-emoji emoji-id="0">x</tg-emoji>`, and a numeric
reference that decodes to one unmatched surrogate. Literal/escaping boundaries include
`&apos;` and `&#x10ffff;` (left literal), `&lt` (decoded without a semicolon), and `<b></b>`
(empty text and no entity at parser output; ordinary message acceptance is a later question).

## Post-parse normalization and limits

Parser output becomes TDLib `inputMessageText`, whose send conversion calls
`get_formatted_text`
([input conversion](https://github.com/tdlib/td/blob/bc9c263e2bfee06aaab41e82db51a103376030bc/td/telegram/InputMessageText.cpp#L28-L66)).
That path validates entity payloads, runs `fix_formatted_text`, and removes entities not allowed
for the dialog
([conversion](https://github.com/tdlib/td/blob/bc9c263e2bfee06aaab41e82db51a103376030bc/td/telegram/MessageEntity.cpp#L4649-L4680)).
This is distinct from `parse_html`.

The fixer sorts and repairs intersections. Bold, italic, underline, strikethrough and spoiler are
"splittable". TDLib separately classifies links, mentions and custom emoji as continuous;
code, pre and date-time as pre-like; and quotes as blockquotes
([classification](https://github.com/tdlib/td/blob/bc9c263e2bfee06aaab41e82db51a103376030bc/td/telegram/MessageEntity.cpp#L1495-L1543)).
The repair implementation gathers all nonsplittable, nonquote entities into a local
`continuous_entities` vector, but that variable is broader than the semantic continuous mask.
It can merge/split style ranges or discard portions that intersect a pre-like entity, rather
than reject the parser's nesting outright
([repair](https://github.com/tdlib/td/blob/bc9c263e2bfee06aaab41e82db51a103376030bc/td/telegram/MessageEntity.cpp#L4385-L4475)).
For example, `<b><code>x</code></b>` yields overlapping `bold` and `code` from the parser, while
the fixer treats the code range as unsplittable and removes the bold portion within it. Feeding
raw parser entities into GramLab's current validator would instead reject that overlap.

The same fixer replaces C0 controls other than LF and CR with spaces, removes CR, removes selected
Unicode line/direction marks and combining marks U+030A, U+0333 and U+033F, and adjusts UTF-16 entity
ranges. Unless trimming is skipped, it removes trailing spaces/newlines and leading spaces/newlines
that precede the first entity. It rejects invalid UTF-8 and ranges that split UTF-16 symbols
([cleaning](https://github.com/tdlib/td/blob/bc9c263e2bfee06aaab41e82db51a103376030bc/td/telegram/MessageEntity.cpp#L4124-L4266),
[trim and repair](https://github.com/tdlib/td/blob/bc9c263e2bfee06aaab41e82db51a103376030bc/td/telegram/MessageEntity.cpp#L4477-L4580)).
Its 35,000-byte internal truncation guard is not the public bot message limit. For bots, the
message-content path separately checks the normalized Unicode-code-point count against TDLib's
`message_text_length_max` option
([limit check](https://github.com/tdlib/td/blob/bc9c263e2bfee06aaab41e82db51a103376030bc/td/telegram/MessageContent.cpp#L4801-L4820)).
The moving [`sendMessage` documentation](https://core.telegram.org/bots/api#sendmessage) states
1–4,096 characters after entities are parsed; the pinned source shown here does not freeze the
option value or prove all remote-server acceptance behavior.

After cleaning and the internal cap, `fix_formatted_text` can also call `find_entities` and merge
automatically recognized entities; flags can instead suppress that scan or request only media
timestamps
([generated-entity branch](https://github.com/tdlib/td/blob/bc9c263e2bfee06aaab41e82db51a103376030bc/td/telegram/MessageEntity.cpp#L4597-L4610)).
The send conversion derives those flags from bot status, session count, dialog rules and options
([flag selection](https://github.com/tdlib/td/blob/bc9c263e2bfee06aaab41e82db51a103376030bc/td/telegram/MessageEntity.cpp#L4659-L4672)).
Consequently the exact automatically generated URL, mention, hashtag or command entities in a
complete Bot API response need pipeline evidence; parser output alone does not freeze them.

## GramLab boundary and next evidence

GramLab's existing nine types cover the style, code/pre and quote rows above. `text_link`,
`text_mention`, `custom_emoji`, and `date_time` require additional model, validation,
serialization and Android projection work; dropping them would silently reduce the pinned
contract. Raw parser nesting also does not fit the current validator whenever TDLib would repair
an overlap. TDLib specifically permits pre/code nested inside a blockquote while forbidding it
inside other entity kinds
([nesting validation](https://github.com/tdlib/td/blob/bc9c263e2bfee06aaab41e82db51a103376030bc/td/telegram/MessageEntity.cpp#L1560-L1607));
`<blockquote><code>x</code></blockquote>` therefore uses only existing GramLab entity names but
still conflicts with GramLab's current blanket code/pre-overlap rejection. Existing-nine HTML
support can require validator and native changes even after parser normalization. Finally, HTML
parsing changes the stored text through markup removal and entity
decoding, and the later cleaner can change it again, so applying the existing plain-text length
and equality behavior before those stages would be observably different.

Before claiming public HTTP parity, independently verify the complete offline pinned pipeline for:

1. raw parser output versus final sent/edited message text and entities for nested code/style,
   nested/crossing quotes, adjacent identical styles and empty tags;
2. each cleaned control/Unicode case with UTF-16 offsets before and after cleanup;
3. valid/invalid links, user mentions, custom emoji and date-time attributes without silently
   projecting unsupported entities;
4. 32-KiB raw markup, exactly 4,096 and 4,097 normalized characters, and markup whose raw size
   exceeds its decoded text size;
5. the exact `sendMessage`/`editMessageText` error and no-state-change behavior for malformed HTML,
   invalid UTF-8, empty normalized text and supplied `entities` alongside HTML mode.

A development-only harness around the pinned official TDLib parser/normalizer could generate
reference observations without an account or DC. Adopting that harness, importing source, or
choosing a reduced fidelity profile is not part of this research checkpoint.
