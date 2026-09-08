# Rich-button implementation contract

Status: coordinator draft under review. The [proposal](rich-button-targeting-proposal.md) and
[ADR 0005](../adr/0005-local-media-and-client-interaction-boundaries.md) are approved; this document
specifies implementation details within those decisions. It does not establish working operations.

## Shared identity and existing boundaries

Use the existing authenticated scenario control envelope and World capability. The supervisor
owns target IDs, operation records and input serialization. An ID is never authorization. Read
the selected canonical bot message, chat ownership and its creation/edit journal revision in one
World transaction. Derive the persona from the selected private chat and verify that access
before returning any target metadata. Do not use an unauthenticated message lookup as admission.

Keep semantic bridge v4 unchanged, including exact callback request fields, response-local
dependencies and frozen callback revisions. The new app-private observation protocol has its
own schema 1 and requires an adapter supporting v4. Existing message revisions already provide
the necessary semantic identity; the GPL adapter must retain the revision actually applied to
each original message rather than merely validate and discard it. No new semantic v5 is needed.

An observation binds run, World, persona, chat, message, revision and client-instance nonce.
Android creates its nonce once per application process lifetime. PID is diagnostic only. A
process restart or World/persona rebind invalidates the old lifetime even if content is equal.
The virtual client owns an equivalent lifetime and its own clipboard state. These are client
state, never World identities or shared clipboard data.

## Canonical occurrences

Paths start at the canonical `rich_message` value; components are literal object keys or
zero-based integer array indices. Booleans are not indices. A row target ends at
`["blocks", 0, "buttons", 1]`; an inline target can end at
`["blocks", 1, "text", 0, "button"]`. Retain all container components, including list-item
blocks, details, table cells, quote credits and photo caption text/credit. Walk canonical content,
not the original bot request, stringified JSON, accessibility order or visual RTL order.

Define document order explicitly: blocks and arrays preserve their array order; details visit
summary before blocks; blockquotes visit blocks before credit; photo captions visit text before
credit; tables visit caption before row-major cells; lists visit item blocks in item order;
ordinary text-bearing blocks visit text before credit. Button rows preserve button array order.
Rich text wrappers recurse through their text; inline button nodes yield their canonical button.
Button labels contain strings, nested arrays and custom-emoji alternatives, not nested actions.
Visible label text concatenates those canonical alternatives without catalog substitution.

Return every admitted occurrence, including hidden and offscreen occurrences. Native availability
is separate from semantic existence. Reject unsupported traversal explicitly; never truncate a
document or silently lose an occurrence. Duplicate labels and payloads are legal and cannot
identify an occurrence. Same-clock and A → B → A edits invalidate prior revisions; unrelated
message edits and rejected no-op edits do not.

## Native observation and ordinary input

Use bounded JSON in the dedicated guest's app-private GramLab directory, with atomic replacement
and strict members/types. No exported component, external listener or scenario-supplied coordinates
are added. Activation carries `schema`, an activation `nonce`, `world_id`, `user_id`, `chat_id`,
`message_id` and `revision`. Authentication and file access remain in the trusted supervisor.
Unknown schema or malformed activation fails explicitly; absence leaves observation disabled.

Each result carries those activation fields plus `client_nonce`, diagnostic `pid`, monotonic
`generation`, `drawn_uptime_ms`, `available`, `reason` and `targets`. A target carries `path`,
the complete canonical `button`, `label`, `available`, `reason`, and, only when measured,
`local_bounds`, `origin` and `screen_bounds`. Rectangles are finite left/top/right/bottom values;
origins are finite x/y values. Fields describe observed geometry, never a reconstructed layout.
Unavailable occurrences remain in canonical order with explicit reasons and no usable hit point.

During decode, bind canonical paths to the exact original rendered row `PageButton` and inline
`textButton` objects. An intermediate copied button is insufficient. Publish mappings only after
successful message application; replace mappings on edits and preserve unrelated messages.
Observe after original drawing on the UI thread; write files away from drawing callbacks. Reject
unmapped or multiply mapped objects. Preserve upstream layout, rendering, hit testing and action
dispatch, including RTL, nesting, clipping and animation behavior.

The host serializes observe/input with other client operations. Observation may open the requested
chat and establish a fresh lifetime. Tapping an issued target must use that lifetime without
calling the existing cold-launch helper. Existing operations that restart the application can
invalidate targets; do not quietly resolve a new target during a tap.

Before dispatch, validate current ownership/content/revision, client nonce, PID, generation,
focused app/window, drawn message and fully visible hit bounds. Retain the original screenshot
before the final freshness read. Require a sample no older than the established five-second
guest-uptime bound, without mixing host and guest clocks. Recheck the activation and exact mapped
object. Any failed check before input is a rejection. One ordinary touch follows a recorded
dispatch intent; there is no automatic retry, action invocation or synthetic callback fallback.

## Native effects and exact callback correlation

Arm one operation with its semantic identity, lifetime, path and exact original button object.
The adapter records an observation-only chain from that object through the original delegate
dispatch, exact native request object/token, generated HTTP `request_id`, returned `callback.id`
and returned `message_revision`. This is app-private schema-1 evidence; no correlation fields are
added to v4 HTTP payloads. Do not infer the chain from labels, payload equality or nearby events.

The row and inline original touch paths retain the exact button object. The existing send-callback
seam can associate it with the native request before transport; the normal adapter receives that
request and generates the HTTP ID. Retain the parsed response revision as well as callback ID.
Missing links, multiple dispatches/tokens/requests, lifetime changes or mismatched snapshots make
the outcome uncertain. An edit after the last host check can still race the actual touch or
callback acceptance. Preserve ordinary callback admission and report that race; an action already
committed cannot be relabeled rejected or rolled back.

Confirm a callback effect against the authoritative complete frozen callback message, exact
payload and accepted revision. Bot answer/edit is separately observable. A matching payload alone
does not establish success, particularly for repeated labels or payloads. Reconciliation after a
lost reply may read retained effects but must never send another touch.

Copy observes the actual foreground clipboard after original input. Record exact before/after
values and source observation; copying the same string twice need not change its value. Never
declare copy success solely from button metadata and never write/paste clipboard text through the
observer. Native acceptance independently pastes through the original composer and removes the
unsent text. Disabled effects retain unchanged clipboard and complete controlled World/API/event
evidence over a bounded quiet interval. Neither action creates a World event or Bot API update.

## Integration and acceptance

The core worker owns independent occurrence traversal, World transactions and target/receipt
state. The GPL worker owns original object mapping, applied revisions, post-draw observations and
request/clipboard evidence in the normal patch series. A host/acceptance worker consumes the frozen
interfaces and owns original touch orchestration and real contained scenarios. The coordinator
owns shared schemas, assignments, integration, conflicts, builds and combined verification.

Required core cases include nested paths, duplicate labels/payloads, hidden occurrences,
same-clock/ABA edits, unrelated edits, wrong identity, capacity, concurrent repeats, response
loss and interruption before/after dispatch intent. Use actual World/API and contained SDK
boundaries. Native acceptance includes callback/copy/disabled row and inline placements,
Persian/English RTL, nesting, clipping, process restart, edit races, exact callback correlation,
original clipboard paste and isolation. Semantic results and original PNG/effect evidence remain
separate. Offscreen rejection is explicit; automatic scrolling, disclosure and long-press are
unimplemented until their own original-input evidence exists. Representative long/RTL/nested
placements remain required for the operational milestone.
