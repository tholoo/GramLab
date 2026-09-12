# First operational milestone

The user requires ordinary messages/buttons and callback-driven edits, rich messages, uploaded
photos/files, and custom emoji for the first operational milestone. Mini Apps may follow later;
they remain in the full [product inventory](../product/requirements.md). A text-only integration
or a static PNG demonstration does not complete this milestone.

Use representative consumer workflows to evaluate readiness through real Bot API requests,
matching simulation/Android semantics, original rendering/input and restart/recovery. Keep public
tests and fixtures independent of consumer application names, code and configuration. The
read-only inventory below identifies immediate method/media and custom-emoji requirements; broader
consumer acceptance still needs executable scenarios. Do not treat unsupported features as optional.

Current [compatibility evidence](../compatibility/matrix.md) establishes bounded text/callback,
formatting, rich-block and explicit mention loops. PNG/JPEG lifecycle, shared completion and
unchanged-photo cache reuse pass focused native acceptance. Custom-emoji lifecycle/faults and public
rich-button actions now have strong bounded original-client evidence, but still need current-APK and
final representative composition. Wider native regression, default document classification and
albums remain open. The four designs approved on 2026-09-07 remain the direction.
Quoted-code correction is complete at its documented checkpoint. Prioritize the remaining
consumer-facing media/emoji/action gaps; HTML parsing and automatic detection are also unsupported.
Keep developer tooling/research bounded to blockers in those workflows.

Track acceptance in the current [handoff](handoff.md) and individual tickets. Readiness requires
complete semantic comparisons, original visual evidence where relevant, isolation, useful reports
and honest unsupported-feature errors. Neither aggregate test counts nor individual successful
screenshots establish operational readiness for the entire required workflow.

A read-only workflow inventory prioritizes structural rich formatting over HTML parse modes for
the first representative consumer flow. Keep HTML in the full library inventory. The immediate
flow needs polling startup, rich links/mentions/custom emoji, callback-driven edits and multipart
photo/file reuse. It also leaves `skip_entity_detection` at its normal default; requiring a
consumer to force it off is not equivalent compatibility. Incoming custom-emoji entities must
survive update delivery as well as outgoing rendering. Preserve these requirements when ordering
implementation; a smaller explicit-entity example cannot stand in for this flow. Consumer-specific
source locations and configuration stay in ignored local notes.

The representative asset workflow requires JPEG as well as PNG photos, reusable photo IDs and
collages/album paths. The animated custom-emoji profile must include transparent VP9 WebM;
TGS-only evidence would leave that required path untested. Custom emoji must work in rich button
labels as well as message content and incoming ordinary entities. Preserve supplied logical IDs
and message fallback text at the scenario/application boundary; do not invent an owner-bot or
catalog-fallback-equality restriction from sticker administration prerequisites. The approved synthetic
catalog/admission design distinguishes logical emoji IDs from
bot-scoped file identities and recipient media access. Static/animated fixtures can be prepared
independently while that design is reviewed.


Original PNG, JPEG, WebP and transparent VP9 WebM fixture inputs now have independent decoding
evidence. JPEG/WebP/WebM reproduce under the pinned media shell. These inputs unblock later media
acceptance tests; they do not establish storage, file reuse, albums or original Android playback.
