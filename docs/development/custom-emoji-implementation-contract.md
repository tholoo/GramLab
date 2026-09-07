# Custom emoji implementation contract

The [approved catalog proposal](custom-emoji-proposal.md) and
[ADR 0005](../adr/0005-local-media-and-client-interaction-boundaries.md) govern this work.
The document, media and resolver interfaces below are frozen for parallel implementation.
Registration/API/entity integration follows on the same interfaces; implementation and original
Android playback remain unverified. Mini Apps and general files remain in the full objective.

## Immutable catalog and media values

A catalog entry has exactly this neutral descriptor (all fields required):

```json
{
  "custom_emoji_id": "9223372036854775807",
  "fallback": "🙂",
  "free": true,
  "needs_repainting": false,
  "main_asset_id": 1,
  "thumbnail_asset_id": 2,
  "duration_ms": 1000
}
```

Logical IDs are positive signed 64-bit integers represented as canonical decimal strings at
neutral/public output boundaries. Asset IDs remain positive integers in their independent
World-local namespace. No floating-point conversion, narrowing, hashing or substitution connects
the two identities. The existing shared asset descriptor retains exactly `asset_id`, `mime_type`,
`file_size`, `sha256`, `width`, `height`; v4 additionally permits `image/webp` and `video/webm`.
Static main media has duration zero; WebM has a validated positive integer millisecond duration.
Main/thumbnail references may identify the same deduplicated bytes when both validations permit it.
Descriptors contain no paths, executable settings, capabilities or client TL fields.

`World.register_custom_emoji(*, request_id, main, thumbnail, fallback, custom_emoji_id=None,
free=True, needs_repainting=False)` accepts bytes and returns the descriptor. The request ID uses
the established 1–128 ASCII identifier rule. Selected IDs accept a positive integer or canonical
decimal string; booleans, signs, whitespace, leading zeroes and values above signed 64-bit reject.
Presentation flags are strict booleans. Catalog fallback is nonempty valid Unicode text, at most
64 UTF-16 units; it is metadata, not a replacement for covered message text or rich alternative text.

An atomic schema-6-to-7 migration adds catalog, registration, document grants and a separate
allocation counter. Choosing the maximum logical ID must not exhaust subsequent automatic
allocation; skip occupied IDs using the separate counter. Canonical registration binds the decoded
main/thumbnail digests, validated metadata, normalized ID and whether the caller supplied it.
Equivalent retries return the same descriptor. Conflicting key/body or ID/body bindings reject
without advancing identifiers or publishing assets. Identical content at a chosen existing ID may
bind another request key to that entry. Registration emits no new message event type and grants no
persona access. Reopen preserves entries, requests, counters and grants. Keep `World.snapshot()`'s
existing report shape; use dedicated catalog methods for registration/lookup evidence.

Publication admits any known catalog ID in the same World, regardless of sender bot or persona.
It atomically grants the recipient that document and both assets. Retain grants after edits until
World deletion. Unknown references reject the whole send/edit before publication, including an
earlier photo allocation in the same transaction. Scan ordinary entities, captions, recursive rich
text and rich button labels. No catalog ownership, production entitlement or real sticker set is
invented.

## Media validation interface

`gramlab._emoji_media.validate_custom_emoji(main: bytes, thumbnail: bytes) -> EmojiMedia` returns
an immutable value with `main: ImageAsset`, `thumbnail: ImageAsset`, `duration_ms: int`. Reuse the
existing immutable media value shape; do not widen the PNG/JPEG photo validator. Both inputs are
detected from their bytes, fully decoded, and retained unchanged with their SHA-256 digests.

Static main is single-frame WebP, exactly 100×100 pixels and at most 512 KiB. Thumbnail is
single-frame WebP with each dimension from 1 through 100 and at most 128 KiB. Pillow validates
container structure and full decoding, with dimensions checked before allocating decoded pixels.
Reject truncated files, animation in WebP and mislabeled/unsupported formats. Transparency is
preserved; opaque valid inputs need not be rejected.

Animated main is WebM containing exactly one VP9 video stream, no audio/other streams, 100×100
pixels, positive duration at most three seconds, at most 30 frames/second and at most 256 KiB.
Inspect frame timestamps and decode the complete stream, rather than trusting header duration or
allowing a valid prefix to hide later corruption. At most 90 frames are admitted. Preserve alpha
through the libvpx VP9 decoder. Timestamp/frame-duration handling must yield the exact one-second
duration of the four-frame original fixture. Reject malformed, truncated, overlong, oversized,
wrong-codec, audio-bearing or inconsistent streams. The size limits are the explicit local
validation profile; the main geometry/video constraints follow the official
[media requirements](https://core.telegram.org/stickers) and
[VP9 guidance](https://core.telegram.org/stickers/webm-vp9-encoding).

Use the already pinned FFmpeg 6.1.6 toolchain as a separate executable dependency. Only trusted
provisioning supplies absolute `GRAMLAB_FFMPEG` and `GRAMLAB_FFPROBE` paths; require both for WebM,
with no PATH search, download or decoder fallback. No executable path enters scenario parameters,
the database or public descriptors. The coordinator supplies these variables and the immutable
codec closure in Nix runtime profiles. Standalone callers may configure them before creating a
World. Missing tools fail explicitly before registration mutates state.

Decoder execution uses byte input, a forced WebM/Matroska demuxer, pipe-only protocol allowance,
one decoder thread, bounded captured output and a total ten-second validation deadline. Restrict
output before accumulating it; `capture_output=True` alone is not an output bound. Kill and reap
timed-out processes. Do not use thread-unsafe `preexec_fn` in the control server or follow media
URLs, paths, playlists or redirects. Normal runtime remains inside the established OS network
boundary. Decoder checks run against actual locally provisioned binaries and original fixtures;
mocked success or a fixture-digest allowlist is not acceptance.

## Shared bridge version 4

v1–v3 keep their supported-content shapes. A selected response containing emoji rejects explicitly
before effects/cursor advancement; frozen callbacks and client-send retries are checked using
their stored message version. v3 photo-only responses omit retained emoji-only asset descriptors
so unrelated historical catalog use does not invalidate ordinary messages. v3 asset delivery
rejects WebP/WebM rather than extending its frozen MIME contract.

v4 snapshot, changes, callbacks and assets use the existing v3 routes under `/v4/`, the same
authentication, command limits, revisions, pagination, error envelopes and atomic read rules.
Each JSON response sets `schema:4`. Snapshot/change/callback responses add exactly one field,
`custom_emoji`, a descriptor array sorted numerically by logical ID with no duplicates. Snapshot
contains every retained document and asset grant; changes and frozen callbacks contain the exact
dependencies of their selected message versions. Install assets and descriptors before messages.
Keep the granted registry for old IDs across edits. Registration and Bot API lookup do not disclose
anything to personas. Every v4 error, including binary-transfer errors, uses schema 4.

`POST /v4/custom-emoji-documents` accepts exactly
`{"custom_emoji_ids":["1","9223372036854775807"]}` with 1–200 canonical decimal strings and the
existing 16,384-byte command bound. Authenticate and authorize the whole batch before serialization.
Deduplicate and sort numerically. Success has exactly `schema:4`, `world_id`, `user_id`,
`custom_emoji` and `assets`, with both referenced assets deduplicated and sorted. Unknown,
ungranted and mixed batches all return HTTP 404 with
`{"schema":4,"error":{"code":"document_unavailable","message":"Document is unavailable"}}`.
Malformed requests use the normal 400 invalid-request envelope. No partial descriptor, per-ID
existence detail or timing-equivalence claim. Lookup does not create a grant.

Incoming `POST /v4/messages` mirrors v2's idempotent command and `send` result, sets schema 4 and
adds `users`, `assets`, `custom_emoji` and `message_revision` for its captured message. The v2 route
must continue to reject emoji before publication. Original composer behavior remains unchanged
until an explicit custom-emoji input contract is implemented; scenario-created incoming entities
are required in this batch.

## GPL projection and original loaders

Neutral ordinary/caption entities add exactly `custom_emoji_id` to their existing `type`,
`offset`, `length` fields. Rich text and rich button labels admit
`{"type":"custom_emoji","custom_emoji_id":"1","alternative_text":"🙂"}` wherever their
approved text grammar permits emoji. Preserve cleaned alternative text separately from catalog
fallback, including a differing string. Native projection keeps the original ID-based entity and
rich custom-emoji node; do not flatten it to text or render a photo block. Continue to enforce
existing recursion/size budgets and strict required fields.

The following is an adapter mapping, not a core data model. Preserve pinned original rendering,
document memory/SQLite caches, loader destinations, notifications and image/animation decoders.
An authorized neutral registry from snapshot dependencies supports cached-document resolution;
it must not preseed original Document caches or substitute an embedded Document for the original
empty-cache `messages.getCustomEmojiDocuments` lookup.

Project a canonical `TL_document`: unchanged logical ID, reserved `dc_id=-1`, access hash zero,
empty file reference, date zero, detected MIME, exact byte size, flags 1, one thumbnail and no video
thumbnails. Add `TL_documentAttributeCustomEmoji` with catalog fallback, supplied `free` and
`text_color`, and nonnull `TL_inputStickerSetEmpty`. Static uses `TL_documentAttributeImageSize`;
WebM uses modern `TL_documentAttributeVideo` with dimensions, duration in seconds, `nosound=true`,
`round_message=false`, `supports_streaming=false` and other optional fields absent. Add filename
attribute `emoji.webp` or `emoji.webm` so the original loader need not infer unknown MIME extensions.

Use `TL_photoSize_layer127` type `m` with exact thumbnail dimensions/size and explicit deprecated
location `volume_id=thumbnail_asset_id`, `local_id=2`, `dc_id=0`. That location serializes only
volume/local fields. Modern PhotoSize reconstructs negative-document locations and can collide
with main document keys; do not substitute it. Main keys are `-1_<logicalID>` and main filenames
`-1_<logicalID>.webp`/`.webm`. Thumbnail keys are `<thumbnailAssetID>_2`; honor the original loader's
chosen extension (normally `.jpg` even for the WebP thumbnail bytes). Existing photos retain
`<assetID>_1`. Verify exact round trips and the IDs 1, 1109 and signed-64-bit maximum.

Resolve main and thumbnail requests only through the authorized document/asset registry. Handle
both FileLoader Document and ImageLocation overloads with the existing authenticated transfer
engine, preserving original delegate types, destination semantics and cancellation. Reserved
document streaming must never reach a DC operation. Do not introduce another download engine.
Static original rendering requests the thumbnail; a native main-WebP GET is not mandatory.
WebM original rendering uses the main document and thumbnail. Bot downloads still cover both.

Intercept only the approved original document request and return its complete Vector on success.
On failure return a bounded non-Vector error. In the offline resolver's existing UI-thread error
branch remove only the failed batch's pending entries and clear callbacks without invoking them:
some original callbacks dereference their Document and cannot accept null. Do not synthesize an
empty Document, return partial success, clear unrelated caches or automatically retry. A fresh
explicit lookup can retry; the first guaranteed visual recovery is cold restart after access is
restored. An already cached unresolved drawable is not guaranteed to retry or paint fallback text.

These choices follow the pinned [source contract](custom-emoji-references.md) and
[resolver findings](../../.scratch/rich-messages/issues/36-custom-emoji-design-review.md).
Codec proof must include missing/extra fields, lossless IDs, flags/attributes, thumbnails and
serialization/cache keys. Native acceptance separately proves empty-cache lookup, transparent WebP,
changing transparent WebM frames, edit/stale completion, cache reuse, cold restart and bounded
failed/mixed lookup with no partial metadata/storage/asset requests. Each guest/cache is tied to one
World lifetime. Recreate it before a different World with equal numeric IDs.
