# Expose typed documents through Bot API and client bridge HTTP

Type: task
Status: ready-for-agent
Work state: resolved
Blocked by: none

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

## Bot API implementation and acceptance

The Bot API slice implements explicit forced-file multipart uploads, named attachments and typed
file-ID reuse, complete Message/Document/callback projection, official getFile fields and exact
authenticated downloads. The local inclusive50,000,000-byte document bound is exercised with real
upload/download bytes while oversized photos retain their old request bound. Default/false uploads
return the exact unsupported detection envelope. Original PNG bytes can independently become a
forced document or photo without identity, route or reuse crossover. Custom emoji survive caption
HTTP projection, retained recipient grants and reopening; an unknown emoji rejects atomically.

Initial four real HTTP cases failed on unsupported sendDocument. The expanded affected run passed
49 cases and exposed one test expectation error: a mismatched download route correctly returns404,
not400. After correcting that assertion and adding exact unsupported envelopes, the changed test
passes separately; the other49 results remain valid. Earlier boundary-test BrokenPipe was caused
by sending a full body after the server correctly rejected its declared photo length; the corrected
header-only request verifies the original early rejection. Ruff lint/format and strict Mypy pass.
Retained JUnits: document-http-red-01, document-http-acceptance-03 and document-http-review-04.

Coordinator integration and combined verification remain. This does not establish default file
classification, document edits/albums or original Android file loading.

Primary integration passes all50 affected HTTP checks with ResourceWarning fatal and strict
Mypy/Ruff. The retained integrated JUnit is document-http-integrated-01.xml. Combined verification
remains; client HTTP103 and native delivery have separate acceptance.

## Integrated acceptance

Core16 passes all 1,126 non-Android cases at 88.02% coverage on the integrated branch;
static15 passes all 64 documented commands and configuration/links in 259 Markdown files.
The retained core16 JUnit, log and outcome establish combined verification after this slice.
This resolves the assigned slice, preserving its focused acceptance and earlier failed evidence.
It does not establish Android document loading, default classification, edits or albums.
