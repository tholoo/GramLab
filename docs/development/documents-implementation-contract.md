# Ordinary document implementation contract

This first implementation batch extends the approved [media architecture](../adr/0005-local-media-and-client-interaction-boundaries.md)
and [source contract](documents-references.md). It is not completed file compatibility. General
files, default content classification, edits and albums remain required for the operational
milestone; the first batch establishes typed ordinary files, upload/reuse/download and versioned
client delivery. Mini Apps remain in the full product scope.

## Immutable typed files

Keep schema-8 `media_blobs` shared by digest, with independent typed image and document metadata.
Schema 9 adds:

- `documents(id INTEGER PRIMARY KEY, sha256 TEXT NOT NULL REFERENCES media_blobs(sha256),
  file_name TEXT NOT NULL, mime_type TEXT NOT NULL, file_unique_id TEXT NOT NULL UNIQUE,
  UNIQUE(sha256, file_name, mime_type))`.
- `bot_document_files(bot_id INTEGER NOT NULL REFERENCES bots(id), file_id TEXT NOT NULL UNIQUE,
  document_id INTEGER NOT NULL REFERENCES documents(id), PRIMARY KEY(bot_id, document_id))`.
- `document_grants(user_id INTEGER NOT NULL REFERENCES users(id),
  document_id INTEGER NOT NULL REFERENCES documents(id), PRIMARY KEY(user_id, document_id))`.

Migration adds these empty tables atomically without changing existing image metadata, bytes,
file identities, grants, histories, revisions or callback retry results. Fresh and migrated schema
must agree; update the schema version last and serialize concurrent openers. Preserve every
previously supported migration path. Failed publication must roll back new bytes, documents,
identities, grants, messages and events together, without consuming public identifiers.

A document has a positive signed-64-bit local integer ID, encoded as a canonical positive decimal
string at public document boundaries. Allocate independently of image and custom-emoji IDs.
Zero, negatives, leading zeroes, signs, whitespace, floating values and overflow are invalid public
IDs. The immutable identity tuple is byte SHA-256, cleaned filename and derived MIME; captions,
keyboards and declared multipart MIME do not change it. A metadata change produces a different
ordinary document even when its bytes are shared. This is an explicit synthetic identity policy,
not a claim about Telegram's private file-ID allocation algorithm.

Use opaque `gramlab_document_` bot file IDs, persisted independently for each bot. The stable
`file_unique_id` is `gramlab_document_unique_` followed by the SHA-256 of UTF-8 JSON containing
`["document", sha256, file_name, mime_type]`, serialized with `ensure_ascii=False` and separators
`(',', ':')`. This namespaced comparison value cannot authorize reuse or download. A photo/emoji
file ID cannot be reused as a document, nor a document file ID as an image. Identical bytes or
matching local numeric IDs never transfer authorization between media kinds or Worlds.

## World boundary

Add an immutable `DocumentUpload(data: bytes, filename: str, content_type: str | None = None)`
value in `gramlab.documents`. Its filename is already decoded header metadata, never a path to
open. Preserve declared content type for inspection, but derive semantic filename/MIME using the
[ticket97 helpers](../../.scratch/rich-messages/issues/97-pinned-document-filename-metadata.md).
Reject non-byte payloads, empty files and malformed input types before publication. The initial
explicit GramLab per-document bound is 50,000,000 bytes inclusive. This is the local profile value;
exact remote cloud byte admission remains unproven. It does not adopt the local Bot API server's
multi-gigabyte upload mode or establish complete album request-memory behavior.

`World.send_document(*, chat_id, sender_id, document, uploads=None, caption=None,
caption_entities=None, reply_markup=None)` accepts `document={"media":"attach://NAME"}` or
`document={"media":"BOT_FILE_ID"}` with exactly that field. Uploads are a mapping from attachment
names to `DocumentUpload`; attachment names must match the single selected upload exactly. Only
the chat bot sends documents in this batch. A bot can acquire its own identity by uploading valid
bytes, never by presenting another bot's ID. Publication grants the chat recipient document
access in the same transaction, retaining that grant after later edits for the World lifetime.

The canonical message keeps ordinary identity/date/chat/sender fields and `text:""`, plus
`document:{"document_id":"1"}` and optional caption/entities/reply markup. Reuse the existing
1,024-code-point caption/entity checks, admission of custom emoji and mention dependencies, and
keyboard semantics. An empty caption follows the existing photo behavior. Do not silently convert
an ordinary document through an existing text-edit operation; reject unsupported document edit
forms until their dedicated implementation is present.

Add `document_descriptor(document_id)`, `document_file(bot_id, document_id)` and
`granted_document(user_id, document_id)`. The descriptor is exactly:

```json
{"document_id":"1","file_name":"report.pdf","mime_type":"application/pdf","file_size":1234,"sha256":"64 lowercase hex"}
```

`document_file` returns Bot API Document fields: bot-scoped `file_id`, `file_unique_id`,
`file_size`, and nonempty `file_name`/`mime_type` only. It contains no image dimensions or synthesized
thumbnail. `granted_document` returns `(descriptor, bytes)` after verifying the persona grant.
Extend `bot_file` to return existing `(info, bytes)` for typed document IDs, keeping all existing
image results unchanged. Its generated `file_path` is `documents/FILE_ID`; never include the
presentation filename. Preserve MIME metadata, including an empty derived MIME; HTTP binary
responses may use `application/octet-stream` when an empty MIME cannot form a useful header.

## Bridge version 5

Negotiate version 5 explicitly without fallback. Preserve exact v1–v4 supported-content results.
If a legacy response would expose a document, reject before mutation/cursor advance rather than
omit it. Add `documents` to v5 snapshots, changes and callbacks, retaining all v4 fields and rules.
Documents sort and deduplicate by numeric local ID, despite their decimal-string wire encoding.
Snapshot dependencies cover every retained persona document grant. Changes and callback responses
cover the exact returned historical message versions; callback retries keep their original message
and revision. Resolve authorization, messages and dependencies within one SQLite read snapshot.
Document captions continue to carry existing identity and custom-emoji dependencies.

`GET /v5/documents/ID` uses the existing client Bearer capability. Check authorization before
returning bytes; unknown and ungranted IDs both produce HTTP404 schema5 `document_unavailable` /
`Document is unavailable`. Existing authentication errors, loopback confinement, strict query and
Range rejection, exact Content-Length, no redirects, no-store and closed-connection transfer rules
apply. v5 retains the corresponding existing image/custom-emoji routes with schema5 errors.
World-only v5 support does not imply HTTP/native negotiation is implemented.

The Android adapter maps canonical `D` to native `-D` at reserved DC-1, preserving positive emoji
IDs and original document carriers, filenames, destinations, cancellation, progress, cache lookup
and notifications. Follow [the sentinel and destination requirements](documents-references.md#native-document-identity-and-destination-requirements).
Install immutable document dependencies before decoding their messages; reject changed metadata
under an existing ID. Never fall through to a Telegram DC for an unknown reserved ID. Actual native
codec, original row/caption/keyboard rendering, download, cache and restart need separate evidence.

## HTTP batch and remaining behavior

`sendDocument` will adapt multipart bytes/decoded filename metadata to the World method and return
an ordinary Message with `document`, caption/entities and reply markup. Same-bot file-ID reuse and
`getFile`/authenticated download use the typed identity. HTTP URL media, host paths, thumbnails,
unsupported options and cross-kind IDs fail explicitly. Preserve image admission and envelopes.
Increase request admission only for the new document method; do not silently widen existing photo
limits. Keep text/header/part-count bounds and reject duplicate/extra attachments before publication.

The first HTTP slice can establish explicit forced-file uploads
(`disable_content_type_detection=true`) and typed file-ID reuse. Default/false uploads require a
separate documented detector/conformance policy because Telegram's remote classifier is not in
the inspected source. Until that is settled and implemented, return an explicit unsupported error
for that upload mode; do not silently treat it as true or call ordinary sendDocument compatibility
complete. Direct World calls deliberately create typed ordinary documents and are not a detector.

Document/photo albums, complete-group native application, document edits, default classification
and the cloud-size boundary remain required subsequent acceptance. The full operational milestone
must not be reduced to this first forced-file upload slice.
