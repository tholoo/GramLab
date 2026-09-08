# Rich-button implementation contract

Status: frozen for implementation under ticket70. The [proposal](rich-button-targeting-proposal.md) and
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

## Scenario operations and receipts

Both methods use the existing control route and strict schema-1 envelope. Reject extra parameters,
non-integer or non-positive message/chat identifiers and unknown target IDs before disclosing
metadata. `rich_buttons(chat_id=..., message_id=...)` returns exactly:

```json
{
  "chat_id": 1,
  "message_id": 4,
  "message_revision": 17,
  "targets": [
    {
      "target_id": "opaque-run-local-id",
      "path": ["blocks", 0, "buttons", 1],
      "button": {"text": "Amber", "callback_data": "pick:amber"},
      "label": "Amber"
    }
  ]
}
```

Registry state binds the remaining identity fields; callers cannot substitute them. Zero targets
returns an empty array. Keep this operation outside the SDK read classification: a lost response
can follow durable allocation, quota consumption or a new native lifetime, even though no button
was tapped. A fresh observation is deliberate and allocates new IDs. Native geometry is not a
public coordinate API. Hidden/offscreen targets are returned and can reject when tapped.

`tap_rich_button(target_id=..., timeout=180)` consumes the returned ID on its first call. Repeating
that same call polls the same operation; it never repeats input. Keep the existing finite positive
timeout validation and run deadline. Return exactly these receipt fields:

```json
{
  "operation_id": "opaque-operation-id",
  "target": {
    "target_id": "opaque-run-local-id",
    "chat_id": 1,
    "message_id": 4,
    "message_revision": 17,
    "path": ["blocks", 0, "buttons", 1],
    "button": {"text": "Amber", "callback_data": "pick:amber"},
    "label": "Amber"
  },
  "status": "in_progress",
  "dispatch": "not_dispatched",
  "effect": null,
  "reason": null,
  "evidence": {
    "mode": "simulation",
    "world_event_sequences": [],
    "clipboard_observation": null
  }
}
```

`status` is `in_progress`, `rejected_before_dispatch`, `succeeded` or `uncertain`.
`dispatch` is `not_dispatched`, `intent_recorded` or `dispatched`. A rejection always has
`not_dispatched`; success always has `dispatched`. After intent, failure cannot become a rejection.
`effect` is null until confirmed, then exactly one of:

- Callback: `{"kind":"callback","callback": CALLBACK,"event_sequence": N}`, with the complete
  creation-time frozen callback, including `answer: null`, exact message and payload. Later bot
  answers are read separately and do not mutate the completed receipt.
- Copy: `{"kind":"copy","text":"exact copied string"}`.
- Disabled: `{"kind":"none","reason":"disabled"}`.

`reason` is null for progress/success, otherwise `{"code": CODE}`. Pre-dispatch codes are
`message_revision_changed`, `access_denied`, `client_restarted`, `target_unavailable` and
`component_stopped`. Uncertain codes are `dispatch_unconfirmed`, `effect_timeout`,
`effect_mismatch` and `component_stopped`. Keep observed mismatches in evidence, not in a successful
effect. Invalid/foreign/previous-run IDs use the existing generic invalid-request error and reveal
no identity. Known invalidated IDs retain their identity and receive a consumed rejection receipt.

Simulation evidence has exactly `mode`, operation-owned `world_event_sequences` and
`clipboard_observation`. The latter is null for callbacks or `{"before": VALUE,"after": VALUE}`
for copy/disabled, with string or null values. Native evidence uses `mode: "headless-android"`,
those same fields and `native` with exactly `observation`, `effect` and `captures`: relative
paths to the retained validated observation/effect JSON, and an array of original capture paths.
The first two are null until evidence exists; captures has at most two entries. No native availability or PNG
is inferred from a simulation result.

## Single use, transactions and interruption

Claim a target under the registry mutex before waiting for the per-client input lock. Concurrent
repeats can return its `in_progress` receipt without acquiring another dispatch. Under the input
lock, validate exact current content/path/button, ownership and revision in one `BEGIN IMMEDIATE`
World transaction. In simulation, the same transaction applies the selected semantic action.
Refactor callback creation through a private helper without a nested `BEGIN`; preserve the public
callback request validation, deduplication and event/update behavior.

The virtual clipboard is client-local state changed under that input lock while the validation
transaction remains open. It is never added to a World snapshot, user profile or event. A failed
commit after an attempted effect remains uncertain. The dedicated guest's clipboard can survive
an application process restart; target nonce invalidation must not assert that the clipboard was
cleared. Reobserve it on a new native lifetime. Virtual state likewise survives a client-process
restart within its isolated run/persona, and is cleared on persona/World replacement or run end.

Before issuing IDs or handing any input to a backend, append the corresponding allocation, claim
or intent to an owned run-local journal and flush/fsync it. This journal is outside the World
database and private to the trusted supervisor; it records scenario-control evidence, not new
World semantics. Append confirmed effects and terminal receipts before returning them. A complete
durable intent with no confirmed effect remains uncertain after supervisor interruption. A claim
without intent proves no backend handoff; artifact recovery can mark it rejected. Ignore only an
incomplete final journal record; reject interior corruption. Do not replay input from the journal.
After a new supervisor/run lifetime, old IDs always reject; retained receipts remain artifacts.

Terminal rejected/succeeded receipts are immutable. Polling may monotonically resolve an
uncertain operation to success from exact retained evidence; it cannot issue another input or
resolve a known mismatch as success. Lost control responses use existing SDK uncertainty errors;
the caller can deliberately repeat the same ID to recover its receipt.

Use the existing 64-interaction run budget for ordinary interaction records plus **issued rich
targets**, including unused and consumed targets. Allocate one reserved interaction slot per
issued target; ordinary operations cannot steal it. Reject the entire observation if all its
occurrences do not fit. This preserves first-call consumption without a late capacity exception.
Repeated observations deliberately consume more slots. Retain every issued ID/receipt for the run;
never evict and permit a second dispatch. A document over 64 occurrences cannot be observed under
this initial local limit, even though its admitted World message remains valid.

Bound the journal to 80 MiB, individual encoded records including their newline to 128 KiB, and each target's lifetime
to eight records (claim, intent, up to four changed evidence records and up to two receipts).
Reserve 1 MiB per issued target plus the actual complete observation record before allocating;
release unused reservation only after an immutable terminal receipt. A capacity failure rejects
allocation before any IDs are returned. Zero-target observations allocate no record or slot.
Unchanged polls write nothing. A bounded uncertain receipt retains paths to further diagnostics
without appending unbounded progress; only one later confirmed success may follow uncertainty.
These are local limits, not Telegram content limits. Larger canonical observations reject as a
whole; do not truncate them.

Clipboard text is capped at 4096 UTF-8 bytes for this input operation. Oversized/non-text clipboard
content is explicitly unavailable before dispatch; do not truncate it or equate it with an empty
clipboard. Null means no clipboard item. Check the frozen target, prospective semantic effect and
complete receipt size before intent. Unexpected oversized post-dispatch evidence becomes bounded
uncertainty, with a diagnostic reference. Native receipt evidence holds relative artifact paths
(up to 256 UTF-8 bytes each), not image bytes or arbitrary log text. Each referenced native JSON
file retains the private protocol's 1 MiB bound. Screenshots remain separate original artifacts.

The journal is `rich-button-journal.jsonl` beneath the trusted run directory. Every record is one
strict UTF-8 JSON object followed by a newline, with exactly `schema: 1`, `sequence`, `run_id`,
`world_id`, `kind` and `payload`. Sequences start at zero and increase by one. Duplicate members,
non-finite numbers, invalid UTF-8, wrong identity or malformed complete lines are corruption.
Only a final line lacking its newline is an incomplete tail. Use a fresh file per supervisor
lifetime and one serialized writer; do not reopen it to resume inputs.

The first `start` record has an empty payload. `observation` payload has exactly `observation`
(the complete public response), `user_id` and `client_nonce`. `claim`, `intent` and `receipt`
payloads each have exactly `receipt` (the complete current receipt) and `client_nonce`.
`evidence` payload has `operation_id`, `client_nonce` and `evidence` (the complete bounded current
evidence object). Allocation is one record for the entire observation, then at most one claim
and one intent per target. Evidence follows intent; receipts follow the corresponding claim or
intent. Legal progression and identities must validate as well as JSON syntax. Fsync each record
before acting on its transition. Unchanged polls write nothing.

Recovery runs only after the supervisor has terminated and writes a separate
`rich-button-recovery.json`; it never modifies the journal or restores a live registry. The
report has `schema`, `run_id`, `world_id`, `incomplete_tail`, `receipts` and `unclaimed_target_ids`.
Completed receipts remain exact. Claims without intent become evidence-only
`rejected_before_dispatch/component_stopped`; intent without a terminal confirmation becomes
`uncertain/component_stopped` with retained evidence. Unclaimed IDs have no operation receipt.
Interior corruption fails recovery visibly rather than inventing recovered status. Expose this
artifact through the run's retained diagnostics even when the normal supervisor observation is
missing. Offline recovery never upgrades unconfirmed evidence to success or makes old IDs usable.

## Native observation and ordinary input

Use bounded JSON in the dedicated guest's app-private GramLab directory, with atomic replacement
and strict members/types. No exported component, external listener or scenario-supplied coordinates
are added. Activation carries `schema`, an activation `nonce`, `world_id`, `user_id`, `chat_id`,
`message_id` and `revision`. Authentication and file access remain in the trusted supervisor.
Unknown schema or malformed activation fails explicitly; absence leaves observation disabled.

Activation lives in `files/gramlab/rich-button-observe.json`; the corresponding result is
`rich-button-observation.json` in that directory. All private files are bounded to 1 MiB. Nonces
and operation IDs contain 1–128 ASCII letters, digits, underscores or hyphens; identity and
revision numbers are positive signed-64 integers, excluding booleans. Generation/uptime are
nonnegative integers. Schema fields are integer 1. Reject extra or missing fields and duplicate
JSON members. The adapter reads activation/arm files outside draw callbacks and installs their
validated state on the UI thread; incomplete updates cannot expose a partially armed operation.

Each result carries those activation fields plus `client_nonce`, diagnostic `pid`, monotonic
`generation`, `drawn_uptime_ms`, `available`, `reason` and `targets`. A target carries `path`,
the complete canonical `button`, `label`, `available`, `reason`, and, only when measured,
`local_bounds`, `origin` and `screen_bounds`. Rectangles are arrays of four finite JSON numbers
in left/top/right/bottom order; origins have two numbers in x/y order. Booleans reject; absolute
coordinate values cannot exceed one million guest pixels. Fractional original geometry is retained. Fields describe observed geometry, never a reconstructed layout.
Unavailable occurrences remain in canonical order with explicit reasons and no usable hit point.
Top-level `available` means the exact applied message and its complete canonical object mapping
are trustworthy. Individual targets determine tap availability: one clipped target does not
disable another visible target. Available results have `reason: null`; unavailable reasons are `not_bound`, `message_not_applied`,
`message_not_drawn`, `offscreen`, `clipped`, `window_unfocused`, `unsupported_layout`,
`unmapped_object`, `ambiguous_object` or `stale_activation`. A message-level unavailable result
may have an empty target array; the supervisor retains its independently enumerated occurrences.

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

The separate `rich-button-arm.json` command contains exactly `schema`, `nonce`, `client_nonce`,
`operation_id`, `world_id`, `user_id`, `chat_id`, `message_id`, `revision`, `path` and
`observation_generation`. It supplies no coordinates or action payload. The adapter resolves
the path to its exact applied object and acknowledges only matching activation/lifetime/revision
with an observation generation at least as new as requested. There is one outstanding arm per
client. Repeating identical arm input observes its state; changing input for the same operation
rejects. A different operation cannot replace a live arm. The first original mapped touch consumes
the arm, including disabled suppression. It is never rearmed by polling or a lost response.

Acknowledgement and subsequent effect evidence use `rich-button-effect.json`, atomically replaced
by a single serialized writer. It has exactly `schema`, `nonce`, `client_nonce`, `operation_id`,
`world_id`, `user_id`, `chat_id`, `message_id`, `revision`, `path`, `generation`, `uptime_ms`,
`state`, `reason`, `touch`, `action`, `requests` and `clipboard`. `state` is `armed`, `consumed`,
`complete`, `unavailable` or `uncertain`. Generation increases on each published change, and
evidence cannot regress. `touch` is null or exactly `down_uptime_ms`, `up_uptime_ms` and `path`, recording original
observed uptime values and object identity. Either uptime may be null until observed; disabled
branches may provide only DOWN because the original code never arms an UP handler.
`action` is null or `callback`, `copy` or `disabled_suppressed`. `requests` is an ordered array
of at most two exact request chains; observing more is an explicit ambiguity, not truncation.
Each chain has `native_request_token`, `request_id`, `callback_id` and `message_revision`, with
null values until each actual identity is observed. `clipboard` is null or an exact foreground
`before`/`after` observation, with null representing no plain-text item. Success requires all
necessary links, not simply `state: complete`.

Effect reasons are null or `wrong_identity`, `revision_changed`, `unavailable_target`,
`arm_conflict`, `unmapped_dispatch`, `multiple_dispatches`, `request_mismatch`,
`clipboard_unavailable` or `component_stopped`. Before any touch they are unavailable/rejection
evidence; after touch/dispatch intent they cannot establish a pre-dispatch rejection. To release
an arm after pre-touch rejection or terminal observation, the host atomically writes
`rich-button-disarm.json` containing exactly `schema`, `nonce`, `client_nonce` and `operation_id`.
It affects only that arm, preserves its last evidence, and never initiates or repeats input.

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

Copy confirmation additionally requires the exact mapped object to reach the original copy
handler, recorded by an observational GPL hook. Disabled confirmation requires the exact object
to receive the original DOWN hit and the original disabled branch to suppress the action. The
original disabled paths never arm an UP action; retain that absence instead of fabricating an
UP object observation. The host still completes its ordinary touch sequence.
Equality of clipboard values or an absence of callbacks alone cannot prove either effect. Hooks
record original decisions without changing those decisions, hit testing, placement or drawing.

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
