# Freeze and implement default document classification

Type: task
Status: ready-for-agent
Work state: claimed
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
