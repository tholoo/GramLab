# Rich-list contract references

Reviewed 2026-09-07 against Bot API server revision
`2efabc722e9493b9cac450233198d09e5cea0573` (10.3), its pinned TDLib revision
`bc9c263e2bfee06aaab41e82db51a103376030bc`, and Android revision
`62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c`. This is source research for an
independently written contract. It is not live Telegram conformance evidence, and no upstream
implementation belongs in the MIT core.

## Public JSON shape

Bot API uses one list block for both ordered and unordered lists. There are no separate public
discriminators and no text-only item variant:

```json
{
  "type": "list",
  "items": [
    {
      "blocks": [{"type": "paragraph", "text": "First"}],
      "has_checkbox": true,
      "is_checked": true,
      "value": 1,
      "type": "A"
    },
    {
      "blocks": [{"type": "paragraph", "text": "Second"}],
      "value": 2,
      "type": "A"
    }
  ]
}
```

The public [input list](https://core.telegram.org/bots/api#inputrichblocklist) has `type: "list"`
and an `items` array. Each [input item](https://core.telegram.org/bots/api#inputrichblocklistitem)
requires an array of nested `blocks` and optionally accepts `has_checkbox`, `is_checked`, integer
`value`, and label `type`. The documented label types are `a`, `A`, `i`, `I`, and `1`. The public
[output list](https://core.telegram.org/bots/api#richblocklist) keeps the same block discriminator.
Each [output item](https://core.telegram.org/bots/api#richblocklistitem) always has `label` and
`blocks`, followed by applicable optional state.

The pinned server parser confirms the exact names and recursive block parsing in
[`get_input_page_block_list_item`](https://github.com/tdlib/telegram-bot-api/blob/2efabc722e9493b9cac450233198d09e5cea0573/telegram-bot-api/Client.cpp#L11521-L11532)
and the
[`list` branch](https://github.com/tdlib/telegram-bot-api/blob/2efabc722e9493b9cac450233198d09e5cea0573/telegram-bot-api/Client.cpp#L11534-L11580).
Optional booleans, integers, and strings default to false, zero, and empty in the pinned
[JSON field readers](https://github.com/tdlib/td/blob/bc9c263e2bfee06aaab41e82db51a103376030bc/tdutils/td/utils/JsonBuilder.h#L485-L503).

## Ordering and validation

A nonempty item `type` selects ordered behavior. TDLib accepts only the five one-character types,
retains that item's value and type, and derives its label. An absent or empty `type` selects
unordered behavior. A list must contain at least one item, and every item must make the same
ordered-versus-unordered choice. Items may use different valid ordered types and arbitrary signed
32-bit values. These checks are in the pinned
[item conversion](https://github.com/tdlib/td/blob/bc9c263e2bfee06aaab41e82db51a103376030bc/td/telegram/WebPageBlock.cpp#L2061-L2087)
and
[list validation](https://github.com/tdlib/td/blob/bc9c263e2bfee06aaab41e82db51a103376030bc/td/telegram/WebPageBlock.cpp#L5272-L5288).

Positive `a` and `A` values produce spreadsheet-style letters. Positive `i` and `I` values below
4000 produce Roman numerals. Other values fall back to decimal text even though the supplied type
is retained. Every generated label ends in a period. The exact derivation is visible in
[`get_ordered_list_label`](https://github.com/tdlib/td/blob/bc9c263e2bfee06aaab41e82db51a103376030bc/td/telegram/WebPageBlock.cpp#L1991-L2059).

The pinned modeled path accepts and preserves an empty item `blocks` array. The server parser
passes the array to recursive block parsing; TDLib's
[block-vector conversion](https://github.com/tdlib/td/blob/bc9c263e2bfee06aaab41e82db51a103376030bc/td/telegram/WebPageBlock.cpp#L5208-L5216)
returns an empty vector without error, and list-item conversion retains it. The output object and
serializer then emit `blocks: []` through the same paths cited below. Only the outer `items` array
must be nonempty. GramLab should therefore preserve empty list-item block arrays even though its
top-level and other nested block arrays retain their existing nonempty limits. This source path is
still not a live production request observation.

The official parser extracts known fields without an unknown-field rejection pass. GramLab's
existing stricter interface should continue to reject unknown list and item fields. At the rich
message root, the official parser gives `blocks` precedence over `markdown`, then `html`, and
defaults automatic detection to enabled; see
[`get_input_rich_message`](https://github.com/tdlib/telegram-bot-api/blob/2efabc722e9493b9cac450233198d09e5cea0573/telegram-bot-api/Client.cpp#L11725-L11748).
That does not change GramLab's documented rejection of ambiguous sources or its requirement for
`skip_entity_detection: true`.

## Canonical output

The pinned [list-item serializer](https://github.com/tdlib/telegram-bot-api/blob/2efabc722e9493b9cac450233198d09e5cea0573/telegram-bot-api/Client.cpp#L963-L981)
always emits `label` and recursively serialized `blocks`. It emits `has_checkbox` only when true,
and emits `is_checked` only inside that true branch. It emits both `type` and `value` exactly when
the internal type is nonempty. The
[list serializer](https://github.com/tdlib/telegram-bot-api/blob/2efabc722e9493b9cac450233198d09e5cea0573/telegram-bot-api/Client.cpp#L4283-L4289)
always emits `type: "list"` and `items`.

This produces the following canonical rules for the shared contract:

- An unordered item has `label: "•"`, always has `blocks`, and omits `type` and `value`.
- An ordered item has its derived `label`, always has `blocks`, and always includes its valid
  `type` and signed 32-bit `value`. Omitted input `value` becomes zero.
- Input `value` without a nonempty `type` is ignored in official normalization and omitted from
  output. Input `type: ""` behaves the same as omission.
- False checkbox flags are omitted. `is_checked: true` without `has_checkbox: true` is normalized
  away; checked output is possible only with a checkbox.
- An empty item `blocks` array remains empty in canonical output; it is not filled with a paragraph
  or rejected by the modeled source path.
- Nested lists use the same contract recursively and count against GramLab's existing whole-tree
  depth, node, and UTF-8 budgets.

The bullet and checkbox rules follow TDLib's
[output item construction](https://github.com/tdlib/td/blob/bc9c263e2bfee06aaab41e82db51a103376030bc/td/telegram/WebPageBlock.cpp#L2157-L2165).
The implementation should compare complete canonical output after send, edit, snapshot, difference,
database reopen, and native serialization. A partial assertion on visible strings cannot establish
the list contract.

`label` is an output field, not an input item field. GramLab's strict unknown-field policy rejects
it in input; consumers must remove output-only labels before resubmitting a returned message as
new input. The Android semantic adapter instead consumes canonical output and must require and
validate the label against the item's bullet or type/value. Keep these two validation contracts
separate rather than admitting output fields into the public input schema.

## Native projection

The pinned Android schema has distinct `pageBlockList` and `pageBlockOrderedList` containers,
text and block item constructors for both, item checkbox state, and ordered per-item number/value/type
plus list-level start/reversal/type. See the pinned
[unordered container](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/tgnet/tl/TL_iv.java#L1105-L1118),
[ordered container](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/tgnet/tl/TL_iv.java#L1750-L1782),
[ordered items](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/tgnet/tl/TL_iv.java#L2049-L2175),
and
[unordered items](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/tgnet/tl/TL_iv.java#L2178-L2260).

The Bot API input variant is always block-based. TDLib maps unordered items to native block items,
ordered items to ordered block items, and sets ordered number/value/type fields; it does not expose
native text-item or list-level start/reversal fields as additional Bot API JSON. The relevant
[outgoing mapping](https://github.com/tdlib/td/blob/bc9c263e2bfee06aaab41e82db51a103376030bc/td/telegram/WebPageBlock.cpp#L2142-L2155)
and
[container selection](https://github.com/tdlib/td/blob/bc9c263e2bfee06aaab41e82db51a103376030bc/td/telegram/WebPageBlock.cpp#L2280-L2290)
give the adapter seam.

The original Android
[`RichMessageLayout`](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/messenger/RichMessageLayout.java#L857-L1004)
renders block items recursively, places markers on the first rendered child, varies unordered
bullets by nesting level, measures ordered labels, moves indentation to the right in RTL, and can
show checkbox state. Its
[marker selection](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/messenger/RichMessageLayout.java#L1184-L1194)
prefers an explicit item number before value/list defaults. GramLab should map its canonical output
to these pinned types inside the GPL adapter, reject inconsistent labels or optional fields, and
leave the renderer and resources unchanged.

Native acceptance requires an actual serialize/deserialize observation equal to the complete
canonical JSON for unordered, ordered, mixed label types, nested blocks, both checkbox states, and
RTL/LTR text. It must also preserve `blocks: []` in an item through the native codec. Independent
malformed snapshots must reject mixed orderedness, bad labels/types, empty outer `items`, wrong
scalars, unknown fields, and budget overflow. Original
send/edit/cold-restart screenshots and UI structure must show list order, marker choice, nesting,
wrapping, multilingual content, RTL indentation, and checkbox presentation. Source capability or a
codec round trip alone does not prove rendering or accessibility behavior; checkbox interaction is
a separate mutation contract.

For an empty block item, the original renderer's list branches skip the item before creating a
marker, checkbox or child layout in the same
[`RichMessageLayout` path](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/messenger/RichMessageLayout.java#L857-L1004).
That invisibility is expected native behavior to preserve. The authoritative history and codec
must retain the empty item, while screenshot and UI hierarchy evidence should establish that it
adds no visible row. Public capture and inline walkers will have no readable fragment for that
item, so an empty item cannot satisfy a text target or disambiguate a rich message.

The renderer's checkbox path checks `canToggleRichMessageCheckbox` and `richEditorAllowed` before
an optimistic state change and edit dispatch; see
[`RichMessageLayout`](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/messenger/RichMessageLayout.java#L9596-L9631).
The enclosing chat delegate additionally requires `richEditorAllowed` and an editable message
before it calls `editRichMessage`; see
[`ChatActivity`](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/ui/ChatActivity.java#L38933-L38966).
For incoming bot-authored messages in the current synthetic user dialog, list checkboxes should
therefore be treated as rendered state controlled by bot send/edit. Native evidence must observe
enabled versus checked presentation and prove a user tap causes no mutation. Supporting a user
checkbox toggle would require a separately defined authorization, world mutation and Bot API
effect contract.

## Work split

Commit the exact JSON interface above before implementation. The following ownership is disjoint:

- Python validation and durable Bot API behavior: `src/gramlab/rich_messages.py`,
  `tests/test_rich_messages.py`, and `tests/test_rich_bot_api.py`.
- GPL projection and native evidence: a new `clients/android/patches/0012-rich-list-projection.patch`
  and its `series` entry, preserving the earlier patch unchanged;
  new list-only files under `clients/android/fixtures/`, `tests/probes/android_rich_lists.py`, and
  `tests/test_android_rich_lists.py`.
- Public capture and inline matching: `src/gramlab/_captures.py`, `src/gramlab/_android.py`,
  `tests/test_runner_rich_capture.py`, and `tests/test_runner_rich_buttons.py`.

The coordinator should retain shared tickets, examples, cross-layer scene fixtures, compatibility
and handoff documents, patch-queue documentation, integration reports, and the combined Android
gate. The GPL worker can begin from a coordinator-authored canonical output fixture while the Python
worker implements input normalization. The capture worker depends only on the committed recursive
item shape. Integration must still prove that list text is found in item/block order without
flattening stored content, while collapsed details retain their existing visibility rule.

## Limits of this review

No account, Bot API service, Telegram DC, Android guest, or build was used. The mutable public
documentation currently reports Bot API 10.3, but it is not a historical commit artifact; the
server and TDLib source links above are immutable. These sources do not establish production item,
list, depth, text, or total-size limits; live acceptance of empty item blocks or unusual integer
values; Android pixels, wrapping, interaction, or accessibility; or live server output after a
send/edit. The pinned modeled path nevertheless establishes that empty item block arrays must be
preserved in this slice. GramLab's other current local budgets and explicit unsupported behavior
remain the supported profile until dedicated evidence justifies a change.
