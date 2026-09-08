# Deliver ordinary documents through the original Android loader

Type: task
Status: ready-for-agent
Work state: unassigned
Blocked by: none for implementation; actual codec101 native acceptance remains pending

Implement the GPL adapter side of the [frozen document contract](../../../docs/development/documents-implementation-contract.md).
World99, Bot API102, v5 HTTP103 and codec101 are integrated. The codec's host checks pass; its actual
native gate remains coordinator-owned. Preserve the complete operational scope; this is the next
single-document delivery slice, not completion of classification, edits, albums or the full goal.

## Ownership and dependencies

Own this ticket, new `clients/android/patches/0030-ordinary-document-delivery.patch`, its series
append, new `tests/test_android_document_delivery.py`, `tests/probes/android_document_delivery.py`
and GPL fixtures under `tests/fixtures/android_document_delivery/`. Keep production code entirely
within the existing Android GPL patch boundary. Do not edit Python core, existing tests, shared
contracts, runner selectors, lockfiles or dependencies. Report any required integration adjustment
to the coordinator. Use a private worktree and only minimal touched-source staging; no full source
copy/export, live build mutation, APK build or guest run. Coordinator owns native execution.

The patch may extend `GramLabMedia`, `GramLabBridge` and `FileLoader` at their existing synthetic
seams. Codec101's strict `GramLabDocument.Entry`, `parse` and `project` are fixed dependencies.
Reuse the existing response scope/epoch mechanism, original message/media classes and loader
callbacks. Do not fabricate image dimensions or adapt a document into an image Asset.

## Response and message application

Negotiate version5 explicitly and retain supported v4 behavior. Extend the response scope with a
distinct ordinary-document map and used-ID set; the existing map named documents contains custom
emoji and must remain separate. Install immutable ordinary dependencies before message decoding.
Reject changed metadata under an existing ID, missing dependencies, malformed/mixed carriers and
inconsistent bindings before publishing state. Snapshots may contain unused retained grants;
changes/callbacks must retain exact historical dependencies and frozen retry semantics. Keep
response validation/commit atomic, including users, images and custom emoji.

Map the canonical ordinary document message to the original `TL_messageMediaDocument` using
codec101 and existing caption entities/keyboards. Retain negative ordinary IDs and positive custom
emoji IDs at DC-1, including magnitudes2147483648 and9223372036854775807. Native adapters must not
interpret canonical decimal strings through a floating-point value or narrow integer.

Preserve original classification as well as drawing: pinned `MessageObject` recognizes image/gif
MIME as GIF even without specialized attributes. A typed ordinary descriptor therefore does not
promise TYPE_FILE for every MIME. Keep canonical MIME and original classification unchanged;
include a real native GIF classification control, and report its resulting original behavior.
Do not rewrite MIME or modify drawing/classification to force every payload into a file row.

## Original loading and destinations

Resolve both reserved Document and ImageLocation loading entry points locally before the original
Integer.MIN_VALUE filename guard or a remote queue. Known negative IDs fetch authenticated
`/v5/documents/D`; positive custom emoji keep their existing route and authority. Unknown reserved
IDs and streams fail locally. Include document-specific trace identity (`document_id`), never a
fabricated `asset_id`, and preserve credential redaction.

Validate exact declared length and SHA before publication; use octet-stream only as transport
fallback for empty MIME. Reuse bounded transfer cancellation, retry, progress, shared consumers,
cleanup and original notifications. Keep original saved-path lookup and cache-type destination
selection, including cache types0/10 and canSaveAsFile. Publish to the original sanitized filename
with original collision suffix behavior where applicable; persist the actual final destination in
FilePathDatabase. A concurrent same-name file must never be overwritten. Preserve keyed cache
destinations for the other applicable modes and handle stale saved paths through the original
semantics. Do not instantiate a remote FileLoadOperation just to borrow a helper.

The private bot adapter has no encrypted/secret-chat delivery implementation. An encrypted-cache
request must fail explicitly before writing, not create plaintext under encrypted-cache semantics.
Record that limitation; this task does not claim secret-chat or local encrypted-cache support.

## Acceptance and handoff

Prepare an actual native probe using original classes, with independently specified full outputs
and no replacement TLRPC/loader implementation. Cover valid v5 mixed responses, rejected-response
atomicity, missing/extra/changed dependencies, historical callback replay and unchanged v4 controls.
Cover both loader entry points and full-range IDs; exact bytes, wrong digest/length/truncation,
cancel/retry, coalescing, unknown IDs, local stream/encryption rejection, saved and missing paths,
concurrent equal filenames, persisted destinations, warm cache and cold restart. Original rows,
captions/custom emoji and keyboard callbacks need real UI evidence alongside complete World/API
state comparisons. Host substitutes may validate orchestration but cannot certify these behaviors.

Follow TESTING.md, licensing, offline safety and the parallel workflow. Run focused host checks,
strict typing, Ruff, Java/D8 compilation and minimal patch staging from the assigned checkout.
Keep red/green evidence and explain unavailable native checks honestly. Report stable probe inputs,
required native run plan and exact frozen branch tip; stop all owned processes before handoff.
Coordinator reviews/merges, builds and runs native acceptance, then enables the host's explicit v5
selector in runner, CLI and Android orchestration only after the delivery contract is verified.
