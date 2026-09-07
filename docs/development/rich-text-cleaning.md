# Pinned rich-text string normalization

This source contract corrects an existing canonical-state gap before further rich actions are
implemented. It is not live server conformance evidence. The pinned TDLib
[plain RichText conversion](https://github.com/tdlib/td/blob/bc9c263e2bfee06aaab41e82db51a103376030bc/td/telegram/WebPageBlock.cpp#L159)
cleans each plain leaf separately, recursively through wrappers and arrays. The same applies to
all current block RichText roles: text, summary, credit, caption and table cell text.
[Preformatted language](https://github.com/tdlib/td/blob/bc9c263e2bfee06aaab41e82db51a103376030bc/td/telegram/WebPageBlock.cpp#L5559)
is cleaned separately before canonical omission of an empty language.

GramLab retains its existing raw-input policy: invalid UTF-8 and C0 controls other than newline
and tab reject before mutation. For strings admitted by that policy, the pinned
[cleaner](https://github.com/tdlib/td/blob/bc9c263e2bfee06aaab41e82db51a103376030bc/td/telegram/misc.cpp#L76)
establishes these transformations:

- Replace tab with one ASCII space; preserve newline.
- Remove U+2028 through U+202E, and U+030A, U+0333 and U+033F.
- Bound each cleaned string by the source's UTF-8 stopping rule: stop before emitting the next
  character when the accumulated byte count is already at least 34,996. A character beginning
  below that count may finish beyond it, yielding at most 34,999 bytes. This is not a simple
  35,000-byte slice or a 35,000-character limit.
- After removals and truncation, replace every marker except the last in each consecutive run of
  U+200E/U+200F with U+200C. Preserve the last marker's original identity. A singleton survives.

The last rule comes from [direction-marker replacement](https://github.com/tdlib/td/blob/bc9c263e2bfee06aaab41e82db51a103376030bc/td/telegram/misc.cpp#L63).
Ordinary Persian letters, ZWNJ, newline and unrelated combining marks retain their values.
The existing aggregate raw/canonical byte, node and depth budgets remain independent checks.
Canonical optional plain-empty text omits after cleaning; wrappers/arrays containing empty text
retain their existing structure. Required plain-empty text remains present.

Independently authored expected examples (escape notation denotes actual Unicode characters):

| Input | Expected output |
| --- | --- |
| `Amber\t42` | `Amber 42` |
| `a\u2028b\u2029c\u202ad\u202be\u202cf\u202dg\u202eh` | `abcdefgh` |
| `A\u030aB\u0333C\u033fD` | `ABCD` |
| `X\u200e\u200f\u200eY` | `X\u200c\u200c\u200eY` |
| 34,996 ASCII `a` characters followed by `b` or `é` | 34,996 ASCII `a` characters |
| 34,995 ASCII `a` characters followed by `éZ` | 34,995 ASCII `a` characters followed by `é` |
| 34,995 ASCII `a` characters followed by `💡Z` | 34,995 ASCII `a` characters followed by `💡` |

Tests must specify complete public-boundary output from these expectations, not call a production
cleaner to construct their oracle. An unrestricted Unicode-preservation property is incorrect
for these admitted transformations; use a preservation property over unaffected characters and
separate transformation and persistence cases. The existing callback payload, ordinary messages,
unsupported rich actions and navigation contracts are outside this correction.
