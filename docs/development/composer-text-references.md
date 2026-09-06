# Pinned composer text semantics

Reviewed against Android revision `62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c` on
2026-09-06. These are source findings for independent semantic tests, not copied client code
for the MIT simulator. The [seven original fixtures](../../tests/fixtures/composer-text.json)
now pass the [actual composer check](../../tests/test_android_composer_text.py): exact submitted
text/entities, persona positions and all pending bot messages agree. The focused guest case takes
about 78 seconds. This establishes bounded native expectations, not simulation parity.

## Typed input differs from submitted text

The [composer](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/ui/Components/ChatActivityEnterView.java#L7735)
first decides whether input is emoji-only. Ordinary text is trimmed using
[the client's trim operation](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/messenger/AndroidUtilities.java#L3205),
which removes boundary ASCII spaces and LF. It does not use general Unicode whitespace trimming.
Tabs, CR, NBSP and Persian ZWNJ therefore need separate tests. Entity extraction trims boundary
space/LF again after removing formatting delimiters, including on the emoji-only path.

The [entity parser](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/messenger/MediaDataController.java#L7201)
rewrites backticks into code/pre entities and extracts formatting spans. Its later passes handle
bold, italic, spoiler and, when allowed, strikethrough delimiters. This is the pinned client's
syntax; neither generic Markdown nor Bot API MarkdownV2 is an interchangeable implementation.
Offsets and lengths use Java UTF-16 indices. The final trim adjusts entity ranges. The reviewed
ordinary path does not add Unicode normalization or case folding before forwarding the result
to [the send request](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/messenger/SendMessagesHelper.java#L5274).

The [pattern passes](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/messenger/MediaDataController.java#L7586)
also interact with existing code/link entities and offsets from earlier passes. Nested styles,
formatting inside code, adjacent matches and unmatched delimiters need actual observations.
Do not assume that a mathematically cleaner parser has the same behavior as this client.
Fenced-code language/newline handling and automatic link extraction require additional fixtures.

## Splitting and input side effects

The composer splits **before** parsing each part's formatting. The effective maximum comes from
[account configuration](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/messenger/MessagesController.java#L532);
the inspected [defaults](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/messenger/AppGlobalConfig.java#L97)
are 4096 ordinary and 8192 premium UTF-16 code units. A bounded backward search prefers double
LF, LF, whitespace after a period, then other whitespace. This is not code-point or grapheme
splitting.

Source concern requiring runtime proof: the
[continuation](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/ui/Components/ChatActivityEnterView.java#L7852)
advances one code unit past the previous part even at a hard boundary without a delimiter.
Whitespace-free and surrogate-boundary inputs may lose a code unit or produce an invalid
surrogate. The bridge already rejects non-round-tripping UTF-8 text before posting it, but this
does not make a multi-part input atomic: an earlier valid part may already have committed.
Test exact-limit, limit-plus-one, emoji-straddling and formatting-spanning boundaries before
claiming long-input parity or a single-message result.

Two other paths matter for a generic scenario method:

- [Send by Enter](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/ui/Components/ChatActivityEnterView.java#L5918)
  can submit a trailing LF during the text watcher before an explicit Send click. Its default is
  false; a reusable input contract must verify the dedicated profile's actual preference.
- A [standalone configured dice emoji](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/messenger/SendMessagesHelper.java#L4532)
  may become dice media instead of a text request. Ordinary emoji in prose is a different case.

The future scenario operation must expose accepted messages and uncertain/partial outcomes
without retrying a physical Send action. Keep raw input and resulting semantic messages separately
in evidence. Continue [ticket 04](../../.scratch/programmatic-scenarios/issues/04-native-composer.md)
with actual observations, an independently written model and cross-mode tests; preserve the
original renderer and report upstream discrepancies explicitly.
