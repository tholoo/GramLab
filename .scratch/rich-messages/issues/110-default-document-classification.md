# Freeze and implement default document classification

Type: task
Status: ready-for-agent
Work state: resolved
Owner: default-document-classification
Blocked by: none

The source-backed forced-file document path is complete, but omitted/false
`disable_content_type_detection` still rejects. The proposed bounded policy is documented in
[default-document-classification-proposal.md](../../../docs/development/default-document-classification-proposal.md).
It preserves PNG/JPEG and other general files as documents and rejects a fixed set of recognized
specialized families until their complete typed contracts exist.

Do not implement or assign this ticket until the user approves the local-policy consequences and
signature table. After approval, give one worker ownership of a new pure admission interface,
`require_supported_default_document(upload: DocumentUpload) -> None`, the narrow Bot API send/edit
admission changes, and independent focused classification/HTTP/media-edit tests. Do not change
World schema, bridge schemas, Android patches or existing forced-file behavior.
Serialize this work with album core work because both touch multipart InputMedia parsing in
`bot_api.py`.

Acceptance must prove omitted/false equivalence, unchanged true and reuse behavior, exact and
near-signature cases, 50,000,000-byte boundaries, atomic rejection/retry, contained real-bot use and
unchanged ordinary-document projection. The result establishes a documented local emulation only.

## Approval

On 2026-09-12 the user approved the complete recommended policy and signature table. Implement the
bounded classifier exactly as frozen; this approval does not authorize partial specialized-media
objects or a Telegram-parity claim.

## Implementation handoff

The assigned worker implemented the frozen pure
`require_supported_default_document(upload: DocumentUpload) -> None` boundary and invokes it only
for fresh multipart `sendDocument` and standalone `InputMediaDocument` uploads when
`disable_content_type_detection` is omitted or false. Explicit true and typed `file_id` reuse keep
their existing paths. No World, bridge, schema or Android file changed.

The classifier covers every frozen exact discriminator and admits named near/short controls,
ordinary PNG/JPEG/PDF/ZIP/text/opaque bytes and generic gzip. Focused HTTP cases prove
omitted/false equivalence, declared-content-type independence, the inclusive 50,000,000-byte
boundary, exact Bot API document projection, complete SQLite rollback, forced retry, reuse, and
atomic standalone media edits. A contained real bot independently uploads an ordinary default
document and receives the stable specialized-family rejection. The coordinator explicitly
expanded ownership to the obsolete classification assertions in `tests/test_document_http.py`;
unrelated forced-file, reuse, validation and media-edit coverage was preserved.

Red evidence is retained at
`artifacts/default-document-classification-red-interface-01.xml` (the required public interface
was absent) and `artifacts/default-document-classification-red-http-02.xml` (18/18 cases exposed
the old unconditional omitted/false rejection). Green evidence is retained at
`artifacts/default-document-classification-green-affected-http-02.xml` (70/70) and
`artifacts/default-document-classification-green-contained-02.xml` (3/3, including the existing
forced-document lifecycle). The affected strict mypy scopes pass for six core/HTTP files and three
contained-scenario files; Ruff check and format-check pass across all nine checked files. Android
was not run because admitted output remains the already verified ordinary-document projection and
this ticket owns no client change. Work state remained claimed until coordinator integration and
combined verification, as required by the parallel workflow.

## Integration

The coordinator reviewed commit `32cb8b2`, reran73 affected HTTP/media-edit/contained-bot cases in
a loopback-only namespace, and passed the strict typing and Ruff scopes on the merged tree. The
approved classifier is integrated; ticket112 is released for serialized album-core implementation.
