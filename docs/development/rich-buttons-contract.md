# Rich callback, copy and disabled buttons

This implementation contract extends the existing rich-message subset using the
[pinned action findings](rich-actions-references.md). Core/API/capture support and focused native
codec/rendering checks pass, and the resumed normal gate covers all 41 cases. The separate
[rich-button input experiment](rich-action-input-experiment.md) passes real row/inline callbacks,
answers/edit/restart and absent/wrong activation checks. The [effect experiment](rich-action-effects-experiment.md)
adds original copy-row/disabled-inline input and clipboard evidence. A public input API remains open; the original renderer is preserved. URL/navigation, Web Apps, login, switch-inline, pay/game and custom emoji
remain separate inventory items requiring their own contracts and evidence.

## Shared JSON boundary

A row is `{"type":"buttons","buttons":[BUTTON],"align":"left"}`. It admits 1–8 buttons.
Absent or empty alignment omits from canonical output; explicit `left`, `center` or `right`
retains. Alignment is case-sensitive. Absent alignment means original fill layout, not left.
A button within any currently admitted RichText position is `{"type":"button","button":BUTTON}`.
Both placements use the same button contract. Existing recursive containers remain supported.

BUTTON requires `text` and exactly one of these direct action fields:

| Action | Input and canonical shape | Validation |
| --- | --- | --- |
| Callback | `"callback_data":"pick:amber"` | String containing 1–64 UTF-8 bytes, retained byte-for-byte |
| Copy | `"copy_text":{"text":"Amber 42"}` | Exactly one string field; raw and cleaned strings each contain 1–256 Unicode code points |
| Disabled | `"disabled":{}` | Exactly an empty object |

The initial label profile supports strings and nonempty recursive arrays of strings. Each leaf
uses the existing [string normalization](rich-text-cleaning.md); array structure survives. Plain
empty labels, including those produced by cleaning, remain representable. Formatting wrappers,
nested buttons and not-yet-supported custom emoji/date labels reject explicitly. This preserves
currently understood plain-label semantics without treating arbitrary RichText entities as allowed
button labels. Labels are content, not a unique target identity.

Optional `style` must be a string. Case-normalize recognized values: absent, empty or `default`
omits; `primary`, `danger`, `success` and `link` retain their lowercase value. `link` requires a
callback action. Unknown fields, action wrappers, missing/multiple actions, nulls, type coercion,
unsupported actions/styles and malformed copy/disabled objects reject before world mutation.
The row count, copied-text bounds, supported labels and link-style restriction follow the public
profile described in the source findings; the pinned parser is more permissive in several cases.
Checking both raw and cleaned copy length is an explicit initial profile restriction, not a claim
that the upstream conversion rejects a string cleaned to empty.

The existing raw and canonical depth/node/UTF-8 budgets and C0 policy remain unchanged. In
particular, admitted callback data is not passed through the label/copied-text cleaner. Ordinary
messages and existing inline keyboard validation retain their separate contracts. A canonical
no-op rich edit must remain atomic and must not allocate an event.

Independent examples:

| Input button | Canonical button |
| --- | --- |
| `{"text":"Choose\tamber","style":"PrImArY","callback_data":"pick:amber"}` | `{"text":"Choose amber","style":"primary","callback_data":"pick:amber"}` |
| `{"text":["Copy ","label"],"style":"DEFAULT","copy_text":{"text":"Amber\t42"}}` | `{"text":["Copy ","label"],"copy_text":{"text":"Amber 42"}}` |
| `{"text":"Later","style":"","disabled":{}}` | `{"text":"Later","disabled":{}}` |

## Native boundary and input experiment

The GPL adapter admits only canonical shapes and creates the original `TL_iv.pageBlockButtonRow`,
`TL_keyboard.PageButton`, `TL_iv.textButton`, `RichButtonStyle` and corresponding callback/copy/
disabled action constructors. Default style is null. Explicit row alignment uses the original
left/center/right bits; callback data uses UTF-8 bytes with `requires_password=false`. The separate
BridgeProbe observes complete content after real native TL serialization. It must retain both
row and inline placement, label structure, action data, style and alignment. Invalid canonical
records reject instead of silently choosing an action or coercing a field.

First verify canonical projection with an independent catalog and malformed cases, then render
actual World messages sent by a real local bot. Use actual ordinary guest input to verify callbacks
and edits, guest clipboard behavior for copy, and no callback/message mutation for disabled.
Original images, live RTL edits and cold restart remain required. Test-only geometry observation
may be explored within the GPL boundary after drawing; it must read actual layout rather than
recreate it. A permanent geometry endpoint, public target identity/staleness contract or changes
to original drawing/accessibility require a concrete proposal and the applicable user consultation.
No marker substitution between world and native content is part of this contract.

Captures traverse button label text in document order. They must not treat callback payload,
copied text, style or alignment as visible content, and must preserve complete structured history.
The current public `tap_inline_button` continues to address reply-markup keyboards only. Initial
rich-button support does not claim a public rich-button targeting API, clipboard simulation or
live-server conformance. Simulation and Android share the same rich message representation;
actual native input effects require their own evidence.
