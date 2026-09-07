# Public rich-button targeting proposal

Status: proposed; user consultation required before implementation.

Rich row and inline buttons render correctly, but `Scenario.tap_inline_button` addresses only
reply-markup keyboards. The separate [callback experiment](rich-action-input-experiment.md) and
[copy/disabled experiment](rich-action-effects-experiment.md) prove original input for short LTR
fixtures. They do not supply a public rich-button operation. This proposal closes that gap while
preserving the original renderer and the existing offline and licensing boundaries.

## Recommended scenario interface

Add two operations, with these provisional Python signatures:

```python
observation = scenario.rich_buttons(chat_id=chat_id, message_id=message_id)
target = next(t for t in observation["targets"] if t["path"] == ["blocks", 0, "buttons", 1])
assert target["button"]["callback_data"] == "pick:amber"
receipt = scenario.tap_rich_button(target_id=target["target_id"], timeout=180)
```

`rich_buttons` returns the selected message revision and all admitted rich button occurrences in
canonical document order. Each target has an opaque run-local ID, a structural path, its complete
canonical button and its visible label text. Labels and callback payloads need not be unique.
The target ID binds the run, World, persona, chat, message, revision and exact structural path;
it is not an authorization credential and cannot be transferred to another run. Existing scenario
capability checks still apply. Each target also binds the client-instance lifetime nonce. The registry invalidates all outstanding
targets when that client restarts, even if its message content is unchanged; a process number alone
is insufficient because it can be reused. A caller must use a returned ID; arbitrary native coordinates and
upstream layout indices are not part of this interface.

Paths are arrays of canonical JSON object keys and zero-based array indices. For example,
`["blocks", 0, "buttons", 1]` identifies the second row button, and
`["blocks", 1, "text", 0, "button"]` identifies a button in an array-valued paragraph. Paths
refer to normalized content, not the bot's pre-normalization input or visual RTL order. Return
paths through all supported rich containers and button-label forms. Hidden/offscreen occurrences
remain identifiable; native availability is a separate observation and is never inferred from
semantic existence. Invalid message/persona access fails before exposing target metadata.

Use the last creation/edit journal sequence of this message as its revision, read atomically with
the canonical content. A content hash or `edit_date` alone is insufficient: an A → B → A edit can
restore identical bytes and multiple edits can share the simulated clock. Edits of this message
invalidate its old targets; an unrelated message edit does not. A rejected no-op edit does not
create a revision. Resolve a fresh target after an edit or client restart.

A successful call returns an interaction receipt containing the target's semantic identity,
operation ID, dispatch outcome and observed effect. Mode-specific rendering/input evidence lives
in a separate receipt field. Keep existing `tap_inline_button` behavior unchanged. Bound retained
observations using the run's existing resource limits; expired observations fail explicitly.

## Input, races and recovery

Revalidate the target's revision, access and content immediately before dispatch. Serialize input
through the existing per-client lock. In simulation, validate and apply the semantic action within
one World transaction. In Android, wait for the exact message revision to be applied and drawn,
then obtain actual native hit bounds for that occurrence. Validate the current client process,
observation generation, active/focused window, visibility, layout state and a measured age limit.
Capture evidence before the final freshness check so screenshot latency does not age the sample.

Dispatch one ordinary Android touch sequence. Never invoke an upstream button action directly or
synthesize a Python callback after a failed native tap. Preserve the original hit-testing and
action dispatch. The post-draw observer remains in the GPL adapter and reads original geometry;
MIT code consumes independently specified semantic IDs and observations, not client layout code.

The existing observer and a host-side tap are not atomic. A bot edit or layout change can occur
after the final check. Report pre-dispatch rejection separately from an uncertain post-dispatch
outcome; do not promise stale-input prevention merely because a sample is recent. Correlate the
native callback request with the dispatch record and compare its full message snapshot and payload.
A mismatched effect fails visibly and retains evidence; an action that already happened cannot be
rolled back by relabeling the operation rejected.

The first call consumes its target even if validation rejects before dispatch. A repeat call
returns the same receipt/status and never sends another tap. Use a fresh observation after an
offscreen, stale or unavailable rejection. Atomically claim the target before validation, then
record either `rejected_before_dispatch` or dispatch intent. An intent without confirmed effect
remains `uncertain`; concurrent repeat calls may report `in_progress`. Record dispatch intent before handing control to the input backend.
A lost response, app death or supervisor interruption after that point leaves an uncertain outcome
until observed effects resolve it. Observation may be polled again; input must not retry itself.
A new deliberate tap requires a fresh target. After a run/supervisor restart, reject old target IDs;
preserve the prior run's receipt and uncertainty in its artifacts without replaying it.

Single-use target behavior is a scenario-control guarantee, not a change to Bot API callback
request semantics. Existing client callback deduplication and bot polling/recovery remain intact.
A native callback's request ID is distinct from the scenario operation ID. The current bridge
sends only request ID, chat, message and payload; `World.create_callback` reads the current message
when accepting that request. Thus a tap of A can be followed by an edit to B before acceptance,
producing A's payload with B's snapshot. Classify that receipt as an uncertain/mismatched effect;
do not change ordinary callback admission into a new stale-revision rejection rule.

Add adapter-side evidence linking the active scenario operation, actual native request ID and
applied message revision. Ambiguous correlation must fail visibly rather than guessing from
matching payloads. This observation/correlation extension belongs in the reviewed bridge/control
contract. Source mapping and native request correlation must be demonstrated before claiming an
exactly matched receipt; the existing callback request alone cannot prove it.

## Effects and semantic consistency

| Action | Shared semantic outcome | Android evidence |
| --- | --- | --- |
| Callback | One callback with complete message snapshot and exact payload, delivered through the ordinary local Bot API path; bot answer/edit remains separately observable. | Actual original input and callback transport, matching receipt, original before/after images and recovery. |
| Copy | Exact copied string in client-local clipboard state; no message, callback, update or World event. | Read the actual clipboard through a bounded foreground observer after ordinary input; original composer paste independently proves the bytes in acceptance. |
| Disabled | Dispatched interaction with no action effect and unchanged shared state. | Original disabled control and ordinary input, unchanged clipboard and complete state/event/API comparison over the controlled observation window. |

Clipboard state belongs to a client instance, not a World or user identity shared by several
clients. The virtual client models that same local state; Android observes its actual clipboard.
Neither backend should declare successful copy from the button's metadata alone. A copy observer
must not set the clipboard, paste into the user's message automatically, or create World events.
Foreground access, duplicate copies and timeout behavior need tests under the pinned Android
profile. This adds a client-local effect model and is part of the requested design consultation.

Report semantic effects separately from delivery/observation evidence. Simulation establishes
World and virtual-client state; it provides no PNG or claim of an actual Android clipboard.
Concurrent bot activity must be accounted for by event identities rather than treating every
new event in a time window as this tap's effect. Disabled acceptance uses a controlled quiet bot;
it is bounded evidence, not a proof that no later unrelated event can occur.

## Native integration and acceptance gates

The experiment uses reflection, assumes two targets, rejects RTL/nested layouts and lacks message
revision binding. Do not promote that helper unchanged. Introduce a normal-adapter observation
seam that binds canonical occurrences to the original button objects while preserving their
original drawing, placement and hit testing. Extend the semantic bridge with the message revision
needed for observations. Coordinate this with the [mention proposal](rich-mention-proposal.md)
in one reviewed successor schema; do not independently allocate conflicting schema versions.
App-private control stays within the dedicated guest and authenticated scenario boundary. No
exported Android component, new external listener or runtime Internet access is required.

Implementation can split after the shared identity/receipt schema is approved:

1. Core/SDK worker: canonical occurrence traversal, transactional revision checks, single-use
   operation records, callback effects and virtual client-local effects. Cover duplicate labels
   and payloads, nested paths, same-clock/ABA edits, unrelated edits, wrong identity and lost replies.
2. GPL worker: canonical occurrence mapping, revision-aware observations and original input/effect
   evidence. Cover callback/copy/disabled in rows and inline text, Persian/English RTL mixtures,
   nesting, animations, clipping, repeated labels, process restart and edit races. Use original
   bounds; no recreated layout or new accessibility labels masquerading as upstream output.
3. Integration coordinator: real contained bot, same scenario in both modes, full state/update/
   history comparisons, original captures, clipboard paste, response-loss recovery, isolation and
   public reports. Reuse existing passing cases only when exact input equivalence is established.

Automatic scrolling, disclosure expansion and long-press need their own original input steps
and evidence. An offscreen target initially reports unavailable before any tap; that is an
explicit gap, not completed support for arbitrary messages. The operational gate must include
representative long/RTL/nested consumer messages and the placements they actually use. A short
LTR callback-only demonstration does not finish public rich-button support or the operational
milestone. URL/navigation and Mini Apps retain their separate scope and network rules.

The main tradeoff is making a small GPL observation seam permanent and adding target/receipt and
client-local effect semantics. Keeping manual coordinates would not provide reliable public
identity; fabricating callbacks would not exercise the original client. The recommendation needs
approval under [AGENTS.md](../../AGENTS.md) before those behavior and bridge changes begin.
