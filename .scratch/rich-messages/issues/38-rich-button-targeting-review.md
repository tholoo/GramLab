# Review public rich-button targets and input receipts

The user explicitly approved all four prepared designs and then resumed the goal. This approval
supersedes the pending-consultation instructions retained below as proposal history. Proceed with
the recommended direction; freeze shared implementation contracts before parallel dispatch.

Type: task
Status: ready-for-agent
Work state: design approved; implementation pending
Blocked by: none; user approved all four designs on 2026-09-07

The [proposal](../../../docs/development/rich-button-targeting-proposal.md) turns the existing
original callback/copy/disabled experiments into a reviewable public interface. It recommends
canonical occurrence paths, message journal revisions, opaque run-bound single-use targets,
explicit dispatch uncertainty, ordinary native input and client-instance clipboard semantics.
No implementation or approval follows from preparing this proposal.

Source review confirmed that existing scenario input selects reply-markup row/column cells;
rich geometry remains opt-in, short LTR, two-target and non-atomic. Current World edits use the
simulated clock, while journal event sequences distinguish same-clock and A → B → A edits.
The callback transport accepts a message and payload but carries no scenario target identity.
The proposed revision/correlation seam therefore requires implementation and independent proof.

After consultation, freeze shared schemas and split core/SDK, GPL observation/input and integrated
real-bot acceptance into separate worker tickets. Coordinate the next bridge schema with mentions
and any approved media metadata. Do not count short LTR input, fresh timestamps or label equality
as complete targeting evidence. Preserve RTL/nesting, duplicate/stale input, effects, response-loss
and actual original rendering requirements.

Independent review required explicit client-lifetime invalidation, consumption on pre-dispatch
rejection and classification of the native-tap/current-World-snapshot race. The proposal now
freezes those choices without changing ordinary callback admission. A guarded disposable World
experiment verifies identical full message bodies across same-clock A → B → A edits with distinct
journal sequences, and no new event for a rejected no-op edit. Local evidence remains ignored.
