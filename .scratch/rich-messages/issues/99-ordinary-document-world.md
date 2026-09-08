# Publish typed ordinary documents through World and version-5 projections

Type: task
Status: ready-for-agent
Work state: open
Blocked by: none

Implement the World portion of the frozen [document contract](../../../docs/development/documents-implementation-contract.md).
The pinned metadata helpers are integrated. This task supplies ordinary typed storage, bot file
reuse/download, recipient grants and coherent version-5 World responses. HTTP and Android are
separate dependent integration tasks; do not claim operational document support from World tests.

## Ownership

Own this ticket; `src/gramlab/world.py`; new `src/gramlab/documents.py`;
`tests/test_document_world.py`; `tests/test_document_storage_migration.py`; bounded original
legacy fixtures under `tests/fixtures/document_storage_v8/`; and necessary schema-version/legacy
fixture maintenance in `tests/test_media_world.py` and `tests/test_media_storage_migration.py`.
Coordinator owns bot_api/client_bridge/native files, shared docs, CI and lockfiles. Request any
additional ownership before touching it; do not work around a missing integration by changing an
unowned test or returning invented legacy success.

Follow the contract exactly for DocumentUpload, admission/identity, schema9 tables, public method
names and return shapes, canonical string IDs, bot_file extension, retained grants, caption/entity
and keyboard behavior, v5 dependencies and strict legacy rejection. Keep neutral bytes shared but
all typed identities and authorization independent. Use one caller-owned transaction for complete
publication; helpers must not commit separately. This first World method deliberately creates an
ordinary typed file; it does not classify uploaded media or implement HTTP default detection.

## Acceptance

Use public World methods to compare complete messages, histories/events, callback captures/retries,
file metadata and bytes, v5 snapshots/change pages and immutable historical dependencies. Exercise
same-bot reuse, a separate bot's independently uploaded identity, different metadata for identical
bytes, image/emoji/document ID confusion, cross-persona/cross-World access, and retained old grants.
Invalid/extra/missing attachments, zero or oversized payloads, non-byte/type errors, external/path
strings, malformed IDs/captions/keyboards and unauthorized senders must leave all public state and
allocation unchanged. Include actual inclusive local byte-boundary admission and rejection; keep
large temporary inputs sequential and promptly release them. Empty/unknown MIME is permitted
metadata, not a reason to reject an ordinary file or apply an image decoder.

v1–v4 must retain exact supported-content outputs and reject selected document responses before
callback mutation or cursor advance. v5 responses must preserve full ordinary/photo/emoji fields
while adding sorted exact document dependencies, including frozen callbacks and old change
versions after later unrelated activity. Existing text-edit entry must reject document conversion.
Do not add undeclared HTTP routes or enable native negotiation.

Generate an authentic populated schema8 legacy fixture using untouched assignment-base source,
with existing photo/emoji grants, file identities, histories/events and callback retry evidence.
Record source hashes and independently retained literal outputs. Prove identical existing results
after migration/reopen, fresh/migrated schema agreement, FK integrity, concurrent opening and
rollback/retry at migration/publication boundaries. Do not manufacture legacy expected outputs
using a downgraded current implementation. Explicitly close fixture database connections.

Run focused document/migration/media/custom-emoji/callback/bridge World checks in the assigned
checkout's pinned isolated environment, plus scoped Ruff and strict mypy. Preserve genuine red/
green evidence; a collected-but-unavailable dependent HTTP/native suite is not a pass. No Android
guest/build, full gate, network, dependency change or upstream source export. Keep legacy export
minimal and retire disposable build/runtime data after preserving its outputs and source hashes.
Freeze a clean actual Git tip with full checks/evidence and terminal process state; root reviews,
merges and runs the combined gate before shared documentation claims implementation.
