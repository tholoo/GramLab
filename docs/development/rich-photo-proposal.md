# Proposed first rich-photo milestone

Approval covers the recommended decisions below. References to future consultation describe the
original proposal stage; do not request this approval again. Further consequential changes outside
these decisions still require consultation. Mini Apps remain deferred, and runtime Internet/DC
access and artifact publication remain excluded.

Status: approved by the user on 2026-09-07; implementation and acceptance remain incomplete.

Add real multipart photo uploads to the existing Bot API surface, keep immutable media in the
World, and satisfy original Android file-loading requests through authenticated local delivery.
The first acceptance should show a real bot sending, reusing and editing a photo rich block, with
original rendering, cold restart and missing/interrupted-download evidence. This continues the
approved Android/shared-world direction; it does not replace the renderer or pre-fill a cache as
proof of on-demand behavior.

The [pinned source findings](rich-photo-references.md) establish the public input/output shapes
and the original photo-loading path. The repository currently lacks an asset store, multipart
handling, public media identifiers and a file delivery adapter. Those new boundaries are why this
proposal needs consultation under [AGENTS.md](../../AGENTS.md).

## Recommended decisions

| Boundary | Proposed choice | Reason and consequence |
| --- | --- | --- |
| Bot input | Standard multipart `attach://` uploads to `sendRichMessage`, plus reuse through returned bot-scoped `file_id` | Real bots use their normal Bot API file shape; no private fixture-registration API becomes the only path |
| World storage | Immutable validated bytes under the owning World, with persisted metadata and atomic publication | Edits and bot/client restarts retain media; no process-global or machine-specific asset registry |
| Identity | Opaque persisted `file_id` scoped to bot and World; stable content-derived `file_unique_id` used only as identity | Reuse works for its bot; another bot/World or a unique ID cannot authorize reads/resends |
| Bot download | Standard `getFile` metadata and authenticated local Bot API file download | Send, reuse and download share the same validated bytes and ownership checks |
| Client download | Versioned bridge asset metadata and an authenticated, persona-scoped byte operation | Publishing a photo to a persona grants that persona asset access for the World lifetime, with expected byte length and digest |
| Native integration | A GPL adapter at original `FileLoader` request/completion handling for mapped synthetic photo locations | Preserve original `RichPhotoBlock`, `ImageReceiver`, decoding, cache naming, progress and failure presentation |
| Missing/partial data | Explicit failure; validate length/digest before atomically publishing a complete cache file | No partial file is presented as a valid image, and no missing asset falls back to a DC or external URL |
| Lifetime | Keep published assets for the World lifetime in this first increment; delete only with owned World cleanup | Avoid premature deletion across edits/recovery; fine-grained garbage collection remains later work |
| Access after edit | Preserve the original persona grant until World reset/deletion; changing message content does not revoke it | In-flight downloads and restart retries can finish consistently; another persona never gains access merely by knowing an ID |

Create each persona grant atomically when a message containing the asset is published to that
persona's conversation. It does not depend on whether the client happened to download or snapshot
the message first. A photo-to-photo edit grants access to the new asset and retains access to the
old one. An old in-flight download may complete into its own cache entry, but its completion must
not replace the newly bound image in the edited message. Reset/deletion terminates the run and
removes its grants and assets together. Permission revocation for future group/membership features
needs its own contract; this first milestone covers the current private-chat model.

Use ordinary Bot API photo-block syntax, for example:

```json
{"type":"photo","photo":{"type":"photo","media":"attach://asset"}}
```

The multipart part `asset` contains the original local image. The response has canonical
`photo: [PhotoSize, ...]` content with actual dimensions, byte counts and reusable public file
identities. Original filenames are neither identifiers nor trusted filesystem paths. Reject
remote HTTP URLs, host file paths and unresolved attachment references explicitly in offline mode.

An authenticated asset operation is a new local transport surface. It must retain independent
OS isolation, validate identity/authorization before reading bytes, deny redirects and external
endpoints, and prevent native fallback before initiating any network operation. A known digest
or file identifier is never a capability. Keep MIT storage/API logic independent of GPL native
objects, cache details and lifecycle callbacks.

## First acceptance profile

Begin with decoded static PNG uploads and one full-size representation. Preserve the validated
source bytes and report that explicit offline profile; do not claim Telegram server recompression,
a full generated thumbnail ladder, arbitrary image formats or all production upload behavior.
Use a pinned, reviewed image decoder with byte/pixel limits and malformed/truncated-image checks.
The existing original square/wide/tall fixtures are ready; their independent browser decoding is
fixture evidence only. Supporting additional formats and server image transformations remains in
the full media inventory after the first real delivery loop.

Include reuse, photo-to-photo edit, mixed-language rich block captions using the existing admitted
text subset, and cold restart in this first milestone. Reject unsupported spoiler/thumbnail/media
options explicitly until their behavior is implemented. A later photo-spoiler increment must
preserve the original reveal behavior; silent omission is not acceptable.

Acceptance must establish:

- Complete multipart request/response, canonical photo metadata, file reuse/download, persistence,
  migration and World/client state comparisons using independently authored expectations.
- Missing/duplicate attachments, invalid bytes, dimension/size boundaries, unknown IDs and
  cross-bot/World/persona rejection before publication or message mutation. Upload temporary files
  must not survive failed requests as public assets.
- On-demand original rendering with an initially empty dedicated cache, visible aspect/orientation,
  byte-for-byte delivery and correct photo-to-photo edit/restart behavior. Explicitly test an old
  asset completing after edit, old-asset retry after restart, denial for an ungranted persona and
  reset/deletion invalidation. No image is substituted
  into a screenshot, special widget or patched renderer.
- Missing and interrupted local delivery through the original failure/loading surface, no readable
  partial cache object, and explicit recovery through the original action or a documented scenario
  operation. Establish cancellation/retry behavior from source and actual observations before
  claiming it, without hiding failures through automatic test retries.
- Account-free guests, independent IPv4/IPv6/DNS/redirect denial for the new delivery path, scoped
  filesystem access, actual source/patch provenance and original PNG/XML/HTML evidence.
- Matching simulation and Android World/API semantics; simulation does not claim rendering,
  clipboard, client cache or animation behavior.

## Parallel implementation after approval

Freeze the versioned semantic asset descriptor, file identity scope, upload error contract and
native completion/cancellation seam together before dispatch. These are shared interfaces, so
workers must not invent competing shapes. Keep current APIs compatible or reject unsupported
older-version media explicitly; do not silently change a versioned snapshot contract.

1. A Python worker owns immutable asset storage, identity/reuse rules, migrations, bounded multipart
   admission, Bot API file operations and World/HTTP behavioral tests.
2. A GPL worker owns native photo/size/location projection and authenticated original file-loader
   delivery, with codec and failure probes. It consumes the frozen independent asset descriptor.
3. A scenario worker owns the real multipart bot, independently specified complete oracles,
   multilingual captions, simulation/native fixtures and report inputs. The coordinator owns APKs,
   guests, source/fidelity review, merges, conflicts and combined acceptance.

The generated assets and source research are already independent completed preparation. This
proposal does not declare media, custom emoji, video/audio, albums, Mini Apps, interactive mode or
the full project complete. No artifact publication, external runtime access or real account/DC use
is included. Approval would authorize this bounded implementation direction; exact private helper
names and routine implementation details remain coordinator decisions within it.
