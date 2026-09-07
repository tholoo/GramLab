# First operational milestone

The user requires ordinary messages/buttons and callback-driven edits, rich messages, uploaded
photos/files, and custom emoji for the first operational milestone. Mini Apps may follow later;
they remain in the full [product inventory](../product/requirements.md). A text-only integration
or a static PNG demonstration does not complete this milestone.

Use representative consumer workflows to evaluate readiness through real Bot API requests,
matching simulation/Android semantics, original rendering/input and restart/recovery. Keep public
tests and fixtures independent of consumer application names, code and configuration. Exact
required methods/media formats and custom-emoji behaviors still need a concrete workflow inventory;
do not convert that missing inventory into an assumption that every unsupported feature is optional.

Current [compatibility evidence](../compatibility/matrix.md) establishes bounded text/callback,
formatting and rich-block loops. Media storage/delivery and custom-emoji document support remain
unimplemented. The [photo design](rich-photo-proposal.md) still requires consultation; the required
feature list alone does not approve its consequential architecture choices. HTML parsing is also
unsupported. Prioritize closing consumer-facing gaps after the current quoted-code correction;
keep developer tooling/research bounded to blockers in those workflows.

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
