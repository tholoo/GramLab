# Publish typed ordinary documents through World and version-5 projections

Type: task
Status: ready-for-agent
Work state: resolved
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

## Implementation

`DocumentUpload` is an immutable typed value that admits exact `bytes` from 1 through 50,000,000
bytes, preserves the decoded filename and declared content type for inspection, and derives its
semantic filename, MIME, digest and stable namespaced comparison identity from the pinned metadata
helpers. World schema 9 adds the three frozen typed tables over schema-8 `media_blobs`. Fresh and
migrated schemas agree, and the migration serializes openers, checks foreign keys and updates the
version last in one transaction.

`World.send_document` accepts one exact attachment or a bot-scoped document file ID. It stores or
reuses neutral bytes and typed metadata, allocates a document ID independently of image/emoji IDs,
creates a separate opaque identity per bot, publishes the full ordinary message, grants the chat
recipient, and journals the message in one caller-owned writer transaction. Public descriptor,
Bot API file, bot download and persona grant methods enforce canonical decimal IDs and typed
authorization. Existing photo/emoji file IDs do not cross into the document namespace, and
`edit_message` rejects ordinary document conversion.

Version-5 World snapshots, change pages and callback dependencies preserve v4 users/assets/custom
emoji fields and add exact sorted document descriptors. Snapshots cover all retained persona
grants; changes and callbacks cover only their returned historical messages. Callback dependency
resolution holds one SQLite read snapshot. Versions 1–4 reject document-bearing selections before
callback insertion or any visible cursor change. HTTP routing, default content detection, Android
mapping, albums and document edits remain separate work and are not claimed here.
Existing rich-content mention dependencies remain present in v5 outputs. Ordinary caption
`text_mention` remains rejected by the existing `formatting_entities` admission boundary; this
batch does not silently add that unsupported formatting kind.

## Worker verification

- The untouched base-source probe fails with `ModuleNotFoundError: gramlab.documents`, preserving
  the missing typed interface red. The temporary source export and tar were removed immediately.
- `tests/fixtures/document_storage_v8/` was generated offline before modifying World from base
  `df1e67e6c61ba2b63c8883732863aca2e714d6b6`, whose World source SHA-256 was
  `a57a4b88f05ae25ab93b67f3132f25fd3415a6d45ec206d53efa2f7dc1d2d8f3`. Its retained SQL and
  complete v4 public outputs prove existing photo/emoji grants, identities, histories, events,
  callback retries and exact bytes across migration and reopen.
- `artifacts/ticket99-focused.xml` retains 96 passing document, schema migration, media, callback,
  client bridge, custom-emoji and rich-mention bridge cases in the outer local network namespace.
  This includes the actual inclusive 50,000,000-byte input, sequential oversized rejection,
  rollback/retry, concurrent openers, full v5 projections and typed isolation.
- Follow-up review closed the concurrent writer connection explicitly and added seeded, persisted
  allocation controls for IDs 10, 2,147,483,648, 9,007,199,254,740,993 and signed-64-bit maximum.
  Exact file/download, grant, v5 snapshot/change/callback and reopen results pass, including numeric
  dependency sorting. Exhaustion and an `AFTER INSERT` document-grant interruption preserve the
  complete logical database; retry after the interruption receives message/document ID 1.
  `artifacts/ticket99-focused-followup.xml` retains all 102 focused cases passing with
  `ResourceWarning` promoted to an error.
- Scoped Ruff check and format pass seven owned/affected Python files. Strict mypy passes the same
  seven files with the tests path explicitly available. No Android guest/build, full gate, network,
  dependency or upstream source operation ran. Remote/cloud admission and operational document
  support remain unproven; coordinator integration and combined verification remain pending.

After recreating the dedicated `.venv` according to `TESTING.md`, reproduction uses the offline
environment:

```sh
tools/dev default --offline --command unshare --user --map-root-user --net bash -eu -c \
  'ip link set lo up; .venv/bin/python -m pytest -q -W error::ResourceWarning \
  --junitxml=artifacts/ticket99-focused-followup.xml tests/test_document_world.py \
  tests/test_document_storage_migration.py tests/test_media_world.py \
  tests/test_media_storage_migration.py tests/test_callbacks.py tests/test_client_bridge.py \
  tests/test_media_bridge.py tests/test_custom_emoji_world.py tests/test_custom_emoji_bridge.py \
  tests/test_rich_mentions_bridge.py'
tools/dev default --offline --command .venv/bin/python -m ruff check \
  src/gramlab/world.py src/gramlab/documents.py tests/test_document_world.py \
  tests/test_document_storage_migration.py tests/test_media_world.py \
  tests/test_media_storage_migration.py tests/fixtures/document_storage_v8/generate.py
tools/dev default --offline --command env MYPYPATH=tests .venv/bin/python -m mypy --strict \
  src/gramlab/world.py src/gramlab/documents.py tests/test_document_world.py \
  tests/test_document_storage_migration.py tests/test_media_world.py \
  tests/test_media_storage_migration.py tests/fixtures/document_storage_v8/generate.py
```

## Integrated acceptance

Core16 passes all 1,126 non-Android cases at 88.02% coverage on the integrated branch;
static15 passes all 64 documented commands and configuration/links in 259 Markdown files.
The retained core16 JUnit, log and outcome establish combined verification after this slice.
This resolves the assigned slice, preserving its focused acceptance and earlier failed evidence.
It does not establish Android document loading, default classification, edits or albums.
