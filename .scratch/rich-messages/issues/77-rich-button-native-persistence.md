# Preserve exact rich-button provenance through original message storage

Type: task
Status: ready-for-review
Work state: frozen on task/rich-button-native-persistence
Blocked by: coordinator integration and native acceptance

Own this ticket and new `clients/android/patches/0026-rich-button-local-provenance.patch`.
Coordinator owns series registration, shared documentation, builds and guest gates. Follow the
frozen rich-button contract, testing, licensing and parallel-work requirements.

Normal25 displays the intended controls but publishes no observation. The retained original
Android diagnostic proves that TL serialization reconstructs both row and inline button objects
without their identity bindings. Stock message history uses that deserialize path before drawing.
The actual private activation and foreground checks already succeed after the separate host fix.

Preserve provenance in the existing message-local `custom_params` storage path. Dedicated local
fields on `TLRPC.Message` may carry the exact applied revision and bounded canonical occurrence
metadata captured alongside that same bridge response. Extend `MessageCustomParamsHelper` version1
with an unused flag and trailing local data; preserve all existing fields and native wire encoding.
Restore bindings against the final reconstructed rich tree before original UI publication.
Do not change public v4, private schema1, rendering, input handlers or native TL serialization.

The metadata is all-or-nothing: a version, exact positive applied revision, ordered canonical
paths and complete canonical buttons. Bound UTF-8 data to 1 MiB and existing path/node limits.
Validate the entire known-container topology before publishing any bindings. Missing, malformed,
oversized, duplicate, mismatched or ambiguous provenance must never grant a target. Pair exact
final objects through explicit structural traversal; no label, payload, geometry, hash or latest
World matching. Preserve original content even when observation metadata is unavailable.

Revision provenance belongs to the exact message row. Same-clock A→B→A must retain distinct
applied revisions after each write/load and after reopening storage. Metadata copy must never
overwrite authoritative destination provenance or inherit stale provenance into a distinct new
message. Include button-free and ordinary replacement cases when defining absence versus an
authoritative empty set. Preserve bounded observer retention and any already armed group.
Inspect stock edit paths that read old local params into a new message, including `load_type == -2`
and `replaceMessageIfExists`. Incoming authoritative metadata must win, and every path that writes
new message data must persist matching provenance. Metadata-only reads into an empty message must
defer object binding safely. A narrow `MessagesStorage.java` correction is within scope if needed
to preserve these properties; document the actual adapter call path and unchanged stock behavior.

Use only the coordinator-supplied normal25 source as read-only input, staging affected files in
an ignored worker directory. Expected patch scope is `TLRPC.java`, `MessageCustomParamsHelper.java`
and the GramLab bridge/rich decoder/observer. Request scope changes before touching other sources.
No full source export, source-tree mutation, guest, Gradle build, Python change or series edit.

Before implementation, specify exact local field names, metadata bytes and helper entry points
for independent regression work. Demonstrate zero-fuzz/offset application and focused compilation
when available. Native acceptance must cover complete original message plus local params through
SQLite write/load/reopen, A→B→A and invalid metadata; a bare RichMessage round trip diagnoses the
bug but is not final acceptance. The coordinator owns the actual public input and clipboard gate.
Return a clean frozen branch with exact hashes, focused evidence and remaining native gaps.

## Coordinator red evidence

The uninstrumented public gate fails at its first observation. A separate original screenshot
shows row and inline controls in the intended viewport, and the private activation file reads
successfully while the observation file is absent. The standalone actual Android serialization
diagnostic reports both original objects mapped, both identities changed, and both rebuilt objects
unmapped, followed by the expected failing assertion. These are retained failures, not acceptance.

## Worker evidence

Patch 0026 stores immutable schema-1 UTF-8 occurrence provenance and its exact applied revision in
stock message `custom_params` under unused v1 flag 14. Authoritative empty records clear prior
button metadata. Restore validates strict JSON, exact canonical paths, complete canonical buttons
and reconstructed row/inline object kinds before publishing any identity binding. Invalid metadata
clears only GramLab provenance and preserves message content.

Stock load-type -2 and replace-if-existing paths retain incoming destination provenance while
merging old stock local parameters. Custom-only metadata reads defer topology binding while preserving validated row-local provenance;
updates never copy caller provenance. Malformed GramLab extension data clears only the extension after
already decoded stock fields, and canonical comparison treats JSON object member order as immaterial.
Final known-container traversal enforces depth and node budgets and invalid restore removes stale
non-armed bindings for the same reconstructed objects. The four adapter/TL/helper sources compile with
`javac -proc:none` against normal25 and cached dependencies. Standalone `MessagesStorage` checking
reaches the source but remains unavailable because the cached classpath exposes an unrelated
`LinkedHashMap.Entry` visibility mismatch. No Gradle build or guest was run.
