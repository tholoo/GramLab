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

The [representative workflow](representative-workflow.md) now composes those surfaces through one
public real bot in simulation and the original normal31 Android renderer. Its evidence includes
default automatic detection, explicit rich entities, ordinary/rich callbacks and edits, restart
replay, PNG/JPEG reuse, default/forced documents, photo/document albums, and static/animated custom
emoji. The five original captures and complete World/Bot API/bridge/input comparisons are retained.
This resolves the first operational milestone at its approved fidelity boundary. It does not make
the wider product inventory complete: HTML parsing, grouped-media edits, external conformance,
interactive mode and Mini Apps remain outside this milestone.

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


Original PNG, JPEG, WebP and transparent VP9 WebM fixture inputs have independent decoding evidence.
The representative run additionally proves their required local storage, reuse, album and original
Android paths; this remains bounded local evidence rather than production-service conformance.
