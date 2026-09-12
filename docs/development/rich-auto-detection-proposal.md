# Proposed offline rich-text automatic detection

Status: frozen fidelity policy; approved on 2026-09-12 and not implemented.

The user approved the complete deterministic offline scanner below as an explicit GramLab
emulation, including its candidate classes, precedence, tree boundaries and acceptance limits.
It does not claim exact Telegram-server parity. Changing that policy requires renewed consultation.

This proposal would let an offline GramLab bot omit `skip_entity_detection` without pretending
that local behavior exactly matches Telegram's server. It needs user approval because it changes
the fidelity target. Until then, GramLab must continue rejecting omitted or false detection rather
than silently treating it as disabled.

## Established facts and policy choices

The [pinned source review](rich-auto-detection.md) establishes only these facts:

- omitted and false `skip_entity_detection` enable detection; true disables it;
- the downstream input carries the inverse `noautolink` flag;
- explicit URL, email, phone, named-user mention and custom-emoji nodes survive conversion; and
- an enriched URL, email or phone returns as the corresponding structured RichText node.

The source does not establish the server's scanning grammar, punctuation rules, precedence,
normalization, cross-node joining, code handling or block-role coverage. Every rule below is
therefore a **GramLab emulation choice**, not a Telegram compatibility claim.

## Proposed deterministic policy

GramLab would clean and validate the complete rich input first, using its existing per-string
cleaner. With an omitted or false flag, it would then enrich the cleaned canonical tree. With a
true flag, it would retain today's output exactly. The flag remains input-only and is absent from
stored and returned `RichMessage` objects.

This policy applies only to outgoing rich-message sends and edits. It does not add detection to
ordinary `sendMessage` text and does not alter incoming ordinary entities, including custom emoji;
those paths keep their explicit range-based contracts.

Detection would recognize these candidate classes:

| Class | Chosen grammar | Canonical metadata |
| --- | --- | --- |
| URL | `http://` or `https://` with a valid host; `www.` and bare DNS/IDNA domains | Explicit URL unchanged; otherwise prepend `https://` |
| Email | Conservative dot-atom local part and DNS/IDNA domain | Exact displayed candidate |
| Phone | Leading `+`; 7–15 ASCII digits after removing spaces, hyphens and balanced parentheses | `+` followed by digits |
| Mention | `@`, then 1–32 ASCII letters, digits or underscores; first character a letter | No separate metadata |
| Hashtag | `#`, then 1–64 Unicode letters, marks, numbers or underscores | No separate metadata |
| Cashtag | `$`, then 1–8 uppercase ASCII letters | No separate metadata |
| Bot command | `/`, then 1–64 ASCII letters, digits or underscores, optionally followed by a valid `@username` | No separate metadata |
| Bank card | 13–19 ASCII digits, with single spaces or hyphens permitted, and a valid Luhn checksum | No separate metadata |

URL, email and phone would use the existing `url`, `email_address` and `phone_number` shapes.
The other five candidates would use recursive `mention`, `hashtag`, `cashtag`, `bot_command` and
`bank_card_number` nodes containing `text`. These are proposed public output shapes; their native
projection must use the original corresponding RichText types. Their exact public and native
schema names require source verification before implementation; this proposal does not treat the
names as pinned facts. Accepting a candidate while flattening it back to plain text would not
implement this policy.

A candidate must begin at the start of its string leaf or after a character that is not a Unicode
letter, mark, number or underscore, and must end before the same boundary. Sentence punctuation
`.,;:!?` is excluded. A closing parenthesis, bracket, brace or quote is excluded only when it is
unmatched within the candidate. Displayed text otherwise remains byte-for-byte equal to the
already-cleaned string. GramLab would not apply NFC or NFKC normalization; IDNA conversion is only
a hostname validity check.

Overlaps resolve by earliest start, then longest candidate, then this fixed priority: email, URL,
phone, mention, hashtag, cashtag, bot command, bank card. This ordering is intentionally stable and
testable. It is not inferred from Telegram.

### Tree boundaries

Each plain string leaf is scanned independently. Adjacent array items, nested wrapper boundaries
and separate block fields are never joined into one candidate. Existing style wrappers remain
outside generated nodes, so a URL inside bold text stays bold. Explicit URL, email, phone,
named-user mention, custom-emoji and inline-button nodes are atomic; neither their visible text nor
their metadata is scanned again.

`code` wrapper contents and `pre` blocks are opaque. Custom-emoji alternative text, callback data,
copied text and every other button action field are also opaque. These are chosen author-control
and safety boundaries.

The scanner applies to every other admitted RichText role:

- paragraph, heading and footer text;
- expandable-blockquote and pullquote text and credit;
- blockquote descendants and credit;
- details summary and descendants;
- table caption and cell text;
- list-item descendants; and
- photo caption text and credit.

Divider has no text. Rich-button labels are deliberately not scanned: turning part of a button
label into another interactive entity conflicts with the enclosing action. Tests must record that
negative behavior. This button-label rule is a material local divergence while Telegram's role
behavior remains unknown.

### Examples

Omitted detection would transform:

```json
{"blocks":[{"type":"paragraph","text":"See https://example.com."}]}
```

into canonical output equivalent to:

```json
{"blocks":[{"type":"paragraph","text":["See ",{"type":"url","text":"https://example.com","url":"https://example.com"},"."]}]}
```

Formatting remains outside a generated entity:

```json
{"type":"bold","text":"Mail team@example.test"}
```

becomes:

```json
{"type":"bold","text":["Mail ",{"type":"email_address","text":"team@example.test","email_address":"team@example.test"}]}
```

`{"skip_entity_detection":true,"blocks":[{"type":"paragraph","text":"https://example.com"}]}`
stays plain. Likewise, `["https://exa","mple.com"]` never becomes one URL,
and URL-looking text inside `code`, `pre`, an explicit node or a button label stays unchanged.

## Mutation, equality and delivery

Expansion occurs before any visible World mutation. Generated nodes count toward the existing
depth, node-count and UTF-8 limits; exceeding a limit rejects the whole send or edit atomically.

Send responses, edit responses, updates, history, snapshots, differences and reopened storage all
return the same enriched canonical tree. Edit equality compares those canonical trees:

- omitted and false are equivalent;
- changing true to omitted/false is a real edit only when enrichment changes the tree; and
- any other canonically unchanged edit returns `MESSAGE_NOT_MODIFIED` without an event.

The original Android renderer must project and render every generated node type before the policy
can be called implemented. Simulator-only output is insufficient.

## Acceptance boundary

An implementation would need independently authored tests for valid, invalid, punctuation,
Unicode and Persian-boundary candidates; every precedence pair; nested styles; opaque code,
explicit nodes and button labels; split siblings; and every text role listed above. HTTP and World
tests must cover omitted, false and true sends, edits, no-ops, atomic failures, response/update
equality and reopening. Original Android tests must cover each newly generated node shape.

Passing those tests would establish this documented local policy only. Exact Telegram parity would
remain open and later external evidence could require a versioned policy change.

## Scanner and alternatives

The pinned Python runtime has no reusable URL, email, phone or entity scanner. Python's standard
library supplies parsers and Unicode data, not this scanner. Android `Linkify` belongs to the
separate GPL client boundary. Adapting TDLib's entity detector would require its own provenance and
[licensing review](licensing.md), and would still not prove server-side rich-block scope.

The approved fidelity choice is:

1. **Use this local policy.** It is deterministic, offline and reviewable, but intentionally
   diverges wherever Telegram behavior is unknown. Waiting for independently supplied server
   observations remains a possible later fidelity revision, not a prerequisite for this slice.

Implementation should prefer reviewed, reusable, permissively
licensed scanner components wherever their behavior satisfies this contract. That can accelerate
delivery, but it does not create a third fidelity policy: the selected component remains subordinate
to these rules and needs dependency, provenance and licensing review. No dependency or source
adaptation is approved or performed by this proposal.

Accepting omitted or false as a no-op is not a valid alternative because it contradicts the known
flag semantics.
