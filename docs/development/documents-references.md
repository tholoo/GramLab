# Ordinary document source contract

Reviewed 2026-09-08 against Bot API server
`2efabc722e9493b9cac450233198d09e5cea0573` (Bot API 10.3), its TDLib submodule
`bc9c263e2bfee06aaab41e82db51a103376030bc`, and Telegram Android
`62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c`. This is source research and a set of
requirements and implementation guidance under the already approved
[ADR 0005](../adr/0005-local-media-and-client-interaction-boundaries.md). It is not implementation
or live-service evidence; no server, bot, account, Telegram DC, Android build, or guest was used.

## Public Bot API contract

`sendDocument` sends one general file and returns the resulting `Message`. Its required media
parameter accepts a multipart upload, a reusable `file_id`, or an HTTP URL. An ordinary document
caption is 0–1,024 characters after entity parsing, can instead carry explicit
`caption_entities`, and can carry a reply keyboard or inline keyboard through `reply_markup`.
`disable_content_type_detection` applies only to multipart uploads. The published cloud-service
limit is 50 MB for an uploaded general file
([current method documentation](https://core.telegram.org/bots/api#senddocument)). The moving
documentation also says URL sends are limited to 20 MB and currently guaranteed only for PDF and
ZIP, while sends by `file_id` have no upload limit
([file modes](https://core.telegram.org/bots/api#sending-files)). GramLab's offline profile already
rejects HTTP media sources and host paths; supporting them would be a separate network and fidelity
decision, not part of ordinary local document support.

The pinned server makes the same request distinction. It obtains `document`, rejects its absence,
loads an optional upload-only thumbnail, parses the normal caption, and passes the detection flag
to TDLib's `inputDocument`
([send entry point](https://github.com/tdlib/telegram-bot-api/blob/2efabc722e9493b9cac450233198d09e5cea0573/telegram-bot-api/Client.cpp#L14057-L14070)).
`attach://NAME` resolves the multipart part named `NAME`; otherwise a string becomes a remote file
identity or URL. Multipart parts reach TDLib through their temporary local file path
([input-file resolution](https://github.com/tdlib/telegram-bot-api/blob/2efabc722e9493b9cac450233198d09e5cea0573/telegram-bot-api/Client.cpp#L10778-L10801)).
The `Client.cpp` layer alone does not show filename/MIME handling, but the pinned TDLib path below
does. Only Telegram-server behavior after `force_file=false` remains outside the public source.

The returned `Message.document` is a `Document`, not a photo-size array. It contains required
`file_id` and `file_unique_id`, plus optional `thumbnail`, `file_name`, `mime_type`, and
`file_size`; `file_size` may exceed 32 bits. The unique ID cannot download or resend the file
([Document](https://core.telegram.org/bots/api#document)). The pinned serializer omits empty
filename and MIME strings, then emits the optional thumbnail and common file identity/size fields
([projection](https://github.com/tdlib/telegram-bot-api/blob/2efabc722e9493b9cac450233198d09e5cea0573/telegram-bot-api/Client.cpp#L2265-L2279)).
The containing message projects the document and caption together, caption entities through the
shared caption serializer, and the keyboard through the ordinary message `reply_markup`
([document message](https://github.com/tdlib/telegram-bot-api/blob/2efabc722e9493b9cac450233198d09e5cea0573/telegram-bot-api/Client.cpp#L4875-L4879),
[caption](https://github.com/tdlib/telegram-bot-api/blob/2efabc722e9493b9cac450233198d09e5cea0573/telegram-bot-api/Client.cpp#L1531-L1545),
[keyboard](https://github.com/tdlib/telegram-bot-api/blob/2efabc722e9493b9cac450233198d09e5cea0573/telegram-bot-api/Client.cpp#L5378-L5380)).

Bot-scoped reuse and download have the same authority split as photos. `file_id` can resend or be
passed to `getFile`; `file_unique_id` is comparison metadata only. Public documentation explicitly
says a `file_id` is bot-specific and a file can have more than one valid ID even for the same bot
([file-ID rules](https://core.telegram.org/bots/api#sending-files)). GramLab can therefore reuse its
existing opaque, bot-scoped `bot_files` identities, stable content-derived unique IDs,
`getFile`, and authenticated bot-file delivery without treating a filename,
MIME type, unique ID, or guessed path as authority.

## Required compatibility behavior

The operational document implementation must support general files rather than a MIME allowlist.
For `sendDocument`, that means multipart upload, same-bot `file_id` reuse, Bot API `Message.document`
projection, caption/entities, reply markup, `getFile`, and authenticated byte download. Multipart
uploads default to Telegram's automatic content-type detection; setting
`disable_content_type_detection=true` disables it. A no-sniff implementation therefore covers only
the explicit `true` case and cannot be presented as normal `sendDocument` compatibility. HTTP URL
input remains outside the approved offline network boundary, but must reject explicitly rather than
be confused with a reusable ID or local path.

The public cloud upload ceiling is 50 MB. A lower GramLab ceiling may be useful while plumbing is
proved, but it is an explicit local deviation and cannot close the operational general-file
milestone. The local Bot API server's separately documented 2,000 MB upload mode is also outside
the current in-database design; neither limit changes the requirement that accepted file sizes and
64-bit output fields be handled without integer truncation.

Files with ordinary MIME types, extensions, or contents must remain ordinary documents. Telegram
may classify some uploaded content as another media type when detection is enabled. The inspected
client/server adapter contains no detector to reproduce: it sends `force_file=false` and Telegram's
server chooses the returned media attributes. That specialized-classification edge remains a
conformance gap. It must not cause GramLab to apply the photo PNG/JPEG decoder, invent dimensions,
or manufacture specialized Android document attributes for ordinary files.

## Filename, MIME type, size, empty files, and thumbnails

A multipart document has three distinct values: bytes, the `filename` parameter in
`Content-Disposition`, and the part `Content-Type`. GramLab now preserves those values in an
immutable upload record through HTTP dispatch, including empty filenames and missing versus empty
Content-Type. Existing photo operations still consume the exact byte payload. This preparatory
change does not implement the document-specific decoding, filename cleaning or MIME projection
below; it preserves the metadata needed to do so.

The pinned TDLib HTTP parser supplies more metadata than the Bot API adapter ultimately uses. It
defaults a missing part content type to `application/octet-stream`, URL-decodes disposition values,
and treats the presence of a `filename` parameter as a file even when its value is empty
([multipart headers](https://github.com/tdlib/td/blob/bc9c263e2bfee06aaab41e82db51a103376030bc/tdnet/td/net/HttpReader.cpp#L296-L423)).
It records the original decoded name, declared/default content type, byte size, and temporary path
in `HttpFile`
([record](https://github.com/tdlib/td/blob/bc9c263e2bfee06aaab41e82db51a103376030bc/tdnet/td/net/HttpFile.h#L14-L28)),
but creates that temporary path from a cleaned filename and falls back to the literal basename
`file` when cleaning produces an empty name
([temporary file](https://github.com/tdlib/td/blob/bc9c263e2bfee06aaab41e82db51a103376030bc/tdnet/td/net/HttpReader.cpp#L472-L504),
[name and write rules](https://github.com/tdlib/td/blob/bc9c263e2bfee06aaab41e82db51a103376030bc/tdnet/td/net/HttpReader.cpp#L786-L850)).

The Bot API adapter passes only `HttpFile.temp_file_name` to TDLib as `inputFileLocal`; it does not
pass `HttpFile.name` or `HttpFile.content_type`. TDLib then takes the temporary path's basename as
`file_name` and derives MIME solely from its extension
([local metadata](https://github.com/tdlib/td/blob/bc9c263e2bfee06aaab41e82db51a103376030bc/td/telegram/MessageContent.cpp#L4771-L4786)).
`MimeType::from_extension` returns an empty string for a missing or unknown extension, rather than
defaulting to `application/octet-stream`
([helper](https://github.com/tdlib/td/blob/bc9c263e2bfee06aaab41e82db51a103376030bc/tdutils/td/utils/MimeType.cpp#L16-L41),
[defaults](https://github.com/tdlib/td/blob/bc9c263e2bfee06aaab41e82db51a103376030bc/tdutils/td/utils/MimeType.h#L14-L18)).
The generated pinned mapping includes `bin` to `application/octet-stream`, `pdf` to
`application/pdf`, and `txt`/`text` to `text/plain`
([mapping](https://github.com/tdlib/td/blob/bc9c263e2bfee06aaab41e82db51a103376030bc/tdutils/generate/mime_types.txt#L51-L59),
[plain text](https://github.com/tdlib/td/blob/bc9c263e2bfee06aaab41e82db51a103376030bc/tdutils/generate/mime_types.txt#L709)).
Therefore multipart `Content-Type` has no semantic precedence in this pinned upload route, for
either value of `disable_content_type_detection`.

The upload sanitizer requires valid UTF-8, keeps only the path basename, limits the stem to 64 and
the extension to 16 emitted Unicode characters, skips characters whose search normalization is
empty and replaces other disallowed characters with spaces, then trims leading or trailing spaces
and dots
([exact algorithm](https://github.com/tdlib/td/blob/bc9c263e2bfee06aaab41e82db51a103376030bc/tdutils/td/utils/filesystem.cpp#L102-L175)).
This filename is untrusted presentation metadata, not a host path or storage name. The pinned
Android client separately reads `documentAttributeFilename`, removes control characters and
characters such as `/`, `\\`, `:`, `?`, and `*`, and uses the remaining extension when creating
the cache filename
([filename extraction and sanitization](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/messenger/FileLoader.java#L1450-L1482),
[cache key](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/messenger/FileLoader.java#L1524-L1555)).
The request flag maps exactly: `true` selects TDLib `DocumentAsFile`; false or omitted selects
`Document`
([selection](https://github.com/tdlib/td/blob/bc9c263e2bfee06aaab41e82db51a103376030bc/td/telegram/MessageContent.cpp#L5202-L5212)).
The upload emits the cleaned filename attribute when nonempty, the extension-derived MIME string,
and Telegram API `force_file=true` only for `DocumentAsFile`
([outbound media](https://github.com/tdlib/td/blob/bc9c263e2bfee06aaab41e82db51a103376030bc/td/telegram/DocumentsManager.cpp#L689-L721)).
No byte sniffer runs in this local route. With `force_file=false`, the inaccessible Telegram server
can return specialized attributes; TDLib classifies those returned attributes as animation, audio,
video, voice, sticker/custom emoji, or a general document
([returned classification](https://github.com/tdlib/td/blob/bc9c263e2bfee06aaab41e82db51a103376030bc/td/telegram/DocumentsManager.cpp#L96-L284)).
The exact server detector and any server rewrite of filename/MIME remain unknowable from these
public sources.

Zero-byte admission is not an open question for this pinned route. Multipart parsing can create a
zero-sized temporary file, but TDLib stats the ready local file and fails with `Can't upload empty
file` before issuing an upload request
([uploader](https://github.com/tdlib/td/blob/bc9c263e2bfee06aaab41e82db51a103376030bc/td/telegram/files/FileUploader.cpp#L187-L193)).

Implementation guidance and temporary proof boundaries:

- Extend the multipart result to retain filename presence/value and declared content type alongside
  bytes, so parsing remains inspectable. For semantic document projection, apply the pinned filename
  sanitizer and fallback, then derive MIME from the pinned extension table; do not use the declared
  part content type as authority or as a filesystem path.
- A 10,000,000-byte nonempty forced-file corpus is a useful implementation probe because it fits
  the existing asset bound. It is not the general-file contract: it exercises only
  `disable_content_type_detection=true` and is narrower than the 50 MB public cloud limit.
- Treat a present empty, invalid-UTF-8, or fully stripped filename as a file named `file`; do not
  require a nonempty admitted filename. Keep stem/extension limits and filtering exact.
- Reject zero-byte uploads before publication with no message, event, asset, identity or grant
  allocation.
- Preserve the distinction between default/false detection and forced-file `true`. Ordinary cases
  can share filename/MIME projection, but potentially specialized inputs under false need a pinned
  simulator classification table or must remain an explicit fidelity gap. Do not silently implement
  false as true.
- Reject `thumbnail` and legacy `thumb` explicitly in the first implementation. If added later,
  use a new JPEG upload only, under 200 kB and at most 320×320, and do not permit thumbnail reuse,
  matching the published method contract. Do not synthesize a thumbnail or silently ignore one.

An early `application/pdf`, `text/plain`, and `application/octet-stream` matrix can prove the
opaque-file path. Completion needs broader filenames, MIME mismatches, enabled/disabled detection,
empty/malformed files, limit boundaries, reuse/download, and specialized-content classification.

## Pinned Android projection

The original carrier must be `TL_messageMediaDocument` containing a `TL_document`. The current
constructor reads the document only when media flag 0 is set
([message media](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/tgnet/TLRPC.java#L6863-L6907)).
The document itself contains `id`, `access_hash`, `file_reference`, `date`, `mime_type`, 64-bit
`size`, `dc_id`, optional thumbnail vectors, and an attribute vector
([Document](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/tgnet/TLRPC.java#L26723-L26903)).
For a general file, the required first-profile attribute is
`TL_documentAttributeFilename{file_name}`
([attribute](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/tgnet/TLRPC.java#L1536-L1546)).
Do not add image-size, audio, video, animated, sticker, or custom-emoji attributes to an opaque
document: Android uses those attributes and selected MIME types to classify specialized media.
An ordinary `TL_message` must also carry its caption in `message`, caption entities in `entities`,
its keyboard in `reply_markup`, and the media-present flag.

With no specialized attribute, `MessageObject` classifies `TL_messageMediaDocument` as
`TYPE_FILE`; filename becomes the visible attachment label
([classification](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/messenger/MessageObject.java#L6384-L6417),
[label](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/messenger/MessageObject.java#L6243-L6262)).
`FileLoader.getPathToAttach` sends ordinary documents to `MEDIA_DIR_DOCUMENT`, consults its file
path database using document ID/DC/type, and names the file from DC ID, document ID and the
sanitized filename extension
([path selection](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/messenger/FileLoader.java#L1243-L1335)).
The original load operation builds `inputDocumentFileLocation` from ID, access hash, file reference
and DC, expects `document.size`, and derives its extension from the filename
([load location](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/messenger/FileLoadOperation.java#L380-L421)).

The existing synthetic loader can be reused in shape: fixed local DC/access/file-reference values,
an immutable ID-to-byte descriptor installed before message decoding, original filename-based
loading, length/SHA-256 validation, temporary-file cleanup, atomic publication, progress,
cancellation, retry, and original delegates. A document path must intercept original
`Document` loading rather than fabricate a photo location. Its synthetic document IDs need a
collision-free namespace across ordinary documents and existing custom-emoji documents; they must
not be guessed from a bot `file_id` or silently equated with an asset ID before that namespace is
frozen.

## Existing primitives and schema boundary

[ADR 0005](../adr/0005-local-media-and-client-interaction-boundaries.md) already approves immutable
validated media owned by one World, atomic recipient grants, separate bot file identities, lifetime
grant retention, authenticated local delivery, versioned bridge dependencies, and original
`FileLoader`. Document work extends those decisions; it does not reopen them. The current concrete
media shapes are not generic:

- `media.ImageAsset` requires width and height and `validate_image` accepts only decoded PNG/JPEG.
- SQLite `assets` requires image dimensions; `asset_descriptor` always emits them.
- v3/v4 `assets` entries are exact image descriptors with mandatory `width` and `height`.
- `_message_assets` and `photo_size` discover/project image references, while existing World photo operations
  consume `Mapping[str, bytes]`; multipart dispatch now additionally preserves filename/type metadata.

Do not widen `ImageAsset`, overload zero dimensions, add filename fields to existing exact asset
objects, or make strict clients guess descriptor kinds. The implementation may either:

1. Generalize immutable byte storage into a neutral blob record, retain image metadata in a
   separate typed record, and point both photo and document records at a blob. Existing grants and
   bot identities then migrate to typed media references.
2. Add document-specific asset, grant, and bot-file tables while reusing the same authorization and
   identity rules. This is a smaller first migration but duplicates mechanisms and makes later
   albums/cross-kind file accounting harder.

The first choice is the deeper module if its migration preserves every existing photo/custom-emoji
ID and response byte-for-byte. The second limits the first schema change but duplicates mechanisms.
This is an implementation seam within ADR 0005; verification of existing identifiers, grants and
strict descriptors is the deciding constraint.

ADR 0005 already requires a negotiated successor bridge schema. The next version can add a separate
exact `documents` dependency collection and fixed authenticated document-byte route while keeping
v4 responses exactly unchanged. A candidate descriptor is:

```json
{
  "document_id": "9001",
  "asset_id": 7,
  "file_name": "report.pdf",
  "mime_type": "application/pdf",
  "file_size": 1234,
  "sha256": "64 lowercase hexadecimal characters"
}
```

The implementation contract must specify number-versus-decimal-string ID encoding,
ordering/deduplication, allowed metadata lengths, native-ID namespace, exact route and error shape,
and whether the descriptor refers to a neutral blob or a document-specific row. Authorization and
retention continue to follow ADR 0005. Adding fields to v4 would violate its strict exact-field
contract.

## Albums are a separate contract

`sendMediaGroup` accepts 2–10 input items and returns an ordered array of sent messages. Documents
may be grouped only with documents, and an album forces content-type detection disabled for every
`InputMediaDocument`
([public method](https://core.telegram.org/bots/api#sendmediagroup),
[pinned document parsing](https://github.com/tdlib/telegram-bot-api/blob/2efabc722e9493b9cac450233198d09e5cea0573/telegram-bot-api/Client.cpp#L12849-L12854),
[pinned send path](https://github.com/tdlib/telegram-bot-api/blob/2efabc722e9493b9cac450233198d09e5cea0573/telegram-bot-api/Client.cpp#L14505-L14570)).
Each returned `Message` has its own message identity and document, plus one shared
`media_group_id` inside the chat. The proposed GramLab contract needs one atomic validation
and publication operation, one stable group identity, contiguous deterministic message ordering,
per-item captions/entities, and complete rollback of messages, events, assets, identities and
grants on any member failure. These are proposed simulator guarantees; the inspected sources do
not prove the exact server rollback/allocation algorithm. Repeating `sendDocument` cannot supply
those guarantees.

Android carries the group ID on each message. `GroupedMessages.calculate` marks groups beginning
with a document/music item as document groups and changes caption/layout behavior
([group model](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/messenger/MessageObject.java#L1174-L1303));
`ChatMessageCell` has separate branches for `currentMessagesGroup.isDocuments`
([cell layout](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/ui/Cells/ChatMessageCell.java#L10079-L10125)).
The album implementation must deliver the complete ordered group to the native grouping layer and
verify document-list layout; independent single-message rendering is insufficient. Albums remain a
separate atomic implementation slice, but they are required for the operational milestone rather
than optional follow-up compatibility.

## Decisions and independent implementation scopes

The consequential unresolved source/behavior choices are:

1. the Telegram-server detector used when `force_file=false`, including specialized media
   classification and any returned filename/MIME rewrite;
2. the supported operational upload ceiling and storage representation needed to reach it while
   retaining ADR 0005 atomicity and lifetime grants; and
3. exact album failure/rollback and group-identity allocation semantics where public documentation
   does not expose server internals.

Schema table layout, successor version number, descriptor field encoding and synthetic ID allocation
are implementation-contract choices under the approved architecture. They need explicit exact
specification and regression tests, but do not require another blanket architecture approval.

After those decisions, work can remain independent: one core/API worker for typed storage,
multipart metadata, send/reuse/download and rollback; one GPL worker for strict dependency decoding,
native `Document` projection and the original loader/cache lifecycle; and one scenario worker for
complete JSON/form/multipart, edit/restart, failure, filename/MIME and keyboard expectations.
Albums should have their own core/native/scenario batch coordinated with the single-document
storage contract so the operational requirement is completed without repeated single sends.
