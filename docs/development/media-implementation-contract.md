# Shared media implementation contract

Status: frozen for the first implementation batch under the user's four approved designs and
[ADR 0005](../adr/0005-local-media-and-client-interaction-boundaries.md). This is an implementation
contract, not completed compatibility evidence. PNG and JPEG are both in this batch; albums,
general files, custom emoji, mentions and public rich input remain required subsequent work.

## World and Bot API

Store validated immutable image bytes and metadata in the owning World's SQLite database. This
uses the existing transaction to publish assets, bot file identities, recipient grants and the
message together, without orphan public files after rollback. Deduplicate bytes within one World;
allocate a positive signed 64-bit `asset_id` for each distinct image. Never use a global registry.
Identifiers are independent of client TL types and carry no authorization.

Add optional `uploads: Mapping[str, bytes] | None` to World rich send/edit operations. Resolve
`attach://NAME` against that operation's upload map, or a reusable bot-scoped `file_id` against
that sender's persisted file identities. Reject external URLs, host paths, unknown/cross-bot IDs,
duplicate attachments and invalid media without advancing message/event/asset identifiers. Add
`World.send_photo(chat_id=..., sender_id=..., photo=..., uploads=..., caption=...,
caption_entities=..., reply_markup=...)` and standard `sendPhoto`/`getFile` HTTP methods. The normal
photo input uses the same attachment/reuse resolver as rich photos. Sender must be the chat bot
in this first upload profile. World methods remain usable for independently authored tests.

A stored rich photo block is `{"type":"photo","asset_id":1}` plus optional normalized rich
`caption`. Public input remains `{"type":"photo","photo":{"type":"photo","media":"attach://asset"}}`;
public output remains `{"type":"photo","photo":[PhotoSize,...]}`. One full-size PhotoSize has
`file_id`, `file_unique_id`, `width`, `height`, and `file_size`. Its file identity belongs to the
sending bot. Retain captions through normal recursive rich validation. Source-ignored nested
ordinary captions do not replace the rich block caption. Unsupported spoiler/thumbnail and other
media options must fail explicitly under the recorded first profile. Do not project empty images
or replace a photo with a divider.

Normal World photo messages retain the existing message identity/date/chat/sender fields and
`text: ""`, with `photo: {"asset_id":1}` and optional `caption`/`caption_entities`/reply markup.
The HTTP Message has `photo: [PhotoSize]` and optional caption fields, with no `text`. Normal
captions are at most 1,024 Unicode code points; use existing admitted ordinary entity validation.
HTML parse modes remain explicitly unsupported. Photo identity is immutable across resends and
edits; a different bot can acquire its own identity only through an authorized upload/catalog
operation, never by presenting another bot's file ID.

`getFile(file_id=...)` returns `file_id`, `file_unique_id`, `file_size` and a local relative
`file_path`. The path is generated from the stored identity and detected format, never a supplied
filename. `GET /file/bot<TOKEN>/<file_path>` authenticates and verifies bot ownership before serving
bytes. A unique ID or guessed path does not grant access. Preserve existing Bot API JSON/form
behavior and error envelopes. Never log capability-bearing paths.

## Decoder and request limits

Pin Pillow 12.3.0 in the Python lock and the runtime's existing nixpkgs input. Open only PNG/JPEG,
verify container structure, reopen and fully decode, reject multi-frame images and malformed or
truncated input, and preserve the validated source bytes. Detect format from bytes rather than
filename/MIME. Check dimensions before full decoding: positive dimensions, width+height <=10,000,
aspect ratio <=20, and at most 25,000,000 pixels. Each image is at most 10,000,000 bytes. These
bounds and one preserved full-size representation are the explicit offline photo profile, not a
claim of Telegram server recompression or thumbnail generation.

Multipart requests have one Content-Length, no Transfer-Encoding, at most 64 parts, at most
65,536 bytes of combined text fields and at most 20,000,000 bytes of uploaded file data, with a
bounded envelope allowance. Reject malformed boundaries/headers, nested multipart, repeated names,
missing/short bodies and duplicate query/body fields before publication. Parse multipart as
bytes; boundary-like bytes inside a file must not be split unless they form a MIME delimiter.
Ignore filenames as filesystem paths and exercise Unicode/path-like names as data. JSON/form
requests retain the existing 65,536-byte body bound. Validation failures expose no public upload.

## Shared bridge version 3

Version 3 coordinates media, later identity dependencies and rich-target message revisions:

- `GET /v3/snapshot` keeps all v2 fields, sets `schema:3`, and adds `assets` and
  `message_revisions`. `users` remains the authoritative visible identity list.
- `GET /v3/changes?after=N&limit=L` keeps v2 pagination/cursor semantics, sets `schema:3`, and adds
  `users` and `assets` dependency lists. Each returned message change also has `revision`, the
  corresponding global message creation/edit event sequence. These are distinct from persona
  change `position` values.
- Each snapshot revision entry is `{"chat_id":1,"message_id":2,"revision":7}`. Sort entries in
  snapshot message order. Same-clock A → B → A edits have different revisions; no-op edits do not.
- Each asset descriptor is exactly `{"asset_id":1,"mime_type":"image/png","file_size":123,
  "sha256":"<64 lowercase hex>","width":16,"height":16}`. JPEG uses `image/jpeg`. Sort and
  deduplicate descriptors by asset ID. No host path, file capability or client-derived fields cross
  this boundary. The client maps one photo ID to this positive asset ID and uses size ordinal 1.
- Snapshot asset dependencies cover every asset granted to the persona, including assets removed
  by later edits. This preserves old-asset retry after cold restart. Snapshot revisions cover only
  current messages. Change dependencies cover the exact returned message versions, including old
  photos after later edits; the native registry retains prior granted mappings. Resolve each
  response under one SQLite read snapshot. Apply dependencies before native messages.
- v1/v2 responses remain unchanged for supported content. If the selected snapshot/event/change
  response would contain media or later v3-only content, reject explicitly without advancing its
  cursor or returning a silently incomplete message. Native v3 negotiation is explicit; no fallback
  discards media. v1 callbacks remain available for legacy content and reject media before any
  mutation. The v2 composer retains its shape because it returns its newly sent ordinary text.

`POST /v3/callbacks` and `GET /v3/callbacks/<id>` retain the established callback command,
idempotency and authorization rules. Their response has exactly `schema:3`, `world_id`, `user_id`,
`callback`, `users`, `assets`, and `message_revision`. The callback has its existing fields with
the canonical neutral message. Dependencies describe that captured message version;
`message_revision` is its creation/edit event sequence when the callback was first created, never
a later edit or callback event sequence. Preserve it across idempotent retries and restart. The
native v3 client uses these callback routes and installs dependencies before decoding the message.
Every `/v3/*` JSON error uses schema 3, including authentication and binary-transfer failures.

`GET /v3/assets/<asset_id>` uses the existing client Bearer capability and loopback-only bridge.
Authorize the persona grant before reading bytes. Successful responses have detected Content-Type,
exact Content-Length, Cache-Control:no-store and Connection:close, with raw bytes and no redirect.
Unknown/ungranted IDs return the same HTTP404 v3 error envelope with code `asset_unavailable` and
message `Asset is unavailable`; missing/invalid capabilities return401 before asset disclosure.
Query parameters, Range and unsupported transfer encodings reject explicitly for this first
complete-file operation. No endpoint URL is supplied by a message or asset descriptor.

Publishing a photo grants the recipient access transactionally; receiving a snapshot is not the
permission event. Keep grants to old assets after edits for this World lifetime. Reset/deletion
ends the run and removes its database and dedicated native cache. A previous grant cannot be
reconstructed merely by knowing an asset ID in another World.

## Original Android loader

Map asset IDs to original Photo IDs and locations in the GPL adapter. Set synthetic DC ID 0,
positive photo/volume ID equal to asset ID, and stable size local ID 1. Register the World-bound
mapping when applying dependencies. Empty access hash/file reference are synthetic metadata, not
credentials. Cache ownership is one World lifetime; preserve existing cache keys across same-World
restart and distinct keys for old/new photo edits.

Intercept synthetic `ImageLocation` loads in `FileLoader.loadFile` before any normal
`FileLoadOperation` or DC queue is created. A reserved synthetic location without a mapping fails
locally. Use the existing validated loopback endpoint, NO_PROXY, no redirects and bounded timeouts.
Stream to a separate temporary file under the original selected cache directory, validate expected
length and SHA-256, then atomically publish its original cache filename. Original ImageReceiver,
rich layout, decoding and binding remain in control.

Rejoin the original loader delegate's progress/completion/failure notifications. Never pass an
unchecked null FileLoadOperation into an original callback that dereferences it. Keep changes to
ImageLoader limited to the necessary synthetic-progress branch. Coalesce duplicate filename loads,
register pending work before execution, cancel/close/delete partial work through the original
filename-based cancellation path, and emit exactly one terminal callback. An old asset completing
after an edit must not overwrite the current binding. Failure permits an explicit original retry;
tests must not hide a failure by retrying the scenario.

## Acceptance ownership

The core worker proves World atomicity/migration, HTTP uploads/reuse/downloads, caption semantics,
access isolation and v3 replay/version rejection. The GPL worker owns mapping, loading, progress,
cancellation and cache lifecycle. The independent scenario worker authors a real multipart bot
and complete semantic expectations; the coordinator owns source preparation/APKs, native guests,
original visual inspection, merges/conflicts and the combined gate. All runs use the existing
outer network guard and shared build/guest locks. Source/data/UI proof remain separate claims.
