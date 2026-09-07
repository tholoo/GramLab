# Own media per World and preserve native input effects

Accepted by the user on 2026-09-07 after review of the four concrete proposals. Store immutable
validated media within its World, publish it atomically with recipient grants, and use separate
bot file identities and authenticated local client delivery through original Android FileLoader.
Retain published grants until World deletion so edits and interrupted/restarted downloads remain
consistent. Knowing a media identifier does not authorize access; native cache state belongs to
one World lifetime. See the [media decision](../development/rich-photo-proposal.md).

Use a World-wide synthetic custom-emoji catalog with chosen or allocated logical IDs, preserving
message fallback text. Model fixture availability independently of production ownership/Premium.
Resolve named-user mentions from authoritative World identities with bot-knowledge admission and
message-derived recipient disclosure. Coordinate a successor bridge schema for identity and media
dependencies. See [custom emoji](../development/custom-emoji-proposal.md) and
[mentions](../development/rich-mention-proposal.md).

Expose rich-button occurrences through revision- and client-lifetime-bound single-use targets.
Preserve ordinary native touch and action dispatch, distinguish rejection before dispatch from
uncertain effects after dispatch, and never automatically repeat an uncertain tap. Clipboard
semantics belong to the client instance. The permanent observation seam stays in the GPL adapter;
MIT code does not recreate native layout. See [targeting](../development/rich-button-targeting-proposal.md).

These choices extend the approved shared-world foundation; they do not establish implementation
or fidelity evidence. PNG/JPEG photos, files, rich messages and static/animated custom emoji remain
required for operational use. Mini Apps remain in the full goal but may follow later. The decisions
do not authorize real accounts, Telegram DCs, external runtime traffic or artifact publication.
