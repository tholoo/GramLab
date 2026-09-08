# Expose typed documents through Bot API and client bridge HTTP

Type: task
Status: ready-for-agent
Work state: claimed — coordinator Bot API slice; client bridge remains unassigned
Blocked by: 99

Complete the HTTP layer of the [frozen document contract](../../../docs/development/documents-implementation-contract.md)
after the typed World implementation is integrated. Multipart decoding100 is resolved. This task
must use real contained HTTP and authoritative World state; collection against a missing World
interface is not behavioral acceptance. Native codec101 proceeds independently.

Root coordinates two non-overlapping ownership slices after99: Bot API (`src/gramlab/bot_api.py`,
new `tests/test_document_http.py`) and client bridge (`src/gramlab/client_bridge.py`, new
`tests/test_document_bridge.py`). Each assigned worker gets a separate ticket/worktree if both
slices run in parallel. Shared docs and combined verification stay coordinator-owned.

## Bot API slice

Add sendDocument multipart upload, attach references and bot-scoped file-ID reuse. Accept only the
contracted chat/document/caption/caption_entities/reply_markup/disable_content_type_detection
fields. New uploads require explicit true for the detection flag; reject default/false uploads
with an honest unsupported error until the unresolved detection policy is implemented. File-ID
reuse retains the already typed file. Do not inspect media bytes or equate false with true.
Reject URL/path imports, thumbnails, extra/missing/unused attachments and unsupported parameters
before publication. Decode metadata exactly once and pass DocumentUpload values to World.

Allow the local50,000,000-byte per-document bound with method-specific multipart request admission;
retain all current photo/other-method and text/header/part-count limits. Test the actual inclusive
boundary sequentially, promptly releasing large temporary buffers and databases. Project complete
Bot API Message/Document/callback responses. getFile returns only official File fields, and the
exact documents/FILE_ID download route serves original bytes with MIME fallback for empty semantic
MIME. Presentation filename never forms a host path or route. Preserve all existing image routes.

## Client bridge slice

Expose explicit v5 snapshot/change/callback/send and retained image/custom-emoji routes using the
existing capabilities, exact response shapes and original replay behavior. Add v5/documents/ID
with exact bytes, no-store, Content-Length, closed connection and empty-MIME transport fallback.
Unknown/ungranted documents return indistinguishable schema5 document_unavailable errors. Retain
strict ID/query/Range/framing/authentication rules and old-route outputs. Legacy document-bearing
responses reject before mutation/cursor advancement. Read document response dependencies coherently
from World; do not construct an independent registry or second simulator state.

## Acceptance and completion

Exercise actual JSON/form/multipart HTTP, Unicode/invalid filename decoding, caption/custom emoji,
keyboard callbacks, complete replies/history/events, reuse and reopen, same-byte typed separation,
cross-bot/persona/World denial, malformed IDs/requests and zero/oversized files. Assert rejected
requests leave complete logical SQLite state unchanged. Verify mixed v5 dependencies, frozen
callback retries, legacy rejection and unchanged photo/emoji responses. Keep complete structured
expectations independently specified; no mocked HTTP handlers or stand-in World implementation.

Follow TESTING.md, offline safety and parallel workflow. Run focused affected HTTP/World/bridge
checks, strict typing and Ruff before coordinator combined verification. No guest/build/network,
new dependencies or upstream exports. First forced-file HTTP support does not complete default
classification, document edits, albums, Android loading or the operational milestone.
