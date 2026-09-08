# Local ordinary documents

GramLab's experimental Bot API now supports explicit forced-file uploads and bot-scoped file reuse.
Typed storage and authenticated version5 client HTTP delivery are integrated. Original Android
file loading is still in development; this page does not establish an operational document UI.
Run bots and clients only inside the [offline boundary](offline-safety.md).

## Sending and reusing a file

Send multipart `sendDocument` to the run's local Bot API endpoint with:

- `chat_id`: the recipient's existing private chat with this bot;
- `document`: the uploaded file part, or a text `attach://NAME` reference to its single file part;
- `disable_content_type_detection`: explicitly true for every new upload; and
- optional `caption`, `caption_entities` and `reply_markup` using the existing caption/keyboard rules.

The response is an ordinary Bot API Message containing `document`, with the bot's opaque
`file_id`, a comparison-only `file_unique_id`, byte size and nonempty filename/MIME metadata.
Retain `file_id` to send the same typed file again with JSON or a form:

```json
{"chat_id":1,"document":"BOT_SCOPED_FILE_ID","caption":"The same file again"}
```

That placeholder must be replaced with the actual ID returned to this bot. Another bot's ID,
`file_unique_id`, a photo/emoji ID, a host path or an external URL cannot authorize document reuse.
Reusing an existing typed document does not require the upload detection flag.

Call `getFile` with that `file_id`. Its response contains only the official File fields:
`file_id`, `file_unique_id`, `file_size` and `file_path`. Fetch the returned `documents/FILE_ID`
path through the same local authenticated bot-file endpoint to receive the original bytes.
The presentation filename is never a download route or a host path.

## Metadata, limits and rejection

Header filenames are decoded once, then cleaned with the pinned filename rules. The semantic MIME
comes from the cleaned filename extension; the declared multipart Content-Type does not override
it. Unknown extensions retain an empty semantic MIME. Binary HTTP delivery uses
`application/octet-stream` as its transport fallback. See the [source contract](documents-references.md)
for the pinned derivation and the distinction from Telegram's unavailable server classifier.

The local document profile accepts1 through50,000,000 bytes inclusive. The50,000,000-byte boundary
has an actual upload/download test; it is a GramLab profile value, not proof of Telegram's exact
cloud admission boundary. The existing photo and multipart text/header/part-count limits remain.
Rejected publications leave bytes, typed metadata, identities, grants, messages and events unchanged.

New uploads with omitted or false detection return
`GRAMLAB_UNSUPPORTED: document upload content detection`. Empty or oversized files, missing/unused
attachments, thumbnails, parse modes, unsupported options and invalid captions/keyboards reject.
File downloads do not support Range requests. Ordinary document edits and albums remain unsupported.

## Client delivery and verification

The [version5 contract](documents-implementation-contract.md#bridge-version-5) adds exact ordinary
document dependencies to snapshots, changes and callbacks. Authenticated `GET /v5/documents/ID`
returns granted original bytes; unknown and ungranted documents share one unavailable response.
Legacy document-bearing results reject before mutation. Image and custom-emoji dependencies retain
their separate identities and grants, including custom emoji in document captions.

The integrated HTTP checks cover complete responses, callback delivery, reuse/reopen, malformed
metadata, rejected-state preservation, exact byte limits, cross-kind/cross-persona authorization
and historical v5 dependencies. Uploading identical valid PNG bytes as a forced document and as a
photo preserves distinct typed identities and exact downloads. These checks prove the local HTTP
contract; original Android loading, rendering and recovery require the separate native gates.

The integrated real-bot document scenario additionally sends a bilingual named file with a
formatted/custom-emoji caption and callback keyboard, checks exact authenticated downloads,
rejects cross-kind/foreign-bot reuse, then sends the same file again after a callback. All three
scenario/evidence host cases pass in `artifacts/document-ui-integrated-01.xml`. Its original
Android workflow remains pending; public runner v5 selection and mixed-content interaction
coverage are tracked separately in [ticket107](../../.scratch/rich-messages/issues/107-document-runner-v5.md).
